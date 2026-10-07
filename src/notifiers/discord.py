"""Discord notification dispatcher via Webhook."""

import logging
import requests
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class DiscordNotifier(BaseNotifier):
    """Sends notifications to a Discord channel via Webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()

    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("https://"))

    def send(self, subject: str, message: str) -> bool:
        if not self.is_configured():
            logger.error("Discord notification skipped: DISCORD_WEBHOOK_URL is not configured.")
            return False

        payload = {"content": message}
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=20)
            if resp.status_code in (200, 204):
                logger.info("Discord alert sent successfully!")
                return True
            else:
                logger.error(f"Discord Webhook error {resp.status_code}: {resp.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Network error while sending Discord message: {e}")
            return False
