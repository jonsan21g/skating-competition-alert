"""Base interface for all notification dispatchers."""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if credentials and parameters are configured."""
        pass

    @abstractmethod
    def send(self, subject: str, message: str) -> bool:
        """
        Dispatch notification message.
        Returns True on success, False otherwise.
        """
        pass
