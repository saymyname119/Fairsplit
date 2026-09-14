"""
modules/invitation/repository.py
──────────────────────────────────
Database operations for the Invitation module.
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.invitation.models import InvitationORM, InvitationStatus
from shared.errors import NotFoundError


class InvitationRepository:
    """Repository for group_invitations table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, invitation: InvitationORM) -> InvitationORM:
        self._session.add(invitation)
        await self._session.flush()
        # Re-fetch with relationships loaded
        return await self.get_by_id_or_raise(invitation.id)

    async def get_by_id(self, invitation_id: str) -> InvitationORM | None:
        stmt = select(InvitationORM).where(InvitationORM.id == invitation_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, invitation_id: str) -> InvitationORM:
        invitation = await self.get_by_id(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation", invitation_id)
        return invitation

    async def get_by_token(self, token: str) -> InvitationORM | None:
        stmt = select(InvitationORM).where(InvitationORM.token == token)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token_or_raise(self, token: str) -> InvitationORM:
        invitation = await self.get_by_token(token)
        if not invitation:
            raise NotFoundError("Invitation", token)
        return invitation

    async def get_pending_by_email_and_group(
        self, email: str, group_id: str
    ) -> InvitationORM | None:
        """Check if a pending invitation already exists for this email + group."""
        stmt = select(InvitationORM).where(
            InvitationORM.email == email,
            InvitationORM.group_id == group_id,
            InvitationORM.status == InvitationStatus.PENDING,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pending_for_group(self, group_id: str) -> list[InvitationORM]:
        """List all pending invitations for a group."""
        stmt = (
            select(InvitationORM)
            .where(
                InvitationORM.group_id == group_id,
                InvitationORM.status == InvitationStatus.PENDING,
            )
            .order_by(InvitationORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_status(
        self, invitation_id: str, status: InvitationStatus
    ) -> None:
        """Update invitation status."""
        stmt = (
            update(InvitationORM)
            .where(InvitationORM.id == invitation_id)
            .values(status=status)
        )
        await self._session.execute(stmt)
        await self._session.flush()
