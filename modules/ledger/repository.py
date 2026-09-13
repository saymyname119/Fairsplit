from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.ledger.models import LedgerBalanceORM, SettlementORM


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

    async def get_group_balances_for_update(
        self, group_id: str
    ) -> Sequence[LedgerBalanceORM]:
        """
        Pessimistic row-level lock on ALL existing balance rows for a group.
        Ordered deterministically by (creditor_id, debtor_id) to eliminate deadlocks.
        """
        stmt = (
            select(LedgerBalanceORM)
            .where(LedgerBalanceORM.group_id == group_id)
            .order_by(LedgerBalanceORM.creditor_id, LedgerBalanceORM.debtor_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def upsert_balance(
        self, group_id: str, creditor_id: str, debtor_id: str, amount_delta: Decimal
    ) -> LedgerBalanceORM:
        """
        Acquires row-level lock on the balance row and applies amount_delta.
        If row doesn't exist, inserts a new balance record.
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
        stmt = (
            select(LedgerBalanceORM)
            .where(LedgerBalanceORM.group_id == group_id)
            .order_by(LedgerBalanceORM.creditor_id, LedgerBalanceORM.debtor_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_group_settlements(self, group_id: str) -> Sequence[SettlementORM]:
        """Fetch all settlement payments recorded in a group."""
        stmt = (
            select(SettlementORM)
            .where(SettlementORM.group_id == group_id)
            .order_by(SettlementORM.created_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active_group_splits(
        self, group_id: str
    ) -> list[tuple[str, str, Decimal]]:
        """
        Returns list of (payer_id, participant_user_id, owed_amount)
        for all non-deleted expenses in a group.
        Uses SQL JOIN to remain decoupled from expense module ORMs.
        """
        stmt = text("""
            SELECT e.paid_by_id, s.user_id, s.owed_amount
            FROM expense_splits s
            JOIN expense_expenses e ON s.expense_id = e.id
            WHERE e.group_id = :group_id AND e.deleted_at IS NULL
        """)
        result = await self._session.execute(stmt, {"group_id": group_id})
        return [(str(r[0]), str(r[1]), Decimal(str(r[2]))) for r in result.all()]

    async def record_settlement(self, settlement: SettlementORM) -> SettlementORM:
        self._session.add(settlement)
        await self._session.flush()
        return settlement

    async def get_user_balances(self, user_id: str) -> Sequence[LedgerBalanceORM]:
        """Get all balance rows where the user is either creditor or debtor."""
        stmt = select(LedgerBalanceORM).where(
            (LedgerBalanceORM.creditor_id == user_id)
            | (LedgerBalanceORM.debtor_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def has_outstanding_balance(self, group_id: str, user_id: str) -> bool:
        """Check if a user has any non-zero balances in a group."""
        stmt = (
            select(LedgerBalanceORM.id)
            .where(
                LedgerBalanceORM.group_id == group_id,
                (LedgerBalanceORM.creditor_id == user_id)
                | (LedgerBalanceORM.debtor_id == user_id),
                LedgerBalanceORM.net_amount != 0,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None
