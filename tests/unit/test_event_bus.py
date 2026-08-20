"""tests/unit/test_event_bus.py — Unit tests for the InProcessEventBus."""
from __future__ import annotations

import pytest

from shared.events import DomainEvent, get_event_bus, reset_event_bus
from shared.events.event_bus import InProcessEventBus


def make_test_event(event_type: str = "test.TestEvent") -> DomainEvent:
    """Helper: create a minimal test event."""
    return DomainEvent(event_type=event_type)


class TestInProcessEventBus:
    def setup_method(self):
        reset_event_bus()

    def test_subscribe_and_receive_event(self):
        received = []
        bus = InProcessEventBus()
        bus.subscribe("test.TestEvent", lambda e: received.append(e))

        event = make_test_event()
        bus.publish(event)

        assert len(received) == 1
        assert received[0] is event

    def test_multiple_subscribers_all_called(self):
        calls = {"a": 0, "b": 0}
        bus = InProcessEventBus()
        bus.subscribe("test.TestEvent", lambda e: calls.__setitem__("a", calls["a"] + 1))
        bus.subscribe("test.TestEvent", lambda e: calls.__setitem__("b", calls["b"] + 1))

        bus.publish(make_test_event())

        assert calls["a"] == 1
        assert calls["b"] == 1

    def test_subscriber_exception_does_not_block_others(self):
        """A failing handler must NOT prevent subsequent handlers from running."""
        received = []

        def bad_handler(e: DomainEvent) -> None:
            raise RuntimeError("Simulated handler failure")

        def good_handler(e: DomainEvent) -> None:
            received.append(e)

        bus = InProcessEventBus()
        bus.subscribe("test.TestEvent", bad_handler)
        bus.subscribe("test.TestEvent", good_handler)

        bus.publish(make_test_event())  # must not raise

        assert len(received) == 1  # good_handler still ran

    def test_publish_with_no_subscribers_is_a_noop(self):
        bus = InProcessEventBus()
        # Should not raise
        bus.publish(make_test_event("test.UnsubscribedEvent"))

    def test_unsubscribe_removes_handler(self):
        received = []

        def handler(e: DomainEvent) -> None:
            received.append(e)

        bus = InProcessEventBus()
        bus.subscribe("test.TestEvent", handler)
        bus.unsubscribe("test.TestEvent", handler)
        bus.publish(make_test_event())

        assert received == []

    def test_event_is_immutable(self):
        """DomainEvent is frozen — mutation must raise."""
        event = make_test_event()
        with pytest.raises((AttributeError, TypeError)):
            event.event_type = "mutated"  # type: ignore[misc]

    def test_singleton_returns_same_instance(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset_clears_singleton(self):
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2
