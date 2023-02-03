from abc import ABCMeta, abstractmethod


class Notifier(metaclass=ABCMeta):
    @abstractmethod
    def send(self, subject: str, message: str):
        raise NotImplementedError("Subclass must implement send(...)")
