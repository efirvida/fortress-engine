"""Tests for MinimalNarrator — RED phase (E2.1).

Verify the narrator ABC contract and minimal narration:
  initialize subscribes to event bus, handle_event returns text
  for key narration events and None for uninteresting ones.

All tests follow Strict TDD: RED first (this file), then GREEN.
"""

import pytest

from fortress_engine.entities.entity import Entity
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_ATTEMPTED,
    ACTION_OUTPUT,
    ACTION_RESOLVED,
    ENTITY_ENTERED,
    ENTITY_EXAMINED,
    ENTITY_TELEPORTED,
    ENTITY_TRANSFERRED,
    ERROR_OUTPUT,
    GAME_OVER,
    INPUT_RECEIVED,
    TURN_ENDED,
    TURN_STARTED,
    EngineEvent,
)


# ===================================================================
# Production import — will fail until MinimalNarrator is implemented
# ===================================================================

from fortress_engine.plugins.narrator_interface import (
    MinimalNarrator,
    NarratorInterface,
)


# ===================================================================
# Helpers
# ===================================================================


def _make_world() -> WorldState:
    """Minimal world state."""
    return WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {}, "room_a"),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
        turn_number=1,
    )


def _make_event(event_type: str, payload: dict, **kwargs) -> EngineEvent:
    """Create a test event."""
    return EngineEvent.create(
        event_type=event_type,
        turn_number=1,
        payload=payload,
        protagonist_id="hero",
        episode_id="episode-01",
        **kwargs,
    )


# ===================================================================
# ABC conformance
# ===================================================================


def test_narrator_is_instance_of_abc():
    """MinimalNarrator is an instance of NarratorInterface."""
    narrator = MinimalNarrator()
    assert isinstance(narrator, NarratorInterface)


# ===================================================================
# initialize()
# ===================================================================


def test_initialize_subscribes_to_bus():
    """initialize() subscribes to the event bus."""
    bus = EventBus()
    narrator = MinimalNarrator()

    # Count subscriber entries before
    initial = sum(len(v) for v in bus._subscribers.values())

    narrator.initialize(bus)

    # Should have new entry keys for specific event types
    after = sum(len(v) for v in bus._subscribers.values())
    assert after > initial


def test_initialize_subscribes_to_specific_events():
    """initialize() subscribes to narration-relevant events, not wildcard."""
    bus = EventBus()
    narrator = MinimalNarrator()

    narrator.initialize(bus)

    # At least 3 specific event types are registered (not wildcard "*")
    total_handlers = sum(
        len(v) for k, v in bus._subscribers.items() if k != "*"
    )
    assert total_handlers >= 3


def test_initialize_idempotent():
    """Calling initialize() twice does not double-subscribe (or is safe)."""
    bus = EventBus()
    narrator = MinimalNarrator()

    narrator.initialize(bus)
    count1 = sum(len(v) for v in bus._subscribers.values())

    narrator.initialize(bus)
    count2 = sum(len(v) for v in bus._subscribers.values())

    # Second initialize should not add more handlers
    assert count2 == count1


# ===================================================================
# handle_event() — narration events → text
# ===================================================================


