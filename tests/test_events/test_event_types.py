"""Tests for EngineEvent dataclass, EngineEvent.create(), serialization, and event type constants.

Follows 13-event-system.md §3 and event-system spec.
"""

import json
import time as _time
from uuid import UUID, uuid4

import pytest

from fortress_engine.events.event_types import (
    EngineEvent,
    event_to_dict,
    event_from_dict,
    EVENT_CATEGORIES,
    # World events
    WORLD_LOADED,
    EPISODE_STARTED,
    EPISODE_COMPLETED,
    EPISODE_TRANSITION,
    GAME_COMPLETED,
    GAME_OVER,
    # Turn events
    TURN_STARTED,
    INPUT_RECEIVED,
    ACTION_ATTEMPTED,
    ACTION_RESOLVED,
    ENTITY_TURN_STARTED,
    ENTITY_TURN_ENDED,
    TURN_ENDED,
    # State-change events
    ENTITY_TRANSFERRED,
    ENTITY_TRANSFORMED,
    ENTITY_COMBINED,
    FLAG_SET,
    ENTITY_TELEPORTED,
    # Narration events
    ENTITY_ENTERED,
    ENTITY_DESCRIBED,
    ENTITY_EXAMINED,
    INVENTORY_LISTED,
    PROTAGONISTS_LISTED,
    ACTION_OUTPUT,
    ERROR_OUTPUT,
    SYSTEM_MESSAGE,
    # Entity events
    ENTITY_ACTED,
    ENTITY_OUTPUT,
    ENTITY_DESTROYED,
    # Meta-game events
    GAME_SAVED,
    GAME_LOADED,
    PROTAGONIST_SWITCHED,
    SAVE_REPLAY_STARTED,
    SAVE_REPLAY_ENDED,
)


# ---------------------------------------------------------------------------
# Event type constants (34 events, 6 categories)
# ---------------------------------------------------------------------------

def test_event_type_constants_count():
    """There are exactly 34 event type constants (6 categories)."""
    event_type_vars = [
        WORLD_LOADED, EPISODE_STARTED, EPISODE_COMPLETED, EPISODE_TRANSITION,
        GAME_COMPLETED, GAME_OVER,
        TURN_STARTED, INPUT_RECEIVED, ACTION_ATTEMPTED, ACTION_RESOLVED,
        ENTITY_TURN_STARTED, ENTITY_TURN_ENDED, TURN_ENDED,
        ENTITY_TRANSFERRED, ENTITY_TRANSFORMED, ENTITY_COMBINED,
        FLAG_SET, ENTITY_TELEPORTED,
        ENTITY_ENTERED, ENTITY_DESCRIBED, ENTITY_EXAMINED, INVENTORY_LISTED,
        PROTAGONISTS_LISTED, ACTION_OUTPUT, ERROR_OUTPUT, SYSTEM_MESSAGE,
        ENTITY_ACTED, ENTITY_OUTPUT, ENTITY_DESTROYED,
        GAME_SAVED, GAME_LOADED, PROTAGONIST_SWITCHED,
        SAVE_REPLAY_STARTED, SAVE_REPLAY_ENDED,
    ]
    assert len(event_type_vars) == 34
    assert len(set(event_type_vars)) == 34  # all unique


def test_event_type_constants_are_strings():
    """All event type constants are plain strings matching their names lowercased."""
    assert isinstance(WORLD_LOADED, str)
    assert WORLD_LOADED == "world_loaded"
    assert TURN_STARTED == "turn_started"
    assert ENTITY_TRANSFERRED == "entity_transferred"
    assert ACTION_OUTPUT == "action_output"
    assert ENTITY_ACTED == "entity_acted"
    assert ENTITY_OUTPUT == "entity_output"
    assert GAME_SAVED == "game_saved"


def test_entity_events_renamed_values():
    """Entity-agnostic event names carry entity_* values."""
    assert ENTITY_TURN_STARTED == "entity_turn_started"
    assert ENTITY_TURN_ENDED == "entity_turn_ended"
    assert ENTITY_ENTERED == "entity_entered"
    assert ENTITY_DESCRIBED == "entity_described"
    assert ENTITY_EXAMINED == "entity_examined"
    assert ENTITY_DESTROYED == "entity_destroyed"


