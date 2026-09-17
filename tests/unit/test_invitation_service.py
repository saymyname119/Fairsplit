"""tests/unit/test_invitation_service.py — InvitationService unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.group.models import GroupMemberORM, GroupORM, MemberRole
from modules.invitation import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    InvitationORM,
    InvitationService,
    InvitationStatus,
)
from modules.user.models import UserORM
from shared.errors import ConflictError, ForbiddenError, ValidationError


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def invitation_service(mock_session):
    return InvitationService(mock_session)


def _make_mock_group(group_id: str = "g1", name: str = "Tokyo Trip") -> GroupORM:
    group = MagicMock(spec=GroupORM)
    group.id = group_id
    group.name = name
    return group


def _make_mock_member(
    group_id: str = "g1", user_id: str = "u1", role: str = MemberRole.ADMIN
) -> GroupMemberORM:
    member = MagicMock(spec=GroupMemberORM)
    member.group_id = group_id
    member.user_id = user_id
    member.role = role
    return member


def _make_mock_invitation(
    inv_id: str = "inv1",
    group_id: str = "g1",
    email: str = "invitee@example.com",
    token: str = "tok123",
    status: str = InvitationStatus.PENDING,
    expires_at: datetime | None = None,
) -> InvitationORM:
    inv = MagicMock(spec=InvitationORM)
    inv.id = inv_id
    inv.group_id = group_id
    inv.invited_by_id = "admin-1"
    inv.email = email
    inv.token = token
    inv.status = status
    inv.created_at = datetime.now(UTC)
    inv.expires_at = expires_at or (datetime.now(UTC) + timedelta(days=7))
    inv.group = MagicMock()
    inv.group.name = "Tokyo Trip"
    inv.invited_by = MagicMock()
    inv.invited_by.name = "Admin User"
    return inv


@pytest.mark.asyncio
async def test_create_invitation_happy_path(invitation_service):
    group = _make_mock_group()
    admin_member = _make_mock_member(role=MemberRole.ADMIN)

    invitation_service._group_repo.get_by_id_or_raise = AsyncMock(return_value=group)
    invitation_service._group_repo.get_member = AsyncMock(return_value=admin_member)
    invitation_service._user_repo.get_by_email = AsyncMock(return_value=None)
    invitation_service._repo.get_pending_by_email_and_group = AsyncMock(return_value=None)

    saved_orm = _make_mock_invitation()
    invitation_service._repo.create = AsyncMock(return_value=saved_orm)

    request = CreateInvitationRequest(email="invitee@example.com")
    result = await invitation_service.create_invitation("g1", "admin-1", request)

    assert result.email == "invitee@example.com"
    assert result.group_name == "Tokyo Trip"
    assert result.status == InvitationStatus.PENDING


@pytest.mark.asyncio
async def test_create_invitation_non_admin_forbidden(invitation_service):
    group = _make_mock_group()
    regular_member = _make_mock_member(role=MemberRole.MEMBER)

    invitation_service._group_repo.get_by_id_or_raise = AsyncMock(return_value=group)
    invitation_service._group_repo.get_member = AsyncMock(return_value=regular_member)

    request = CreateInvitationRequest(email="invitee@example.com")
    with pytest.raises(ForbiddenError):
        await invitation_service.create_invitation("g1", "user-2", request)


@pytest.mark.asyncio
async def test_create_invitation_already_member_conflict(invitation_service):
    group = _make_mock_group()
    admin_member = _make_mock_member(role=MemberRole.ADMIN)
    existing_user = MagicMock(spec=UserORM, id="existing-u")

    invitation_service._group_repo.get_by_id_or_raise = AsyncMock(return_value=group)
    invitation_service._group_repo.get_member = AsyncMock(return_value=admin_member)
    invitation_service._user_repo.get_by_email = AsyncMock(return_value=existing_user)
    invitation_service._group_repo.is_member = AsyncMock(return_value=True)

    request = CreateInvitationRequest(email="existing@example.com")
    with pytest.raises(ConflictError) as exc:
        await invitation_service.create_invitation("g1", "admin-1", request)
    assert "already a member" in str(exc.value)


@pytest.mark.asyncio
async def test_create_invitation_duplicate_pending_conflict(invitation_service):
    group = _make_mock_group()
    admin_member = _make_mock_member(role=MemberRole.ADMIN)

    invitation_service._group_repo.get_by_id_or_raise = AsyncMock(return_value=group)
    invitation_service._group_repo.get_member = AsyncMock(return_value=admin_member)
    invitation_service._user_repo.get_by_email = AsyncMock(return_value=None)
    invitation_service._repo.get_pending_by_email_and_group = AsyncMock(
        return_value=_make_mock_invitation()
    )

    request = CreateInvitationRequest(email="invitee@example.com")
    with pytest.raises(ConflictError) as exc:
        await invitation_service.create_invitation("g1", "admin-1", request)
    assert "pending invitation already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_accept_invitation_happy_path(invitation_service):
    inv = _make_mock_invitation()
    invitation_service._repo.get_by_token_or_raise = AsyncMock(return_value=inv)
    invitation_service._user_repo.get_by_email = AsyncMock(return_value=None)

    new_user = MagicMock(
        spec=UserORM, id="new-user-id", email="invitee@example.com", name="invitee"
    )
    invitation_service._user_repo.create = AsyncMock(return_value=new_user)
    invitation_service._group_repo.is_member = AsyncMock(return_value=False)
    invitation_service._group_repo.add_member = AsyncMock()
    invitation_service._repo.mark_status = AsyncMock()

    request = AcceptInvitationRequest(token="tok123")
    result = await invitation_service.accept_invitation(request)

    assert result["group_id"] == "g1"
    assert result["user_id"] == "new-user-id"
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"]["email"] == "invitee@example.com"
    invitation_service._repo.mark_status.assert_called_once_with(
        "inv1", InvitationStatus.ACCEPTED
    )


@pytest.mark.asyncio
async def test_accept_invitation_expired(invitation_service):
    expired_time = datetime.now(UTC) - timedelta(hours=1)
    inv = _make_mock_invitation(expires_at=expired_time)
    invitation_service._repo.get_by_token_or_raise = AsyncMock(return_value=inv)
    invitation_service._repo.mark_status = AsyncMock()

    request = AcceptInvitationRequest(token="tok123")
    with pytest.raises(ValidationError) as exc:
        await invitation_service.accept_invitation(request)
    assert "expired" in str(exc.value)
    invitation_service._repo.mark_status.assert_called_once_with(
        "inv1", InvitationStatus.EXPIRED
    )


@pytest.mark.asyncio
async def test_cancel_invitation_by_admin(invitation_service):
    inv = _make_mock_invitation()
    invitation_service._repo.get_by_id_or_raise = AsyncMock(return_value=inv)
    admin_member = _make_mock_member(role=MemberRole.ADMIN)
    invitation_service._group_repo.get_member = AsyncMock(return_value=admin_member)
    invitation_service._repo.mark_status = AsyncMock()

    await invitation_service.cancel_invitation("inv1", "admin-1")
    invitation_service._repo.mark_status.assert_called_once_with(
        "inv1", InvitationStatus.CANCELLED
    )


@pytest.mark.asyncio
async def test_cancel_invitation_by_non_admin_forbidden(invitation_service):
    inv = _make_mock_invitation()
    invitation_service._repo.get_by_id_or_raise = AsyncMock(return_value=inv)
    reg_member = _make_mock_member(role=MemberRole.MEMBER)
    invitation_service._group_repo.get_member = AsyncMock(return_value=reg_member)

    with pytest.raises(ForbiddenError):
        await invitation_service.cancel_invitation("inv1", "user-2")
