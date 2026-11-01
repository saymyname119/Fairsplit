from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.ledger.models import LedgerBalanceORM
from modules.ledger.service import LedgerService


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def ledger_service(mock_session):
    mock_session.add = MagicMock()
    service = LedgerService(mock_session)
    service._repo.lock_group = AsyncMock(return_value=MagicMock(version=0))
    service._repo.version = AsyncMock(return_value=0)
    service._repo.find_retry = AsyncMock(return_value=None)
    return service


@pytest.mark.asyncio
async def test_debt_simplification_three_people_chain(ledger_service):
    # A owes B $10, B owes C $5
    # Balances: A-B: B is owed 10 (creditor B, debtor A, net 10)
    # B-C: C is owed 5 (creditor C, debtor B, net 5)

    mock_balances = [
        LedgerBalanceORM(
            group_id="g1",
            creditor_id="B",
            debtor_id="A",
            net_amount=Decimal("10"),
        ),
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
        LedgerBalanceORM(
            group_id="g1",
            creditor_id="B",
            debtor_id="A",
            net_amount=Decimal("10"),
        ),
        LedgerBalanceORM(
            group_id="g1",
            creditor_id="C",
            debtor_id="B",
            net_amount=Decimal("10"),
        ),
        LedgerBalanceORM(
            group_id="g1",
            creditor_id="A",
            debtor_id="C",
            net_amount=Decimal("10"),
        ),
    ]
    ledger_service._repo.get_group_balances = AsyncMock(return_value=mock_balances)

    result = await ledger_service.get_simplified_balances("g1")

    # Expected Net: A: 0, B: 0, C: 0
    # Simplified: []
    assert len(result.simplified) == 0
    assert result.net_by_user["A"] == Decimal("0")
    assert result.net_by_user["B"] == Decimal("0")
    assert result.net_by_user["C"] == Decimal("0")


@pytest.mark.parametrize("for_update", [False, True])
@pytest.mark.parametrize("zero_rows", [0, 2])
async def test_sparse_graph_keeps_shorter_bilateral_plan(ledger_service, for_update, zero_rows):
    # A -> B 3, C -> B 3, D -> E 4: greedy produces four payments, not three.
    rows = [
        LedgerBalanceORM(group_id="g1", creditor_id="A", debtor_id="B", net_amount=Decimal("-3")),
        LedgerBalanceORM(group_id="g1", creditor_id="B", debtor_id="C", net_amount=Decimal("3")),
        LedgerBalanceORM(group_id="g1", creditor_id="D", debtor_id="E", net_amount=Decimal("-4")),
    ]
    rows += [
        LedgerBalanceORM(group_id="g1", creditor_id="A", debtor_id=user, net_amount=Decimal("0"))
        for user in ("F", "G")[:zero_rows]
    ]
    ledger_service._repo.get_group_balances = AsyncMock(return_value=rows)
    ledger_service._repo.get_group_balances_for_update = AsyncMock(return_value=rows)
    ledger_service._repo.version.return_value = 7

    result = await ledger_service.get_simplified_balances("g1", for_update=for_update)

    assert result.version == 7
    assert [(d.from_user_id, d.to_user_id, d.amount) for d in result.simplified] == [
        ("A", "B", Decimal("3")),
        ("C", "B", Decimal("3")),
        ("D", "E", Decimal("4")),
    ]
    reconstructed = dict.fromkeys(result.net_by_user, Decimal("0"))
    for debt in result.simplified:
        reconstructed[debt.from_user_id] -= debt.amount
        reconstructed[debt.to_user_id] += debt.amount
    assert reconstructed == result.net_by_user


@pytest.mark.parametrize("zero_only", [False, True])
async def test_empty_or_zero_balances_need_no_payments(ledger_service, zero_only):
    rows = (
        [LedgerBalanceORM(group_id="g1", creditor_id="A", debtor_id="B", net_amount=Decimal("0"))]
        if zero_only else []
    )
    ledger_service._repo.get_group_balances = AsyncMock(return_value=rows)

    result = await ledger_service.get_simplified_balances("g1")

    assert result.simplified == []
    assert all(amount == 0 for amount in result.net_by_user.values())


async def test_shorter_greedy_plan_still_settles_indirect_debt(ledger_service):
    ledger_service._repo.get_group_balances = AsyncMock(return_value=[
        LedgerBalanceORM(group_id="g1", creditor_id="A", debtor_id="B", net_amount=Decimal("-5")),
        LedgerBalanceORM(group_id="g1", creditor_id="B", debtor_id="C", net_amount=Decimal("-5")),
    ])

    result = await ledger_service.get_simplified_balances("g1")

    assert [(d.from_user_id, d.to_user_id, d.amount) for d in result.simplified] == [
        ("A", "C", Decimal("5")),
    ]
