"""api/routes/ledger.py — Balance and settlement endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from modules.ledger.models import CreateSettlementRequest

router = APIRouter()


@router.get(
    "/{group_id}/balances",
    summary="Get group balances",
    responses={
        200: {"description": "Net balances between all member pairs"},
        404: {"description": "Group not found"},
    },
)
async def get_group_balances(group_id: str) -> JSONResponse:
    """
    GET /groups/:id/balances

    Returns net balances between all member pairs in the group.
    Cache strategy (Prompt 3):
      1. Check Redis key: balances:group:{group_id}
      2. Cache hit → return cached data
      3. Cache miss → call LedgerService.get_group_balances(), cache result, return

    Invalidated by: ExpenseCreated and SettlementRecorded events.
    """
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 3"})


@router.get(
    "/{group_id}/balances/simplified",
    summary="Get simplified settlement plan",
    responses={
        200: {"description": "Minimum transactions to settle the group"},
        404: {"description": "Group not found"},
    },
)
async def get_simplified_balances(group_id: str) -> JSONResponse:
    """
    GET /groups/:id/balances/simplified
    Returns minimum set of payments to settle all debts in the group.
    Full implementation in Prompt 2 (debt simplification algorithm).
    """
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 2"})


@router.post(
    "/{group_id}/settle",
    summary="Record a settlement payment",
    status_code=201,
    responses={
        201: {"description": "Settlement recorded, balances updated"},
        400: {"description": "Invalid settlement data"},
        404: {"description": "Group or user not found"},
        409: {"description": "Settlement amount exceeds outstanding balance"},
    },
)
async def record_settlement(group_id: str, request: CreateSettlementRequest) -> JSONResponse:
    """
    POST /groups/:id/settle

    Records that from_user paid to_user amount.
    Uses SELECT FOR UPDATE to prevent concurrent settlement race conditions.
    Full implementation in Prompt 2.
    """
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 2"})
