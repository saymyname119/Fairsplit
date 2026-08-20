"""
shared/db/base.py
──────────────────
SQLAlchemy declarative base and common column mixins.

All ORM models across every module import Base from here.
This gives Alembic a single place to discover all models for autogenerate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Single declarative base for the entire application.

    Why one base?
    ─────────────
    Alembic's autogenerate scans Base.metadata to detect schema changes.
    If we had per-module bases, migrations would require merging metadata
    manually — unnecessary complexity for a monolith. When we split into
    microservices, each service will get its own schema file and its own
    alembic history.
    """

    pass


# ─────────────────────────────────────────────────────────────────────────────
# Re-usable column mixins
#
# Mixins let us stamp every table with the same audit columns without
# repeating ourselves. Python MRO handles composition cleanly.
# ─────────────────────────────────────────────────────────────────────────────


class UUIDPrimaryKeyMixin:
    """Mixin: UUID primary key generated at the application layer (not DB serial)."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        # Application-generated UUIDs give us the ID before the INSERT,
        # which is required for our event payloads (we include expense_id in
        # ExpenseCreated before the DB round-trip completes).
    )


class TimestampMixin:
    """Mixin: created_at / updated_at columns on every table."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin: soft-delete support via deleted_at column.

    We soft-delete expenses and settlements rather than hard-deleting them.
    Rationale:
    - Financial records must be auditable; hard deletes destroy the audit trail.
    - A deleted expense still affected historical balances — we need it for
      'point in time' balance queries.
    All repository queries must filter deleted_at IS NULL unless explicitly
    fetching deleted records for audit purposes.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
