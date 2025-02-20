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
        report_folder: str = "",
        trivy_options: List[str] = [],
    ) -> None:
        super().__init__(
            registry_id=registry_id,
            repositories=repositories,
            allowed_tag_patterns=allowed_tag_patterns,
            report_folder=report_folder,
        )
        self._trivy_options = trivy_options

    def _trivy_output_json_filename(self, repo_name, image_tag):
        return os.path.join(
            self._report_folder,
            f"data/trivy/{os.path.basename(repo_name)}-{image_tag}.json",
        )

    def _trigger_trivy_scan(self, repo_name, image_tag):
        trivy_output_json = self._trivy_output_json_filename(repo_name, image_tag)

        # Ensure reports destination folder exists otherwise creates it
        os.makedirs(name=os.path.dirname(trivy_output_json), exist_ok=True)

        # Ensure the file does not exist before scanning
        if os.path.exists(trivy_output_json):
            os.remove(trivy_output_json)

        # Touch the file (create empty file)
        with open(trivy_output_json, "w") as f:
            pass

        try:
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
                + self._trivy_options
                + [
                    f"{self._registry_id}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}:{image_tag}",
                ]
            )
            self.__logger.info(f"Invoking Trivy scan command: {' '.join(trivy_cmd)}")
            subprocess.run(
                trivy_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error running Trivy scan: {e.stderr}")
            return {}

        # Load the JSON output from the file
        try:
            with open(trivy_output_json, "r") as f:
                scan_results = json.load(f)
                # Workaround for Backstage PubSub integration
                # to ensure the Vulnerabilities key exists
                for result in scan_results["Results"]:
                    result["Vulnerabilities"] = result.get("Vulnerabilities", [])
            return scan_results

        except Exception as e:
            print(f"Failed to parse Trivy output: {e}")
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

    def _get_trivy_scan_findings(self, images: List[Dict[Any, Any]]):
        ecr_findings = []
        for image in images:
            repo_name = image["repository"]
            image_tag = image["tag"]
            trivy_output_json = self._trivy_output_json_filename(
                repo_name=repo_name, image_tag=image_tag
            )
            self.__logger.info(f"Triggering Trivy Scan for {repo_name} {image_tag}")

            findings = self._trigger_trivy_scan(repo_name, image_tag)

            self._wait_for_trivy_scan(trivy_output_json)

            ecr_findings.append(
                {
                    "imagePath": f"{self._registry_id}.dkr.ecr.us-east-1.amazonaws.com/{repo_name}",
                    "commitHash": image_tag,
                    "trivyReport": findings,
                }
            )

        return ecr_findings

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
