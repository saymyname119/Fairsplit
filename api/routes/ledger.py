"""api/routes/ledger.py — Balance and settlement endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_dependency import get_current_user
from modules.ledger import (
    Balance,
    CreateSettlementRequest,
    LedgerService,
    Settlement,
    SimplifiedBalanceResult,
)
from shared.cache import balance_cache_key, get_cached, set_cached
from shared.db.session import get_db

router = APIRouter()


@router.get(
    "/{group_id}/balances",
    summary="Get group balances",
    response_model=list[Balance],
    responses={
        200: {"description": "Net balances between all member pairs"},
        404: {"description": "Group not found"},
    },
)
async def get_group_balances(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[Balance]:
    """
    GET /groups/:id/balances

    Returns net balances between all member pairs in the group.
    Cache strategy (write-invalidate):
      1. Check Redis key: balances:group:{group_id}
      2. Cache hit → deserialize and return
      3. Cache miss → call LedgerService.get_group_balances(), cache result, return

    Invalidated by: ExpenseCreated and SettlementRecorded event handlers.
    """
    cache_key = balance_cache_key(group_id)

    # 1. Try cache
    cached = await get_cached(cache_key)
    if cached is not None:
        data = json.loads(cached)
        return [Balance(**item) for item in data]

    # 2. Cache miss — fetch from DB
    service = LedgerService(db)
    balances = await service.get_group_balances(group_id)

    # 3. Cache the result
    await set_cached(cache_key, [b.model_dump() for b in balances])

    return balances


@router.get(
    "/{group_id}/balances/simplified",
    summary="Get simplified settlement plan",
    response_model=SimplifiedBalanceResult,
    responses={
        200: {"description": "Minimum transactions to settle the group"},
        404: {"description": "Group not found"},
    },
)
async def get_simplified_balances(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SimplifiedBalanceResult:
    """
    GET /groups/:id/balances/simplified
    Returns minimum set of payments to settle all debts in the group.
    Uses the Greedy Net-Flow algorithm (O(N log N)).
    """
    service = LedgerService(db)
    return await service.get_simplified_balances(group_id)


@router.post(
    "/{group_id}/settle",
    summary="Record a settlement payment",
    status_code=201,
    response_model=Settlement,
    responses={
        201: {"description": "Settlement recorded, balances updated"},
        400: {"description": "Invalid settlement data"},
        404: {"description": "Group or user not found"},
        409: {"description": "Settlement amount exceeds outstanding balance"},
    },
)
async def record_settlement(
    group_id: str,
    request: CreateSettlementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Settlement:
    """
    POST /groups/:id/settle

    Records that from_user paid to_user amount.
    Uses SELECT FOR UPDATE to prevent concurrent settlement race conditions.
    """
    service = LedgerService(db)
    return await service.record_settlement(group_id, request)
