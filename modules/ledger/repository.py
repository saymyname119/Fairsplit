from __future__ import annotations

from typing import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.ledger.models import LedgerBalanceORM, SettlementORM
from shared.errors import NotFoundError


class LedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_balance(
        self, group_id: str, creditor_id: str, debtor_id: str
    ) -> LedgerBalanceORM | None:
        stmt = select(LedgerBalanceORM).where(
            LedgerBalanceORM.group_id == group_id,
            LedgerBalanceORM.creditor_id == creditor_id,
            LedgerBalanceORM.debtor_id == debtor_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_balance_for_update(
        self, group_id: str, creditor_id: str, debtor_id: str
    ) -> LedgerBalanceORM | None:
        stmt = (
            select(LedgerBalanceORM)
            .where(
                LedgerBalanceORM.group_id == group_id,
                LedgerBalanceORM.creditor_id == creditor_id,
                LedgerBalanceORM.debtor_id == debtor_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_balance(
        self, group_id: str, creditor_id: str, debtor_id: str, amount_delta: Decimal
    ) -> LedgerBalanceORM:
        """
        Since we need `with_for_update`, we do a select and then insert or update.
        """
        balance = await self.get_balance_for_update(group_id, creditor_id, debtor_id)
        if balance:
            balance.net_amount += amount_delta
        else:
            balance = LedgerBalanceORM(
                group_id=group_id,
                creditor_id=creditor_id,
                debtor_id=debtor_id,
                net_amount=amount_delta,
            )
            self._session.add(balance)
        
        await self._session.flush()
        return balance

    async def get_group_balances(self, group_id: str) -> Sequence[LedgerBalanceORM]:
        stmt = select(LedgerBalanceORM).where(LedgerBalanceORM.group_id == group_id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def record_settlement(self, settlement: SettlementORM) -> SettlementORM:
        self._session.add(settlement)
        await self._session.flush()
        return settlement
