"""Unit tests for notification dispatchers."""

import unittest
from unittest.mock import patch, MagicMock
from src.notifiers.whatsapp import WhatsAppNotifier
from src.notifiers.console import ConsoleNotifier


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

    @patch("requests.get")
    def test_whatsapp_send_failure(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get.return_value = mock_resp

        wa = WhatsAppNotifier(phone="4512345678", api_key="test_key")
        result = wa.send(subject="Test", message="Test Message")

        self.assertFalse(result)

    def test_console_notifier(self):
        cn = ConsoleNotifier()
        self.assertTrue(cn.is_configured())
        self.assertTrue(cn.send(subject="Test", message="Test Message"))


if __name__ == "__main__":
    unittest.main()
