from __future__ import annotations

import abc
import hashlib
import heapq
import json
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from modules.ledger.models import (
    Balance,
    CreateSettlementRequest,
    LedgerBalanceORM,
    ReverseSettlementRequest,
    Settlement,
    SettlementORM,
    SimplifiedBalanceResult,
    SimplifiedDebt,
    UserBalance,
)
from modules.ledger.repository import LedgerRepository
from shared.cache import balance_cache_key, invalidate
from shared.errors import ConflictError
from shared.events import ExpenseCreated, SettlementRecorded, get_event_bus


class HeapItem:
    def __init__(self, amount: Decimal, user_id: str) -> None:
        self.amount = amount
        self.user_id = user_id

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, HeapItem):
            return NotImplemented
        return (-self.amount, self.user_id) < (-other.amount, other.user_id)


class ILedgerService(abc.ABC):
    @abc.abstractmethod
    async def get_group_balances(self, group_id: str) -> list[Balance]: ...

    @abc.abstractmethod
    async def get_simplified_balances(
        self, group_id: str, for_update: bool = False
    ) -> SimplifiedBalanceResult: ...

    @abc.abstractmethod
    async def recalculate_group_balances(self, group_id: str) -> list[Balance]: ...

    @abc.abstractmethod
    async def record_settlement(
        self, group_id: str, request: CreateSettlementRequest
    ) -> Settlement: ...

    @abc.abstractmethod
    async def handle_expense_created(self, event: ExpenseCreated) -> None: ...

    @abc.abstractmethod
    async def get_user_balances(self, user_id: str) -> UserBalance: ...


