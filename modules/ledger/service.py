from __future__ import annotations

import abc
import heapq
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from modules.ledger.models import (
    Balance,
    CreateSettlementRequest,
    Settlement,
    SettlementORM,
    SimplifiedBalanceResult,
    SimplifiedDebt,
    UserBalance,
)
from modules.ledger.repository import LedgerRepository
from shared.errors import ConflictError
from shared.events import ExpenseCreated, SettlementRecorded, get_event_bus


class HeapItem:
    def __init__(self, amount: Decimal, user_id: str) -> None:
        self.amount = amount
        self.user_id = user_id

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, HeapItem):
            return NotImplemented
        return self.amount > other.amount  # inverted for max-heap


class ILedgerService(abc.ABC):
    @abc.abstractmethod
    async def get_group_balances(self, group_id: str) -> list[Balance]: ...

    @abc.abstractmethod
    async def get_simplified_balances(self, group_id: str) -> SimplifiedBalanceResult: ...

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

    async def get_simplified_balances(self, group_id: str) -> SimplifiedBalanceResult:
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

        return SimplifiedBalanceResult(simplified=simplified, net_by_user=net_balances)

    async def record_settlement(
        self, group_id: str, request: CreateSettlementRequest
    ) -> Settlement:
        if request.from_user_id == request.to_user_id:
            raise ConflictError("Cannot settle with oneself")

        creditor, debtor, sign = self._canonical_pair(request.to_user_id, request.from_user_id)

        # 1. Lock the balance row
        balance = await self._repo.get_balance_for_update(group_id, creditor, debtor)

        if not balance:
            raise ConflictError("No outstanding balance between these users")

        # Determine actual debt value from the POV of the person receiving money (to_user_id)
        # If to_user_id is the canonical creditor, balance.net_amount is what they are owed.
        # If they are canonical debtor, -balance.net_amount is what they are owed.
        owed_to_receiver = balance.net_amount * sign

        if request.amount > owed_to_receiver:
            raise ConflictError(
                f"Settlement amount {request.amount} exceeds balance {owed_to_receiver}"
            )

        # 3. Insert settlement
        orm_settlement = SettlementORM(
            group_id=group_id,
            from_user_id=request.from_user_id,
            to_user_id=request.to_user_id,
            amount=request.amount,
            notes=request.notes,
        )
        await self._repo.record_settlement(orm_settlement)

        # 4. Update balance (deducting the debt)
        balance.net_amount -= request.amount * sign

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

    async def handle_expense_created(self, event: ExpenseCreated) -> None:
        payer = event.paid_by_id

        for split in event.splits:
            if split.user_id == payer:
                continue

            owed = split.owed_amount
            creditor, debtor, sign = self._canonical_pair(payer, split.user_id)

            # The payer is owed `owed`.
            # If payer is the canonical creditor, we add `owed`.
            # If payer is the canonical debtor, we subtract `owed`.
            amount_delta = owed * sign

            await self._repo.upsert_balance(event.group_id, creditor, debtor, amount_delta)

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
