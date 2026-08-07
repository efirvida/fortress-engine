"""Tests for WorldState — flags, entity queries, weight sum, serialization.

Follows world-state spec and tdd.md §4.4.
"""

from fortress_engine.entities.entity import Entity
from fortress_engine.entities.components import WEIGHT, MAX_WEIGHT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    entity_id: str,
    type_: str = "item",
    components: dict | None = None,
    spatial_anchor: str | None = None,
) -> Entity:
    return Entity(
        entity_id=entity_id,
        type=type_,
        name=entity_id.replace("_", " ").title(),
        components=components or {},
        spatial_anchor=spatial_anchor,
    )


def _make_player(
    entity_id: str, capacity: int = 20, spatial_anchor: str = "room_01"
) -> Entity:
    return Entity(
        entity_id=entity_id,
        type="player",
        name="Player",
        components={MAX_WEIGHT: capacity},
        spatial_anchor=spatial_anchor,
    )


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

def test_set_flag_and_get_flag():
    """set_flag stores a flag value and get_flag retrieves it."""
    from fortress_engine.engine.state import WorldState

    state = WorldState()
    state.set_flag("alarm", True)
    assert state.get_flag("alarm") is True

    state.set_flag("alarm", False)
    assert state.get_flag("alarm") is False


def test_get_flag_missing_returns_false():
    """get_flag on an unknown key returns False without mutating flag_book."""
    from fortress_engine.engine.state import WorldState

    state = WorldState()
    initial_keys = set(state.flag_book.keys())
    assert state.get_flag("unknown") is False
    # Must not have added the key.
    assert "unknown" not in state.flag_book
    assert set(state.flag_book.keys()) == initial_keys


# ---------------------------------------------------------------------------
# Entity queries
# ---------------------------------------------------------------------------

def test_get_entity_returns_entity():
    """get_entity returns the Entity for a known ID."""
    from fortress_engine.engine.state import WorldState

    e = _make_entity("sword_01")
    state = WorldState(entities={"sword_01": e})
    assert state.get_entity("sword_01") is e


def test_get_entity_raises_keyerror_for_missing():
    """get_entity raises KeyError with descriptive message for unknown ID."""
    from fortress_engine.engine.state import WorldState

    state = WorldState()
    try:
        state.get_entity("nonexistent")
    except KeyError as exc:
        assert "nonexistent" in str(exc)
    else:
        raise AssertionError("Expected KeyError was not raised")


def test_entity_exists():
    """entity_exists returns True/False correctly."""
    from fortress_engine.engine.state import WorldState

    e = _make_entity("key_01")
    state = WorldState(entities={"key_01": e})
    assert state.entity_exists("key_01") is True
    assert state.entity_exists("ghost") is False


def test_get_entities_in_container():
    """Filters entities by spatial_anchor."""
    from fortress_engine.engine.state import WorldState

    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    item_in_a = _make_entity("rock", spatial_anchor="room_a")
    item_in_b = _make_entity("stick", spatial_anchor="room_b")
    item_in_a2 = _make_entity("pebble", spatial_anchor="room_a")

    state = WorldState(
        entities={
            "room_a": room_a,
            "room_b": room_b,
            "rock": item_in_a,
            "stick": item_in_b,
            "pebble": item_in_a2,
        }
    )

    in_a = state.get_entities_in_container("room_a")
    assert len(in_a) == 2
    ids = {e.entity_id for e in in_a}
    assert ids == {"rock", "pebble"}

    in_b = state.get_entities_in_container("room_b")
    assert len(in_b) == 1
    assert in_b[0].entity_id == "stick"

    empty = state.get_entities_in_container("void")
    assert empty == []


def test_get_player_inventory():
    """get_player_inventory is an alias of get_entities_in_container for the player."""
    from fortress_engine.engine.state import WorldState

    player = _make_player("hero")
    sword = _make_entity("sword", components={"weight": 5}, spatial_anchor="hero")
    potion = _make_entity("potion", components={"weight": 2}, spatial_anchor="hero")
    rock = _make_entity("rock", components={"weight": 3}, spatial_anchor="room_01")

    state = WorldState(
        entities={
            "hero": player,
            "sword": sword,
            "potion": potion,
            "rock": rock,
            "room_01": _make_entity("room_01", type_="room"),
        }
    )

    inv = state.get_player_inventory("hero")
    inv_ids = {e.entity_id for e in inv}
    assert inv_ids == {"sword", "potion"}


# ---------------------------------------------------------------------------
# Weight sum
# ---------------------------------------------------------------------------

def test_get_inventory_weight_sums_weights():
    """Sum of WEIGHT components for items anchored to protagonist."""
    from fortress_engine.engine.state import WorldState

    hero = _make_player("hero", capacity=100)
    sword = _make_entity("sword", components={WEIGHT: 10}, spatial_anchor="hero")
    shield = _make_entity("shield", components={WEIGHT: 6}, spatial_anchor="hero")
    feather = _make_entity("feather", components={}, spatial_anchor="hero")
    # item in room, not in inventory
    rock = _make_entity("rock", components={WEIGHT: 99}, spatial_anchor="room_01")

    state = WorldState(
        entities={
            "hero": hero,
            "sword": sword,
            "shield": shield,
            "feather": feather,
            "rock": rock,
            "room_01": _make_entity("room_01", type_="room"),
        }
    )

    assert state.get_inventory_weight("hero") == 16  # 10 + 6 + 0


