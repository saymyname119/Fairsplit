"""tests/unit/test_auth_dependency.py — JWT auth dependency tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from api.auth_dependency import get_current_user
from shared.errors import AuthenticationError


SECRET = "test-secret-key"
ALGORITHM = "HS256"


def _make_token(
    user_id: str = "user-123",
    email: str = "test@example.com",
    token_type: str = "access",
    expired: bool = False,
) -> str:
    exp = datetime.now(UTC) + (timedelta(hours=-1) if expired else timedelta(hours=1))
    payload = {
        "sub": user_id,
        "email": email,
        "exp": exp,
        "type": token_type,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


@pytest.mark.asyncio
async def test_valid_access_token():
    token = _make_token()
    result = await get_current_user(token)
    assert result["user_id"] == "user-123"
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_expired_token_raises():
    token = _make_token(expired=True)
    with pytest.raises(AuthenticationError, match="Invalid or expired"):
        await get_current_user(token)


@pytest.mark.asyncio
async def test_refresh_token_rejected():
    token = _make_token(token_type="refresh")
    with pytest.raises(AuthenticationError, match="expected access token"):
        await get_current_user(token)


@pytest.mark.asyncio
async def test_malformed_token_raises():
    with pytest.raises(AuthenticationError, match="Invalid or expired"):
        await get_current_user("not-a-valid-jwt")


@pytest.mark.asyncio
async def test_missing_sub_raises():
    payload = {
        "email": "test@example.com",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "type": "access",
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    with pytest.raises(AuthenticationError, match="Invalid token payload"):
        await get_current_user(token)
