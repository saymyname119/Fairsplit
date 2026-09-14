"""tests/unit/test_resend_client.py — Resend email client unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from modules.notification.resend_client import (
    ResendClient,
    render_invitation_html,
    render_invitation_text,
)


def test_is_configured_true():
    client = ResendClient(api_key="re_valid_key_123")
    assert client.is_configured is True


def test_is_configured_false_for_placeholder():
    client = ResendClient(api_key="re_CHANGE_ME")
    assert client.is_configured is False

    client_empty = ResendClient(api_key="")
    assert client_empty.is_configured is False


def test_render_invitation_templates():
    html = render_invitation_html("Tokyo Trip", "Manoj", "http://localhost:5173/invite/accept?token=abc")
    assert "Tokyo Trip" in html
    assert "Manoj" in html
    assert "http://localhost:5173/invite/accept?token=abc" in html

    text = render_invitation_text("Tokyo Trip", "Manoj", "http://localhost:5173/invite/accept?token=abc")
    assert "Tokyo Trip" in text
    assert "Manoj" in text
    assert "http://localhost:5173/invite/accept?token=abc" in text


@pytest.mark.asyncio
async def test_send_email_unconfigured_returns_none():
    client = ResendClient(api_key="")
    result = await client.send_email(
        to="test@example.com",
        subject="Hello",
        html="<p>Test</p>",
    )
    assert result is None


@pytest.mark.asyncio
async def test_send_email_success():
    client = ResendClient(api_key="re_test_key_123", from_email="FairSplit <onboarding@resend.dev>")

    mock_resp = httpx.Response(
        200,
        json={"id": "email_msg_123"},
        request=httpx.Request("POST", "https://api.resend.com/emails"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        res = await client.send_email(
            to="friend@example.com",
            subject="Invite",
            html="<p>Join</p>",
        )

        assert res == {"id": "email_msg_123"}
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer re_test_key_123"
        assert call_kwargs["json"]["to"] == ["friend@example.com"]
        assert call_kwargs["json"]["subject"] == "Invite"


@pytest.mark.asyncio
async def test_send_email_api_error():
    client = ResendClient(api_key="re_test_key_123")

    mock_resp = httpx.Response(
        422,
        text="Invalid domain",
        request=httpx.Request("POST", "https://api.resend.com/emails"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        res = await client.send_email(
            to="friend@example.com",
            subject="Invite",
            html="<p>Join</p>",
        )

        assert res is None
