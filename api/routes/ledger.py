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
from modules.ledger.models import ReverseSettlementRequest
from shared.cache import balance_cache_key, get_cached, set_cached
from shared.db.session import get_db


async def require_member(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    from modules.group.repository import GroupRepository
    from shared.errors import ForbiddenError

    if not await GroupRepository(db).is_member(group_id, current_user["user_id"]):
        raise ForbiddenError("Group membership required")


router = APIRouter(dependencies=[Depends(require_member)])


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
    Cache strategy (versioned cache-aside):
      1. Check Redis key: balances:group:{group_id}:v{version}
      2. Cache hit → deserialize and return
      3. Cache miss → call LedgerService.get_group_balances(), cache result, return
    """
    from modules.ledger.repository import LedgerRepository

    state = await LedgerRepository(db).lock_group(group_id)
    cache_key = f"{balance_cache_key(group_id)}:v{state.version}"

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
        200: {"description": "Reduced transaction settlement plan"},
        404: {"description": "Group not found"},
    },
)
async def get_simplified_balances(
    group_id: str,
    for_update: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SimplifiedBalanceResult:
    """
    GET /groups/:id/balances/simplified
    Returns a reduced transaction settlement plan (greedy net-flow algorithm).
    If for_update=True, acquires row-level locks on balance rows to prevent concurrent mutations.
    """
    from modules.ledger.repository import LedgerRepository

    await LedgerRepository(db).lock_group(group_id)
    service = LedgerService(db)
    from modules.group.service import GroupService
    result = await service.get_simplified_balances(group_id, for_update=for_update)
    result.currency = (await GroupService(db).get_group(group_id)).currency
    return result


@router.post(
    "/{group_id}/balances/recalculate",
    summary="Recalculate group balances with row-level locks",
    response_model=list[Balance],
    responses={
        200: {"description": "Recalculated balances for group"},
        404: {"description": "Group not found"},
    },
)
async def recalculate_group_balances(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Balance]:
    """
    POST /groups/:id/balances/recalculate
    Recalculates ground-truth net balances from active expenses and settlements.
    Uses SELECT FOR UPDATE row-level locks and atomically invalidates Redis balance cache.
    """
    service = LedgerService(db)
    return await service.recalculate_group_balances(group_id)


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


@router.get("/{group_id}/settlements", response_model=list[Settlement])
async def list_settlements(group_id: str, db: AsyncSession = Depends(get_db)):
    from modules.ledger.repository import LedgerRepository

    return [
        Settlement.model_validate(s)
        for s in await LedgerRepository(db).get_group_settlements(group_id)
    ]


@router.post("/{group_id}/settlements/{settlement_id}/reverse", response_model=Settlement)
async def reverse_settlement(
    group_id: str,
    settlement_id: str,
    request: ReverseSettlementRequest,
    db: AsyncSession = Depends(get_db),
):
    return await LedgerService(db).reverse_settlement(group_id, settlement_id, request)


@router.get("/{group_id}/notifications")
async def notifications(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    from sqlalchemy import select

    from modules.notification.outbox import NotificationORM

    result = await db.execute(
        select(NotificationORM)
        .where(
            NotificationORM.group_id == group_id,
            NotificationORM.user_id == current_user["user_id"],
        )
        .order_by(NotificationORM.created_at.desc())
        .limit(100)
    )
    return [
        {"id": n.id, "title": n.title, "body": n.body, "created_at": n.created_at}
        for n in result.scalars()
    ]


@router.get("/{group_id}/journal")
async def journal_history(group_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    from modules.ledger.models import JournalORM

    rows = (
        await db.execute(
            select(JournalORM)
            .where(JournalORM.group_id == group_id)
            .order_by(JournalORM.created_at, JournalORM.id)
            .limit(500)
        )
    ).scalars()
    return [
        {
            "id": r.id,
            "reason": r.reason,
            "created_at": r.created_at,
            "postings": [
                {"user_id": r.credit_user_id, "amount": r.amount},
                {"user_id": r.debit_user_id, "amount": -r.amount},
            ],
        }
        for r in rows
    ]