def test_event_categories_structure():
    """EVENT_CATEGORIES groups the 34 events into 6 categories (§2)."""
    assert set(EVENT_CATEGORIES) == {
        "world", "turn", "state_change", "narration", "entity", "meta_game",
    }
    assert EVENT_CATEGORIES["entity"] == [
        ENTITY_ACTED, ENTITY_OUTPUT, ENTITY_ENTERED, ENTITY_DESTROYED,
    ]
    assert EVENT_CATEGORIES["narration"] == [
        ENTITY_ENTERED, ENTITY_DESCRIBED, ENTITY_EXAMINED,
        INVENTORY_LISTED, PROTAGONISTS_LISTED,
        ACTION_OUTPUT, ERROR_OUTPUT, SYSTEM_MESSAGE,
    ]
    assert EVENT_CATEGORIES["turn"] == [
        TURN_STARTED, INPUT_RECEIVED, ACTION_ATTEMPTED, ACTION_RESOLVED,
        ENTITY_TURN_STARTED, ENTITY_TURN_ENDED, TURN_ENDED,
    ]


def test_event_categories_partition_all_constants():
    """Every event constant appears in exactly the categories defined."""
    covered = {e for events in EVENT_CATEGORIES.values() for e in events}
    constants = {
        WORLD_LOADED, EPISODE_STARTED, EPISODE_COMPLETED, EPISODE_TRANSITION,
        GAME_COMPLETED, GAME_OVER,
        TURN_STARTED, INPUT_RECEIVED, ACTION_ATTEMPTED, ACTION_RESOLVED,
        ENTITY_TURN_STARTED, ENTITY_TURN_ENDED, TURN_ENDED,
        ENTITY_TRANSFERRED, ENTITY_TRANSFORMED, ENTITY_COMBINED,
        FLAG_SET, ENTITY_TELEPORTED,
        ENTITY_ENTERED, ENTITY_DESCRIBED, ENTITY_EXAMINED, INVENTORY_LISTED,
        PROTAGONISTS_LISTED, ACTION_OUTPUT, ERROR_OUTPUT, SYSTEM_MESSAGE,
        ENTITY_ACTED, ENTITY_OUTPUT, ENTITY_DESTROYED,
        GAME_SAVED, GAME_LOADED, PROTAGONIST_SWITCHED,
        SAVE_REPLAY_STARTED, SAVE_REPLAY_ENDED,
    }
    assert covered == constants
    assert len(constants) == 34  # one event merged away


# ---------------------------------------------------------------------------
# EngineEvent construction
# ---------------------------------------------------------------------------

def test_engine_event_is_frozen():
    """EngineEvent is a frozen dataclass — immutable after creation."""
    evt = EngineEvent(
        event_id=uuid4(),
        type="test",
        turn_number=1,
        timestamp=_time.monotonic(),
        payload={"key": "value"},
    )
    with pytest.raises(Exception):
        evt.type = "other"


def test_engine_event_defaults():
    """protagonist_id and episode_id default to None."""
    evt = EngineEvent(
        event_id=uuid4(),
        type="turn_started",
        turn_number=0,
        timestamp=_time.monotonic(),
        payload={},
    )
    assert evt.protagonist_id is None
    assert evt.episode_id is None


def test_engine_event_full():
    """All fields populated explicitly."""
    uid = uuid4()
    ts = _time.monotonic()
    evt = EngineEvent(
        event_id=uid,
        type="entity_transferred",
        turn_number=42,
        timestamp=ts,
        payload={"entity_id": "antorcha_01", "from_container_id": "room_03",
                  "to_container_id": "player_inventory"},
        protagonist_id="player_1",
        episode_id="episode-01",
    )
    assert evt.event_id == uid
    assert evt.type == "entity_transferred"
    assert evt.turn_number == 42
    assert evt.timestamp == ts
    assert evt.payload["entity_id"] == "antorcha_01"
    assert evt.protagonist_id == "player_1"
    assert evt.episode_id == "episode-01"


# ---------------------------------------------------------------------------
# EngineEvent.create() factory
# ---------------------------------------------------------------------------

