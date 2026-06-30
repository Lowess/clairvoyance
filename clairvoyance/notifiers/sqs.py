import json
import logging
from typing import Any, Dict

import boto3

from clairvoyance.notifiers.notifier import Notifier


class SqsNotifier(Notifier):
    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        jira_product_squad: str,
        region: str,
        account_id: str,
        queue_name: str,
    ) -> None:
        self._sqs = boto3.client("sqs", region_name=region)
        self._jira_product_squad = jira_product_squad
        self._queue_url = self._get_queue_url(queue_name, account_id)

    def __repr__(self) -> str:
        return (
            f"{str(self.__class__.__name__)} configured to notify "
            f"to SQS queue: {self._queue_url}"
        )

    def _scan_result_payload(
        self, subject: str, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "ComponentName": message.get("ComponentName", subject),
            "ProductSquad": self._jira_product_squad,
            "Vulnerabilities": message.get("Vulnerabilities", []),
            "Licenses": message.get("Licenses", []),
        }

    def _get_queue_url(self, queue_name: str, account_id: str) -> str:
        response = self._sqs.get_queue_url(
            QueueName=queue_name,
            QueueOwnerAWSAccountId=account_id,
        )
        return response["QueueUrl"]

    def send(self, subject: str, message: Dict[str, Any]) -> None:
        payload = self._scan_result_payload(subject, message)

        response = self._sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(payload, default=str),
        )

        message_id = response.get("MessageId")
        if not message_id:
            raise RuntimeError("SQS did not return a message ID")

        self.__logger.info(f"SQS notification {message_id} delivered successfully")
        self.__logger.debug(f"SQS message was set to:{payload}")
