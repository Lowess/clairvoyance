import json
import logging
import os
import subprocess
from textwrap import dedent
from typing import Any, Dict, List

import backoff
import boto3

from clairvoyance.reporters.ecr import EcrReporter


class TrivyScanStillInProgressException(Exception):
    """
    Custom exception class used to trigger backoff/retries
    when an ECR image scan is not complete
    """

    pass


class EcrTrivyReporter(EcrReporter):
    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        registry_id: str,
        repositories: List[str],
        allowed_tag_patterns: List[str],
        trivy_fs_scan_path: str,
        report_folder: str = "",
        trivy_image_options: List[str] = [],
        trivy_fs_options: List[str] = [],
        trivy_fs_allowlist: List[str] = [],
    ) -> None:
        super().__init__(
            registry_id=registry_id,
            repositories=repositories,
            allowed_tag_patterns=allowed_tag_patterns,
            report_folder=report_folder,
        )
        self._trivy_image_options = trivy_image_options
        self._trivy_fs_options = trivy_fs_options
        self._trivy_fs_scan_path = trivy_fs_scan_path
        self._trigger_fs_allowlist = trivy_fs_allowlist

    def _trivy_output_json_filename(self, repo_name, image_tag, scan_type="image"):
        filename_prefix = f"data/trivy/{os.path.basename(repo_name)}-{image_tag}"
        if scan_type == "image":
            return os.path.join(self._report_folder, f"{filename_prefix}.json")
        elif scan_type == "fs":
            return os.path.join(self._report_folder, f"{filename_prefix}-fs.json")
        else:
            raise ValueError("scan_type should be one of 'image' or 'fs'")

    def _trigger_trivy_image_scan(self, repo_name: str, image_tag: str) -> Dict:
        trivy_output_json = self._trivy_output_json_filename(
            repo_name, image_tag, scan_type="image"
        )

        # Ensure reports destination folder exists
        os.makedirs(os.path.dirname(trivy_output_json), exist_ok=True)

        # (Re)create empty file
        if os.path.exists(trivy_output_json):
            os.remove(trivy_output_json)
        open(trivy_output_json, "w").close()

        trivy_cmd = (
            [
                "trivy",
                "image",
                "--format",
                "json",
                "--output",
                trivy_output_json,
                "--quiet",
            ]
            + self._trivy_image_options
            + [
                f"{self._registry_id}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}:{image_tag}"
            ]
        )
        self.__logger.info(f"Invoking Trivy image scan: {' '.join(trivy_cmd)}")

        try:
            subprocess.run(trivy_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.__logger.error(f"Trivy image scan failed: {e.stderr}")
            return {}

        # load & normalize
        try:
            with open(trivy_output_json) as f:
                scan = json.load(f)
            for result in scan.get("Results", []):
                result["Vulnerabilities"] = result.get("Vulnerabilities", [])
            return scan
        except Exception as e:
            self.__logger.error(f"Failed parsing Trivy image output: {e}")
            return {}

    def _trigger_trivy_fs_scan(self, repo_name: str, image_tag: str) -> Dict:
        """
        Runs a filesystem scan (`trivy fs`) on the given path,
        including vulnerability and license checks.
        """
        trivy_output_json = self._trivy_output_json_filename(
            repo_name, image_tag, scan_type="fs"
        )
        os.makedirs(os.path.dirname(trivy_output_json), exist_ok=True)

        if os.path.exists(trivy_output_json):
            os.remove(trivy_output_json)
        open(trivy_output_json, "w").close()

        trivy_cmd = (
            [
                "trivy",
                "fs",
                "--format",
                "json",
                "--output",
                trivy_output_json,
                "--quiet",
            ]
            + self._trivy_fs_options
            + [self._trivy_fs_scan_path]
        )

        self.__logger.info(
            f"Invoking Trivy FS scan in {self._trivy_fs_scan_path}: {' '.join(trivy_cmd)}"
        )

        try:
            subprocess.run(trivy_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.__logger.error(f"Trivy FS scan failed: {e.stderr}")
            return {}

        # load & normalize
        try:
            with open(trivy_output_json) as f:
                scan = json.load(f)
            for result in scan.get("Results", []):
                result["Vulnerabilities"] = result.get("Vulnerabilities", [])
                result["Licenses"] = result.get("Licenses", [])
            return scan
        except Exception as e:
            self.__logger.error(f"Failed parsing Trivy FS output: {e}")
            return {}

    def _is_trivy_scan_complete(self, file_path):
        """
        Checks if the Trivy JSON file is fully written and contains scan results.
        """
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return bool(data)  # Ensure JSON is not empty
        except (json.JSONDecodeError, OSError):
            return False  # JSON file is incomplete or unreadable

    @backoff.on_exception(
        backoff.constant,
        TrivyScanStillInProgressException,
        jitter=None,
        interval=5,
        max_time=60,
    )
    def _wait_for_trivy_scan(self, file_path):
        """
        Waits for the Trivy scan output file to be populated.
        """
        if not self._is_trivy_scan_complete(file_path):
            raise TrivyScanStillInProgressException(
                f"Trivy scan for {file_path} is still in progress."
            )
        return True

    def _get_trivy_scan_findings(
        self, images: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        For each image: run both an FS scan and an image scan, then merge into
        a single ScanResult dict with deduped vulns/licenses per your JS logic.
        """
        scan_results = []
        for image in images:
            repo_name = image["repository"]
            image_tag = image["tag"]
            component_name = os.path.basename(repo_name)

            # 1) run image scan
            self.__logger.info(
                f"Triggering Trivy image scan for {repo_name}:{image_tag}"
            )
            image_report = self._trigger_trivy_image_scan(repo_name, image_tag)
            self._wait_for_trivy_scan(
                self._trivy_output_json_filename(
                    repo_name, image_tag, scan_type="image"
                )
            )

            # 2) run FS scan
            self.__logger.info(f"Triggering Trivy FS scan for {repo_name}:{image_tag}")
            fs_report = self._trigger_trivy_fs_scan(repo_name, image_tag)
            self._wait_for_trivy_scan(
                self._trivy_output_json_filename(repo_name, image_tag, scan_type="fs")
            )

            # 3) merge into one ScanResult
            scan_results.append(
                self._generate_scan_result(component_name, fs_report, image_report)
            )

        return scan_results

    def _generate_scan_result(
        self,
        component_name: str,
        fs_report: Dict[str, Any],
        image_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Filters by Trivy class allowlist and
        dedupes vulns/licenses, tags each by 'library' or 'os'.
        """

        result = {
            "ComponentName": component_name,
            "RawReports": {
                "Image": image_report,
                "Fs": fs_report,
            },
            "Vulnerabilities": [],
            "Licenses": [],
        }

        for report, pkg_type in ((fs_report, "library"), (image_report, "os")):
            for r in report.get("Results", []):
                if r.get("Class") not in self._trigger_fs_allowlist:
                    continue

                # add vulnerabilities
                for v in r.get("Vulnerabilities", []):
                    if not any(
                        existing["VulnerabilityCVEID"] == v["VulnerabilityID"]
                        for existing in result["Vulnerabilities"]
                    ):
                        result["Vulnerabilities"].append(
                            {
                                "VulnerabilityCVEID": v["VulnerabilityID"],
                                "PackageName": v["PkgName"],
                                "PackageType": pkg_type,
                                "InstalledVersion": v.get("InstalledVersion"),
                                "FixedVersion": v.get("FixedVersion"),
                                "Title": v.get("Title"),
                                "Description": v.get("Description"),
                                "Severity": v.get("Severity"),
                                "References": v.get("References"),
                                "Status": v.get("Status"),
                            }
                        )

                # add licenses
                for l in r.get("Licenses", []):
                    if not any(
                        existing["Name"] == l["Name"] for existing in result["Licenses"]
                    ):
                        result["Licenses"].append(
                            {
                                "Name": l["Name"],
                                "PackageName": l["PkgName"],
                                "PackageType": pkg_type,
                                "Severity": l.get("Severity"),
                                "Category": l.get("Category"),
                            }
                        )

        self.__logger.info(
            f"ScanResult for {component_name} → "
            f"{len(result['Vulnerabilities'])} vulns, "
            f"{len(result['Licenses'])} licenses"
        )
        return result

    def analyze(self) -> List[Any]:
        return self._get_trivy_scan_findings(self._list_ecr_images())

    def report(self, findings: List[Any]) -> None:
        for finding in findings:
            trivy_report = finding["trivyReport"]
            image_tag = os.path.basename(trivy_report["ArtifactName"]).split(":")[-1]
            repo_name = os.path.basename(trivy_report["ArtifactName"])
            scan_completed_at = trivy_report["CreatedAt"]

            self.__logger.info(f"Generating report for {repo_name}/{image_tag}")

            ecr_data_json = os.path.join(
                self._report_folder, f"data/ecr/{repo_name}-{image_tag}.json"
            )
            report_index_md = os.path.join(
                self._report_folder, f"content/reports/{repo_name}/_index.md"
            )
            report_image_md = os.path.join(
                self._report_folder, f"content/reports/{repo_name}/{image_tag}.md"
            )

            # Ensure reports destination folder exists otherwise creates it
            os.makedirs(name=os.path.dirname(ecr_data_json), exist_ok=True)
            os.makedirs(name=os.path.dirname(report_index_md), exist_ok=True)

            # Write ECR scan findings JSON payload in data folder
            with open(ecr_data_json, "w+") as f:
                f.write(json.dumps(trivy_report, default=str))

            # Generate Hugo Markdown index page
            with open(report_index_md, "w+") as f:
                repository_index_md = f"""
                    ---
                    title: '{repo_name}'
                    date: {scan_completed_at}
                    weight: 1
                    layout: 'repository'
                    ---
                """
                f.write(dedent(repository_index_md))

            # Generate Hugo Markdown report page
            with open(report_image_md, "w+") as f:
                report_md = f"""
                    ---
                    title: '{repo_name} {image_tag}'
                    date: {scan_completed_at}
                    weight: 1
                    scan_type: ecr
                    scan_report: {repo_name}-{image_tag}.json
                    ---
                """
                f.write(dedent(report_md))
