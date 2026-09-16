"""
modules/invitation/models.py
──────────────────────────────
Domain and ORM models for the Invitation module.

An Invitation represents a pending request for someone (identified by email)
to join a group. The invited person may or may not have an existing account.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from modules.group.models import GroupORM
    from modules.user.models import UserORM


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────


class InvitationStatus(StrEnum):
    """Lifecycle states of an invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ─────────────────────────────────────────────────────────────────────────────
# ORM Model
# ─────────────────────────────────────────────────────────────────────────────


class InvitationORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Database table: group_invitations

    Tracks pending, accepted, expired, and cancelled invitations.
    Token is a unique UUID used in the invitation link — it's the
    "capability URL" pattern (knowing the token = having permission).
    """

    __tablename__ = "group_invitations"
    __table_args__ = (
        # Prevent duplicate pending invitations for the same email + group
        UniqueConstraint(
            "group_id",
            "email",
            "status",
            name="uq_invitations_group_email_pending",
        ),
    )

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_groups.id"), nullable=False, index=True
    )
    invited_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=InvitationStatus.PENDING, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships for eager loading
    group: Mapped[GroupORM] = relationship("GroupORM", foreign_keys=[group_id], lazy="joined")
    invited_by: Mapped[UserORM] = relationship(
        "UserORM", foreign_keys=[invited_by_id], lazy="joined"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Domain / DTO Models
# ─────────────────────────────────────────────────────────────────────────────


class Invitation(BaseModel):
    """Public domain representation of an invitation."""

    id: str
    group_id: str
    group_name: str
    invited_by_id: str
    invited_by_name: str
    email: str
    status: InvitationStatus
    token: str = ""
    invite_url: str = ""
    email_dispatched: bool = False
    delivery_status: str | None = None
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class CreateInvitationRequest(BaseModel):
    """Input schema for creating an invitation."""

    email: EmailStr


class AcceptInvitationRequest(BaseModel):
    """Input schema for accepting an invitation via token."""

    token: str


class InvitationInfo(BaseModel):
    """
    Public info about an invitation — returned when someone clicks
    the invite link, before they accept.
    """

    id: str
    group_name: str
    invited_by_name: str
    email: str
    status: InvitationStatus
    is_expired: bool

