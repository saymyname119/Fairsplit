"""Regression tests for verified OAuth, recovery, AI validation and currencies."""

import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import httpx
import pytest

from api.auth_dependency import get_current_user
from modules.ai.models import ParseExpenseRequest
from modules.ai.service import AiService
from modules.group.models import CreateGroupRequest, GroupMember, MemberRole
from modules.user.identity import verified_supabase_user
from modules.user.models import RefreshTokenRequest
from modules.user.recovery import request_reset, reset_password
from modules.user.service import UserService
from shared.errors import AuthenticationError, ExternalServiceError, UnprocessableError


def remote_response(body, status=200):
    response = httpx.Response(
        status, json=body, request=httpx.Request("GET", "https://test.example")
    )
    client = AsyncMock()
    client.get.return_value = response
    client.post.return_value = response
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    return manager, client


async def test_oauth_identity_comes_from_auth_server():
    manager, client = remote_response(
        {"id": "verified", "email": "real@example.com", "email_confirmed_at": "now"}
    )
    with (
        patch(
            "modules.user.identity.get_settings",
            return_value=SimpleNamespace(
                supabase_url="https://project.supabase.co", supabase_publishable_key="public"
            ),
        ),
        patch("httpx.AsyncClient", return_value=manager),
    ):
        user = await verified_supabase_user("signed-token")
    assert user["email"] == "real@example.com"
    assert client.get.call_args.kwargs["headers"]["Authorization"] == "Bearer signed-token"


@pytest.mark.parametrize("body,status", [({}, 401), ({"id": "x", "email": "a@example.com"}, 200)])
async def test_oauth_rejects_invalid_or_unverified_identity(body, status):
    manager, _ = remote_response(body, status)
    with (
        patch(
            "modules.user.identity.get_settings",
            return_value=SimpleNamespace(
                supabase_url="https://project.supabase.co", supabase_publishable_key="public"
            ),
        ),
        patch("httpx.AsyncClient", return_value=manager),
    ):
        with pytest.raises(AuthenticationError):
            await verified_supabase_user("invalid-token")


def reset_db(user):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute.return_value = result
    return db


def reset_user():
    return SimpleNamespace(
        is_active=True,
        deleted_at=None,
        reset_token_hash="hash",
        reset_expires_at=datetime.now(UTC) + timedelta(minutes=20),
        hashed_password="old",
        password_changed_at=None,
    )


async def test_reset_consumes_token_and_changes_hash():
    user = reset_user()
    await reset_password(reset_db(user), "test-token", "new-password-123")
    assert user.reset_token_hash is None and user.reset_expires_at is None
    assert user.password_changed_at is not None
    assert bcrypt.checkpw(b"new-password-123", user.hashed_password.encode())


async def test_expired_reset_is_rejected_without_mutation():
    user = reset_user()
    user.reset_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(AuthenticationError):
        await reset_password(reset_db(user), "expired", "new-password-123")
    assert user.hashed_password == "old"


async def test_reset_stores_only_digest_and_delivers_link():
    user = reset_user()
    user.reset_expires_at = None
    smtp = MagicMock(is_configured=True)
    smtp.send_email = AsyncMock(return_value=True)
    with patch("modules.user.recovery.SmtpClient", return_value=smtp):
        await request_reset(reset_db(user), "person@example.com")
    from urllib.parse import parse_qs, urlparse

    text = smtp.send_email.call_args.kwargs["text"]
    token = parse_qs(urlparse(text.split(": ", 1)[1]).query)["reset_token"][0]
    assert user.reset_token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in user.reset_token_hash


async def test_reset_requires_delivery_configuration():
    with (
        patch(
            "modules.user.recovery.SmtpClient", return_value=SimpleNamespace(is_configured=False)
        ),
        patch(
            "modules.user.recovery.ResendClient", return_value=SimpleNamespace(is_configured=False)
        ),
    ):
        with pytest.raises(ExternalServiceError, match="not configured"):
            await request_reset(AsyncMock(), "a@example.com")


async def test_password_change_invalidates_access_and_refresh():
    service = UserService(AsyncMock())
    tokens = service._generate_tokens("id", "a@example.com")
    user = SimpleNamespace(
        is_active=True,
        deleted_at=None,
        password_changed_at=datetime.now(UTC) + timedelta(seconds=1),
    )
    db = AsyncMock()
    db.get.return_value = user
    with pytest.raises(AuthenticationError, match="Password changed"):
        await get_current_user(tokens.access_token, db)
    service._repo.get_by_id = AsyncMock(return_value=user)
    with pytest.raises(AuthenticationError, match="Password changed"):
        await service.refresh_token(RefreshTokenRequest(refresh_token=tokens.refresh_token))


def members():
    return [
        GroupMember(
            user_id=uid,
            user_name=name,
            user_email=f"{uid}@example.com",
            role=MemberRole.MEMBER,
            joined_at=datetime.now(UTC),
        )
        for uid, name in [("a", "Alex"), ("s", "Sam")]
    ]


def preview(**updates):
    return {
        "amount": "800",
        "description": "Dinner",
        "paid_by_name": "Alex",
        "participant_names": ["Alex", "Sam"],
        "split_type": "equal",
        **updates,
    }


@pytest.mark.parametrize(
    "updates",
    [
        {"paid_by_name": "Unknown"},
        {"participant_names": ["Alex", "Alex"]},
        {"amount": "-1"},
        {"is_ambiguous": True, "ambiguity_reason": "Which Sam?"},
    ],
)
async def test_ai_rejects_ambiguous_and_invalid_output(updates):
    manager, _ = remote_response(
        {"content": [{"type": "tool_use", "name": "expense_preview", "input": preview(**updates)}]}
    )
    with (
        patch(
            "modules.ai.service.get_settings",
            return_value=SimpleNamespace(claude_api_key="test-key", claude_model="test"),
        ),
        patch("httpx.AsyncClient", return_value=manager),
    ):
        with pytest.raises(UnprocessableError):
            await AiService().parse_expense(
                ParseExpenseRequest(text="Dinner for everyone"), members(), "a", "INR"
            )


async def test_ai_returns_preview_with_resolved_members_without_writes():
    manager, _ = remote_response(
        {"content": [{"type": "tool_use", "name": "expense_preview", "input": preview()}]}
    )
    with (
        patch(
            "modules.ai.service.get_settings",
            return_value=SimpleNamespace(claude_api_key="test-key", claude_model="test"),
        ),
        patch("httpx.AsyncClient", return_value=manager),
    ):
        result = await AiService().parse_expense(
            ParseExpenseRequest(text="Dinner 800 Alex and Sam"), members(), "a", "INR"
        )
    assert result.confirmation_required
    assert result.preview.participant_ids == ["a", "s"]
    assert result.preview.paid_by_id == "a"


def test_currency_selection_is_validated():
    assert CreateGroupRequest(name="Trip", currency="INR").currency == "INR"
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreateGroupRequest(name="Trip", currency="INVALID")
