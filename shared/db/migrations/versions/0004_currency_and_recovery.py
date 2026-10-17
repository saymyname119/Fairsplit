"""Persist group currencies and single-use password recovery tokens."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "group_groups", sa.Column("currency", sa.String(3), nullable=False, server_default="USD")
    )
    # Earlier versions encoded the selection in the description.
    op.execute(
        "UPDATE group_groups SET currency = substring(description from 11 for 3) "
        "WHERE description IN ('Currency: USD', 'Currency: EUR', 'Currency: GBP', "
        "'Currency: JPY', 'Currency: INR')"
    )
    op.add_column("user_accounts", sa.Column("reset_token_hash", sa.String(64), nullable=True))
    op.add_column(
        "user_accounts", sa.Column("reset_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_accounts", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("user_accounts", "password_changed_at")
    op.drop_column("user_accounts", "reset_expires_at")
    op.drop_column("user_accounts", "reset_token_hash")
    op.drop_column("group_groups", "currency")
