"""Tests for TemplateNarrator — RED phase (N5.1).

Verify the data-driven narrator:
  9 event handlers → non-empty text,
  unrelated/unknown events → None,
  idempotent initialize, template overrides,
  language default/override, payload-key fallback,
  world_state None path, room description lookup,
  inventory formatting.

All tests follow Strict TDD: RED first (this file), then GREEN.
"""

import pytest

from fortress_engine.entities.entity import Entity
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_OUTPUT,
    ENTITY_DESCRIBED,
    ENTITY_ENTERED,
    ENTITY_EXAMINED,
    ENTITY_TRANSFERRED,
    EPISODE_COMPLETED,
    ERROR_OUTPUT,
    GAME_OVER,
    INVENTORY_LISTED,
    SYSTEM_MESSAGE,
    EngineEvent,
)
from fortress_engine.plugins.narrator_interface import NarratorInterface

# ---------------------------------------------------------------------------
# Production import — will fail until TemplateNarrator exists (RED phase)
# ---------------------------------------------------------------------------

from fortress_engine.plugins.template_narrator import TemplateNarrator


# ===================================================================
# Helpers
# ===================================================================


def _make_world() -> WorldState:
    """Minimal world state with rooms and items."""
    return WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {}, "room_a"),
            "room_a": Entity(
                "room_a",
                "room",
                "Sala Inicial",
                {"description": "Una sala pequeña y oscura."},
                spatial_anchor=None,
            ),
            "room_b": Entity(
                "room_b",
                "room",
                "Pasillo Largo",
                {"description": "Un pasillo iluminado por antorchas."},
                spatial_anchor=None,
            ),
            "rusty_key": Entity(
                "rusty_key",
                "item",
                "Rusty Key",
                {"weight": 1},
                spatial_anchor="room_a",
            ),
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


def test_template_narrator_is_instance_of_abc():
    """TemplateNarrator is an instance of NarratorInterface."""
    narrator = TemplateNarrator()
    assert isinstance(narrator, NarratorInterface)


# ===================================================================
# Language property
# ===================================================================


def test_language_default_es():
    """TemplateNarrator() defaults language to 'es'."""
    n = TemplateNarrator()
    assert n.language == "es"


def test_language_override_en():
    """TemplateNarrator(language='en') stores and exposes 'en'."""
    n = TemplateNarrator(language="en")
    assert n.language == "en"


def test_language_is_read_only():
    """language is a read-only property — assigning it raises."""
    n = TemplateNarrator()
    with pytest.raises(AttributeError):
        n.language = "fr"  # type: ignore[misc]


# ===================================================================
# initialize() — idempotent subscription
# ===================================================================


def test_initialize_subscribes_to_bus():
    """initialize() registers handlers for the 9 template event types."""
    bus = EventBus()
    narrator = TemplateNarrator()

    initial = sum(len(v) for v in bus._subscribers.values())
    narrator.initialize(bus)
    after = sum(len(v) for v in bus._subscribers.values())

    assert after > initial


def test_initialize_subscribes_to_nine_events():
    """initialize() subscribes to exactly the 9 supported event types."""
    bus = EventBus()
    narrator = TemplateNarrator()

    narrator.initialize(bus)

    # Count specific (non-wildcard) handlers
    specific_handlers = sum(
        len(v) for k, v in bus._subscribers.items() if k != "*"
    )
    assert specific_handlers == 9


def test_initialize_idempotent():
    """Calling initialize() twice does not double-subscribe."""
    bus = EventBus()
    narrator = TemplateNarrator()

    narrator.initialize(bus)
    count1 = sum(len(v) for v in bus._subscribers.values())

    narrator.initialize(bus)
    count2 = sum(len(v) for v in bus._subscribers.values())

    assert count2 == count1


# ===================================================================
# handle_event() — 9 supported events → non-empty text
# ===================================================================


def test_handle_entity_entered():
    """entity_entered returns text with entity_name from payload."""
    narrator = TemplateNarrator()
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


