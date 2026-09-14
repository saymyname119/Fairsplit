"""
shared/events/event_types.py
─────────────────────────────
All named domain events in the system, organised by emitting module.

Convention
----------
- Event class name = past-tense verb phrase (something that *happened*)
- event_type string = "<module>.<PascalCaseName>" for namespacing
- All fields are immutable (inherited frozen=True from DomainEvent)

Adding a new event
------------------
1. Add a dataclass here that inherits DomainEvent.
2. Set event_type to the namespaced string constant.
3. Publish it from the module that owns the domain action.
4. Add a subscriber in the relevant module's __init__.py.

No other file needs to change — that's the point of the event bus abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from shared.events.base import DomainEvent

# ─────────────────────────────────────────────────────────────────────────────
# User module events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Fired after a new user account is created."""

    event_type: str = "user.UserRegistered"
    user_id: str = ""
    email: str = ""
    name: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Group module events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GroupCreated(DomainEvent):
    """Fired after a new group is created."""

    event_type: str = "group.GroupCreated"
    group_id: str = ""
    creator_id: str = ""
    name: str = ""


@dataclass(frozen=True)
class MemberAdded(DomainEvent):
    """Fired when a user joins a group."""

    event_type: str = "group.MemberAdded"
    group_id: str = ""
    user_id: str = ""
    added_by_id: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Expense module events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpenseCreated(DomainEvent):
    """
    Fired after an expense is persisted and splits are calculated.

    Subscribers:
    - LedgerModule  → updates net balances
    - NotificationModule → notifies group members
    - CacheModule (Prompt 3) → invalidates balances:group:{group_id}
    """

    event_type: str = "expense.ExpenseCreated"
    expense_id: str = ""
    group_id: str = ""
    paid_by_id: str = ""
    amount: Decimal = Decimal("0")
    description: str = ""
    splits: list[ExpenseSplitEvent] = field(default_factory=list)


@dataclass(frozen=True)
class ExpenseSplitEvent:
    user_id: str
    owed_amount: Decimal


@dataclass(frozen=True)
class ExpenseDeleted(DomainEvent):
    """Fired when an expense is deleted (reversal required in ledger)."""

    event_type: str = "expense.ExpenseDeleted"
    expense_id: str = ""
    group_id: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Ledger module events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SettlementRecorded(DomainEvent):
    """
    Fired after a settlement payment is recorded.

    Subscribers:
    - NotificationModule → notifies both parties
    - CacheModule (Prompt 3) → invalidates balances:group:{group_id}
    """

    event_type: str = "ledger.SettlementRecorded"
    settlement_id: str = ""
    group_id: str = ""
    from_user_id: str = ""
    to_user_id: str = ""
    amount: Decimal = Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# Invitation module events
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InvitationCreated(DomainEvent):
    """Fired when a group admin sends an invitation to an email."""

    event_type: str = "invitation.InvitationCreated"
    invitation_id: str = ""
    group_id: str = ""
    group_name: str = ""
    email: str = ""
    token: str = ""
    invited_by_name: str = ""


@dataclass(frozen=True)
class InvitationAccepted(DomainEvent):
    """Fired when an invitee accepts their invitation."""

    event_type: str = "invitation.InvitationAccepted"
    invitation_id: str = ""
    group_id: str = ""
    user_id: str = ""
    email: str = ""
