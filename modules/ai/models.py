"""
modules/ai/models.py
─────────────────────
Domain models for the AI / natural language expense parsing module.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from modules.expense.models import SplitType


class ParsedSplitValue(BaseModel):
    """One participant's value in a parsed non-equal split."""
    name: str   # raw name from LLM — needs resolving to user_id
    value: Decimal  # percentage or exact amount


class ParsedExpense(BaseModel):
    """
    Structured expense data extracted by the LLM from natural language.
    This is NOT a committed expense — it's a preview for user confirmation.

    Why preview instead of auto-create?
      Money actions must not be auto-committed on ambiguous input.
      The user must confirm before the expense is created.
      See docs/design-decisions.md §AI for full rationale.
    """

    amount: Decimal
    description: str
    paid_by_name: str           # resolved to paid_by_id after member lookup
    paid_by_id: str | None = None  # set after name resolution
    participant_names: list[str]  # raw names from LLM
    participant_ids: list[str] = Field(default_factory=list)  # resolved
    split_type: SplitType
    splits: list[ParsedSplitValue] = Field(default_factory=list)

    # Populated if any ambiguity was detected
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class ParseExpenseRequest(BaseModel):
    """Input for the natural language expense parsing endpoint."""

    text: str = Field(
        min_length=5,
        max_length=1000,
        description="Natural language description of the expense",
    )


class ParseExpenseResponse(BaseModel):
    """
    Response from POST /groups/:id/expenses/parse.
    Always a preview — caller must POST to /expenses to actually create it.
    """

    preview: ParsedExpense
    raw_llm_output: str | None = None  # included in dev/test for debugging
    confirmation_required: bool = True  # always True — by design
