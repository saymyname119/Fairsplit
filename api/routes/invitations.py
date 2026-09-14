"""api/routes/invitations.py — Invitation endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_dependency import get_current_user
from modules.invitation import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    Invitation,
    InvitationInfo,
    InvitationService,
)
from shared.db.session import get_db

router = APIRouter()


# ── Group-Scoped Invitation Routes (Mounted under /groups) ─────────────


@router.post(
    "/{group_id}/invitations",
    summary="Send an email invitation to join a group",
    status_code=status.HTTP_201_CREATED,
    response_model=Invitation,
    responses={
        201: {"description": "Invitation created and email dispatched"},
        403: {"description": "Only group admins can send invitations"},
        409: {"description": "User is already a member or pending invitation exists"},
    },
)
async def create_invitation(
    group_id: str,
    request: CreateInvitationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Invitation:
    """POST /groups/:id/invitations — creates invite token and triggers Resend email."""
    service = InvitationService(db)
    return await service.create_invitation(group_id, current_user["user_id"], request)


@router.get(
    "/{group_id}/invitations",
    summary="List pending invitations for a group",
    response_model=list[Invitation],
    responses={
        200: {"description": "List of outstanding invitations"},
    },
)
async def list_pending_invitations(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Invitation]:
    """GET /groups/:id/invitations — lists pending invites for group admin UI."""
    service = InvitationService(db)
    return await service.list_pending(group_id)


# ── Public / Token-Based Invitation Routes (Mounted under /invitations) ──


@router.get(
    "/info/{token}",
    summary="Get invitation information by token",
    response_model=InvitationInfo,
    responses={
        200: {"description": "Public invitation metadata for accept screen"},
        404: {"description": "Invitation token not found"},
    },
)
async def get_invitation_info(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> InvitationInfo:
    """GET /invitations/info/:token — unauthenticated preview of invite."""
    service = InvitationService(db)
    return await service.get_invitation_info(token)


@router.post(
    "/accept",
    summary="Accept an invitation using a capability token",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Invitation accepted; user joined group"},
        400: {"description": "Invitation expired or invalid"},
        404: {"description": "Token not found"},
    },
)
async def accept_invitation(
    request: AcceptInvitationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """POST /invitations/accept — public endpoint to claim invitation link."""
    service = InvitationService(db)
    return await service.accept_invitation(request)


@router.delete(
    "/{invitation_id}",
    summary="Cancel/revoke a pending invitation",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Invitation cancelled"},
        403: {"description": "Only group admins can cancel invitations"},
        404: {"description": "Invitation not found"},
    },
)
async def cancel_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """DELETE /invitations/:id — revokes a pending invite link."""
    service = InvitationService(db)
    await service.cancel_invitation(invitation_id, current_user["user_id"])
