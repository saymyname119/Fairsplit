from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.ledger import CreateSettlementRequest, LedgerService
from shared.errors import ConflictError
from shared.events import ExpenseCreated, ExpenseSplitEvent


@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def ledger_service(mock_session):
    return LedgerService(mock_session)

@pytest.mark.asyncio
async def test_handle_expense_created(ledger_service):
    ledger_service._repo.upsert_balance = AsyncMock()

    # Alice pays $30, Bob owes $15
    event = ExpenseCreated(
        expense_id="exp-1",
        group_id="group-1",
        paid_by_id="alice",
        amount=Decimal("30"),
        description="Dinner",
        splits=[
            ExpenseSplitEvent(user_id="alice", owed_amount=Decimal("15")),
            ExpenseSplitEvent(user_id="bob", owed_amount=Decimal("15")),
        ]
    )

    await ledger_service.handle_expense_created(event)

    # Check upsert_balance call
    ledger_service._repo.upsert_balance.assert_called_once_with(
        "group-1", "alice", "bob", Decimal("15")  # alice < bob, alice is creditor
    )

@pytest.mark.asyncio
async def test_record_settlement_reduces_balance(ledger_service):
    request = CreateSettlementRequest(
        from_user_id="bob",
        to_user_id="alice",
        amount=Decimal("10")
    )

    mock_balance = AsyncMock()
    mock_balance.net_amount = Decimal("15")  # alice is owed 15 by bob
    ledger_service._repo.get_balance_for_update = AsyncMock(return_value=mock_balance)

    async def mock_record_settlement(settlement):
        settlement.id = "s-1"
        return settlement

    ledger_service._repo.record_settlement = AsyncMock(side_effect=mock_record_settlement)
    ledger_service._bus.publish = AsyncMock()

    settlement = await ledger_service.record_settlement("group-1", request)
    assert settlement.amount == Decimal("10")
    assert mock_balance.net_amount == Decimal("5")  # Reduced from 15 to 5

@pytest.mark.asyncio
async def test_record_settlement_exceeds_balance(ledger_service):
    request = CreateSettlementRequest(
        from_user_id="bob",
        to_user_id="alice",
        amount=Decimal("20")
    )

    mock_balance = AsyncMock()
    mock_balance.net_amount = Decimal("15")
    ledger_service._repo.get_balance_for_update = AsyncMock(return_value=mock_balance)

    with pytest.raises(ConflictError, match="exceeds balance"):
        await ledger_service.record_settlement("group-1", request)
