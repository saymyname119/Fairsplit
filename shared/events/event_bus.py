"""
shared/events/event_bus.py
───────────────────────────
In-process publish/subscribe event bus.

Architecture contract
─────────────────────
This module defines IEventBus — the interface ALL publisher and subscriber code
depends on. The only concrete implementation here is InProcessEventBus, which
uses a plain dict of lists to route events synchronously in-process.

To migrate to Kafka/RabbitMQ in the future:
  1. Write KafkaEventBus(IEventBus) in a new file.
  2. Change the singleton in get_event_bus() to return KafkaEventBus().
  3. Nothing else changes — publishers and subscribers are unaware of the transport.

This is the Open/Closed principle applied to infrastructure:
open for extension (new bus implementations), closed for modification (callers).

Synchronous vs Asynchronous
────────────────────────────
The InProcessEventBus fires handlers *synchronously* in the publisher's call stack.
This keeps the code simple and easy to reason about during development.
The tradeoff: a slow subscriber (e.g., email send) will slow the HTTP response.

Production mitigation options (pick one at Prompt 3/5):
  Option A: Move to Kafka → handlers run in a separate consumer process entirely.
  Option B: Wrap handlers in asyncio.create_task() for fire-and-forget within the
            same process (simpler, but no durability guarantee on crash).
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, TypeAlias

from shared.events.base import DomainEvent

logger = logging.getLogger(__name__)

# Type alias for clarity — a handler is any callable that accepts a DomainEvent
EventHandler: TypeAlias = Callable[[DomainEvent], None]


class IEventBus(ABC):
    """
    Interface for the event bus.
    All modules interact ONLY with this interface — never with the concrete class.
    """

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.
        All subscribers registered for event.event_type will be called.
        """
        ...

    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Register a handler function for a specific event type.

        Parameters
        ----------
        event_type : The event_type string (e.g. "expense.ExpenseCreated").
                     Must match exactly — no wildcards in InProcessEventBus
                     (Kafka topics handle fan-out differently).
        handler    : Callable that receives the DomainEvent. Should not raise —
                     exceptions are caught and logged so one bad subscriber
                     doesn't prevent others from running.
        """
        ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler (useful in tests for isolation)."""
        ...


class InProcessEventBus(IEventBus):
    """
    Synchronous, in-process implementation of IEventBus.

    Uses a dict[event_type -> list[handler]] for routing.
    Thread-safety: not guaranteed. This is fine for the current single-process
    setup. A Kafka implementation would use Kafka's consumer group semantics.
    """

    def __init__(self) -> None:
        # defaultdict means we never need to check if the key exists before appending
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def publish(self, event: DomainEvent) -> None:
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            logger.debug("No subscribers for event type: %s", event.event_type)
            return

        logger.info("Publishing event: %s to %d subscriber(s)", event, len(handlers))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                # Critical: one failing subscriber must NOT prevent others from running.
                # In production (Kafka), a failed handler would use the dead-letter queue.
                logger.exception(
                    "Event handler %s failed for event %s — continuing to next handler",
                    handler.__name__,
                    event,
                )

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                logger.warning(
                    "Attempted to unsubscribe %s from %s but it was not registered",
                    handler.__name__,
                    event_type,
                )


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
#
# In a FastAPI app, the event bus is shared across all requests.
# We use a module-level singleton rather than FastAPI's dependency injection
# so that modules can subscribe at import time (before the app starts).
# ─────────────────────────────────────────────────────────────────────────────
_bus: IEventBus | None = None


def get_event_bus() -> IEventBus:
    """Return the application-wide event bus singleton."""
    global _bus
    if _bus is None:
        _bus = InProcessEventBus()
    return _bus


def reset_event_bus() -> None:
    """
    Reset the bus singleton.
    ONLY use this in tests to ensure handler isolation between test cases.
    """
    global _bus
    _bus = None
