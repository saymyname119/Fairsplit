"""shared/events/__init__.py — public interface for the events package."""
from shared.events.base import DomainEvent
from shared.events.event_bus import IEventBus, get_event_bus, reset_event_bus
from shared.events.event_types import (
    ExpenseCreated,
    ExpenseSplitEvent,
    ExpenseDeleted,
    GroupCreated,
    MemberAdded,
    SettlementRecorded,
    UserRegistered,
)

__all__ = [
    "DomainEvent",
    "IEventBus",
    "get_event_bus",
    "reset_event_bus",
    # Events
    "UserRegistered",
    "GroupCreated",
    "MemberAdded",
    "ExpenseCreated",
    "ExpenseSplitEvent",
    "ExpenseDeleted",
    "SettlementRecorded",
]
