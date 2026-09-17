"""tests/unit/test_smtp_client.py — Unit tests for SmtpClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from modules.notification.smtp_client import SmtpClient


def test_smtp_client_is_configured_false():
    client = SmtpClient(user="", password="")
    assert client.is_configured is False

    client_placeholder = SmtpClient(user="me@gmail.com", password="CHANGE_ME")
    assert client_placeholder.is_configured is False


def test_smtp_client_is_configured_true():
    client = SmtpClient(user="me@gmail.com", password="app-password-1234")
    assert client.is_configured is True


@pytest.mark.asyncio
async def test_smtp_client_unconfigured_fails_gracefully():
    client = SmtpClient(user="", password="")
    success = await client.send_email(
        to="recipient@example.com",
        subject="Hello",
        html="<p>Test</p>",
    )
    assert success is False
    assert "not configured" in (client.last_error or "")


@pytest.mark.asyncio
async def test_smtp_client_send_ssl_success():
    client = SmtpClient(
        host="smtp.gmail.com",
        port=465,
        user="test@gmail.com",
        password="password1234",
    )

    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server

    with patch("smtplib.SMTP_SSL", return_value=mock_server):
        success = await client.send_email(
            to="friend@example.com",
            subject="Group Invite",
            html="<p>Click here</p>",
            text="Click here",
        )
        assert success is True
        assert client.last_error is None
        mock_server.login.assert_called_once_with("test@gmail.com", "password1234")
        mock_server.sendmail.assert_called_once()
