"""
modules/expense/models.py
──────────────────────────
Domain and ORM models for the Expense module.

Money representation: DECIMAL(19, 4)
─────────────────────────────────────
All monetary values use Python's Decimal type (not float) and are stored as
DECIMAL(19, 4) in Postgres. This is a deliberate design decision documented in
docs/design-decisions.md.

Summary of the tradeoff:
  float  → fast, but 0.1 + 0.2 ≠ 0.3 in IEEE 754. Unacceptable for money.
  int (cents) → exact, zero storage overhead, common in payment systems (Stripe).
  Decimal → exact, human-readable (1250.00 vs 125000), matches DB DECIMAL.

We chose Decimal because:
  1. The product exposes decimal amounts in the UI (not cents).
  2. DECIMAL(19,4) gives us 15 digits of precision — more than enough for any
     realistic multi-currency scenario.
  3. Python's decimal.Decimal is exact: Decimal("0.1") + Decimal("0.2") == Decimal("0.3").

Rounding: any split arithmetic that produces a fraction is rounded to 4 decimal
places using ROUND_HALF_UP. Rounding residuals (the "missing cent" problem) are
handled in the split strategy layer (see Prompt 2).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────


class SplitType(StrEnum):
    """
    How an expense is divided among participants.
    Each type maps to a concrete SplitStrategy (implemented in Prompt 2).
    """

    EQUAL = "equal"  # Amount / N, remainder on first participant
    PERCENT = "percent"  # Percentages must sum to 100
    EXACT = "exact"  # Exact amounts must sum to total


# ─────────────────────────────────────────────────────────────────────────────
# ORM Models (private to this module)
# ─────────────────────────────────────────────────────────────────────────────


class ExpenseORM(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Database table: expense_expenses
    Index on group_id: primary access pattern is "all expenses in group G"
    Index on paid_by_id: for "expenses I paid" user-facing queries
    """

    __tablename__ = "expense_expenses"

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_groups.id"), nullable=False, index=True
    )
    paid_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=19, scale=4), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    split_type: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class SplitORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Database table: expense_splits
    One row per participant per expense.

    Composite index on (expense_id, user_id): join pattern when loading
    all splits for an expense.
    Index on (group_id, user_id): used by the ledger module when calculating
    net balances — "all splits for user U in group G".
    """

    __tablename__ = "expense_splits"

    expense_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("expense_expenses.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    group_id: Mapped[str] = mapped_column(
        # Denormalised for query efficiency: avoids a JOIN to expense_expenses
        # on every balance calculation. This is a deliberate denormalisation.
        String(36),
        ForeignKey("group_groups.id"),
        nullable=False,
        index=True,
    )
    owed_amount: Mapped[Decimal] = mapped_column(Numeric(precision=19, scale=4), nullable=False)
    # For PERCENT splits: store the percentage for audit/display purposes
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(precision=7, scale=4), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# Domain Models (public — returned by service facade)
# ─────────────────────────────────────────────────────────────────────────────


class Split(BaseModel):
    """One participant's share of an expense."""

    user_id: str
    owed_amount: Decimal
    percentage: Decimal | None = None

    model_config = {"from_attributes": True}


class Expense(BaseModel):
    """Public domain representation of an expense."""

    id: str
    group_id: str
    paid_by_id: str
    amount: Decimal
    description: str
    split_type: SplitType
    splits: list[Split] = Field(default_factory=list)
    notes: str | None = None

    model_config = {"from_attributes": True}


class SplitInput(BaseModel):
    """Input for one participant in a split — used in CreateExpenseRequest."""

    user_id: str
    value: Decimal = Field(gt=0)  # percentage (0-100) or exact amount depending on split_type


class CreateExpenseRequest(BaseModel):
    """Input schema for expense creation."""

    paid_by_id: str
    amount: Decimal = Field(gt=0, description="Total expense amount")
    description: str = Field(min_length=1, max_length=500)
    split_type: SplitType
    participants: list[str] = Field(min_length=2, description="User IDs of all participants")
    splits: list[SplitInput] | None = Field(
        default=None,
        description="Required for PERCENT and EXACT split types. Omit for EQUAL.",
    )
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("amount")
    @classmethod
    def amount_precision(cls, v: Decimal) -> Decimal:
        """Enforce max 4 decimal places on input."""
        return round(v, 4)


class UpdateExpenseRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    amount: Decimal | None = Field(default=None, gt=0)
    paid_by_id: str | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("amount")
    @classmethod
    def amount_precision(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            return round(v, 4)
        return v

