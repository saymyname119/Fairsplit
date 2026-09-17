"""
modules/notification/smtp_client.py
───────────────────────────────────
Standard asynchronous SMTP client for sending transactional emails
using Python's built-in smtplib (zero external pip dependencies).

Ideal for free email delivery via Gmail SMTP (smtp.gmail.com:465)
using a 16-character Google App Password, with no custom domain required.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared.config import get_settings

logger = logging.getLogger(__name__)


class SmtpClient:
    """Client for sending transactional emails via SMTP (e.g., Gmail)."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
    ) -> None:
        settings = get_settings()
        self.host = host if host is not None else settings.smtp_host
        self.port = port if port is not None else settings.smtp_port
        self.user = user if user is not None else settings.smtp_user
        self.password = password if password is not None else settings.smtp_password
        self.from_email = (
            from_email if from_email is not None else settings.smtp_from_email
        )
        self.last_error: str | None = None

    @property
    def is_configured(self) -> bool:
        """Returns True if SMTP username and password credentials are set."""
        return bool(
            self.user
            and self.password
            and "CHANGE_ME" not in self.password
            and len(self.password.strip()) > 0
        )

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        text: str | None = None,
    ) -> bool:
        """Send an email asynchronously via smtplib running in a worker thread."""
        recipients = [to] if isinstance(to, str) else to

        if not self.is_configured:
            msg = "SMTP credentials (user/password) are not configured."
            self.last_error = msg
            logger.info(f"[SMTP Unconfigured] Email not sent to {recipients}")
            return False

        return await asyncio.to_thread(
            self._send_sync,
            recipients=recipients,
            subject=subject,
            html=html,
            text=text,
        )

    def _send_sync(
        self,
        recipients: list[str],
        subject: str,
        html: str,
        text: str | None,
    ) -> bool:
        """Synchronous SMTP worker function."""
        try:
            msg = MIMEMultipart("alternative")
            sender_addr = (
                self.from_email
                if self.from_email
                else f"FairSplit <{self.user}>"
            )
            msg["From"] = sender_addr
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject

            if text:
                msg.attach(MIMEText(text, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            if self.port == 465:
                # SSL connection (standard for Gmail port 465)
                with smtplib.SMTP_SSL(self.host, self.port, timeout=10.0) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.user, recipients, msg.as_string())
            else:
                # Plain SMTP with STARTTLS (port 587)
                with smtplib.SMTP(self.host, self.port, timeout=10.0) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.user, self.password)
                    server.sendmail(self.user, recipients, msg.as_string())

            self.last_error = None
            logger.info(f"Email successfully dispatched via SMTP to {recipients}")
            return True

        except Exception as exc:
            err_msg = str(exc)
            self.last_error = err_msg
            logger.error(f"SMTP dispatch failed to {recipients}: {err_msg}")
            return False
