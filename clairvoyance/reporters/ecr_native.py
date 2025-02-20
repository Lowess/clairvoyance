import json
import logging
import os
from textwrap import dedent
from typing import Any, Dict, List

import backoff
from botocore.exceptions import ClientError

from clairvoyance.reporters.ecr import EcrReporter


class EcrScanStillInProgressException(Exception):
    """
    Custom exception class used to trigger backoff/retries
    when an ECR image scan is not complete
    """

    pass


class EcrNativeReporter(EcrReporter):
    __logger = logging.getLogger(__name__)

    @backoff.on_exception(
        backoff.constant,
        EcrScanStillInProgressException,
        jitter=None,
        interval=5,
        max_time=60,
    )
    def _get_ecr_scan_findings(self, images: List[Dict[Any, Any]]):
        ecr_findings = []
        for image in images:
            kwargs = {
                "registryId": self._registry_id,
                "repositoryName": image["repository"],
                "imageId": {
                    "imageDigest": image["digest"],
                    "imageTag": image["tag"],
                },
                "maxResults": 1000,
            }
            try:
                while True:
                    findings = self._ecr.describe_image_scan_findings(**kwargs)
                    # Only keep scan result when status is complete
                    if findings["imageScanStatus"]["status"] == "COMPLETE":
                        ecr_findings.append(findings)

                        self.__logger.info(
                            f"Scan found for {kwargs['repositoryName']}"
                            f":{kwargs['imageId']['imageTag']}"
                        )
                    else:
                        # Trigger the retry logic to wait for image scan completion
                        self.__logger.warning(
                            f"Scan found for {kwargs['repositoryName']}"
                            f":{kwargs['imageId']['imageTag']} "
                            "but ignored as scan report is still pending"
                        )
                        raise EcrScanStillInProgressException()
                    kwargs["nextToken"] = findings[
                        "nextToken"
                    ]  # raises KeyError on last page

            except ClientError:
                self.__logger.warning(
                    f"No scan found for {kwargs['repositoryName']}"
                    f":{kwargs['imageId']['imageTag']}"
                )
            except KeyError:
                pass

        return ecr_findings

    def analyze(self) -> List[Any]:
        return self._get_ecr_scan_findings(self._list_ecr_images())

    def report(self, findings: List[Any]) -> None:
        for finding in findings:
            repo_name = os.path.basename(finding["repositoryName"])
            image_tag = finding["imageId"]["imageTag"]
            scan_completed_at = finding["imageScanFindings"][
                "imageScanCompletedAt"
            ].strftime("%Y-%m-%d %H:%M:%S")

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
                f.write(json.dumps(finding, default=str))

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
