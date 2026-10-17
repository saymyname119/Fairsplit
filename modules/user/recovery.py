"""Hashed, expiring, single-use password reset tokens for local accounts."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import bcrypt
from sqlalchemy import select

from modules.notification.resend_client import ResendClient
from modules.notification.smtp_client import SmtpClient
from modules.user.models import UserORM
from shared.config import get_settings
from shared.errors import AuthenticationError, ExternalServiceError, ValidationError


def password_hash(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValidationError("Password must be at most 72 UTF-8 bytes")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


async def request_reset(db, email: str):
    smtp, resend = SmtpClient(), ResendClient()
    if not smtp.is_configured and not resend.is_configured:
        raise ExternalServiceError(
            "Password recovery email is not configured. Please contact the app administrator."
        )
    # Lock serializes reset requests and consumption for the same account.
    user = (
        await db.execute(select(UserORM).where(UserORM.email == email).with_for_update())
    ).scalar_one_or_none()
    if not user or not user.is_active or user.deleted_at:
        return
    now = datetime.now(UTC)
    if user.reset_expires_at and user.reset_expires_at > now + timedelta(minutes=29):
        return
    token = secrets.token_urlsafe(32)
    user.reset_token_hash = hashlib.sha256(token.encode()).hexdigest()
    user.reset_expires_at = now + timedelta(minutes=30)
    await db.flush()
    url = get_settings().app_base_url.rstrip("/") + "/?" + urlencode({"reset_token": token})
    text = "Reset your FairSplit password (valid for 30 minutes): " + url
    # Never log reset URLs or return them to the caller.
    kwargs = dict(
        to=email,
        subject="Reset your FairSplit password",
        html=(
            "<p>Reset your password within 30 minutes.</p>"
            f'<p><a href="{url}">Choose a new password</a></p>'
        ),
        text=text,
    )
    delivered = (
        await smtp.send_email(**kwargs) if smtp.is_configured else await resend.send_email(**kwargs)
    )
    if not delivered:
        raise ExternalServiceError(
            "Password reset email could not be delivered. Please try again later."
        )


async def reset_password(db, token: str, password: str):
    digest = hashlib.sha256(token.encode()).hexdigest()
    user = (
        await db.execute(
            select(UserORM).where(UserORM.reset_token_hash == digest).with_for_update()
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if (
        not user
        or not user.is_active
        or user.deleted_at
        or not user.reset_expires_at
        or user.reset_expires_at <= now
    ):
        raise AuthenticationError("This reset link is invalid or expired. Request a new link.")
    user.hashed_password = password_hash(password)
    user.password_changed_at = now
    user.reset_token_hash = None
    user.reset_expires_at = None
    await db.flush()