def test_create_uses_uuid4():
    """EngineEvent.create() generates a fresh event_id via uuid4() each call."""
    e1 = EngineEvent.create("test", 1, {"x": 1})
    e2 = EngineEvent.create("test", 1, {"x": 1})
    assert e1.event_id != e2.event_id
    assert isinstance(e1.event_id, UUID)
    assert e1.event_id.version == 4


def test_create_uses_monotonic():
    """EngineEvent.create() sets timestamp via time.monotonic()."""
    before = _time.monotonic()
    evt = EngineEvent.create("test", 5, {})
    after = _time.monotonic()
    assert before <= evt.timestamp <= after


def test_create_defaults():
    """protagonist_id and episode_id default to None in EngineEvent.create()."""
    evt = EngineEvent.create("world_loaded", 0, {"world_id": "fortaleza", "episode_count": 2})
    assert evt.protagonist_id is None
    assert evt.episode_id is None


def test_create_with_optional_fields():
    """EngineEvent.create() accepts protagonist_id and episode_id."""
    evt = EngineEvent.create("turn_started", 1, {"turn_number": 1},
                 protagonist_id="player_1", episode_id="episode-01")
    assert evt.protagonist_id == "player_1"
    assert evt.episode_id == "episode-01"


# ---------------------------------------------------------------------------
# event_to_dict / event_from_dict round-trip
# ---------------------------------------------------------------------------

def test_event_to_dict_output():
    """event_to_dict produces a dictionary with all EngineEvent fields."""
    uid = uuid4()
    ts = 142.837
    evt = EngineEvent(
        event_id=uid,
        type="entity_transferred",
        turn_number=42,
        timestamp=ts,
        payload={"entity_id": "antorcha_01", "from_container_id": "room_03"},
        protagonist_id="player_1",
        episode_id="episode-01",
    )
    d = event_to_dict(evt)
    assert d["event_id"] == str(uid)
    assert d["type"] == "entity_transferred"
    assert d["turn_number"] == 42
    assert d["timestamp"] == ts
    assert d["payload"] == {"entity_id": "antorcha_01", "from_container_id": "room_03"}
    assert d["protagonist_id"] == "player_1"
    assert d["episode_id"] == "episode-01"


def test_event_from_dict_reconstructs():
    """event_from_dict reconstructs an EngineEvent from a dict."""
    uid = uuid4()
    data = {
        "event_id": str(uid),
        "type": "flag_set",
        "turn_number": 10,
        "timestamp": 50.5,
        "payload": {"flag_name": "door_open", "old_value": False, "new_value": True},
        "protagonist_id": "player_1",
        "episode_id": "episode-02",
    }
    evt = event_from_dict(data)
    assert evt.event_id == uid
    assert evt.type == "flag_set"
    assert evt.turn_number == 10
    assert evt.timestamp == 50.5
    assert evt.payload == data["payload"]
    assert evt.protagonist_id == "player_1"
    assert evt.episode_id == "episode-02"


def test_event_round_trip_preserves_all_fields():
    """event_to_dict → event_from_dict preserves all fields."""
    evt = EngineEvent.create(
        "action_output",
        turn_number=7,
        payload={"hyper_edge_id": "h1", "text": "You win!"},
        protagonist_id="player_2",
    )
    restored = event_from_dict(event_to_dict(evt))
    assert restored == evt


def test_event_round_trip_none_optionals():
    """Round-trip preserves None for protagonist_id and episode_id."""
    evt = EngineEvent.create("game_completed", 100, {"world_id": "f", "total_turns": 100})
    d = event_to_dict(evt)
    restored = event_from_dict(d)
    assert restored.protagonist_id is None
    assert restored.episode_id is None


def test_event_dict_is_json_serializable():
    """event_to_dict output is JSON-serializable (all primitives)."""
    evt = EngineEvent.create("entity_transferred", 1,
                 {"entity_id": "a", "from_container_id": "r1",
                  "to_container_id": "r2", "hyper_edge_id": "h1"})
    d = event_to_dict(evt)
    json_str = json.dumps(d)
    assert isinstance(json_str, str)
    # JSON round-trip preserves data
    reloaded = json.loads(json_str)
    assert reloaded["type"] == "entity_transferred"
    assert reloaded["turn_number"] == 1
