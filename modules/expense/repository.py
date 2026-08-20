from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.expense.models import ExpenseORM, SplitORM
from shared.errors import NotFoundError


class ExpenseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_expense(self, expense: ExpenseORM, splits: list[SplitORM]) -> ExpenseORM:
        self._session.add(expense)
        self._session.add_all(splits)
        await self._session.flush()
        return expense

    async def get_by_id(self, expense_id: str) -> ExpenseORM | None:
        stmt = select(ExpenseORM).where(ExpenseORM.id == expense_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_splits(
        self, expense_id: str
    ) -> tuple[ExpenseORM | None, Sequence[SplitORM]]:
        stmt = select(ExpenseORM).where(ExpenseORM.id == expense_id)
        result = await self._session.execute(stmt)
        expense = result.scalar_one_or_none()

        if not expense:
            return None, []

        split_stmt = select(SplitORM).where(SplitORM.expense_id == expense_id)
        split_result = await self._session.execute(split_stmt)
        splits = split_result.scalars().all()

        return expense, splits

    async def get_by_id_or_raise(self, expense_id: str) -> tuple[ExpenseORM, Sequence[SplitORM]]:
        expense, splits = await self.get_by_id_with_splits(expense_id)
        if not expense:
            raise NotFoundError("Expense", expense_id)
        return expense, splits

    async def soft_delete(self, expense_id: str) -> None:
        stmt = (
            update(ExpenseORM)
            .where(ExpenseORM.id == expense_id)
            .values(deleted_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
