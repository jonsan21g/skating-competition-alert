"""Notifier factory and registry."""

from typing import List
from .base import BaseNotifier
from .whatsapp import WhatsAppNotifier
from .console import ConsoleNotifier
from ..config import AppConfig


def get_active_notifiers() -> List[BaseNotifier]:
    """Returns all enabled and configured notifiers (Console and WhatsApp via CallMeBot)."""
    enabled_keys = [k.lower() for k in AppConfig.NOTIFIERS_ENABLED]
    notifiers: List[BaseNotifier] = []

    # Console is always available if specified (or default fallback)
    if "console" in enabled_keys:
        notifiers.append(ConsoleNotifier())

    if "whatsapp" in enabled_keys:
        wa = WhatsAppNotifier(
            phone=AppConfig.CALLMEBOT_PHONE,
            api_key=AppConfig.CALLMEBOT_API_KEY,
        )
        if wa.is_configured():
            notifiers.append(wa)

    # If no configured notifiers found, default to console
    if not notifiers:
        notifiers.append(ConsoleNotifier())

    return notifiers