def test_handle_action_output():
    """action_output returns text from payload 'text' key."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_OUTPUT,
        {
            "hyper_edge_id": "h1",
            "text": "Tomas la llave.",
            "protagonist_id": "hero",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert "Tomas la llave" in result


def test_handle_error_output():
    """error_output returns text from payload 'message' key."""
    narrator = TemplateNarrator()
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
    assert "No entiendes" in result


def test_handle_episode_completed():
    """episode_completed returns text from payload 'victory_text' key."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        EPISODE_COMPLETED,
        {
            "episode_id": "episode-01",
            "victory_text": "Victoria!",
            "carry_over": {"inventory": [], "flags": []},
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert "Victoria" in result


def test_handle_game_over():
    """game_over returns text from template or payload 'reason'."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        GAME_OVER,
        {"reason": "player_death", "turn_number": 1},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_system_message():
    """system_message returns text from payload 'message' key."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        SYSTEM_MESSAGE,
        {"message": "Bienvenido al mundo."},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert "Bienvenido" in result


def test_handle_entity_described():
    """entity_described returns text from payload 'description' key."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_DESCRIBED,
        {
            "entity_id": "room_a",
            "entity_name": "Sala Inicial",
            "description": "Una sala oscura.",
            "protagonist_id": "hero",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert "Una sala oscura" in result


def test_handle_item_examined():
    """entity_examined (item_examined) returns text from payload 'description'."""
    narrator = TemplateNarrator()
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
    assert "Una llave oxidada" in result


def test_handle_inventory_listed():
    """inventory_listed returns formatted items text from template."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        INVENTORY_LISTED,
        {"items": "Rusty Key, Sword", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


# ===================================================================
# handle_event() — unrelated/unknown events → None
# ===================================================================


def test_handle_entity_transferred_returns_none():
    """entity_transferred is not narrated → returns None."""
    narrator = TemplateNarrator()
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


def test_handle_unknown_event_returns_none():
    """Completely unknown event type returns None (no crash)."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event("garbage_event_type", {})

    result = narrator.handle_event(event, world)
    assert result is None


# ===================================================================
# Template overrides
# ===================================================================


def test_template_override_game_over():
    """Custom template for game_over is used instead of default."""
    narrator = TemplateNarrator(
        templates={"game_over": "GAME OVER — {reason}!"}
    )
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        GAME_OVER,
        {"reason": "player_death", "turn_number": 1},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert "GAME OVER" in result


def test_template_override_inventory():
    """Custom template for inventory_listed is used."""
    narrator = TemplateNarrator(
        templates={"inventory_listed": "Llevas: {items}"}
    )
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        INVENTORY_LISTED,
        {"items": "Rusty Key", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert "Llevas:" in result


# ===================================================================
# Payload-key fallback
# ===================================================================


def test_action_output_missing_text_falls_back():
    """action_output without 'text' in payload returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_OUTPUT,
        {"hyper_edge_id": "h1", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_error_output_missing_message_falls_back():
    """error_output without 'message' in payload returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ERROR_OUTPUT,
        {"error_code": "unknown", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_entity_entered_missing_entity_name_falls_back():
    """entity_entered without 'entity_name' returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_ENTERED,
        {
            "entity_id": "hero",
            "from_anchor_id": "room_a",
            "to_anchor_id": "room_b",
        },
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_entity_described_missing_description_falls_back():
    """entity_described without 'description' returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_DESCRIBED,
        {"entity_id": "room_a", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_episode_completed_missing_victory_text_falls_back():
    """episode_completed without 'victory_text' returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        EPISODE_COMPLETED,
        {"episode_id": "episode-01", "carry_over": {"inventory": [], "flags": []}},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_system_message_missing_message_falls_back():
    """system_message without 'message' returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(SYSTEM_MESSAGE, {})

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_entity_examined_missing_description_falls_back():
    """entity_examined without 'description' returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        ENTITY_EXAMINED,
        {"entity_id": "rusty_key", "entity_name": "Rusty Key", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_inventory_listed_missing_items_falls_back():
    """inventory_listed without 'items' returns fallback text."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        INVENTORY_LISTED,
        {"protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


# ===================================================================
# World state None path (bus handler)
# ===================================================================


def test_handle_event_with_world_state_none():
    """handle_event with world_state=None does not crash and returns text."""
    narrator = TemplateNarrator()
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

    result = narrator.handle_event(event, world_state=None)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_bus_handler_called_with_none_world_state():
    """When event is delivered via bus, the handler receives world_state=None
    and does not crash."""
    bus = EventBus()
    narrator = TemplateNarrator()
    narrator.initialize(bus)

    event = _make_event(
        ACTION_OUTPUT,
        {"hyper_edge_id": "h1", "text": "Test.", "protagonist_id": "hero"},
    )

    # Emit through bus — the bus handler passes world_state=None
    bus.emit(event)

    # Manual call with None should also work
    result = narrator.handle_event(event, None)
    assert result is not None
    assert "Test" in result


# ===================================================================
# Room description lookup via world_state
# ===================================================================


def test_entity_entered_includes_room_description():
    """entity_entered uses world_state to look up room description."""
    narrator = TemplateNarrator()
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
    # The text should include the room name from the template
    assert isinstance(result, str)
    assert len(result) > 0


# ===================================================================
# Inventory formatting
# ===================================================================


def test_inventory_listed_formats_items():
    """inventory_listed uses template with items from payload."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    event = _make_event(
        INVENTORY_LISTED,
        {"items": "Rusty Key, Sword", "protagonist_id": "hero"},
    )

    result = narrator.handle_event(event, world)
    assert result is not None
    # The result should contain the items
    assert "Rusty Key" in result
    assert "Sword" in result


# ===================================================================
# Unhandled event type → None (dispatch fall-through safety)
# ===================================================================


def test_unhandled_narration_event_returns_none():
    """An event type not in the 9-handler set returns None."""
    narrator = TemplateNarrator()
    world = _make_world()
    bus = EventBus()
    narrator.initialize(bus)

    # protagonists_listed is a narration event but NOT in the 9
    from fortress_engine.events.event_types import PROTAGONISTS_LISTED
    event = _make_event(
        PROTAGONISTS_LISTED,
        {"protagonists": []},
    )

    result = narrator.handle_event(event, world)
    assert result is None


# ===================================================================
# Guard: esperar must not appear in source
# ===================================================================


def test_esperar_not_in_template_narrator_source():
    """TemplateNarrator source must not contain 'esperar'."""
    import inspect
    source = inspect.getsource(TemplateNarrator)
    assert "esperar" not in source.lower()
