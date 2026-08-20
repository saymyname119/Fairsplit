"""api/routes/groups.py — Group endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession = Depends(get_db)
) -> Group:
    """POST /groups"""
    # For now, hardcode creator_id. In Prompt 3 we add actual auth extraction.
    creator_id = "temp-creator-id"
    service = GroupService(db)
    return await service.create_group(creator_id, request)


@router.get(
    "/{group_id}",
    summary="Get group details",
    responses={
        200: {"description": "Group with member list"},
        404: {"description": "Group not found"},
    },
)
async def get_group(group_id: str) -> JSONResponse:
    """GET /groups/:id — full implementation in Prompt 2."""
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 2"})


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
    db: AsyncSession = Depends(get_db)
) -> Group:
    """POST /groups/:id/members"""
    adder_id = "temp-adder-id"
    service = GroupService(db)
    return await service.add_member(group_id, adder_id, request)


@router.delete(
    "/{group_id}/members/{user_id}",
    summary="Remove a member from a group",
    responses={
        204: {"description": "Member removed"},
        403: {"description": "Not authorized"},
        409: {"description": "User has outstanding balances"},
    },
)
async def remove_member(group_id: str, user_id: str) -> JSONResponse:
    """DELETE /groups/:id/members/:userId — full implementation in Prompt 2."""
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 2"})
