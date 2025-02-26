import json
import logging
from typing import Any, Dict

import boto3

from clairvoyance.notifiers.notifier import Notifier


class SnsNotifier(Notifier):
    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        topic_arn: str,
    ) -> None:
        self._sns = boto3.client("sns")
        self._topic_arn = topic_arn

    def __repr__(self) -> str:
        return (
            f"{str(self.__class__.__name__)} configured to notify "
            f"to SNS topic: {self._topic_arn}"
        )

    def send(self, subject: str, message: Dict[str, Any]) -> None:
        response = self._sns.publish(
            TopicArn=self._topic_arn,
            Subject=subject,
            Message=json.dumps(message, default=str),
        )
        self.__logger.info(
            f"SNS notification {response['MessageId']} delivered successfully"
        )
        self.__logger.debug(f"SNS message was set to:{message}")
