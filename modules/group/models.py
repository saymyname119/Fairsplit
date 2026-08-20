"""
modules/group/models.py
────────────────────────
Domain and ORM models for the Group module.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from modules.user.models import UserORM

# ─────────────────────────────────────────────────────────────────────────────
# ORM Models (private to this module)
# ─────────────────────────────────────────────────────────────────────────────

class GroupORM(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Database table: group_groups
    Prefixed group_ to namespace within the shared schema.
    """

    __tablename__ = "group_groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_accounts.id"),
        nullable=False,
        # Index on creator for "groups I created" queries
        index=True,
    )

    members: Mapped[list[GroupMemberORM]] = relationship(
        "GroupMemberORM", back_populates="group", lazy="selectin"
    )


class MemberRole(StrEnum):
    """Member roles within a group."""
    ADMIN = "admin"    # Can add/remove members, delete the group
    MEMBER = "member"  # Can add expenses, view balances


class GroupMemberORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Database table: group_members
    Junction table: Group ↔ User (many-to-many with metadata).

    Composite unique constraint prevents a user joining the same group twice.
    Index on (group_id, user_id) optimises the most common query pattern:
    "is user X a member of group G?" — used on every expense creation.
    """

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),
        # Composite index: lookup "all members of group G" and "all groups for user U"
        # These are the two most common access patterns for this table.
    )

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_groups.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), default=MemberRole.MEMBER, nullable=False)

    group: Mapped[GroupORM] = relationship("GroupORM", back_populates="members")
    # String reference to avoid circular imports. UserORM is in modules.user.models.
    user: Mapped[UserORM] = relationship("UserORM", foreign_keys=[user_id], lazy="joined")


# ─────────────────────────────────────────────────────────────────────────────
# Domain Models (public — returned by service facade)
# ─────────────────────────────────────────────────────────────────────────────

class GroupMember(BaseModel):
    """A user's membership record within a group."""

    user_id: str
    user_name: str
    user_email: str
    role: MemberRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class Group(BaseModel):
    """Public domain representation of a group."""

    id: str
    name: str
    description: str | None
    created_by_id: str
    created_at: datetime
    members: list[GroupMember] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CreateGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class AddMemberRequest(BaseModel):
    user_id: str
    role: MemberRole = MemberRole.MEMBER