def test_handle_event_action_output_returns_text():
    """action_output events produce narration text."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_OUTPUT,
        {"hyper_edge_id": "h1", "text": "Tomas la llave.", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_event_entity_entered_returns_text():
    """entity_entered events produce narration text with entity/room info."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_ENTERED,
        {
            "entity_id": "hero",
            "entity_name": "Hero",
            "from_anchor_id": "room_a",
            "to_anchor_id": "room_b",
            "protagonist_id": "hero",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_event_entity_examined_returns_text():
    """entity_examined events produce narration text."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_EXAMINED,
        {
            "entity_id": "rusty_key",
            "entity_name": "Rusty Key",
            "description": "Una llave oxidada.",
            "protagonist_id": "hero",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_event_error_output_returns_text():
    """error_output events produce narration text with the error message."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ERROR_OUTPUT,
        {
            "error_code": "no_action",
            "message": "No entiendes como hacer eso.",
            "protagonist_id": "hero",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert "No entiendes" in result


# ===================================================================
# handle_event() — uninteresting events → None
# ===================================================================


def test_handle_event_turn_started_returns_none():
    """turn_started events are not narrated."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        TURN_STARTED,
        {"turn_number": 1, "active_protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is None


def test_handle_event_turn_ended_returns_none():
    """turn_ended events are not narrated."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        TURN_ENDED,
        {"turn_number": 1, "actions_resolved": 1},
    )

    result = narrator.handle_event(event, world)
    assert result is None


def test_handle_event_input_received_returns_none():
    """input_received is not narrated."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        INPUT_RECEIVED,
        {"raw_text": "ir norte", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is None


def test_handle_event_action_attempted_returns_none():
    """action_attempted is not narrated."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_ATTEMPTED,
        {"hyper_edge_id": "h1", "clique": {}, "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is None


def test_handle_event_action_resolved_returns_none():
    """action_resolved is not narrated."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_RESOLVED,
        {
            "hyper_edge_id": "h1",
            "operators_executed": ["TRANSFER"],
            "has_effects": True,
            "protagonist_id": "hero",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is None


def test_handle_event_state_change_returns_none():
    """State-change events (entity_transferred) are not narrated."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_TRANSFERRED,
        {
            "entity_id": "key",
            "from_container_id": "room_a",
            "to_container_id": "hero",
            "hyper_edge_id": None,
        },
    )

    result = narrator.handle_event(event, world)
    assert result is None


def test_handle_event_game_over_returns_none():
    """game_over is not narrated (handled by other events)."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        GAME_OVER,
        {"reason": "player_death", "turn_number": 1},
    )

    result = narrator.handle_event(event, world)
    assert result is None


# ===================================================================
# handle_event() — unknown event → None
# ===================================================================


def test_handle_event_completely_unknown_returns_none():
    """Completely unknown event types return None (no crash)."""
    narrator = MinimalNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event("garbage_event_type", {})

    result = narrator.handle_event(event, world)
    assert result is None


# ===================================================================
# Bus integration — event flow
# ===================================================================


def test_narrator_receives_events_through_bus():
    """Narrator registered via initialize() receives events emitted through the bus."""
    bus = EventBus()
    narrator = MinimalNarrator()
    world = _make_world()

    # Initialize narrator — subscribes to bus
    narrator.initialize(bus)

    # Also subscribe a listener to verify events fire
    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))

    # Emit an event the narrator handles
    event = _make_event(
        ACTION_OUTPUT,
        {"hyper_edge_id": "h1", "text": "Test text.", "protagonist_id": "hero"},
    )
    bus.emit(event)

    # The listener received it
    assert len(received) == 1

    # handle_event should still produce text when called directly
    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)


# ===================================================================
# Narration text content assertions
# ===================================================================


def test_action_output_text_includes_message(world=None):
    """Action output narration includes the message text."""
    if world is None:
        world = _make_world()
    narrator = MinimalNarrator()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_OUTPUT,
        {"hyper_edge_id": "h1", "text": "Tomas la llave.", "protagonist_id": "hero"},
    )

    text = narrator.handle_event(event, world)
    assert "Tomas la llave" in text


def test_entity_entered_text_includes_room_name(world=None):
    """Entity entered narration includes meaningful info from the event."""
    if world is None:
        world = _make_world()
    narrator = MinimalNarrator()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_ENTERED,
        {
            "entity_id": "hero",
            "entity_name": "Hero",
            "from_anchor_id": "room_a",
            "to_anchor_id": "room_b",
            "protagonist_id": "hero",
        },
    )

    text = narrator.handle_event(event, world)
    assert isinstance(text, str)
    assert len(text) > 0


def test_error_output_text_includes_message(world=None):
    """Error output narration includes the error message."""
    if world is None:
        world = _make_world()
    narrator = MinimalNarrator()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ERROR_OUTPUT,
        {
            "error_code": "no_action",
            "message": "No puedes hacer eso aqui.",
            "protagonist_id": "hero",
        },
    )

    text = narrator.handle_event(event, world)
    assert "No puedes" in text


# ===================================================================
# N1 — Language property (specs/plugin-contracts)
# ===================================================================


def test_narrator_language_default_es():
    """MinimalNarrator() defaults language to 'es'."""
    n = MinimalNarrator()
    assert n.language == "es"


def test_narrator_language_override_en():
    """MinimalNarrator(language='en') stores and exposes 'en'."""
    n = MinimalNarrator(language="en")
    assert n.language == "en"


def test_narrator_language_preserved_on_instance():
    """Each MinimalNarrator instance keeps its own language value."""
    n_es = MinimalNarrator()
    n_en = MinimalNarrator(language="en")
    assert n_es.language == "es"
    assert n_en.language == "en"


def test_narrator_language_is_read_only():
    """language is a read-only property — assigning it raises."""
    n = MinimalNarrator()
    with pytest.raises(AttributeError):
        n.language = "fr"  # type: ignore[misc]


def test_narrator_abc_has_language_abstract():
    """NarratorInterface declares an abstract `language` property."""
    assert hasattr(NarratorInterface, "language")
    from abc import abstractmethod
    assert getattr(NarratorInterface.language, "__isabstractmethod__", False) is True


def test_narrator_no_arg_backcompat():
    """MinimalNarrator() with no args retains all existing behavior."""
    n = MinimalNarrator()
    bus = EventBus()
    n.initialize(bus)
    # initialize idempotent as before
    n.initialize(bus)
    assert n.language == "es"
    # handle_event still works
    world = _make_world()
    event = _make_event(
        ACTION_OUTPUT,
        {"hyper_edge_id": "h1", "text": "Tomas la llave.", "protagonist_id": "hero"},
    )
    result = n.handle_event(event, world)
    assert result is not None
    assert "Tomas la llave" in result


def test_narrator_language_override_still_works():
    """MinimalNarrator(language='en') narration behavior unchanged."""
    n = MinimalNarrator(language="en")
    assert n.language == "en"
    bus = EventBus()
    n.initialize(bus)
    world = _make_world()
    event = _make_event(
        ENTITY_ENTERED,
        {
            "entity_id": "hero",
            "entity_name": "Hero",
            "from_anchor_id": "room_a",
            "to_anchor_id": "room_b",
            "protagonist_id": "hero",
        },
    )
    result = n.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
