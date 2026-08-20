"""modules/ai/service.py — AI module public facade."""
from __future__ import annotations

from abc import ABC, abstractmethod

from modules.ai.models import ParseExpenseRequest, ParseExpenseResponse
from modules.group.models import GroupMember


class IAiService(ABC):
    """Public interface for the AI / NLP expense parsing module."""

    @abstractmethod
    async def parse_expense(
        self,
        request: ParseExpenseRequest,
        group_members: list[GroupMember],
    ) -> ParseExpenseResponse:
        """
        Parse natural language into a structured expense preview.

        Parameters
        ----------
        request        : The user's text input.
        group_members  : All members of the group — passed to the LLM as context
                         so it can resolve names to real members. The LLM never
                         sees user IDs; name resolution happens in this service.

        Flow (implemented in Prompt 4):
          1. Build a system prompt with member names and the structured output schema.
          2. Call Claude API with the user's text.
          3. Parse the JSON response (defensively — strip markdown fences, retry once).
          4. Resolve participant names against group_members list.
          5. If any name is ambiguous or absent: return ParsedExpense(is_ambiguous=True).
          6. If all clear: return a fully resolved ParseExpenseResponse(preview=...).
          7. Never create the expense — that's the caller's job after user confirmation.

        Raises:
          UnprocessableError  — ambiguous names, missing amount, etc.
          ExternalServiceError — Claude API timeout or HTTP error
        """
        ...


class AiService(IAiService):
    """Stub — full implementation in Prompt 4."""

    async def parse_expense(
        self,
        request: ParseExpenseRequest,
        group_members: list[GroupMember],
    ) -> ParseExpenseResponse:
        raise NotImplementedError("Implemented in Prompt 4")
