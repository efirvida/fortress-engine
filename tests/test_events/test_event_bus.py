"""Tests for EventBus — subscribe, unsubscribe, emit, wildcard, handler isolation, FIFO.

Follows event-system spec §2 and 13-event-system.md §4.
"""

from uuid import uuid4

from fortress_engine.events.event_types import EngineEvent


def _make_event(event_type: str = "test_event") -> EngineEvent:
    """Helper: create a minimal EngineEvent for bus tests."""
    return EngineEvent(
        event_id=uuid4(),
        type=event_type,
        turn_number=0,
        timestamp=0.0,
        payload={},
    )


# ---------------------------------------------------------------------------
# Subscribe & emit
# ---------------------------------------------------------------------------

def test_subscribe_and_emit():
    """Handler subscribed to a specific type receives matching events."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    received: list[EngineEvent] = []

    def handler(event: EngineEvent) -> None:
        received.append(event)

    bus.subscribe("test_event", handler)
    evt = _make_event("test_event")
    bus.emit(evt)

    assert len(received) == 1
    assert received[0] is evt


def test_subscribe_type_mismatch_not_delivered():
    """Handler for type 'a' does NOT receive events of type 'b'."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    received: list[EngineEvent] = []

    bus.subscribe("turn_started", lambda e: received.append(e))
    bus.emit(_make_event("turn_ended"))
    bus.emit(_make_event("turn_started"))

    assert len(received) == 1
    assert received[0].type == "turn_started"


def test_multiple_handlers_same_type():
    """Multiple handlers for the same type all receive the event."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    called: list[str] = []

    def h1(e: EngineEvent) -> None:
        called.append("h1")

    def h2(e: EngineEvent) -> None:
        called.append("h2")

    def h3(e: EngineEvent) -> None:
        called.append("h3")

    bus.subscribe("action_output", h1)
    bus.subscribe("action_output", h2)
    bus.subscribe("action_output", h3)
    bus.emit(_make_event("action_output"))

    assert called == ["h1", "h2", "h3"]


# ---------------------------------------------------------------------------
# FIFO ordering
# ---------------------------------------------------------------------------

def test_emit_is_fifo_by_registration_order():
    """Handlers are called in registration order (FIFO)."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    order: list[int] = []

    for i in range(5):

        def make_handler(n: int):
            def h(e: EngineEvent) -> None:
                order.append(n)
            return h

        bus.subscribe("fifo", make_handler(i))

    bus.emit(_make_event("fifo"))
    assert order == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Unsubscribe
# ---------------------------------------------------------------------------

def test_unsubscribe_removes_handler():
    """Unsubscribed handler no longer receives events."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    received: list[EngineEvent] = []

    def handler(event: EngineEvent) -> None:
        received.append(event)

    bus.subscribe("test", handler)
    bus.unsubscribe("test", handler)
    bus.emit(_make_event("test"))

    assert len(received) == 0


def test_unsubscribe_nonexistent_handler_does_not_raise():
    """Unsubscribing an unregistered handler silently succeeds."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()

    def handler(event: EngineEvent) -> None:
        pass

    # Not subscribed — unsubscribe should not raise
    bus.unsubscribe("never_subscribed", handler)


def test_unsubscribe_removes_only_specified_handler():
    """Unsubscribing one handler leaves others intact."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    called: list[str] = []

    def h1(e: EngineEvent) -> None:
        called.append("h1")

    def h2(e: EngineEvent) -> None:
        called.append("h2")

    bus.subscribe("test", h1)
    bus.subscribe("test", h2)
    bus.unsubscribe("test", h1)
    bus.emit(_make_event("test"))

    assert called == ["h2"]


# ---------------------------------------------------------------------------
# Wildcard "*"
# ---------------------------------------------------------------------------

def test_wildcard_receives_all_events():
    """Handler subscribed to "*" receives every event regardless of type."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    received: list[str] = []

    bus.subscribe("*", lambda e: received.append(e.type))
    bus.emit(_make_event("turn_started"))
    bus.emit(_make_event("action_output"))
    bus.emit(_make_event("game_over"))

    assert received == ["turn_started", "action_output", "game_over"]


def test_wildcard_and_specific_both_deliver():
    """Both specific and wildcard handlers fire (list-based verification)."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    delivered: set[str] = set()

    bus.subscribe("turn_started", lambda e: delivered.add("specific"))
    bus.subscribe("*", lambda e: delivered.add("wildcard"))
    bus.emit(_make_event("turn_started"))

    assert delivered == {"specific", "wildcard"}


# ---------------------------------------------------------------------------
# Handler error isolation
# ---------------------------------------------------------------------------

def test_failing_handler_does_not_block_others():
    """One handler raising an exception does not prevent others from running."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    second_called = False

    def failing_handler(event: EngineEvent) -> None:
        raise RuntimeError("simulated handler crash")

    def normal_handler(event: EngineEvent) -> None:
        nonlocal second_called
        second_called = True

    bus.subscribe("test_event", failing_handler)
    bus.subscribe("test_event", normal_handler)
    bus.emit(_make_event("test_event"))

    assert second_called is True


def test_failing_handler_exception_does_not_escape():
    """emit() never raises even when a handler throws."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()

    def boom(event: EngineEvent) -> None:
        raise RuntimeError("boom")

    bus.subscribe("test", boom)
    # Must not raise
    bus.emit(_make_event("test"))


def test_multiple_failing_handlers_isolated():
    """Multiple failing handlers don't cascade — each is isolated."""
    from fortress_engine.events.event_bus import EventBus

    bus = EventBus()
    third_called = False

    def fail1(event: EngineEvent) -> None:
        raise ValueError("fail1")

    def fail2(event: EngineEvent) -> None:
        raise TypeError("fail2")

    def ok(event: EngineEvent) -> None:
        nonlocal third_called
        third_called = True

    bus.subscribe("test", fail1)
    bus.subscribe("test", fail2)
    bus.subscribe("test", ok)
    # Must not raise
    bus.emit(_make_event("test"))

    assert third_called is True


# ---------------------------------------------------------------------------
# Not a singleton
# ---------------------------------------------------------------------------

def test_event_bus_instances_are_independent():
    """Each EventBus instance has its own subscriber registry — NOT a singleton."""
    from fortress_engine.events.event_bus import EventBus

    bus1 = EventBus()
    bus2 = EventBus()
    received1: list[EngineEvent] = []
    received2: list[EngineEvent] = []

    bus1.subscribe("test", lambda e: received1.append(e))
    bus2.subscribe("test", lambda e: received2.append(e))

    bus1.emit(_make_event("test"))

    assert len(received1) == 1
    assert len(received2) == 0  # bus2 is independent