def test_get_inventory_weight_empty_inventory_returns_zero():
    """An empty inventory has weight 0."""
    from fortress_engine.engine.state import WorldState

    hero = _make_player("hero")
    state = WorldState(entities={"hero": hero})
    assert state.get_inventory_weight("hero") == 0


def test_get_inventory_weight_unknown_player_returns_zero():
    """Querying weight for a non-existent protagonist returns 0."""
    from fortress_engine.engine.state import WorldState

    state = WorldState()
    assert state.get_inventory_weight("ghost") == 0


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------

def test_to_dict_and_from_dict_round_trip():
    """Full state survives to_dict → from_dict with fidelity."""
    from fortress_engine.engine.state import WorldState

    room = _make_entity("room_01", type_="room", components={"light": True})
    hero = _make_player("hero", capacity=40, spatial_anchor="room_01")
    sword = _make_entity(
        "sword",
        components={"weight": 5, "damage": 10},
        spatial_anchor="hero",
    )
    key = _make_entity(
        "key_01",
        components={"weight": 1},
        spatial_anchor="room_01",
    )

    state = WorldState(
        entities={"room_01": room, "hero": hero, "sword": sword, "key_01": key},
        flag_book={"door_open": True, "boss_defeated": False},
        player_controlled_entities=["hero", "companion"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
        turn_number=7,
    )

    data = state.to_dict()
    reconstructed = WorldState.from_dict(data)

    # Structural equality checks
    assert reconstructed.entities.keys() == state.entities.keys()
    for eid, orig in state.entities.items():
        recon = reconstructed.entities[eid]
        assert recon.entity_id == orig.entity_id
        assert recon.type == orig.type
        assert recon.name == orig.name
        assert recon.components == orig.components
        assert recon.spatial_anchor == orig.spatial_anchor

    assert reconstructed.flag_book == state.flag_book
    assert reconstructed.player_controlled_entities == state.player_controlled_entities
    assert reconstructed.active_protagonist_id == state.active_protagonist_id
    assert reconstructed.current_episode_id == state.current_episode_id
    assert reconstructed.turn_number == state.turn_number


def test_from_dict_rejects_malformed_data():
    """from_dict raises ValueError for invalid input."""
    from fortress_engine.engine.state import WorldState

    try:
        WorldState.from_dict(None)  # type: ignore[arg-type]
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for None input")

    try:
        WorldState.from_dict({"entities": {}})
    except ValueError as exc:
        assert "Missing required key" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing keys")


def test_from_dict_rejects_non_dict_entities():
    """from_dict raises ValueError when the 'entities' value is not a dict.

    The dict must carry every required key so the non-dict check on the
    ``entities`` value is reached (not the missing-key guard).
    """
    from fortress_engine.engine.state import WorldState

    data = {
        "entities": "not_a_dict",
        "flag_book": {},
        "player_controlled_entities": [],
        "active_protagonist_id": "",
        "current_episode_id": "",
        "turn_number": 0,
    }
    try:
        WorldState.from_dict(data)
    except ValueError as exc:
        assert "'entities' must be a dict" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-dict entities")


# ---------------------------------------------------------------------------
# Multi-protagonist: list invariance
# ---------------------------------------------------------------------------

def test_player_controlled_entities_is_always_list():
    """player_controlled_entities is a list even for single protagonist."""
    from fortress_engine.engine.state import WorldState

    state = WorldState(player_controlled_entities=["solo_hero"])
    assert isinstance(state.player_controlled_entities, list)
    assert state.player_controlled_entities == ["solo_hero"]


def test_entities_with_none_spatial_anchor_are_not_in_any_container():
    """Entities with spatial_anchor=None don't appear in container queries."""
    from fortress_engine.engine.state import WorldState

    destroyed_sword = _make_entity("sword", spatial_anchor=None)
    room = _make_entity("room_01", type_="room")
    state = WorldState(
        entities={
            "sword": destroyed_sword,
            "room_01": room,
        }
    )
    in_room = state.get_entities_in_container("room_01")
    assert len(in_room) == 0  # room_01 itself is in the dict, but anchor is room_01? No… room_01's anchor is None.
    # Actually room entity has spatial_anchor=None by default. Let's check if it's found as "in itself".

    # Re-test: container_id itself is in entities dict but may not anchor to itself.
    # Let's use a different room.
    room_b = _make_entity("room_b", type_="room")
    item = _make_entity("item", spatial_anchor="room_b")
    state2 = WorldState(
        entities={
            "room_b": room_b,
            "item": item,
            "sword": destroyed_sword,
        }
    )
    in_b = state2.get_entities_in_container("room_b")
    ids = {e.entity_id for e in in_b}
    assert "item" in ids
    assert "sword" not in ids  # destroyed, not in any container
