"""
modules/notification/resend_client.py
──────────────────────────────────────
Lightweight asynchronous Resend API client for transactional emails.
Uses httpx.AsyncClient for native async non-blocking execution.
"""

# ruff: noqa: E501

from __future__ import annotations

import logging
from typing import Any

import httpx

from shared.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendClient:
    """Client for sending transactional emails via Resend."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.resend_api_key
        self.from_email = (
            from_email if from_email is not None else settings.resend_from_email
        )

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-placeholder Resend API key is provided."""
        return bool(
            self.api_key
            and self.api_key.startswith("re_")
            and "CHANGE_ME" not in self.api_key
        )

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        text: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Send an email via Resend API.
        If not configured, logs the email and returns None.
        """
        recipients = [to] if isinstance(to, str) else to

        if not self.is_configured:
            logger.info(
                f"[Resend Offline/Unconfigured] Email not dispatched via API.\n"
                f"To: {recipients}\nSubject: {subject}\n"
            )
            return None

        payload: dict[str, Any] = {
            "from": self.from_email,
            "to": recipients,
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code in (200, 201):
                    data: dict[str, Any] = response.json()
                    logger.info(
                        f"Resend email dispatched successfully to {recipients}: id={data.get('id')}"
                    )
                    return data

                error_detail = response.text
                logger.error(
                    f"Resend API error {response.status_code} sending to {recipients}: {error_detail}"
                )
                return None
        except Exception as exc:
            logger.error(f"Failed to communicate with Resend API: {exc}")
            return None


def render_invitation_html(
    group_name: str,
    invited_by_name: str,
    invite_url: str,
) -> str:
    """Render a modern, responsive Apple-style HTML email invitation."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>You're invited to {group_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f7; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1d1d1f; -webkit-font-smoothing: antialiased;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f5f5f7; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06); border: 1px solid rgba(0, 0, 0, 0.04);">
          <!-- Header -->
          <tr>
            <td style="padding: 36px 36px 20px 36px; text-align: center;">
              <div style="display: inline-block; width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, #2c3e50 0%, #1a252f 100%); margin-bottom: 16px;">
                <span style="font-size: 24px; line-height: 48px; color: #ffffff;">⚖️</span>
              </div>
              <p style="margin: 0; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #86868b;">FairSplit Invitation</p>
              <h1 style="margin: 10px 0 0 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; color: #1d1d1f; line-height: 1.25;">
                Join {group_name}
              </h1>
            </td>
          </tr>

          <!-- Body Card -->
          <tr>
            <td style="padding: 0 36px 28px 36px;">
              <div style="background-color: #fbfbfd; border: 1px solid #e5e5ea; border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 24px;">
                <p style="margin: 0 0 8px 0; font-size: 15px; color: #424245; line-height: 1.5;">
                  <strong>{invited_by_name}</strong> invited you to join the group <strong>"{group_name}"</strong> to share and split expenses effortlessly.
                </p>
                <p style="margin: 0; font-size: 13px; color: #86868b;">
                  Track who paid, see who owes what, and settle up with simplified balances.
                </p>
              </div>

              <!-- CTA Button -->
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <a href="{invite_url}" target="_blank" style="display: inline-block; background-color: #0071e3; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; padding: 14px 32px; border-radius: 980px; box-shadow: 0 4px 14px rgba(0, 113, 227, 0.25); transition: background-color 0.2s ease;">
                      Accept &amp; Join Group
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Link Fallback -->
              <p style="margin: 28px 0 0 0; font-size: 12px; line-height: 1.5; color: #86868b; text-align: center; word-break: break-all;">
                Or copy and paste this link in your browser:<br>
                <a href="{invite_url}" style="color: #0071e3; text-decoration: underline;">{invite_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 36px 32px 36px; border-top: 1px solid #f2f2f7; text-align: center; background-color: #fafafa;">
              <p style="margin: 0; font-size: 11px; color: #98989d; line-height: 1.4;">
                This invitation link is valid for 7 days.<br>
                If you were not expecting this invitation, you can safely ignore this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def render_invitation_text(
    group_name: str,
    invited_by_name: str,
    invite_url: str,
) -> str:
    """Render plain text fallback for email clients."""
    return (
        f"Hi there,\n\n"
        f"{invited_by_name} has invited you to join the group \"{group_name}\" on FairSplit.\n\n"
        f"Click the link below to accept the invitation and start tracking expenses together:\n"
        f"{invite_url}\n\n"
        f"This link will expire in 7 days.\n\n"
        f"— FairSplit Team"
    )
