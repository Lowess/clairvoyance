from abc import ABCMeta, abstractmethod
from typing import Any, List


class Reporter(metaclass=ABCMeta):
    @abstractmethod
    def analyze(self) -> List[Any]:
        raise NotImplementedError("Subclass must implement analyze(...)")

    @abstractmethod
    def report(self, findings: List[Any]):
        raise NotImplementedError("Subclass must implement report(...)")
