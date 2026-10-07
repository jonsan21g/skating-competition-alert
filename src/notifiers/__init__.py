"""Notifier factory and registry."""

from typing import List
from .base import BaseNotifier
from .whatsapp import WhatsAppNotifier
from .telegram import TelegramNotifier
from .discord import DiscordNotifier
from .email_notifier import EmailNotifier
from .console import ConsoleNotifier
from ..config import AppConfig


def get_active_notifiers() -> List[BaseNotifier]:
    """Returns all enabled and configured notifiers."""
    enabled_keys = [k.lower() for k in AppConfig.NOTIFIERS_ENABLED]
    notifiers: List[BaseNotifier] = []

    # Console is always available if specified (or default fallback)
    if "console" in enabled_keys:
        notifiers.append(ConsoleNotifier())

    if "whatsapp" in enabled_keys:
        wa = WhatsAppNotifier(phone=AppConfig.CALLMEBOT_PHONE, api_key=AppConfig.CALLMEBOT_API_KEY)
        if wa.is_configured():
            notifiers.append(wa)

    if "telegram" in enabled_keys:
        tg = TelegramNotifier(bot_token=AppConfig.TELEGRAM_BOT_TOKEN, chat_id=AppConfig.TELEGRAM_CHAT_ID)
        if tg.is_configured():
            notifiers.append(tg)

    if "discord" in enabled_keys:
        dc = DiscordNotifier(webhook_url=AppConfig.DISCORD_WEBHOOK_URL)
        if dc.is_configured():
            notifiers.append(dc)

    if "email" in enabled_keys:
        em = EmailNotifier(
            host=AppConfig.EMAIL_SMTP_HOST,
            port=AppConfig.EMAIL_SMTP_PORT,
            user=AppConfig.EMAIL_SMTP_USER,
            password=AppConfig.EMAIL_SMTP_PASSWORD,
            to_addr=AppConfig.EMAIL_TO,
        )
        if em.is_configured():
            notifiers.append(em)

    # If no configured notifiers found, default to console
    if not notifiers:
        notifiers.append(ConsoleNotifier())

    return notifiers
