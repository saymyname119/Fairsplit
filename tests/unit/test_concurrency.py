"""tests/unit/test_concurrency.py — Tests for concurrency and locking."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.ledger.models import LedgerBalanceORM, SettlementORM
from modules.ledger.service import LedgerService
from shared.db.session import isolated_transaction
from shared.events import ExpenseCreated, ExpenseSplitEvent


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.in_transaction.return_value = False
    return session


@pytest.fixture
def ledger_service(mock_session):
    return LedgerService(mock_session)


@pytest.mark.asyncio
async def test_handle_expense_created_canonical_lock_ordering(ledger_service):
    """
    Verify that when an expense has multiple splits, balance updates are applied
    in strictly sorted canonical (creditor_id, debtor_id) order.
    This guarantees global lock acquisition order across all transactions and prevents deadlocks.
    """
    call_order: list[tuple[str, str]] = []

    async def mock_upsert(group_id, creditor_id, debtor_id, delta):
        call_order.append((creditor_id, debtor_id))
        return MagicMock()

    ledger_service._repo.upsert_balance = AsyncMock(side_effect=mock_upsert)

    # Paid by "charlie". Participants: "alice", "bob", "david"
    # Unordered splits in event
    event = ExpenseCreated(
        expense_id="exp-multi",
        group_id="group-1",
        paid_by_id="charlie",
        amount=Decimal("100"),
        description="Hotel",
        splits=[
            ExpenseSplitEvent(user_id="david", owed_amount=Decimal("25")),
            ExpenseSplitEvent(user_id="alice", owed_amount=Decimal("25")),
            ExpenseSplitEvent(user_id="charlie", owed_amount=Decimal("25")),
            ExpenseSplitEvent(user_id="bob", owed_amount=Decimal("25")),
        ],
    )

    with patch("modules.ledger.service.invalidate", new_callable=AsyncMock) as mock_invalidate:
        await ledger_service.handle_expense_created(event)
        mock_invalidate.assert_called_once_with("balances:group:group-1")

    # Canonical pairs between charlie and participants:
    # charlie & alice -> ("alice", "charlie")
    # charlie & bob   -> ("bob", "charlie")
    # charlie & david -> ("charlie", "david")
    # Expected sorted order:
    expected_order = [
        ("alice", "charlie"),
        ("bob", "charlie"),
        ("charlie", "david"),
    ]
    assert call_order == expected_order


@pytest.mark.asyncio
async def test_recalculate_group_balances_with_locks(ledger_service):
    """
    Verify that recalculate_group_balances locks rows via get_group_balances_for_update,
    computes ground truth from expenses and settlements, and invalidates cache.
    """
    # Existing ORM row: Alice and Bob already have a row with net 10
    existing_row = LedgerBalanceORM(
        id="bal-1", group_id="g1", creditor_id="alice", debtor_id="bob", net_amount=Decimal("10")
    )
    ledger_service._repo.get_group_balances_for_update = AsyncMock(return_value=[existing_row])

    # Active splits:
    # 1. Alice paid $40, Bob owed $20 -> Alice is creditor, Bob debtor: +20
    # 2. Bob paid $10, Charlie owed $10 -> Bob creditor, Charlie debtor: +10
    ledger_service._repo.get_active_group_splits = AsyncMock(
        return_value=[
            ("alice", "bob", Decimal("20")),
            ("bob", "charlie", Decimal("10")),
        ]
    )

    # Settlements:
    # Bob settled $5 to Alice
    mock_settlement = SettlementORM(
        id="set-1", group_id="g1", from_user_id="bob", to_user_id="alice", amount=Decimal("5")
    )
    ledger_service._repo.get_group_settlements = AsyncMock(return_value=[mock_settlement])

    # upsert_balance mock for new pairs (bob-charlie)
    new_row = LedgerBalanceORM(
        id="bal-2", group_id="g1", creditor_id="bob", debtor_id="charlie", net_amount=Decimal("10")
    )
    ledger_service._repo.upsert_balance = AsyncMock(return_value=new_row)

    with patch("modules.ledger.service.invalidate", new_callable=AsyncMock) as mock_invalidate:
        balances = await ledger_service.recalculate_group_balances("g1")
        mock_invalidate.assert_called_once_with("balances:group:g1")

    # Verify lock was acquired
    ledger_service._repo.get_group_balances_for_update.assert_called_once_with("g1")

    # Verify net balance between Alice and Bob: 20 (from expense) - 5 (settlement) = 15
    assert existing_row.net_amount == Decimal("15")

    # Total returned balances: Alice-Bob and Bob-Charlie
    assert len(balances) == 2
    alice_bob = next(b for b in balances if b.creditor_id == "alice" and b.debtor_id == "bob")
    assert alice_bob.net_amount == Decimal("15")


@pytest.mark.asyncio
async def test_get_simplified_balances_for_update(ledger_service):
    """
    Verify get_simplified_balances(for_update=True) acquires row-level locks
    on all balance rows during settlement planning.
    """
    mock_balance = LedgerBalanceORM(
        id="bal-1", group_id="g1", creditor_id="alice", debtor_id="bob", net_amount=Decimal("30")
    )
    ledger_service._repo.get_group_balances_for_update = AsyncMock(return_value=[mock_balance])

    result = await ledger_service.get_simplified_balances("g1", for_update=True)

    ledger_service._repo.get_group_balances_for_update.assert_called_once_with("g1")
    assert len(result.simplified) == 1
    assert result.simplified[0].from_user_id == "bob"
    assert result.simplified[0].to_user_id == "alice"
    assert result.simplified[0].amount == Decimal("30")


@pytest.mark.asyncio
async def test_isolated_transaction_context_manager(mock_session):
    """Verify isolated_transaction sets execution options and enters transaction."""
    mock_conn = AsyncMock()
    mock_session.connection = AsyncMock(return_value=mock_conn)
    mock_session.in_transaction = MagicMock(return_value=False)
    mock_tx = AsyncMock()
    mock_tx.__aenter__ = AsyncMock(return_value=mock_tx)
    mock_tx.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=mock_tx)

    async with isolated_transaction(mock_session, isolation_level="SERIALIZABLE") as s:
        assert s == mock_session

    mock_conn.execution_options.assert_called_once_with(isolation_level="SERIALIZABLE")
    mock_session.begin.assert_called_once()

