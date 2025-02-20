import logging
from typing import Any, Dict

from clairvoyance.notifiers.notifier import Notifier


class StdoutNotifier(Notifier):
    __logger = logging.getLogger(__name__)

    def __repr__(self) -> str:
        return f"{str(self.__class__.__name__)} configured to notify to stdout"

    def send(self, subject: str, message: Dict[str, Any]) -> None:
        self.__logger.info(f"subject: {subject}")
        self.__logger.info(f"message: {message}")
