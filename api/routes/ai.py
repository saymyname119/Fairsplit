"""api/routes/ai.py — AI / natural language expense parsing endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from modules.ai.models import ParseExpenseRequest

router = APIRouter()


@router.post(
    "/{group_id}/expenses/parse",
    summary="Parse natural language into expense preview",
    responses={
        200: {"description": "Parsed expense preview (not yet created — confirm first)"},
        422: {"description": "Ambiguous input — clarification required"},
        502: {"description": "Claude API unavailable"},
    },
)
async def parse_expense(group_id: str, request: ParseExpenseRequest) -> JSONResponse:
    """
    POST /groups/:id/expenses/parse

    Accepts natural language text and returns a structured expense preview.
    Does NOT create the expense — the caller must confirm and POST to
    /groups/:id/expenses to actually create it.

    Example input:
        { "text": "I paid 800 for dinner with Raj and Priya, split equally" }

    Full implementation in Prompt 4 (AI module + Claude API integration).
    """
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 4"})
