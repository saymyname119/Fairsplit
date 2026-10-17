"""Real PostgreSQL tests; use an isolated database migrated through 0003.

FAIRSPLIT_TEST_DATABASE_URL must point at a disposable database. These tests use
unique group IDs and do not touch existing groups.
"""

import asyncio
import os
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from modules.expense.models import CreateExpenseRequest, SplitType, UpdateExpenseRequest
from modules.expense.service import ExpenseService
from modules.group.models import GroupORM
from modules.ledger.models import CreateSettlementRequest, JournalORM, SettlementORM
from modules.ledger.service import LedgerService
from modules.notification.outbox import NotificationJobORM, NotificationORM, process_batch
from modules.user.models import UserORM
from shared.errors import ConflictError
from shared.events import ExpenseCreated, ExpenseSplitEvent

pytestmark = pytest.mark.skipif(
    not os.getenv("FAIRSPLIT_TEST_DATABASE_URL"), reason="Set disposable PostgreSQL URL"
)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(os.environ["FAIRSPLIT_TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = [str(uuid.uuid4()) for _ in range(4)]
    group, a, b, c = ids
    async with factory() as session:
        for user in (a, b, c):
            session.add(
                UserORM(id=user, name=user, email=f"{user}@example.com", hashed_password="test")
            )
        await session.flush()
        session.add(GroupORM(id=group, name="financial test", created_by_id=a))
        await session.flush()
        from modules.group.models import GroupMemberORM

        for user in (a, b, c):
            session.add(GroupMemberORM(group_id=group, user_id=user, role="admin"))
        await session.commit()
    with patch("modules.ledger.service.invalidate", new_callable=AsyncMock):
        yield factory, group, a, b, c
    await engine.dispose()


async def seed(factory, group, payer, debtor, amount="30"):
    async with factory() as s:
        await LedgerService(s).handle_expense_created(
            ExpenseCreated(
                expense_id=str(uuid.uuid4()),
                group_id=group,
                paid_by_id=payer,
                amount=Decimal(amount),
                description="Test",
                splits=[ExpenseSplitEvent(user_id=debtor, owed_amount=Decimal(amount))],
            )
        )
        await s.commit()


def payment(payer, receiver, version, key, amount="10"):
    return CreateSettlementRequest(
        from_user_id=payer,
        to_user_id=receiver,
        expected_version=version,
        idempotency_key=key,
        amount=Decimal(amount),
    )


async def test_parallel_retry_is_exactly_once_and_stale_is_rejected(db):
    factory, group, a, b, _ = db
    await seed(factory, group, a, b)

    async def pay(key):
        async with factory() as s:
            result = await LedgerService(s).record_settlement(group, payment(b, a, 1, key))
            await s.commit()
            return result.id

    first, second = await asyncio.gather(pay("same-key"), pay("same-key"))
    assert first == second
    async with factory() as s:
        assert (
            len(
                (await s.execute(select(SettlementORM).where(SettlementORM.group_id == group)))
                .scalars()
                .all()
            )
            == 1
        )
        assert (await LedgerService(s).get_simplified_balances(group)).simplified[
            0
        ].amount == Decimal("20")
    with pytest.raises(ConflictError, match="changed"):
        await pay("different-key")
    async with factory() as s:
        with pytest.raises(ConflictError, match="different payment"):
            await LedgerService(s).record_settlement(group, payment(b, a, 2, "same-key", "9"))


async def test_concurrent_first_expenses_and_journal_invariants(db):
    factory, group, a, b, _ = db
    await asyncio.gather(*(seed(factory, group, a, b, "1") for _ in range(10)))
    async with factory() as s:
        plan = await LedgerService(s).get_simplified_balances(group)
        assert plan.version == 10
        assert plan.simplified[0].amount == 10
        rows = (
            (await s.execute(select(JournalORM).where(JournalORM.group_id == group)))
            .scalars()
            .all()
        )
        net = {}
        for row in rows:
            net[row.credit_user_id] = net.get(row.credit_user_id, Decimal(0)) + row.amount
            net[row.debit_user_id] = net.get(row.debit_user_id, Decimal(0)) - row.amount
        assert sum(net.values()) == 0
        assert net == plan.net_by_user
        with pytest.raises(Exception, match="immutable"):
            await s.execute(
                text("UPDATE ledger_journal SET amount=0 WHERE group_id=:g"), {"g": group}
            )


async def test_simplified_indirect_payment_and_reversal(db):
    factory, group, a, b, c = db
    await seed(factory, group, a, b)
    await seed(factory, group, b, c)
    async with factory() as s:
        service = LedgerService(s)
        plan = await service.get_simplified_balances(group)
        assert plan.simplified[0].from_user_id == c
        original = await service.record_settlement(group, payment(c, a, 2, "indirect"))
        await s.commit()
    from api.routes.ledger import reverse_settlement
    from modules.ledger.models import ReverseSettlementRequest

    async with factory() as s:
        reversal = await reverse_settlement(
            group,
            original.id,
            ReverseSettlementRequest(expected_version=3, idempotency_key="reverse"),
            s,
        )
        await s.commit()
        assert reversal.amount == -10
        assert (await LedgerService(s).get_simplified_balances(group)).net_by_user[a] == 30
    async with factory() as s:
        again = await reverse_settlement(
            group,
            original.id,
            ReverseSettlementRequest(expected_version=3, idempotency_key="reverse"),
            s,
        )
        assert again.id == reversal.id


async def test_worker_rollback_and_retry_do_not_duplicate_notifications(db):
    factory, group, a, b, _ = db
    await seed(factory, group, a, b)
    async with factory() as s:
        # Simulate failure after processing, before commit.
        with patch.object(s, "commit", side_effect=RuntimeError("worker crash")):
            with pytest.raises(RuntimeError):
                await process_batch(s)
        await s.rollback()
    async with factory() as s:
        await process_batch(s)
        await process_batch(s)
        rows = (
            (await s.execute(select(NotificationORM).where(NotificationORM.group_id == group)))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        job = (
            await s.execute(select(NotificationJobORM).where(NotificationJobORM.group_id == group))
        ).scalar_one()
        assert job.completed_at is not None


async def test_edit_delete_and_settle_preserve_projection(db):
    factory, group, a, b, _ = db
    async with factory() as s:
        await LedgerService(s)._repo.lock_group(group)
        expense = await ExpenseService(s).create_expense(
            group,
            CreateExpenseRequest(
                paid_by_id=a,
                amount=Decimal("60"),
                description="Dinner",
                split_type=SplitType.EQUAL,
                participants=[a, b],
            ),
        )
        await LedgerService(s).handle_expense_created(
            ExpenseCreated(
                expense_id=expense.id,
                group_id=group,
                paid_by_id=a,
                amount=expense.amount,
                description=expense.description,
                splits=[
                    ExpenseSplitEvent(user_id=x.user_id, owed_amount=x.owed_amount)
                    for x in expense.splits
                ],
            )
        )
        await s.commit()

    async def edit():
        async with factory() as s:
            await LedgerService(s)._repo.lock_group(group)
            updated = await ExpenseService(s).update_expense(
                expense.id, UpdateExpenseRequest(amount=Decimal("80")), a
            )
            assert sum(x.owed_amount for x in updated.splits) == 80
            await LedgerService(s).recalculate_group_balances(group)
            await s.commit()

    async def settle():
        async with factory() as s:
            try:
                await LedgerService(s).record_settlement(group, payment(b, a, 1, "overlap"))
                await s.commit()
            except ConflictError:
                await s.rollback()

    await asyncio.gather(edit(), settle())
    async with factory() as s:
        ledger = LedgerService(s)
        before = await ledger.get_simplified_balances(group)
        await ledger.recalculate_group_balances(group)
        assert (await ledger.get_simplified_balances(group)).net_by_user == before.net_by_user
        await ExpenseService(s).delete_expense(expense.id, a)
        await ledger.recalculate_group_balances(group)
        rows = (
            (await s.execute(select(JournalORM).where(JournalORM.group_id == group)))
            .scalars()
            .all()
        )
        net = {a: Decimal(0), b: Decimal(0)}
        for r in rows:
            net[r.credit_user_id] += r.amount
            net[r.debit_user_id] -= r.amount
        assert net == (await ledger.get_simplified_balances(group)).net_by_user
        await s.commit()


async def test_versioned_cache_does_not_reuse_old_balances(db):
    factory, group, a, b, _ = db
    from api.routes.ledger import get_group_balances

    cached = {}

    async def get(key):
        return cached.get(key)

    async def put(key, value):
        import json

        cached[key] = json.dumps(value, default=str)

    with (
        patch("api.routes.ledger.get_cached", side_effect=get),
        patch("api.routes.ledger.set_cached", side_effect=put),
    ):
        await seed(factory, group, a, b, "30")
        async with factory() as s:
            first = await get_group_balances(group, s, {"user_id": a})
            await s.commit()
        old = cached[f"balances:group:{group}:v1"]
        await seed(factory, group, a, b, "10")
        # A delayed reader may fill the old version after the new version commits.
        cached[f"balances:group:{group}:v1"] = old
        async with factory() as s:
            second = await get_group_balances(group, s, {"user_id": a})
            await s.commit()
        assert abs(first[0].net_amount) == 30
        assert abs(second[0].net_amount) == 40
        assert f"balances:group:{group}:v2" in cached


async def test_worker_delivery_failure_is_retried(db):
    factory, group, a, b, _ = db
    from datetime import UTC, datetime

    await seed(factory, group, a, b)
    async with factory() as s:
        # The nested savepoint isolates one delivery failure from its queue record.
        with patch.object(s, "flush", side_effect=RuntimeError("delivery unavailable")):
            await process_batch(s)
    async with factory() as s:
        job = (
            await s.execute(select(NotificationJobORM).where(NotificationJobORM.group_id == group))
        ).scalar_one()
        assert job.attempts == 1
        assert job.completed_at is None
        assert "delivery unavailable" in job.last_error
        job.available_at = datetime.now(UTC)
        await s.commit()
        await process_batch(s)
        result = (
            (await s.execute(select(NotificationORM).where(NotificationORM.group_id == group)))
            .scalars()
            .all()
        )
        assert len(result) == 1
