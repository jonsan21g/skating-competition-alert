"""Email notification dispatcher via SMTP."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Sends notifications via SMTP (e.g. Gmail, Outlook, private server)."""

    def __init__(self, host: str, port: int, user: str, password: str, to_addr: str):
        self.host = host.strip()
        self.port = port
        self.user = user.strip()
        self.password = password.strip()
        self.to_addr = to_addr.strip()

    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password and self.to_addr)

    def send(self, subject: str, message: str) -> bool:
        if not self.is_configured():
            logger.error("Email notification skipped: SMTP credentials not fully configured.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.user
            msg["To"] = self.to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain", "utf-8"))

            server = smtplib.SMTP(self.host, self.port, timeout=25)
            server.starttls()
            server.login(self.user, self.password)
            server.sendmail(self.user, [self.to_addr], msg.as_string())
            server.quit()

            logger.info(f"Email alert sent successfully to {self.to_addr}!")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
