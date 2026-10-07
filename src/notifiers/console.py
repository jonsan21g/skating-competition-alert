"""Console / Terminal notification dispatcher."""

import sys
from .base import BaseNotifier


class ConsoleNotifier(BaseNotifier):
    """Prints formatted notifications to terminal / standard output."""

    def is_configured(self) -> bool:
        return True

    def send(self, subject: str, message: str) -> bool:
        separator = "=" * 70
        sys.stdout.write(f"\n{separator}\n{subject}\n{separator}\n{message}\n{separator}\n\n")
        sys.stdout.flush()
        return True
