import json
import logging
import os
import re
from textwrap import dedent
from typing import Any, Dict, List

import backoff
import boto3
from botocore.exceptions import ClientError

from clairvoyance.reporters.reporter import Reporter


class EcrScanStillInProgressException(Exception):
    """
    Custom exception class used to trigger backoff/retries
    when an ECR image scan is not complete
    """

    pass


class EcrReporter(Reporter):
    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        registry_id: str,
        repositories: List[str],
        allowed_tag_patterns: List[str],
        report_folder: str = "",
    ) -> None:
        self._ecr = boto3.client("ecr")
        self._registry_id = registry_id
        self._repositories = repositories
        self._allowed_tag_patterns = allowed_tag_patterns
        self._report_folder = report_folder

    def __repr__(self) -> str:
        return (
            f"{str(self.__class__.__name__)} configured to search "
            f"in {len(self._repositories)} repositories "
            f"from registry {self._registry_id}. "
            f"Only images with {self._allowed_tag_patterns} tagging patterns "
            f"will be scanned."
        )

    def _is_allowed_pattern(self, image_tag) -> bool:
        """
        Returns True if an image_tag complies to allowed patterns.
        """
        for pattern in self._allowed_tag_patterns:
            if len(re.findall(rf"^{pattern}", image_tag)) > 0:
                return True

        return False

    def _list_ecr_images(self) -> List[Dict[Any, Any]]:
        ecr_images = []

        for repository in self._repositories:
            kwargs = {
                "registryId": self._registry_id,
                "repositoryName": repository,
                "maxResults": 1000,
                "filter": {"tagStatus": "TAGGED"},
            }
            try:
                while True:
                    images = self._ecr.list_images(**kwargs)
                    for image in images["imageIds"]:
                        if self._is_allowed_pattern(image["imageTag"]):
                            ecr_images.append(
                                dict(
                                    repository=repository,
                                    tag=image["imageTag"],
                                    digest=image["imageDigest"],
                                )
                            )
                    # raises KeyError on last page
                    kwargs["nextToken"] = images["nextToken"]
            except KeyError:
                pass

        return ecr_images
