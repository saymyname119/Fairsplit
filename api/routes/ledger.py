"""api/routes/ledger.py — Balance and settlement endpoints."""

from __future__ import annotations

import json
from typing import Any

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
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Balance]:
    """
    GET /groups/:id/balances

    Returns net balances between all member pairs in the group.
    Cache strategy (write-invalidate):
      1. Check Redis key: balances:group:{group_id}
      2. Cache hit → deserialize and return
      3. Cache miss → call LedgerService.get_group_balances(), cache result, return
    """
    cache_key = balance_cache_key(group_id)

    # 1. Try cache
    cached_data = await get_cached(cache_key)
    if cached_data is not None:
        raw_list = json.loads(cached_data)
        return [Balance.model_validate(b) for b in raw_list]

    # 2. Cache miss — compute from DB
    service = LedgerService(db)
    balances = await service.get_group_balances(group_id)

    # 3. Write to cache (TTL handles safety net)
    await set_cached(cache_key, [b.model_dump() for b in balances])

    return balances


@router.get(
    "/{group_id}/balances/simplified",
    summary="Get simplified settlement plan",
    response_model=SimplifiedBalanceResult,
    responses={
        200: {"description": "Minimum transaction settlement plan"},
        404: {"description": "Group not found"},
    },
)
async def get_simplified_balances(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SimplifiedBalanceResult:
    """
    GET /groups/:id/balances/simplified
    Returns the minimum transaction settlement plan (greedy net-flow algorithm).
    """
    service = LedgerService(db)
    return await service.get_simplified_balances(group_id)


@router.post(
    "/{group_id}/settle",
    summary="Record a settlement payment",
    status_code=201,
    response_model=Settlement,
    responses={
        201: {"description": "Settlement recorded"},
        400: {"description": "Invalid amount or self-settlement"},
        404: {"description": "Group or user not found"},
    },
)
async def record_settlement(
    group_id: str,
    request: CreateSettlementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Settlement:
    """
    POST /groups/:id/settle

    Records that from_user paid to_user amount.
    """
    service = LedgerService(db)
    return await service.record_settlement(group_id, request)