class LedgerService(ILedgerService):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = LedgerRepository(session)
        self._bus = get_event_bus()

    def _canonical_pair(self, u1: str, u2: str) -> tuple[str, str, int]:
        """Returns (creditor, debtor, sign) based on canonical alphabetical ordering."""
        if u1 < u2:
            return u1, u2, 1
        return u2, u1, -1

    async def get_group_balances(self, group_id: str) -> list[Balance]:
        orms = await self._repo.get_group_balances(group_id)
        return [Balance.model_validate(o) for o in orms]

    async def get_simplified_balances(
        self, group_id: str, for_update: bool = False
    ) -> SimplifiedBalanceResult:
        if for_update:
            orms = await self._repo.get_group_balances_for_update(group_id)
            balances = [Balance.model_validate(o) for o in orms]
        else:
            balances = await self.get_group_balances(group_id)

        # 1. Compute net balances per user
        net_balances: dict[str, Decimal] = {}

        for b in balances:
            if b.creditor_id not in net_balances:
                net_balances[b.creditor_id] = Decimal("0")
            if b.debtor_id not in net_balances:
                net_balances[b.debtor_id] = Decimal("0")

            # creditor is owed money (positive net_amount)
            net_balances[b.creditor_id] += b.net_amount
            net_balances[b.debtor_id] -= b.net_amount

        # 2. Setup max heaps for creditors and debtors
        creditors: list[HeapItem] = []
        debtors: list[HeapItem] = []

        for user_id, net in net_balances.items():
            # Filter out rounding dust (< 0.0001)
            if net > Decimal("0.0000"):
                heapq.heappush(creditors, HeapItem(net, user_id))
            elif net < Decimal("0.0000"):
                heapq.heappush(debtors, HeapItem(abs(net), user_id))

        # 3. Greedy matching
        simplified: list[SimplifiedDebt] = []

        while creditors and debtors:
            largest_creditor = heapq.heappop(creditors)
            largest_debtor = heapq.heappop(debtors)

            transfer = min(largest_creditor.amount, largest_debtor.amount)

            simplified.append(
                SimplifiedDebt(
                    from_user_id=largest_debtor.user_id,
                    to_user_id=largest_creditor.user_id,
                    amount=transfer,
                )
            )

            remaining_creditor = largest_creditor.amount - transfer
            remaining_debtor = largest_debtor.amount - transfer

            # Use a tiny epsilon to avoid floating/decimal zero issues recreating loops
            if remaining_creditor > Decimal("0.0000"):
                heapq.heappush(creditors, HeapItem(remaining_creditor, largest_creditor.user_id))
            if remaining_debtor > Decimal("0.0000"):
                heapq.heappush(debtors, HeapItem(remaining_debtor, largest_debtor.user_id))

        return SimplifiedBalanceResult(
            version=await self._repo.version(group_id),
            simplified=simplified,
            net_by_user=net_balances,
        )

    async def record_settlement(
        self, group_id: str, request: CreateSettlementRequest
    ) -> Settlement:
        if request.from_user_id == request.to_user_id:
            raise ConflictError("Cannot settle with oneself")

        state = await self._repo.lock_group(group_id)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "from": request.from_user_id,
                    "to": request.to_user_id,
                    "amount": str(request.amount.normalize()),
                    "notes": request.notes,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        retry = await self._repo.find_retry(group_id, request.idempotency_key)
        if retry:
            if retry.request_hash != fingerprint:
                raise ConflictError("Idempotency key already used for a different payment")
            return Settlement.model_validate(retry)
        if state.version != request.expected_version:
            raise ConflictError("Balances changed. Refresh and confirm the payment again.")
        creditor, debtor, sign = self._canonical_pair(request.to_user_id, request.from_user_id)

        plan = await self.get_simplified_balances(group_id, for_update=True)
        allowed = next(
            (
                d.amount
                for d in plan.simplified
                if d.from_user_id == request.from_user_id and d.to_user_id == request.to_user_id
            ),
            Decimal("0"),
        )
        if request.amount > allowed:
            raise ConflictError(f"Settlement exceeds current suggested payment {allowed}")

        # 3. Insert settlement
        orm_settlement = SettlementORM(
            group_id=group_id,
            from_user_id=request.from_user_id,
            to_user_id=request.to_user_id,
            amount=request.amount,
            notes=request.notes,
            idempotency_key=request.idempotency_key,
            request_hash=fingerprint,
        )
        await self._repo.record_settlement(orm_settlement)

        # 4. Update balance (deducting the debt)
        await self._repo.upsert_balance(group_id, creditor, debtor, -request.amount * sign)
        self._repo.journal(
            group_id,
            request.from_user_id,
            request.to_user_id,
            request.amount,
            f"settlement:{orm_settlement.id}",
        )
        state.version += 1
        from modules.notification.outbox import enqueue

        enqueue(
            self._session,
            group_id,
            "Settlement recorded",
            request.to_user_id,
            f"Payment of {request.amount} received from {request.from_user_id}.",
        )
        await self._session.flush()

        # The unit of work (router) commits the transaction here

        domain_settlement = Settlement.model_validate(orm_settlement)

        # 5. Publish event
        self._bus.publish(
            SettlementRecorded(
                settlement_id=domain_settlement.id,
                group_id=group_id,
                from_user_id=domain_settlement.from_user_id,
                to_user_id=domain_settlement.to_user_id,
                amount=domain_settlement.amount,
            )
        )

        return domain_settlement

    async def reverse_settlement(
        self, group_id: str, settlement_id: str, request: ReverseSettlementRequest
    ) -> Settlement:
        from modules.notification.outbox import enqueue
        from shared.errors import ConflictError, NotFoundError

        repo = self._repo
        state = await repo.lock_group(group_id)
        retry = await repo.find_retry(group_id, request.idempotency_key)
        if retry:
            if retry.reversal_of != settlement_id:
                raise ConflictError("Idempotency key already used")
            return Settlement.model_validate(retry)
        if state.version != request.expected_version:
            raise ConflictError("Balances changed. Refresh before reversing.")
        settlements = await repo.get_group_settlements(group_id)
        original = next((s for s in settlements if s.id == settlement_id), None)
        if not original:
            raise NotFoundError("Settlement", settlement_id)
        if original.reversal_of or any(s.reversal_of == settlement_id for s in settlements):
            raise ConflictError("Settlement already reversed or is itself a reversal")
        reversal = SettlementORM(
            group_id=group_id,
            from_user_id=original.from_user_id,
            to_user_id=original.to_user_id,
            amount=-original.amount,
            notes="Settlement reversal",
            reversal_of=original.id,
            idempotency_key=request.idempotency_key,
        )
        await repo.record_settlement(reversal)
        c, d, sign = self._canonical_pair(original.to_user_id, original.from_user_id)
        await repo.upsert_balance(group_id, c, d, original.amount * sign)
        repo.journal(group_id, c, d, original.amount * sign, f"reversal:{original.id}")
        state.version += 1
        enqueue(
            self._session,
            group_id,
            "Settlement reversed",
            original.to_user_id,
            f"Payment of {original.amount} was reversed.",
        )
        await self._session.flush()
        return Settlement.model_validate(reversal)

    async def handle_expense_created(self, event: ExpenseCreated) -> None:
        state = await self._repo.lock_group(event.group_id)
        payer = event.paid_by_id

        # 1. Group split amounts by canonical pair (creditor, debtor)
        pair_deltas: dict[tuple[str, str], Decimal] = {}
        for split in event.splits:
            if split.user_id == payer:
                continue

            owed = split.owed_amount
            creditor, debtor, sign = self._canonical_pair(payer, split.user_id)
            amount_delta = owed * sign
            pair_deltas[(creditor, debtor)] = (
                pair_deltas.get((creditor, debtor), Decimal("0")) + amount_delta
            )

        # 2. Acquire row locks and update balances in deterministic sorted order
        # to strictly prevent lock-order deadlocks between concurrent expenses.
        for creditor, debtor in sorted(pair_deltas.keys()):
            delta = pair_deltas[(creditor, debtor)]
            await self._repo.upsert_balance(event.group_id, creditor, debtor, delta)
            self._repo.journal(
                event.group_id, creditor, debtor, delta, f"expense:{event.expense_id}"
            )
        state.version += 1
        from modules.notification.outbox import enqueue

        for split in event.splits:
            if split.user_id != payer:
                enqueue(
                    self._session,
                    event.group_id,
                    "Expense added",
                    split.user_id,
                    f"You owe {split.owed_amount} for {event.description}.",
                )
        await self._session.flush()

        # 3. Synchronously invalidate cached balances
        cache_key = balance_cache_key(event.group_id)
        await invalidate(cache_key)

    async def recalculate_group_balances(self, group_id: str) -> list[Balance]:
        """
        Recalculates all net balances for a group from active expenses and settlements.
        Uses SELECT FOR UPDATE row-level locking on all group balance rows to eliminate
        concurrency race conditions and stale caches.
        """
        state = await self._repo.lock_group(group_id)
        # 1. Pessimistic row-level lock on existing balance rows
        existing_orms = await self._repo.get_group_balances_for_update(group_id)
        existing_map = {(o.creditor_id, o.debtor_id): o for o in existing_orms}

        # 2. Fetch ground truth data for the group
        active_splits = await self._repo.get_active_group_splits(group_id)
        settlements = await self._repo.get_group_settlements(group_id)

        # 3. Compute net balance for every pair in canonical order
        pair_nets: dict[tuple[str, str], Decimal] = {}

        for payer_id, user_id, owed_amount in active_splits:
            if payer_id == user_id or owed_amount <= Decimal("0"):
                continue
            creditor, debtor, sign = self._canonical_pair(payer_id, user_id)
            pair_nets[(creditor, debtor)] = pair_nets.get((creditor, debtor), Decimal("0")) + (
                owed_amount * sign
            )

        for s in settlements:
            if s.from_user_id == s.to_user_id or s.amount == Decimal("0"):
                continue
            creditor, debtor, sign = self._canonical_pair(s.to_user_id, s.from_user_id)
            pair_nets[(creditor, debtor)] = pair_nets.get((creditor, debtor), Decimal("0")) - (
                s.amount * sign
            )

        # 4. Synchronize ORM rows under lock in deterministic sorted order
        all_pairs = sorted(set(list(existing_map.keys()) + list(pair_nets.keys())))
        result_orms: list[LedgerBalanceORM] = []

        for c, d in all_pairs:
            net = pair_nets.get((c, d), Decimal("0"))
            if (c, d) in existing_map:
                orm = existing_map[(c, d)]
                self._repo.journal(group_id, c, d, net - orm.net_amount, "expense-adjustment")
                orm.net_amount = net
                result_orms.append(orm)
            elif net != Decimal("0"):
                self._repo.journal(group_id, c, d, net, "expense-adjustment")
                orm = await self._repo.upsert_balance(group_id, c, d, net)
                result_orms.append(orm)

        state.version += 1
        await self._session.flush()
        # 5. Invalidate Redis cache
        cache_key = balance_cache_key(group_id)
        await invalidate(cache_key)

        return [Balance.model_validate(o) for o in result_orms]

    async def get_user_balances(self, user_id: str) -> UserBalance:
        """Aggregate a user's balances across all groups."""
        balance_rows = await self._repo.get_user_balances(user_id)

        total_owed = Decimal("0")
        total_owed_to = Decimal("0")
        by_group: dict[str, Decimal] = {}

        for b in balance_rows:
            if b.net_amount == 0:
                continue

            if b.creditor_id == user_id:
                # This user is the creditor — they are owed money
                if b.net_amount > 0:
                    total_owed_to += b.net_amount
                    by_group[b.group_id] = by_group.get(b.group_id, Decimal("0")) + b.net_amount
                else:
                    # Negative net_amount means the canonical creditor actually owes
                    total_owed += abs(b.net_amount)
                    by_group[b.group_id] = by_group.get(b.group_id, Decimal("0")) + b.net_amount
            elif b.debtor_id == user_id:
                # This user is the debtor
                if b.net_amount > 0:
                    total_owed += b.net_amount
                    by_group[b.group_id] = by_group.get(b.group_id, Decimal("0")) - b.net_amount
                else:
                    total_owed_to += abs(b.net_amount)
                    by_group[b.group_id] = by_group.get(b.group_id, Decimal("0")) - b.net_amount

        net = total_owed_to - total_owed

        return UserBalance(
            user_id=user_id,
            total_owed=total_owed,
            total_owed_to=total_owed_to,
            net=net,
            by_group=by_group,
        )
