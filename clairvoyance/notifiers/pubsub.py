import base64
import json
import logging
import os
from typing import Any, Dict

from google.cloud import pubsub_v1
from google.oauth2 import service_account

from clairvoyance.notifiers.notifier import Notifier


class PubSubNotifier(Notifier):
    __logger = logging.getLogger(__name__)

    def __init__(self, jira_product_squad: str, topic_arn: str) -> None:
        # Load the credentials from an environment variable
        service_account_json = base64.b64decode(
            os.getenv("GOOGLE_CREDENTIALS_BASE64")
        ).decode("utf-8")
        credentials_dict = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict
        )
        self._pubsub = pubsub_v1.PublisherClient(credentials=credentials)
        self._topic_arn = topic_arn
        self._jira_product_squad = jira_product_squad

    def __repr__(self) -> str:
        return (
            f"{str(self.__class__.__name__)} configured to notify "
            f"to PubSub topic: {self._topic_arn}"
        )

    def send(self, subject: str, message: Dict[str, Any]) -> None:
        # Append the Jira related data to the payload
        message["ProductSquad"] = self._jira_product_squad

        message_bytes = json.dumps(message, default=str).encode("utf-8")

        future = self._pubsub.publish(self._topic_arn, message_bytes)
        self.__logger.info(
            f"PubSub notification {future.result()} delivered successfully"
        )

        self.__logger.info(f"PubSub message was set to:{message_bytes}")
