"""api/routes/groups.py — Group endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_dependency import get_current_user
from modules.group import (
    AddMemberRequest,
    CreateGroupRequest,
    Group,
    GroupService,
)
from shared.db.session import get_db

router = APIRouter()


@router.post(
    "/",
    summary="Create a new group",
    status_code=201,
    response_model=Group,
    responses={201: {"description": "Group created"}},
)
async def create_group(
    request: CreateGroupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Group:
    """POST /groups — creates a group with the authenticated user as admin."""
    service = GroupService(db)
    return await service.create_group(current_user["user_id"], request)


@router.get(
    "/",
    summary="List groups for the current user",
    response_model=list[Group],
    responses={200: {"description": "List of groups the authenticated user belongs to"}},
)
async def list_groups(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Group]:
    """GET /groups — returns all groups the authenticated user is a member of."""
    service = GroupService(db)
    return await service.list_user_groups(current_user["user_id"])


@router.get(
    "/{group_id}",
    summary="Get group details",
    response_model=Group,
    responses={
        200: {"description": "Group with member list"},
        404: {"description": "Group not found"},
    },
)
async def get_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Group:
    """GET /groups/:id — returns group details with all members."""
    service = GroupService(db)
    return await service.get_group(group_id)


@router.post(
    "/{group_id}/members",
    summary="Add a member to a group",
    response_model=Group,
    responses={
        200: {"description": "Member added"},
        404: {"description": "Group or user not found"},
        409: {"description": "User is already a member"},
        403: {"description": "Requesting user is not an admin"},
    },
)
async def add_member(
    group_id: str,
    request: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Group:
    """POST /groups/:id/members"""
    service = GroupService(db)
    return await service.add_member(group_id, current_user["user_id"], request)


@router.delete(
    "/{group_id}/members/{user_id}",
    summary="Remove a member from a group",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Member removed"},
        403: {"description": "Not authorized"},
        409: {"description": "User has outstanding balances"},
    },
)
async def remove_member(
    group_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """DELETE /groups/:id/members/:userId — admin-only, checks outstanding balances."""
    service = GroupService(db)
    await service.remove_member(group_id, current_user["user_id"], user_id)
