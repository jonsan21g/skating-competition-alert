"""Unit tests for notification dispatchers."""

import unittest
from unittest.mock import patch, MagicMock
from src.notifiers.whatsapp import WhatsAppNotifier
from src.notifiers.telegram import TelegramNotifier
from src.notifiers.discord import DiscordNotifier


class TestNotifiers(unittest.TestCase):

    def test_whatsapp_configuration(self):
        wa_unconfigured = WhatsAppNotifier(phone="", api_key="")
        self.assertFalse(wa_unconfigured.is_configured())

        wa_configured = WhatsAppNotifier(phone="+45 12 34 56 78", api_key="test_api_key")
        self.assertTrue(wa_configured.is_configured())
        self.assertEqual(wa_configured.phone, "4512345678")

    @patch("requests.get")
    def test_whatsapp_send_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        wa = WhatsAppNotifier(phone="4512345678", api_key="test_key")
        result = wa.send(subject="Test", message="Test Message")

        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch("requests.post")
    def test_telegram_send_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        tg = TelegramNotifier(bot_token="test_token", chat_id="12345")
        result = tg.send(subject="Test", message="Test Message")

        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_discord_send_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_post.return_value = mock_resp

        dc = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/xyz")
        result = dc.send(subject="Test", message="Test Message")

        self.assertTrue(result)
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
