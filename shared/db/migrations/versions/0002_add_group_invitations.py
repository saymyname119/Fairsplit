"""Add group_invitations table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False
        ),
        sa.Column(
            "invited_by_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(36), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "group_id", "email", "status", name="uq_invitations_group_email_pending"
        ),
    )
    op.create_index("ix_group_invitations_group_id", "group_invitations", ["group_id"])
    op.create_index("ix_group_invitations_email", "group_invitations", ["email"])
    op.create_index("ix_group_invitations_token", "group_invitations", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_group_invitations_token", table_name="group_invitations")
    op.drop_index("ix_group_invitations_email", table_name="group_invitations")
    op.drop_index("ix_group_invitations_group_id", table_name="group_invitations")
    op.drop_table("group_invitations")
