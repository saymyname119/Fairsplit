"""Initial schema — all module tables

Revision ID: 0001
Revises: None
Create Date: 2026-08-20

Tables created (namespaced by module):
  user_*    → user_accounts
  group_*   → group_groups, group_members
  expense_* → expense_expenses, expense_splits
  ledger_*  → ledger_balances, ledger_settlements

Index strategy:
  - Primary keys: UUID string (generated at application layer)
  - FKs: always indexed (join performance)
  - Composite indexes documented per-table with rationale
  - Unique constraints enforce data integrity at DB level (not just app layer)

Money columns: DECIMAL(19, 4)
  19 digits total, 4 decimal places.
  Chosen for exact arithmetic — no floating point rounding errors.
  See docs/design-decisions.md for full tradeoff discussion.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # user_accounts
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Index on email: unique constraint + fast lookup by email (login flow)
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=True)

    # ──────────────────────────────────────────────────────────────────────
    # group_groups
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "group_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column(
            "created_by_id",
            sa.String(36),
            sa.ForeignKey("user_accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Index on created_by_id: query "groups I created" (admin dashboard use case)
    op.create_index("ix_group_groups_created_by_id", "group_groups", ["created_by_id"])

    # ──────────────────────────────────────────────────────────────────────
    # group_members
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "group_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Unique: prevents the same user joining the same group twice
    op.create_unique_constraint(
        "uq_group_members_group_user", "group_members", ["group_id", "user_id"]
    )
    # Index on group_id: "all members of group G" — used on every expense creation
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    # Index on user_id: "all groups for user U" — used for /users/:id/groups
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    # ──────────────────────────────────────────────────────────────────────
    # expense_expenses
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "expense_expenses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column("paid_by_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("split_type", sa.String(20), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Composite index on (group_id, created_at DESC): paginated expense list for a group
    op.create_index(
        "ix_expense_expenses_group_id_created_at",
        "expense_expenses",
        ["group_id", sa.text("created_at DESC")],
    )
    # Index on paid_by_id: "expenses I paid" filter
    op.create_index("ix_expense_expenses_paid_by_id", "expense_expenses", ["paid_by_id"])

    # ──────────────────────────────────────────────────────────────────────
    # expense_splits
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "expense_splits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "expense_id", sa.String(36), sa.ForeignKey("expense_expenses.id"), nullable=False
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column(
            "group_id",
            sa.String(36),
            sa.ForeignKey("group_groups.id"),
            nullable=False,
            comment="Denormalised from expense for query efficiency — avoids JOIN on balance calc",
        ),
        sa.Column("owed_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Composite index on (expense_id, user_id): load all splits for one expense
    op.create_index(
        "ix_expense_splits_expense_id_user_id", "expense_splits", ["expense_id", "user_id"]
    )
    # Composite index on (group_id, user_id): balance calculation query
    # "all amounts user U owes in group G" — the core ledger read
    op.create_index(
        "ix_expense_splits_group_id_user_id", "expense_splits", ["group_id", "user_id"]
    )

    # ──────────────────────────────────────────────────────────────────────
    # ledger_balances
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "ledger_balances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column(
            "creditor_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False
        ),
        sa.Column("debtor_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column(
            "net_amount",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # One balance row per (group, creditor, debtor) pair
    op.create_unique_constraint(
        "uq_ledger_balances_group_creditor_debtor",
        "ledger_balances",
        ["group_id", "creditor_id", "debtor_id"],
    )
    # Composite index: "all balances in group G" — primary query for balance view
    op.create_index(
        "ix_ledger_balances_group_id_creditor_id",
        "ledger_balances",
        ["group_id", "creditor_id"],
    )
    op.create_index(
        "ix_ledger_balances_group_id_debtor_id",
        "ledger_balances",
        ["group_id", "debtor_id"],
    )

    # ──────────────────────────────────────────────────────────────────────
    # ledger_settlements
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "ledger_settlements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column(
            "from_user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False
        ),
        sa.Column(
            "to_user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False
        ),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # No deleted_at: settlements are immutable audit records
    )
    # Index on group_id: "all settlements in group G" for settlement history
    op.create_index("ix_ledger_settlements_group_id", "ledger_settlements", ["group_id"])
    # Index on from_user_id: "payments made by user U"
    op.create_index(
        "ix_ledger_settlements_from_user_id", "ledger_settlements", ["from_user_id"]
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("ledger_settlements")
    op.drop_table("ledger_balances")
    op.drop_table("expense_splits")
    op.drop_table("expense_expenses")
    op.drop_table("group_members")
    op.drop_table("group_groups")
    op.drop_table("user_accounts")
