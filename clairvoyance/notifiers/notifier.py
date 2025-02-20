from abc import ABCMeta, abstractmethod
from typing import Any, Dict


class Notifier(metaclass=ABCMeta):
    @abstractmethod
    def send(self, subject: str, message: Dict[str, Any]):
        raise NotImplementedError("Subclass must implement send(...)")
