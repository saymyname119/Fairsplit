"""tests/unit/test_expense_service.py — ExpenseService unit tests."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.expense import ExpenseService, UpdateExpenseRequest
from modules.expense.models import ExpenseORM, SplitORM
from shared.errors import ForbiddenError, NotFoundError


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def expense_service(mock_session):
    return ExpenseService(mock_session)


def _make_mock_expense(
    expense_id: str = "exp-1",
    group_id: str = "g1",
) -> ExpenseORM:
    e = MagicMock(spec=ExpenseORM)
    e.id = expense_id
    e.group_id = group_id
    e.paid_by_id = "user-1"
    e.amount = Decimal("30")
    e.description = "Dinner"
    e.split_type = "equal"
    e.notes = None
    e.deleted_at = None
    e.created_at = datetime.now()
    return e


def _make_mock_split(
    expense_id: str = "exp-1",
    user_id: str = "user-1",
    owed: Decimal = Decimal("15"),
) -> SplitORM:
    s = MagicMock(spec=SplitORM)
    s.expense_id = expense_id
    s.user_id = user_id
    s.group_id = "g1"
    s.owed_amount = owed
    s.percentage = None
    return s


@pytest.mark.asyncio
async def test_get_expense_happy_path(expense_service):
    mock_expense = _make_mock_expense()
    mock_splits = [
        _make_mock_split(user_id="user-1", owed=Decimal("15")),
        _make_mock_split(user_id="user-2", owed=Decimal("15")),
    ]
    expense_service._repo.get_by_id_or_raise = AsyncMock(
        return_value=(mock_expense, mock_splits)
    )

    result = await expense_service.get_expense("exp-1")
    assert result.id == "exp-1"
    assert result.amount == Decimal("30")
    assert len(result.splits) == 2


@pytest.mark.asyncio
async def test_get_expense_not_found(expense_service):
    expense_service._repo.get_by_id_or_raise = AsyncMock(
        side_effect=NotFoundError("Expense", "exp-999")
    )

    with pytest.raises(NotFoundError):
        await expense_service.get_expense("exp-999")


@pytest.mark.asyncio
async def test_get_expense_soft_deleted(expense_service):
    mock_expense = _make_mock_expense()
    mock_expense.deleted_at = datetime.now()
    expense_service._repo.get_by_id_or_raise = AsyncMock(
        return_value=(mock_expense, [])
    )

    with pytest.raises(NotFoundError):
        await expense_service.get_expense("exp-1")


@pytest.mark.asyncio
async def test_list_expenses_happy_path(expense_service):
    mock_group = MagicMock()
    expense_service._group_repo.get_by_id = AsyncMock(return_value=mock_group)

    expense1 = _make_mock_expense(expense_id="exp-1")
    expense2 = _make_mock_expense(expense_id="exp-2")
    splits1 = [_make_mock_split(expense_id="exp-1")]
    splits2 = [_make_mock_split(expense_id="exp-2")]

    expense_service._repo.list_by_group = AsyncMock(
        return_value=[(expense1, splits1), (expense2, splits2)]
    )

    result = await expense_service.list_expenses("g1", limit=50, offset=0)
    assert len(result) == 2
    assert result[0].id == "exp-1"
    assert result[1].id == "exp-2"


@pytest.mark.asyncio
async def test_list_expenses_group_not_found(expense_service):
    expense_service._group_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await expense_service.list_expenses("g-missing")


@pytest.mark.asyncio
async def test_update_expense_happy_path(expense_service):
    mock_expense = _make_mock_expense()
    mock_splits = [_make_mock_split()]
    expense_service._repo.get_by_id_or_raise = AsyncMock(
        return_value=(mock_expense, mock_splits)
    )

    req = UpdateExpenseRequest(description="Updated Dinner", amount=Decimal("45"))
    updated = await expense_service.update_expense("exp-1", req, updated_by_id="user-1")

    assert updated.description == "Updated Dinner"
    assert updated.amount == Decimal("45")
    assert mock_expense.description == "Updated Dinner"


@pytest.mark.asyncio
async def test_update_expense_unauthorized(expense_service):
    mock_expense = _make_mock_expense()
    expense_service._repo.get_by_id_or_raise = AsyncMock(
        return_value=(mock_expense, [])
    )
    expense_service._group_repo.get_member = AsyncMock(return_value=None)

    req = UpdateExpenseRequest(description="Hacked")
    with pytest.raises(ForbiddenError):
        await expense_service.update_expense("exp-1", req, updated_by_id="other-user")

