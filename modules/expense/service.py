from __future__ import annotations

import abc

from sqlalchemy.ext.asyncio import AsyncSession

from modules.expense.models import (
    CreateExpenseRequest,
    Expense,
    ExpenseORM,
    Split,
    SplitORM,
)
from modules.expense.repository import ExpenseRepository
from modules.expense.strategies import SplitStrategyFactory
from modules.group.repository import GroupRepository
from shared.errors import DomainError, ForbiddenError, NotFoundError
from shared.events import ExpenseCreated, ExpenseSplitEvent, get_event_bus


class IExpenseService(abc.ABC):
    @abc.abstractmethod
    async def create_expense(self, group_id: str, request: CreateExpenseRequest) -> Expense: ...

    @abc.abstractmethod
    async def get_expense(self, expense_id: str) -> Expense: ...

    @abc.abstractmethod
    async def list_expenses(
        self, group_id: str, limit: int = 50, offset: int = 0
    ) -> list[Expense]: ...

    @abc.abstractmethod
    async def delete_expense(self, expense_id: str, deleted_by_id: str) -> None: ...


class ExpenseService(IExpenseService):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ExpenseRepository(session)
        self._group_repo = GroupRepository(session)
        self._bus = get_event_bus()

    async def create_expense(self, group_id: str, request: CreateExpenseRequest) -> Expense:
        # 1 & 2 & 3. Validate group and memberships
        group = await self._group_repo.get_by_id(group_id)
        if not group:
            raise NotFoundError("Group", group_id)

        all_users = set([request.paid_by_id] + request.participants)

        for user_id in all_users:
            if not await self._group_repo.is_member(group_id, user_id):
                raise DomainError(f"User {user_id} is not a member of the group")

        # 4. Strategy
        strategy = SplitStrategyFactory.get(request.split_type)

        # 5. Validate & Calculate
        strategy.validate(request.amount, request.participants, request.splits)
        domain_splits = strategy.calculate_splits(
            request.amount, request.participants, request.splits
        )

        # Invariant check
        if sum(s.owed_amount for s in domain_splits) != request.amount:
            raise DomainError("Fatal: Split amounts do not sum to total")

        # 6. DB Insert
        orm_expense = ExpenseORM(
            group_id=group_id,
            paid_by_id=request.paid_by_id,
            amount=request.amount,
            description=request.description,
            split_type=request.split_type.value,
            notes=request.notes,
        )

        orm_splits = [
            SplitORM(
                user_id=ds.user_id,
                group_id=group_id,
                owed_amount=ds.owed_amount,
                percentage=ds.percentage,
            )
            for ds in domain_splits
        ]

        # ExpenseRepository handles adding both to session
        # However, we need expense.id for splits. SQLAlchemy will populate it on flush.
        self._session.add(orm_expense)
        await self._session.flush()

        for orm_split in orm_splits:
            orm_split.expense_id = orm_expense.id
            self._session.add(orm_split)

        await self._session.flush()

        # 7. Map to domain
        domain_expense = Expense(
            id=orm_expense.id,
            group_id=group_id,
            paid_by_id=request.paid_by_id,
            amount=request.amount,
            description=request.description,
            split_type=request.split_type,
            notes=request.notes,
            splits=domain_splits,
        )

        # 8. Publish Event (Ideally after transaction commit,
        # but our unit of work commits in middleware/router)
        self._bus.publish(
            ExpenseCreated(
                expense_id=domain_expense.id,
                group_id=group_id,
                paid_by_id=domain_expense.paid_by_id,
                amount=domain_expense.amount,
                description=domain_expense.description,
                splits=[
                    ExpenseSplitEvent(user_id=s.user_id, owed_amount=s.owed_amount)
                    for s in domain_splits
                ],
            )
        )

        return domain_expense

    async def delete_expense(self, expense_id: str, deleted_by_id: str) -> None:
        expense, splits = await self._repo.get_by_id_or_raise(expense_id)
        if expense.deleted_at:
            raise NotFoundError("Expense", expense_id)

        # Verify deleted_by_id is paid_by_id or group admin
        if deleted_by_id != expense.paid_by_id:
            deleter = await self._group_repo.get_member(expense.group_id, deleted_by_id)
            if not deleter or deleter.role != "admin":
                raise ForbiddenError("Only the payer or a group admin can delete an expense")

        # In a real app we'd verify it has no settled splits
        await self._repo.soft_delete(expense_id)

    async def get_expense(self, expense_id: str) -> Expense:
        expense_orm, split_orms = await self._repo.get_by_id_or_raise(expense_id)
        if expense_orm.deleted_at:
            raise NotFoundError("Expense", expense_id)
        return self._map_to_domain(expense_orm, split_orms)

    async def list_expenses(
        self, group_id: str, limit: int = 50, offset: int = 0
    ) -> list[Expense]:
        # Verify group exists
        group = await self._group_repo.get_by_id(group_id)
        if not group:
            raise NotFoundError("Group", group_id)

        expenses_with_splits = await self._repo.list_by_group(group_id, limit, offset)
        return [
            self._map_to_domain(expense, splits)
            for expense, splits in expenses_with_splits
        ]

    @staticmethod
    def _map_to_domain(
        expense_orm: ExpenseORM, split_orms: list[SplitORM] | tuple[SplitORM, ...]
    ) -> Expense:
        from modules.expense.models import SplitType

        splits = [Split.model_validate(s) for s in split_orms]
        return Expense(
            id=expense_orm.id,
            group_id=expense_orm.group_id,
            paid_by_id=expense_orm.paid_by_id,
            amount=expense_orm.amount,
            description=expense_orm.description,
            split_type=SplitType(expense_orm.split_type),
            notes=expense_orm.notes,
            splits=splits,
        )
