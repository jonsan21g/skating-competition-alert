"""Telegram notification dispatcher via official Telegram Bot API."""

import logging
import requests
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Sends notifications to a Telegram chat or channel."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, subject: str, message: str) -> bool:
        if not self.is_configured():
            logger.error("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": False,
        }

        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info("Telegram alert sent successfully!")
                return True
            else:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Network error while sending Telegram message: {e}")
            return False
