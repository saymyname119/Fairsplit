"""
shared/events/base.py
─────────────────────
Base type for all domain events in the system.

Design note — why domain events?
  Modules MUST NOT call each other's service interfaces directly.
  Instead, a module publishes a DomainEvent; other modules subscribe to it.
  This is what makes the "could become microservices" claim credible:
  swapping the InProcessEventBus for a KafkaEventBus only requires
  changing one class — all publisher and subscriber code stays the same.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DomainEvent:
    """
    Immutable base class for all domain events.

    frozen=True  → events are value objects; they cannot be mutated after creation.
    Every subclass must call super().__init__() or use dataclass inheritance.

    Fields
    ------
    event_id    : Unique ID for idempotency (deduplication when we move to Kafka).
    event_type  : String discriminator used by the event bus to route to subscribers.
    occurred_at : UTC timestamp of when the domain event *happened* (not when it was
                  published — important distinction for audit logs and event sourcing).
    """

    event_type: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __str__(self) -> str:
        return f"{self.event_type}[{self.event_id}] @ {self.occurred_at.isoformat()}"
