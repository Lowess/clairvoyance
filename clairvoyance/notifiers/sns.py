import logging

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

    def send(self, subject: str, message: str) -> None:
        response = self._sns.publish(
            TopicArn=self._topic_arn,
            Subject=subject,
            Message=message,
        )
        self.__logger.info(
            f"SNS notification {response['MessageId']} delivered {message}"
        )
