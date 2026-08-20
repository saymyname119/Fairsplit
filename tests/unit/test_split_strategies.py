from decimal import Decimal
import pytest

from modules.expense.models import SplitInput, SplitType
from modules.expense.strategies import SplitStrategyFactory
from shared.errors import DomainError


def test_equal_split_strategy():
    strategy = SplitStrategyFactory.get(SplitType.EQUAL)
    
    # Test 3 participants, $30 -> 10, 10, 10
    splits = strategy.calculate_splits(Decimal("30.00"), ["u1", "u2", "u3"], None)
    assert len(splits) == 3
    assert all(s.owed_amount == Decimal("10.0000") for s in splits)
    assert sum(s.owed_amount for s in splits) == Decimal("30.00")
    
    # Test rounding: $10, 3 participants -> 3.3333, 3.3333, 3.3334
    splits = strategy.calculate_splits(Decimal("10.00"), ["u1", "u2", "u3"], None)
    assert splits[0].owed_amount == Decimal("3.3333")
    assert splits[1].owed_amount == Decimal("3.3333")
    assert splits[2].owed_amount == Decimal("3.3334")
    assert sum(s.owed_amount for s in splits) == Decimal("10.00")
    
    # Validation
    with pytest.raises(DomainError):
        strategy.validate(Decimal("10.00"), ["u1"], None)


def test_percent_split_strategy():
    strategy = SplitStrategyFactory.get(SplitType.PERCENT)
    
    # Test 100% split correctly
    inputs = [
        SplitInput(user_id="u1", value=Decimal("50")),
        SplitInput(user_id="u2", value=Decimal("30")),
        SplitInput(user_id="u3", value=Decimal("20")),
    ]
    splits = strategy.calculate_splits(Decimal("100.00"), ["u1", "u2", "u3"], inputs)
    assert splits[0].owed_amount == Decimal("50.0000")
    assert splits[1].owed_amount == Decimal("30.0000")
    assert splits[2].owed_amount == Decimal("20.0000")
    assert sum(s.owed_amount for s in splits) == Decimal("100.00")
    
    # Validation - does not sum to 100
    bad_inputs = [
        SplitInput(user_id="u1", value=Decimal("50")),
        SplitInput(user_id="u2", value=Decimal("30")),
        SplitInput(user_id="u3", value=Decimal("21")),
    ]
    with pytest.raises(DomainError, match="must sum to 100"):
        strategy.validate(Decimal("100.00"), ["u1", "u2", "u3"], bad_inputs)
        

def test_exact_split_strategy():
    strategy = SplitStrategyFactory.get(SplitType.EXACT)
    
    inputs = [
        SplitInput(user_id="u1", value=Decimal("15")),
        SplitInput(user_id="u2", value=Decimal("10")),
        SplitInput(user_id="u3", value=Decimal("5")),
    ]
    splits = strategy.calculate_splits(Decimal("30.00"), ["u1", "u2", "u3"], inputs)
    assert sum(s.owed_amount for s in splits) == Decimal("30.00")
    
    # Validation - sums wrong
    bad_inputs = [
        SplitInput(user_id="u1", value=Decimal("15")),
        SplitInput(user_id="u2", value=Decimal("10")),
        SplitInput(user_id="u3", value=Decimal("4")),
    ]
    with pytest.raises(DomainError, match="sum to 29"):
        strategy.validate(Decimal("30.00"), ["u1", "u2", "u3"], bad_inputs)
