"""
modules/ledger/models.py
─────────────────────────
Domain and ORM models for the Ledger module.

The Ledger is the financial heart of the system.
It maintains *net* balances between pairs of users within a group.

Net balance example:
  Alice pays $30 for dinner (Bob owes $15).
  Bob pays $20 for coffee (Alice owes $10).
  → Net: Bob owes Alice $5 (not two separate debts of $15 and $10).
  → Only one row in ledger_balances: (alice_id, bob_id, group_id) → 5.00

Why net balances?
  Storing per-expense debts would require O(expenses) reads for the balance view.
  Net balance: O(1) read per user-pair. This is the classic Splitwise insight.
  Tradeoff: if we ever need "show me the expense that caused this debt", we need
  to join back to expense_splits — which is fine and indexed for it.

Settlement table:
  Separate from ledger_balances for audit purposes.
  A settlement is a financial event (money changed hands) — we soft-delete
  expenses, but settlements are immutable records once recorded.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ─────────────────────────────────────────────────────────────────────────────
# ORM Models (private to this module)
# ─────────────────────────────────────────────────────────────────────────────

class LedgerBalanceORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Database table: ledger_balances
    One row per (creditor, debtor, group) pair.

    creditor_id → the user who is owed money (positive balance = money owed TO them)
    debtor_id   → the user who owes money

    Convention: always store with creditor_id < debtor_id (alphabetically)
    to prevent duplicate rows. When debtor_id owes creditor_id, use a positive
    net_amount. When it flips, flip the sign and swap IDs.

    Composite unique constraint enforces one row per pair per group.
    Composite index on (group_id, creditor_id) and (group_id, debtor_id) for
    the two most common query patterns:
      "what does user X owe/is owed in group G?"
    """

    __tablename__ = "ledger_balances"
    __table_args__ = (
        UniqueConstraint(
            "group_id", "creditor_id", "debtor_id",
            name="uq_ledger_balances_group_creditor_debtor",
        ),
    )

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_groups.id"), nullable=False, index=True
    )
    creditor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    debtor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4), nullable=False, default=Decimal("0")
    )


class SettlementORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Database table: ledger_settlements
    Immutable record of a payment between two users.
    Note: no SoftDeleteMixin — settlements are permanent audit records.
    """

    __tablename__ = "ledger_settlements"

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_groups.id"), nullable=False, index=True
    )
    from_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    to_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# Domain Models (public)
# ─────────────────────────────────────────────────────────────────────────────

class Balance(BaseModel):
    """Net balance between two users in a group."""

    creditor_id: str
    debtor_id: str
    group_id: str
    net_amount: Decimal  # Amount debtor owes creditor

    model_config = {"from_attributes": True}


class SimplifiedDebt(BaseModel):
    """
    One transaction in a simplified settlement plan.
    getSimplifiedBalances() returns a list of these — the minimum set of
    payments needed to settle the entire group.
    """

    from_user_id: str   # pays
    to_user_id: str     # receives
    amount: Decimal


class Settlement(BaseModel):
    """Public domain representation of a recorded settlement."""

    id: str
    group_id: str
    from_user_id: str
    to_user_id: str
    amount: Decimal
    notes: str | None = None

    model_config = {"from_attributes": True}


class CreateSettlementRequest(BaseModel):
    """Input schema for recording a settlement."""

    from_user_id: str
    to_user_id: str
    amount: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)


class UserBalance(BaseModel):
    """
    A user's aggregated balance across all groups.
    total_owed: total amount this user owes others (sum across all groups).
    total_owed_to: total amount others owe this user.
    net: total_owed_to - total_owed (positive = net creditor).
    """

    user_id: str
    total_owed: Decimal
    total_owed_to: Decimal
    net: Decimal
    by_group: dict[str, Decimal] = Field(default_factory=dict)


class SimplifiedBalanceResult(BaseModel):
    """Result of the greedy net-flow simplification algorithm."""

    simplified: list[SimplifiedDebt]
    net_by_user: dict[str, Decimal]
