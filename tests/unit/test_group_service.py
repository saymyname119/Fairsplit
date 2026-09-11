"""tests/unit/test_group_service.py — GroupService unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.group import GroupService, MemberRole
from modules.group.models import GroupMemberORM, GroupORM
from shared.errors import ConflictError, ForbiddenError, NotFoundError


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def group_service(mock_session):
    return GroupService(mock_session)


def _make_mock_group(group_id: str = "g1", name: str = "Test Group") -> GroupORM:
    from datetime import datetime

    group = MagicMock(spec=GroupORM)
    group.id = group_id
    group.name = name
    group.description = "A test group"
    group.created_by_id = "user-1"
    group.created_at = datetime.now()
    group.members = []
    return group


def _make_mock_member(
    group_id: str = "g1",
    user_id: str = "user-1",
    role: str = MemberRole.ADMIN,
) -> GroupMemberORM:
    member = MagicMock(spec=GroupMemberORM)
    member.group_id = group_id
    member.user_id = user_id
    member.role = role
    return member


@pytest.mark.asyncio
async def test_get_group_happy_path(group_service):
    mock_group = _make_mock_group()
    group_service._repo.get_by_id_or_raise = AsyncMock(return_value=mock_group)

    result = await group_service.get_group("g1")
    assert result.id == "g1"
    assert result.name == "Test Group"


@pytest.mark.asyncio
async def test_get_group_not_found(group_service):
    group_service._repo.get_by_id_or_raise = AsyncMock(
        side_effect=NotFoundError("Group", "g999")
    )

    with pytest.raises(NotFoundError):
        await group_service.get_group("g999")


@pytest.mark.asyncio
async def test_remove_member_as_admin(group_service):
    mock_group = _make_mock_group()
    group_service._repo.get_by_id_or_raise = AsyncMock(return_value=mock_group)

    admin_member = _make_mock_member(role=MemberRole.ADMIN)
    target_member = _make_mock_member(user_id="user-2", role=MemberRole.MEMBER)

    def get_member_side_effect(group_id, user_id):
        if user_id == "user-1":
            return admin_member
        if user_id == "user-2":
            return target_member
        return None

    group_service._repo.get_member = AsyncMock(side_effect=get_member_side_effect)
    group_service._ledger_repo.has_outstanding_balance = AsyncMock(return_value=False)
    group_service._repo.remove_member = AsyncMock()

    await group_service.remove_member("g1", "user-1", "user-2")

    group_service._repo.remove_member.assert_called_once_with("g1", "user-2")


@pytest.mark.asyncio
async def test_remove_member_non_admin_forbidden(group_service):
    mock_group = _make_mock_group()
    group_service._repo.get_by_id_or_raise = AsyncMock(return_value=mock_group)

    non_admin = _make_mock_member(role=MemberRole.MEMBER)
    group_service._repo.get_member = AsyncMock(return_value=non_admin)

    with pytest.raises(ForbiddenError, match="Only admins"):
        await group_service.remove_member("g1", "user-1", "user-2")


@pytest.mark.asyncio
async def test_remove_member_with_outstanding_balance(group_service):
    mock_group = _make_mock_group()
    group_service._repo.get_by_id_or_raise = AsyncMock(return_value=mock_group)

    admin_member = _make_mock_member(role=MemberRole.ADMIN)
    target_member = _make_mock_member(user_id="user-2", role=MemberRole.MEMBER)

    def get_member_side_effect(group_id, user_id):
        if user_id == "user-1":
            return admin_member
        if user_id == "user-2":
            return target_member
        return None

    group_service._repo.get_member = AsyncMock(side_effect=get_member_side_effect)
    group_service._ledger_repo.has_outstanding_balance = AsyncMock(return_value=True)

    with pytest.raises(ConflictError, match="outstanding balances"):
        await group_service.remove_member("g1", "user-1", "user-2")


@pytest.mark.asyncio
async def test_remove_self_blocked(group_service):
    mock_group = _make_mock_group()
    group_service._repo.get_by_id_or_raise = AsyncMock(return_value=mock_group)

    admin_member = _make_mock_member(role=MemberRole.ADMIN)
    group_service._repo.get_member = AsyncMock(return_value=admin_member)

    with pytest.raises(ConflictError, match="Cannot remove yourself"):
        await group_service.remove_member("g1", "user-1", "user-1")
