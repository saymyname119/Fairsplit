"""
modules/invitation/service.py
───────────────────────────────
Business logic for the Invitation module.

Handles the full invitation lifecycle:
  1. Create invitation → generates token, validates constraints, publishes event
  2. Accept invitation → validates token, creates user if needed, adds to group
  3. List pending → returns outstanding invitations for admin UI
  4. Cancel invitation → revokes a pending invitation
"""

from __future__ import annotations

import abc
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from modules.group.models import GroupMemberORM, MemberRole
from modules.group.repository import GroupRepository
from modules.invitation.models import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    Invitation,
    InvitationInfo,
    InvitationORM,
    InvitationStatus,
)
from modules.invitation.repository import InvitationRepository
from modules.user.models import UserORM
from modules.user.repository import UserRepository
from shared.errors import ConflictError, ForbiddenError, ValidationError
from shared.events import get_event_bus

logger = logging.getLogger(__name__)

# How long an invitation link is valid
INVITATION_EXPIRY_DAYS = 7


class IInvitationService(abc.ABC):
    """Public interface for the Invitation module."""

    @abc.abstractmethod
    async def create_invitation(
        self, group_id: str, inviter_id: str, request: CreateInvitationRequest
    ) -> Invitation: ...

    @abc.abstractmethod
    async def accept_invitation(self, request: AcceptInvitationRequest) -> dict[str, Any]: ...

    @abc.abstractmethod
    async def get_invitation_info(self, token: str) -> InvitationInfo: ...

    @abc.abstractmethod
    async def list_pending(self, group_id: str) -> list[Invitation]: ...

    @abc.abstractmethod
    async def cancel_invitation(
        self, invitation_id: str, canceller_id: str
    ) -> None: ...


