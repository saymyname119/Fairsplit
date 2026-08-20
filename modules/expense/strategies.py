from __future__ import annotations

import abc
from decimal import ROUND_HALF_UP, Decimal

from modules.expense.models import Split, SplitInput, SplitType
from shared.errors import DomainError


class ISplitStrategy(abc.ABC):
    @abc.abstractmethod
    def calculate_splits(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> list[Split]:
        pass

    @abc.abstractmethod
    def validate(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> None:
        pass


class EqualSplitStrategy(ISplitStrategy):
    def validate(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> None:
        if len(participants) < 2:
            raise DomainError("At least 2 participants required for equal split")

    def calculate_splits(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> list[Split]:
        n = len(participants)
        # Calculate raw amount per person and round to 4 decimal places
        amount_each = (total / Decimal(n)).quantize(Decimal("0.0000"), rounding=ROUND_HALF_UP)

        splits = []
        current_sum = Decimal("0")

        # Assign to all but the last participant
        for i in range(n - 1):
            splits.append(Split(user_id=participants[i], owed_amount=amount_each))
            current_sum += amount_each

        # The last participant gets the residual
        last_amount = total - current_sum
        splits.append(Split(user_id=participants[-1], owed_amount=last_amount))

        return splits


class PercentSplitStrategy(ISplitStrategy):
    def validate(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> None:
        if not inputs or len(inputs) != len(participants):
            raise DomainError("Percent split requires inputs for all participants")

        total_percent = sum(inp.value for inp in inputs)
        if total_percent != Decimal("100.0000") and total_percent != Decimal("100"):
            raise DomainError(f"Percentages must sum to 100, got {total_percent}")

        for inp in inputs:
            if not (0 < inp.value < 100):
                raise DomainError("Each percentage must be between 0 and 100")

    def calculate_splits(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> list[Split]:
        splits = []
        current_sum = Decimal("0")

        inputs_by_user = {inp.user_id: inp for inp in inputs}  # type: ignore

        # Calculate for all but the last
        for i in range(len(participants) - 1):
            user_id = participants[i]
            pct = inputs_by_user[user_id].value
            amount = (total * (pct / Decimal("100"))).quantize(
                Decimal("0.0000"), rounding=ROUND_HALF_UP
            )
            splits.append(Split(user_id=user_id, owed_amount=amount, percentage=pct))
            current_sum += amount

        # Last gets the residual
        last_user = participants[-1]
        last_pct = inputs_by_user[last_user].value
        last_amount = total - current_sum
        splits.append(Split(user_id=last_user, owed_amount=last_amount, percentage=last_pct))

        return splits


class ExactSplitStrategy(ISplitStrategy):
    def validate(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> None:
        if not inputs or len(inputs) != len(participants):
            raise DomainError("Exact split requires inputs for all participants")

        total_exact = sum(inp.value for inp in inputs)
        if total_exact != total:
            raise DomainError(f"Exact amounts sum to {total_exact}, expected {total}")

        for inp in inputs:
            if inp.value <= 0:
                raise DomainError("Split amounts must be positive")

    def calculate_splits(
        self, total: Decimal, participants: list[str], inputs: list[SplitInput] | None
    ) -> list[Split]:
        splits = []
        inputs_by_user = {inp.user_id: inp for inp in inputs}  # type: ignore

        for user_id in participants:
            amount = inputs_by_user[user_id].value.quantize(
                Decimal("0.0000"), rounding=ROUND_HALF_UP
            )
            splits.append(Split(user_id=user_id, owed_amount=amount))

        return splits


class SplitStrategyFactory:
    _strategies = {
        SplitType.EQUAL: EqualSplitStrategy(),
        SplitType.PERCENT: PercentSplitStrategy(),
        SplitType.EXACT: ExactSplitStrategy(),
    }

    @classmethod
    def get(cls, split_type: SplitType) -> ISplitStrategy:
        return cls._strategies[split_type]
