"""WhatsApp notification dispatcher via CallMeBot API."""

import logging
import requests
from .base import BaseNotifier

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


class WhatsAppNotifier(BaseNotifier):
    """Sends WhatsApp alerts using CallMeBot gateway."""

    def __init__(self, phone: str, api_key: str):
        self.phone = phone.strip().lstrip("+").replace(" ", "")
        self.api_key = api_key.strip()

    def is_configured(self) -> bool:
        return bool(self.phone and self.api_key)

    def send(self, subject: str, message: str) -> bool:
        if not self.is_configured():
            logger.error("WhatsApp notification skipped: CALLMEBOT_PHONE or CALLMEBOT_API_KEY is missing.")
            return False

        logger.info(f"Sending WhatsApp notification via CallMeBot to {self.phone[:4]}****...")
        params = {
            "phone": self.phone,
            "text": message,
            "apikey": self.api_key,
        }

        try:
            resp = requests.get(CALLMEBOT_URL, params=params, timeout=25)
            if resp.status_code == 200:
                logger.info("WhatsApp alert sent successfully!")
                return True
            else:
                logger.error(f"CallMeBot API returned HTTP {resp.status_code}: {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            logger.error(f"Network error while sending WhatsApp message: {e}")
            return False