class InvitationService(IInvitationService):
    """Implementation of the Invitation module business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InvitationRepository(session)
        self._group_repo = GroupRepository(session)
        self._user_repo = UserRepository(session)
        self._bus = get_event_bus()

    async def create_invitation(
        self, group_id: str, inviter_id: str, request: CreateInvitationRequest
    ) -> Invitation:
        """
        Create and persist a new invitation.

        Validates:
        - Group exists
        - Inviter is a group admin
        - Email is not already a group member
        - No duplicate pending invitation exists
        """
        # 1. Group must exist
        group = await self._group_repo.get_by_id_or_raise(group_id)

        # 2. Inviter must be admin
        inviter_member = await self._group_repo.get_member(group_id, inviter_id)
        if not inviter_member or inviter_member.role != MemberRole.ADMIN:
            raise ForbiddenError("Only group admins can send invitations")

        email = request.email.lower().strip()

        # 3. Check if this email belongs to an existing user who is already a member
        existing_user = await self._user_repo.get_by_email(email)
        if existing_user:
            is_member = await self._group_repo.is_member(group_id, existing_user.id)
            if is_member:
                raise ConflictError(f"{email} is already a member of this group")

        # 4. Check for duplicate pending invitation
        existing_invite = await self._repo.get_pending_by_email_and_group(email, group_id)
        if existing_invite:
            raise ConflictError(
                f"A pending invitation already exists for {email} in this group"
            )

        # 5. Create the invitation
        token = str(uuid.uuid4())
        now = datetime.now(UTC)
        orm_invitation = InvitationORM(
            group_id=group_id,
            invited_by_id=inviter_id,
            email=email,
            token=token,
            status=InvitationStatus.PENDING,
            expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
        )

        created = await self._repo.create(orm_invitation)

        invitation = self._map_to_domain(created)

        # 6. Publish event for email notification
        from shared.events.event_types import InvitationCreated

        self._bus.publish(
            InvitationCreated(
                invitation_id=invitation.id,
                group_id=group_id,
                group_name=invitation.group_name,
                email=email,
                token=token,
                invited_by_name=invitation.invited_by_name,
            )
        )

        logger.info(
            f"Invitation created: {email} → group '{group.name}' "
            f"(token={token[:8]}…, expires={invitation.expires_at})"
        )

        return invitation

    async def accept_invitation(self, request: AcceptInvitationRequest) -> dict[str, Any]:
        """
        Accept an invitation and add the user to the group.

        If the email doesn't have an account, one is auto-created
        (password-less — they can sign in via Google OAuth later).

        Returns a dict with group_id and user_id for the frontend to redirect.
        """
        invitation = await self._repo.get_by_token_or_raise(request.token)

        # Validate status
        if invitation.status != InvitationStatus.PENDING:
            raise ValidationError(
                f"This invitation has already been {invitation.status}"
            )

        # Validate expiry
        now = datetime.now(UTC)
        if now > invitation.expires_at:
            await self._repo.mark_status(invitation.id, InvitationStatus.EXPIRED)
            raise ValidationError("This invitation has expired")

        email = invitation.email

        # Find or create the user
        user = await self._user_repo.get_by_email(email)
        if not user:
            # Auto-create account with a random password
            # User can sign in with Google OAuth or reset password later
            random_pw = str(uuid.uuid4())
            hashed_bytes = bcrypt.hashpw(
                random_pw.encode("utf-8"), bcrypt.gensalt()
            )
            user = UserORM(
                email=email,
                name=email.split("@")[0],  # Use email prefix as initial name
                hashed_password=hashed_bytes.decode("utf-8"),
            )
            user = await self._user_repo.create(user)
            logger.info(f"Auto-created user account for invited email: {email}")

        # Check if already a member (edge case: accepted invite link twice)
        is_member = await self._group_repo.is_member(
            invitation.group_id, user.id
        )
        if is_member:
            await self._repo.mark_status(invitation.id, InvitationStatus.ACCEPTED)
            return {
                "group_id": invitation.group_id,
                "user_id": user.id,
                "message": "You are already a member of this group",
            }

        # Add user to the group
        member = GroupMemberORM(
            group_id=invitation.group_id,
            user_id=user.id,
            role=MemberRole.MEMBER,
        )
        await self._group_repo.add_member(member)

        # Mark invitation as accepted
        await self._repo.mark_status(invitation.id, InvitationStatus.ACCEPTED)

        # Publish event
        from shared.events import MemberAdded

        self._bus.publish(
            MemberAdded(
                group_id=invitation.group_id,
                user_id=user.id,
                added_by_id=invitation.invited_by_id,
            )
        )

        logger.info(
            f"Invitation accepted: {email} joined group '{invitation.group.name}'"
        )

        return {
            "group_id": invitation.group_id,
            "user_id": user.id,
            "group_name": invitation.group.name,
            "message": f"Welcome! You've joined {invitation.group.name}",
        }

    async def get_invitation_info(self, token: str) -> InvitationInfo:
        """
        Get public info about an invitation — used when someone clicks the
        invite link, before they accept. No auth required.
        """
        invitation = await self._repo.get_by_token_or_raise(token)

        now = datetime.now(UTC)
        is_expired = now > invitation.expires_at

        return InvitationInfo(
            id=invitation.id,
            group_name=invitation.group.name if invitation.group else "Unknown Group",
            invited_by_name=(
                invitation.invited_by.name if invitation.invited_by else "Unknown"
            ),
            email=invitation.email,
            status=InvitationStatus(invitation.status),
            is_expired=is_expired,
        )

    async def list_pending(self, group_id: str) -> list[Invitation]:
        """List all pending invitations for a group."""
        orm_list = await self._repo.list_pending_for_group(group_id)
        return [self._map_to_domain(inv) for inv in orm_list]

    async def cancel_invitation(
        self, invitation_id: str, canceller_id: str
    ) -> None:
        """Cancel a pending invitation. Only the group admin can do this."""
        invitation = await self._repo.get_by_id_or_raise(invitation_id)

        if invitation.status != InvitationStatus.PENDING:
            raise ValidationError("Only pending invitations can be cancelled")

        # Verify canceller is admin of the group
        canceller = await self._group_repo.get_member(
            invitation.group_id, canceller_id
        )
        if not canceller or canceller.role != MemberRole.ADMIN:
            raise ForbiddenError("Only group admins can cancel invitations")

        await self._repo.mark_status(invitation_id, InvitationStatus.CANCELLED)
        logger.info(f"Invitation {invitation_id} cancelled by {canceller_id}")

    def _map_to_domain(self, orm: InvitationORM) -> Invitation:
        """Map ORM model to domain model."""
        return Invitation(
            id=orm.id,
            group_id=orm.group_id,
            group_name=orm.group.name if orm.group else "Unknown Group",
            invited_by_id=orm.invited_by_id,
            invited_by_name=(
                orm.invited_by.name if orm.invited_by else "Unknown"
            ),
            email=orm.email,
            status=InvitationStatus(orm.status),
            created_at=orm.created_at,
            expires_at=orm.expires_at,
        )
