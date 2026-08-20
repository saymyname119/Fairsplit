from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from modules.ledger.models import LedgerBalanceORM
from modules.ledger.service import LedgerService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def ledger_service(mock_session):
    return LedgerService(mock_session)


@pytest.mark.asyncio
async def test_debt_simplification_three_people_chain(ledger_service):
    # A owes B $10, B owes C $5
    # Balances: A-B: B is owed 10 (creditor B, debtor A, net 10)
    # B-C: C is owed 5 (creditor C, debtor B, net 5)

    mock_balances = [
        LedgerBalanceORM(group_id="g1", creditor_id="B", debtor_id="A", net_amount=Decimal("10")),
        LedgerBalanceORM(group_id="g1", creditor_id="C", debtor_id="B", net_amount=Decimal("5")),
    ]
    ledger_service._repo.get_group_balances = AsyncMock(return_value=mock_balances)

    result = await ledger_service.get_simplified_balances("g1")

    # Expected Net: A: -10, B: +10 - 5 = +5, C: +5
    # Simplified: A->B 5, A->C 5 (or similar, max 2 transactions)
    assert len(result.simplified) <= 2

    # Validate the final balances match the expected net balances
    simulated_net = {"A": Decimal("0"), "B": Decimal("0"), "C": Decimal("0")}
    for debt in result.simplified:
        simulated_net[debt.from_user_id] -= debt.amount
        simulated_net[debt.to_user_id] += debt.amount

    assert simulated_net["A"] == Decimal("-10")
    assert simulated_net["B"] == Decimal("5")
    assert simulated_net["C"] == Decimal("5")


@pytest.mark.asyncio
async def test_debt_simplification_circular(ledger_service):
    # A owes B 10, B owes C 10, C owes A 10
    mock_balances = [
        LedgerBalanceORM(group_id="g1", creditor_id="B", debtor_id="A", net_amount=Decimal("10")),
        LedgerBalanceORM(group_id="g1", creditor_id="C", debtor_id="B", net_amount=Decimal("10")),
        LedgerBalanceORM(group_id="g1", creditor_id="A", debtor_id="C", net_amount=Decimal("10")),
    ]
    ledger_service._repo.get_group_balances = AsyncMock(return_value=mock_balances)

    result = await ledger_service.get_simplified_balances("g1")

    # Expected Net: A: 0, B: 0, C: 0
    # Simplified: []
    assert len(result.simplified) == 0
    assert result.net_by_user["A"] == Decimal("0")
    assert result.net_by_user["B"] == Decimal("0")
    assert result.net_by_user["C"] == Decimal("0")
