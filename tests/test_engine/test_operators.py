"""Tests for the five atomic operators and the OperatorResult contract.

Follows atomic-operators spec and tdd.md §7.1.
L3: code+data replaces error_message; English diagnostics removed.
"""

import pytest

from fortress_engine.entities.entity import Entity
from fortress_engine.entities.components import WEIGHT, MAX_WEIGHT
from fortress_engine.engine.state import WorldState, LIMBO_ROOM_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    entity_id: str,
    type_: str = "item",
    components: dict | None = None,
    spatial_anchor: str | None = None,
    name: str | None = None,
) -> Entity:
    return Entity(
        entity_id=entity_id,
        type=type_,
        name=name or entity_id.replace("_", " ").title(),
        components=components or {},
        spatial_anchor=spatial_anchor,
    )


def _make_player(
    entity_id: str = "hero",
    capacity: int = 20,
    spatial_anchor: str = "room_01",
) -> Entity:
    return _make_entity(
        entity_id,
        type_="player",
        components={MAX_WEIGHT: capacity},
        spatial_anchor=spatial_anchor,
        name="Hero",
    )


def _minimal_state(
    player: Entity | None = None,
    room: Entity | None = None,
    extras: dict[str, Entity] | None = None,
) -> WorldState:
    """Build a WorldState with at least one room and one player."""
    p = player or _make_player()
    r = room or _make_entity("room_01", type_="room", components={"visited": False})
    entities: dict[str, Entity] = {"room_01": r, p.entity_id: p}
    if extras:
        entities.update(extras)
    return WorldState(
        entities=entities,
        player_controlled_entities=[p.entity_id],
        active_protagonist_id=p.entity_id,
    )


# ===================================================================
# OperatorResult contract (L3: error_message removed)
# ===================================================================


def test_operator_result_has_no_error_message_attribute():
    """OperatorResult has code+data; error_message attribute does NOT exist."""
    from fortress_engine.engine.operators import OperatorResult

    r = OperatorResult(success=True)
    assert hasattr(r, "code")
    assert hasattr(r, "data")
    assert not hasattr(r, "error_message")

    r_fail = OperatorResult(success=False, code="entity_not_found", data={"entity_id": "x"})
    assert r_fail.code == "entity_not_found"
    assert r_fail.data == {"entity_id": "x"}
    assert not hasattr(r_fail, "error_message")


# ===================================================================
# TRANSFER
# ===================================================================


def test_transfer_item_to_inventory_success():
    """TRANSFER: move item from room to protagonist inventory."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", capacity=20)
    sword = _make_entity("sword", components={WEIGHT: 3}, spatial_anchor="room_01")
    state = _minimal_state(hero, extras={"sword": sword})

    op = TransferOp(entity="sword", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is True
    assert result.code is None
    assert result.data == {}
    assert state.get_entity("sword").spatial_anchor == "hero"
    payload = result.events_payload
    assert payload is not None
    assert payload["entity_id"] == "sword"
    assert payload["from_container_id"] == "room_01"
    assert payload["to_container_id"] == "hero"


def test_transfer_item_exceeds_max_weight():
    """Item weight > protagonist capacity → code=not_portable + data."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", capacity=5)
    boulder = _make_entity(
        "boulder", components={WEIGHT: 10}, spatial_anchor="room_01"
    )
    state = _minimal_state(hero, extras={"boulder": boulder})

    op = TransferOp(entity="boulder", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "not_portable"
    assert result.data == {"entity_id": "boulder", "item_weight": 10, "max_capacity": 5}
    assert result.events_payload is None
    # State must be unchanged
    assert state.get_entity("boulder").spatial_anchor == "room_01"


def test_transfer_inventory_full():
    """Inventory full → code=too_heavy + data."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", capacity=10)
    # Hero already carrying 8 weight units.
    rock = _make_entity("rock", components={WEIGHT: 8}, spatial_anchor="hero")
    barrel = _make_entity(
        "barrel", components={WEIGHT: 5}, spatial_anchor="room_01"
    )
    state = _minimal_state(hero, extras={"rock": rock, "barrel": barrel})

    op = TransferOp(entity="barrel", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "too_heavy"
    assert result.data == {
        "entity_id": "barrel",
        "current_weight": 8,
        "item_weight": 5,
        "max_capacity": 10,
    }
    assert result.events_payload is None
    assert state.get_entity("barrel").spatial_anchor == "room_01"


def test_transfer_item_not_portable():
    """Entity with portable=false → code=not_portable + data."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", capacity=100)
    furniture = _make_entity(
        "table", components={"portable": False}, spatial_anchor="room_01"
    )
    state = _minimal_state(hero, extras={"table": furniture})

    op = TransferOp(entity="table", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "not_portable"
    assert result.data == {"entity_id": "table"}
    assert result.events_payload is None
    assert state.get_entity("table").spatial_anchor == "room_01"


def test_transfer_item_without_portable_key_is_portable():
    """Item without a 'portable' component defaults to portable=True."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", capacity=100)
    sword = _make_entity(
        "sword", components={WEIGHT: 3}, spatial_anchor="room_01"
    )
    state = _minimal_state(hero, extras={"sword": sword})

    op = TransferOp(entity="sword", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is True
    assert result.code is None
    assert state.get_entity("sword").spatial_anchor == "hero"


def test_transfer_non_portable_with_weight_fails():
    """portable=false + WEIGHT → code=not_portable."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", capacity=100)
    statue = _make_entity(
        "statue",
        components={"portable": False, WEIGHT: 10},
        spatial_anchor="room_01",
    )
    state = _minimal_state(hero, extras={"statue": statue})

    op = TransferOp(entity="statue", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "not_portable"
    assert result.data == {"entity_id": "statue"}
    assert result.events_payload is None
    assert state.get_entity("statue").spatial_anchor == "room_01"


def test_transfer_default_max_weight_is_40():
    """Protagonist without max_weight can carry items up to 40 units."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_entity(
        "hero",
        type_="player",
        components={"player_controlled": True},
        spatial_anchor="room_01",
        name="Hero",
    )
    heavy = _make_entity("heavy", components={WEIGHT: 40}, spatial_anchor="room_01")
    too_heavy = _make_entity(
        "too_heavy", components={WEIGHT: 41}, spatial_anchor="room_01"
    )
    room = _make_entity("room_01", type_="room")
    state = WorldState(
        entities={"room_01": room, "hero": hero, "heavy": heavy, "too_heavy": too_heavy},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
    )

    op_ok = TransferOp(entity="heavy", from_container="room_01", to_container="hero")
    result_ok = execute_transfer(state, op_ok, protagonist_id="hero")
    assert result_ok.success is True
    assert state.get_entity("heavy").spatial_anchor == "hero"

    op_too = TransferOp(entity="too_heavy", from_container="room_01", to_container="hero")
    result_too = execute_transfer(state, op_too, protagonist_id="hero")
    assert result_too.success is False
    assert result_too.code == "not_portable"
    assert result_too.data == {
        "entity_id": "too_heavy",
        "item_weight": 41,
        "max_capacity": 40,
    }


def test_transfer_to_nonexistent_container_fails():
    """TRANSFER to a container that does not exist fails with container_not_found."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero")
    rock = _make_entity("rock", components={WEIGHT: 1}, spatial_anchor="room_01")
    state = _minimal_state(hero, extras={"rock": rock})

    op = TransferOp(entity="rock", from_container="room_01", to_container="void")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "container_not_found"
    assert result.data == {"container_id": "void"}
    assert result.events_payload is None
    assert state.get_entity("rock").spatial_anchor == "room_01"


def test_transfer_entity_not_in_from_container_fails():
    """TRANSFER fails when the entity is not in from_container."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero")
    rock = _make_entity("rock", components={WEIGHT: 1}, spatial_anchor="room_02")
    room_02 = _make_entity("room_02", type_="room")
    state = _minimal_state(hero, extras={"rock": rock, "room_02": room_02})

    op = TransferOp(entity="rock", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "entity_not_in_container"
    assert result.data == {"entity_id": "rock", "container_id": "room_01"}
    assert result.events_payload is None
    assert state.get_entity("rock").spatial_anchor == "room_02"


def test_transfer_to_null_destroys_entity():
    """TRANSFER to None → spatial_anchor = None (destroyed)."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero")
    item = _make_entity(
        "cursed_gem", components={WEIGHT: 1}, spatial_anchor="room_01"
    )
    state = _minimal_state(hero, extras={"cursed_gem": item})

    op = TransferOp(entity="cursed_gem", from_container="room_01", to_container=None)
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is True
    assert result.code is None
    assert state.get_entity("cursed_gem").spatial_anchor is None
    payload = result.events_payload
    assert payload is not None
    assert payload["to_container_id"] is None


def test_transfer_at_anchor_resolves_to_protagonist_room():
    """TRANSFER with ``to_container == "@anchor"`` resolves to the
    protagonist's current spatial anchor at execution time (generic
    ``dejar <item>`` edges)."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", spatial_anchor="hall")
    key = _make_entity("key", components={WEIGHT: 1}, spatial_anchor="hero")
    hall = _make_entity("hall", type_="room")
    state = _minimal_state(hero, hall, extras={"key": key})
    # `_minimal_state` stores the room under its own entity_id.
    state.entities["hall"] = hall

    op = TransferOp(entity="key", from_container="hero", to_container="@anchor")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is True
    assert state.get_entity("key").spatial_anchor == "hall"
    payload = result.events_payload
    assert payload is not None
    assert payload["to_container_id"] == "hall"


def test_transfer_at_anchor_moves_with_protagonist():
    """``@anchor`` follows the protagonist: dropping in a different room
    lands the item there, not in the previous anchor."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", spatial_anchor="kitchen")
    key = _make_entity("key", components={WEIGHT: 1}, spatial_anchor="hero")
    kitchen = _make_entity("kitchen", type_="room")
    state = _minimal_state(hero, kitchen, extras={"key": key})
    state.entities["kitchen"] = kitchen

    # The protagonist is already in the kitchen (post-move).
    state.get_entity("hero").spatial_anchor = "kitchen"

    op = TransferOp(entity="key", from_container="hero", to_container="@anchor")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is True
    assert state.get_entity("key").spatial_anchor == "kitchen"


def test_transfer_at_anchor_without_room_destroys():
    """``@anchor`` when the protagonist has no anchor (limbo) moves the item
    to limbo — the destination is whatever the anchor resolves to."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero", spatial_anchor=None)
    key = _make_entity("key", components={WEIGHT: 1}, spatial_anchor="hero")
    state = _minimal_state(hero, extras={"key": key})

    op = TransferOp(entity="key", from_container="hero", to_container="@anchor")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is True
    assert state.get_entity("key").spatial_anchor is None


def test_transfer_fails_when_entity_missing():
    """TRANSFER for a non-existent entity fails with entity_not_found."""
    from fortress_engine.engine.operators import TransferOp, execute_transfer

    hero = _make_player("hero")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    op = TransferOp(entity="ghost", from_container="room_01", to_container="hero")
    result = execute_transfer(state, op, protagonist_id="hero")

    assert result.success is False
    assert result.code == "entity_not_found"
    assert result.data == {"entity_id": "ghost"}
    assert result.events_payload is None


# ===================================================================
# TRANSFORM
# ===================================================================


def test_transform_changes_component():
    """TRANSFORM: changes a component value when old_value matches."""
    from fortress_engine.engine.operators import TransformOp, execute_transform

    door = _make_entity("door_01", type_="door", components={"state": "closed"})
    state = WorldState(entities={"door_01": door})

    op = TransformOp(
        entity="door_01", component="state", old_value="closed", new_value="open"
    )
    result = execute_transform(state, op)

    assert result.success is True
    assert result.code is None
    assert state.get_entity("door_01").components["state"] == "open"
    payload = result.events_payload
    assert payload is not None
    assert payload["entity_id"] == "door_01"
    assert payload["component_key"] == "state"
    assert payload["old_value"] == "closed"
    assert payload["new_value"] == "open"


def test_transform_fails_if_old_value_mismatch():
    """TRANSFORM: old_value mismatch → code=transform_component_missing."""
    from fortress_engine.engine.operators import TransformOp, execute_transform

    door = _make_entity("door_01", type_="door", components={"state": "open"})
    state = WorldState(entities={"door_01": door})

    op = TransformOp(
        entity="door_01", component="state", old_value="closed", new_value="sealed"
    )
    result = execute_transform(state, op)

    assert result.success is False
    assert result.code == "transform_component_missing"
    assert result.data == {"entity_id": "door_01", "component": "state"}
    assert result.events_payload is None
    # State untouched
    assert state.get_entity("door_01").components["state"] == "open"


def test_transform_fails_if_entity_missing():
    """TRANSFORM: non-existent entity → code=entity_not_found."""
    from fortress_engine.engine.operators import TransformOp, execute_transform

    state = WorldState()
    op = TransformOp(
        entity="ghost", component="state", old_value="a", new_value="b"
    )
    result = execute_transform(state, op)

    assert result.success is False
    assert result.code == "entity_not_found"
    assert result.data == {"entity_id": "ghost"}
    assert result.events_payload is None


# ===================================================================
# COMBINE
# ===================================================================


def test_combine_destroys_inputs_and_creates_output():
    """COMBINE: inputs → None, output → anchor_id."""
    from fortress_engine.engine.operators import CombineOp, execute_combine

    flour = _make_entity("flour", spatial_anchor="room_01")
    water = _make_entity("water", spatial_anchor="room_01")
    dough = _make_entity("dough", spatial_anchor=None)  # in limbo
    room = _make_entity("room_01", type_="room")
    state = WorldState(
        entities={
            "flour": flour,
            "water": water,
            "dough": dough,
            "room_01": room,
        }
    )

    op = CombineOp(input_entities=["flour", "water"], output_entity="dough")
    result = execute_combine(state, op, anchor_id="room_01")

    assert result.success is True
    assert result.code is None
    assert result.events_payload is not None
    assert result.events_payload["input_entity_ids"] == ["flour", "water"]
    assert result.events_payload["output_entity_id"] == "dough"

    # Inputs destroyed
    assert state.get_entity("flour").spatial_anchor is None
    assert state.get_entity("water").spatial_anchor is None
    # Output anchored to room
    assert state.get_entity("dough").spatial_anchor == "room_01"


def test_combine_fails_if_input_missing():
    """COMBINE: missing input entity → code=combine_inputs_missing."""
    from fortress_engine.engine.operators import CombineOp, execute_combine

    flour = _make_entity("flour", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = WorldState(entities={"flour": flour, "room_01": room})

    op = CombineOp(input_entities=["flour", "water"], output_entity="dough")
    result = execute_combine(state, op, anchor_id="room_01")

    assert result.success is False
    assert result.code == "combine_inputs_missing"
    assert result.data == {"input_entity_id": "water"}
    assert result.events_payload is None


def test_combine_fails_if_output_missing():
    """COMBINE: output entity doesn't exist → code=combine_inputs_missing."""
    from fortress_engine.engine.operators import CombineOp, execute_combine

    flour = _make_entity("flour", spatial_anchor="room_01")
    water = _make_entity("water", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = WorldState(entities={"flour": flour, "water": water, "room_01": room})

    op = CombineOp(input_entities=["flour", "water"], output_entity="dough")
    result = execute_combine(state, op, anchor_id="room_01")

    assert result.success is False
    assert result.code == "combine_inputs_missing"
    assert result.data == {"output_entity_id": "dough"}
    assert result.events_payload is None


# ===================================================================
# FLAG
# ===================================================================


def test_flag_sets_value():
    """FLAG: sets a global flag, always succeeds."""
    from fortress_engine.engine.operators import FlagOp, execute_flag

    state = WorldState()
    state.set_flag("door_open", False)

    op = FlagOp(flag="door_open", value=True)
    result = execute_flag(state, op)

    assert result.success is True
    assert result.code is None
    assert state.get_flag("door_open") is True
    payload = result.events_payload
    assert payload is not None
    assert payload["flag_name"] == "door_open"
    assert payload["old_value"] is False
    assert payload["new_value"] is True


def test_flag_sets_new_flag():
    """FLAG: creating a brand-new flag."""
    from fortress_engine.engine.operators import FlagOp, execute_flag

    state = WorldState()
    op = FlagOp(flag="visited_cave", value=True)
    result = execute_flag(state, op)

    assert result.success is True
    assert result.code is None
    assert state.get_flag("visited_cave") is True
    payload = result.events_payload
    assert payload["flag_name"] == "visited_cave"
    assert payload["old_value"] is False  # default
    assert payload["new_value"] is True


# ===================================================================
# TELEPORT
# ===================================================================


def test_teleport_moves_entity():
    """TELEPORT: changes spatial_anchor."""
    from fortress_engine.engine.operators import TeleportOp, execute_teleport

    hero = _make_player("hero")
    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    state = WorldState(
        entities={"hero": hero, "room_a": room_a, "room_b": room_b}
    )

    op = TeleportOp(entity="hero", from_anchor="room_a", to_anchor="room_b")
    result = execute_teleport(state, op)

    assert result.success is True
    assert result.code is None
    assert state.get_entity("hero").spatial_anchor == "room_b"
    payload = result.events_payload
    assert payload is not None
    assert payload["entity_id"] == "hero"
    assert payload["from_anchor_id"] == "room_a"
    assert payload["to_anchor_id"] == "room_b"


def test_teleport_fails_if_entity_missing():
    """TELEPORT: entity doesn't exist → code=teleport_entity_not_found."""
    from fortress_engine.engine.operators import TeleportOp, execute_teleport

    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    state = WorldState(entities={"room_a": room_a, "room_b": room_b})

    op = TeleportOp(entity="ghost", from_anchor="room_a", to_anchor="room_b")
    result = execute_teleport(state, op)

    assert result.success is False
    assert result.code == "teleport_entity_not_found"
    assert result.data == {"entity_id": "ghost"}
    assert result.events_payload is None


def test_teleport_fails_if_room_not_found():
    """TELEPORT: to_anchor entity doesn't exist → code=teleport_anchor_not_found."""
    from fortress_engine.engine.operators import TeleportOp, execute_teleport

    hero = _make_player("hero")
    room_a = _make_entity("room_a", type_="room")
    state = WorldState(entities={"hero": hero, "room_a": room_a})

    op = TeleportOp(entity="hero", from_anchor="room_a", to_anchor="void")
    result = execute_teleport(state, op)

    assert result.success is False
    assert result.code == "teleport_anchor_not_found"
    assert result.data == {"to_anchor": "void"}
    assert result.events_payload is None


# ===================================================================
# execute_operator factory + operator_from_dict
# ===================================================================


def test_execute_operator_dispatches_flag():
    """execute_operator dispatches to the correct function based on op type."""
    from fortress_engine.engine.operators import execute_operator

    state = WorldState()
    op_data = {"type": "FLAG", "flag": "tested", "value": True}
    result = execute_operator(state, op_data, "hero", None)

    assert result.success is True
    assert state.get_flag("tested") is True


def test_execute_operator_dispatches_teleport():
    """execute_operator handles TELEPORT with graph for room validation."""
    from fortress_engine.engine.operators import execute_operator

    hero = _make_player("hero")
    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    state = WorldState(
        entities={"hero": hero, "room_a": room_a, "room_b": room_b}
    )

    op_data = {
        "type": "TELEPORT",
        "entity": "hero",
        "from_anchor": "room_a",
        "to_anchor": "room_b",
    }
    result = execute_operator(state, op_data, "hero", None)

    assert result.success is True
    assert state.get_entity("hero").spatial_anchor == "room_b"


def test_execute_operator_unknown_type_returns_error():
    """Unknown operator type → code=unknown_operator."""
    from fortress_engine.engine.operators import execute_operator

    state = WorldState()
    result = execute_operator(state, {"type": "BOGUS"}, "hero", None)

    assert result.success is False
    assert result.code == "unknown_operator"
    assert result.data == {"op_type": "BOGUS"}
    assert result.events_payload is None


def test_execute_operator_combine_unknown_protagonist_fails():
    """COMBINE with a missing protagonist → code=protagonist_not_found."""
    from fortress_engine.engine.operators import execute_operator

    flour = _make_entity("flour", spatial_anchor="room_01")
    dough = _make_entity("dough", spatial_anchor=None)
    room = _make_entity("room_01", type_="room")
    state = WorldState(
        entities={"flour": flour, "dough": dough, "room_01": room}
    )

    op_data = {"type": "COMBINE", "input_entities": ["flour"], "output_entity": "dough"}
    result = execute_operator(state, op_data, "ghost", None)

    assert result.success is False
    assert result.code == "protagonist_not_found"
    assert result.data == {"entity_id": "ghost"}
    assert result.events_payload is None
    # No state mutation happened
    assert state.get_entity("flour").spatial_anchor == "room_01"


def test_operator_from_dict_transfer():
    """operator_from_dict constructs TransferOp from dict."""
    from fortress_engine.engine.operators import operator_from_dict, TransferOp

    op = operator_from_dict({
        "type": "TRANSFER",
        "entity": "rock",
        "from_container": "room_01",
        "to_container": "hero",
    })

    assert isinstance(op, TransferOp)
    assert op.entity == "rock"
    assert op.from_container == "room_01"
    assert op.to_container == "hero"


def test_operator_from_dict_transform():
    """operator_from_dict constructs TransformOp from dict."""
    from fortress_engine.engine.operators import operator_from_dict, TransformOp

    op = operator_from_dict({
        "type": "TRANSFORM",
        "entity": "door",
        "component": "state",
        "old_value": "closed",
        "new_value": "open",
    })

    assert isinstance(op, TransformOp)
    assert op.entity == "door"
    assert op.component == "state"
    assert op.old_value == "closed"
    assert op.new_value == "open"


def test_operator_from_dict_combine():
    """operator_from_dict constructs CombineOp from dict."""
    from fortress_engine.engine.operators import operator_from_dict, CombineOp

    op = operator_from_dict({
        "type": "COMBINE",
        "input_entities": ["a", "b"],
        "output_entity": "c",
    })

    assert isinstance(op, CombineOp)
    assert op.input_entities == ["a", "b"]
    assert op.output_entity == "c"


def test_operator_from_dict_flag():
    """operator_from_dict constructs FlagOp from dict."""
    from fortress_engine.engine.operators import operator_from_dict, FlagOp

    op = operator_from_dict({
        "type": "FLAG",
        "flag": "door_open",
        "value": True,
    })

    assert isinstance(op, FlagOp)
    assert op.flag == "door_open"
    assert op.value is True


def test_operator_from_dict_unknown_type_raises_value_error():
    """operator_from_dict raises ValueError for an unknown operator type."""
    from fortress_engine.engine.operators import operator_from_dict

    with pytest.raises(ValueError) as exc:
        operator_from_dict({"type": "BOGUS"})
    assert "BOGUS" in str(exc.value)


def test_operator_from_dict_unknown_key_raises_value_error():
    """operator_from_dict raises ValueError naming an unknown dict key."""
    from fortress_engine.engine.operators import operator_from_dict

    with pytest.raises(ValueError) as exc:
        operator_from_dict({
            "type": "TRANSFER",
            "entity": "rock",
            "bogus_key": 1,
        })
    assert "bogus_key" in str(exc.value)
    assert "TRANSFER" in str(exc.value)


def test_operator_from_dict_missing_type_raises_value_error():
    """operator_from_dict raises ValueError when 'type' is missing."""
    from fortress_engine.engine.operators import operator_from_dict

    with pytest.raises(ValueError):
        operator_from_dict({"entity": "rock"})


def test_operator_from_dict_teleport():
    """operator_from_dict constructs TeleportOp from dict."""
    from fortress_engine.engine.operators import operator_from_dict, TeleportOp

    op = operator_from_dict({
        "type": "TELEPORT",
        "entity": "hero",
        "from_anchor": "room_01",
        "to_anchor": "room_02",
    })

    assert isinstance(op, TeleportOp)
    assert op.entity == "hero"
    assert op.from_anchor == "room_01"
    assert op.to_anchor == "room_02"


# ===================================================================
# Remaining failure paths & dispatch branches
# ===================================================================


def test_combine_op_defaults_input_entities_to_empty_list():
    """CombineOp without input_entities defaults to an empty list, not None."""
    from fortress_engine.engine.operators import CombineOp, operator_from_dict

    direct = CombineOp(output_entity="dough")
    assert direct.input_entities == []

    from_dict = operator_from_dict({"type": "COMBINE", "output_entity": "dough"})
    assert isinstance(from_dict, CombineOp)
    assert from_dict.input_entities == []


def test_execute_operator_dispatches_transfer():
    """execute_operator routes TRANSFER to execute_transfer."""
    from fortress_engine.engine.operators import execute_operator

    hero = _make_player("hero", capacity=20)
    sword = _make_entity("sword", components={WEIGHT: 3}, spatial_anchor="room_01")
    state = _minimal_state(hero, extras={"sword": sword})

    op_data = {
        "type": "TRANSFER",
        "entity": "sword",
        "from_container": "room_01",
        "to_container": "hero",
    }
    result = execute_operator(state, op_data, "hero", None)

    assert result.success is True
    assert result.events_payload is not None
    assert state.get_entity("sword").spatial_anchor == "hero"


def test_execute_operator_dispatches_transform():
    """execute_operator routes TRANSFORM to execute_transform."""
    from fortress_engine.engine.operators import execute_operator

    door = _make_entity("door_01", type_="door", components={"state": "closed"})
    state = WorldState(entities={"door_01": door})

    op_data = {
        "type": "TRANSFORM",
        "entity": "door_01",
        "component": "state",
        "old_value": "closed",
        "new_value": "open",
    }
    result = execute_operator(state, op_data, "hero", None)

    assert result.success is True
    assert result.events_payload is not None
    assert state.get_entity("door_01").components["state"] == "open"


def test_execute_operator_combine_uses_limbo_anchor_for_detached_protagonist():
    """COMBINE with a protagonist whose spatial_anchor is None anchors the
    output in LIMBO_ROOM_ID instead of crashing."""
    from fortress_engine.engine.operators import execute_operator

    hero = _make_player("hero", spatial_anchor=None)  # detached / in limbo
    flour = _make_entity("flour", spatial_anchor="room_01")
    dough = _make_entity("dough", spatial_anchor=None)
    room = _make_entity("room_01", type_="room")
    state = WorldState(
        entities={"hero": hero, "flour": flour, "dough": dough, "room_01": room},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
    )

    op_data = {"type": "COMBINE", "input_entities": ["flour"], "output_entity": "dough"}
    result = execute_operator(state, op_data, "hero", None)

    assert result.success is True
    assert state.get_entity("dough").spatial_anchor == LIMBO_ROOM_ID


def test_execute_operator_combine_uses_protagonist_anchor():
    """COMBINE dispatch anchors the output in the protagonist's actual room
    when its spatial_anchor is set (non-limbo branch)."""
    from fortress_engine.engine.operators import execute_operator

    hero = _make_player("hero", spatial_anchor="room_01")
    flour = _make_entity("flour", spatial_anchor="room_01")
    dough = _make_entity("dough", spatial_anchor=None)
    room = _make_entity("room_01", type_="room")
    state = WorldState(
        entities={"hero": hero, "flour": flour, "dough": dough, "room_01": room},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
    )

    op_data = {"type": "COMBINE", "input_entities": ["flour"], "output_entity": "dough"}
    result = execute_operator(state, op_data, "hero", None)

    assert result.success is True
    assert state.get_entity("dough").spatial_anchor == "room_01"
    assert result.events_payload == {
        "input_entity_ids": ["flour"],
        "output_entity_id": "dough",
    }


# ===================================================================
# Parametrized: every failure path → correct code + data
# ===================================================================

_operator_failure_cases = [
    # --- TRANSFER ---
    pytest.param(
        "TRANSFER",
        {
            "type": "TRANSFER", "entity": "ghost",
            "from_container": "room_01", "to_container": "hero",
        },
        {"hero": ("player", None, "room_01"), "room_01": ("room", None, None)},
        "entity_not_found",
        {"entity_id": "ghost"},
        id="TRANSFER: entity_not_found",
    ),
    pytest.param(
        "TRANSFER",
        {
            "type": "TRANSFER", "entity": "rock",
            "from_container": "room_01", "to_container": "hero",
        },
        {
            "hero": ("player", {"max_weight": 100}, "room_01"),
            "rock": ("item", {"weight": 1}, "room_02"),
            "room_01": ("room", None, None),
            "room_02": ("room", None, None),
        },
        "entity_not_in_container",
        {"entity_id": "rock", "container_id": "room_01"},
        id="TRANSFER: entity_not_in_container",
    ),
    pytest.param(
        "TRANSFER",
        {
            "type": "TRANSFER", "entity": "rock",
            "from_container": "room_01", "to_container": "void",
        },
        {"hero": ("player", None, "room_01"), "rock": ("item", {"weight": 1}, "room_01")},
        "container_not_found",
        {"container_id": "void"},
        id="TRANSFER: container_not_found",
    ),
    pytest.param(
        "TRANSFER",
        {
            "type": "TRANSFER", "entity": "table",
            "from_container": "room_01", "to_container": "hero",
        },
        {"hero": ("player", None, "room_01"), "table": ("item", {"portable": False}, "room_01")},
        "not_portable",
        {"entity_id": "table"},
        id="TRANSFER: not_portable (portable=False)",
    ),
    pytest.param(
        "TRANSFER",
        {
            "type": "TRANSFER", "entity": "boulder",
            "from_container": "room_01", "to_container": "hero",
        },
        {"hero": ("player", {"max_weight": 5}, "room_01"), "boulder": ("item", {"weight": 10}, "room_01")},
        "not_portable",
        {"entity_id": "boulder", "item_weight": 10, "max_capacity": 5},
        id="TRANSFER: not_portable (weight > max_capacity)",
    ),
    pytest.param(
        "TRANSFER",
        {
            "type": "TRANSFER", "entity": "barrel",
            "from_container": "room_01", "to_container": "hero",
        },
        {
            "hero": ("player", {"max_weight": 10}, "room_01"),
            "rock": ("item", {"weight": 8}, "hero"),
            "barrel": ("item", {"weight": 5}, "room_01"),
        },
        "too_heavy",
        {"entity_id": "barrel", "current_weight": 8, "item_weight": 5, "max_capacity": 10},
        id="TRANSFER: too_heavy",
    ),
    # --- TRANSFORM ---
    pytest.param(
        "TRANSFORM",
        {
            "type": "TRANSFORM", "entity": "ghost",
            "component": "state", "old_value": "a", "new_value": "b",
        },
        {},
        "entity_not_found",
        {"entity_id": "ghost"},
        id="TRANSFORM: entity_not_found",
    ),
    pytest.param(
        "TRANSFORM",
        {
            "type": "TRANSFORM", "entity": "door_01",
            "component": "state", "old_value": "closed", "new_value": "sealed",
        },
        {"door_01": ("door", {"state": "open"}, None)},
        "transform_component_missing",
        {"entity_id": "door_01", "component": "state"},
        id="TRANSFORM: transform_component_missing",
    ),
    # --- COMBINE ---
    pytest.param(
        "COMBINE",
        {
            "type": "COMBINE", "input_entities": ["flour", "water"],
            "output_entity": "dough",
        },
        {
            "hero": ("player", None, "room_01"),
            "flour": ("item", None, "room_01"),
            "room_01": ("room", None, None),
        },
        "combine_inputs_missing",
        {"input_entity_id": "water"},
        id="COMBINE: combine_inputs_missing (input)",
    ),
    pytest.param(
        "COMBINE",
        {
            "type": "COMBINE", "input_entities": ["flour", "water"],
            "output_entity": "dough",
        },
        {
            "hero": ("player", None, "room_01"),
            "flour": ("item", None, "room_01"),
            "water": ("item", None, "room_01"),
            "room_01": ("room", None, None),
        },
        "combine_inputs_missing",
        {"output_entity_id": "dough"},
        id="COMBINE: combine_inputs_missing (output)",
    ),
    # --- TELEPORT ---
    pytest.param(
        "TELEPORT",
        {
            "type": "TELEPORT", "entity": "ghost",
            "from_anchor": "room_a", "to_anchor": "room_b",
        },
        {"room_a": ("room", None, None), "room_b": ("room", None, None)},
        "teleport_entity_not_found",
        {"entity_id": "ghost"},
        id="TELEPORT: teleport_entity_not_found",
    ),
    pytest.param(
        "TELEPORT",
        {
            "type": "TELEPORT", "entity": "hero",
            "from_anchor": "room_a", "to_anchor": "void",
        },
        {"hero": ("player", None, "room_a"), "room_a": ("room", None, None)},
        "teleport_anchor_not_found",
        {"to_anchor": "void"},
        id="TELEPORT: teleport_anchor_not_found",
    ),
    # --- dispatch ---
    pytest.param(
        "BOGUS",
        {"type": "BOGUS"},
        {},
        "unknown_operator",
        {"op_type": "BOGUS"},
        id="dispatch: unknown_operator",
    ),
    pytest.param(
        "COMBINE",
        {
            "type": "COMBINE", "input_entities": ["flour"],
            "output_entity": "dough",
        },
        {"flour": ("item", None, "room_01"), "dough": ("item", None, None), "room_01": ("room", None, None)},
        "protagonist_not_found",
        {"entity_id": "ghost"},
        id="dispatch: protagonist_not_found",
    ),
]


def _op_entity_spec_to_entity(eid: str, spec: tuple) -> Entity:
    """Convert a (type, optional_components_dict, optional_spatial_anchor) spec to Entity."""
    type_, comps, anchor = spec
    components = {}
    if comps is not None:
        components.update(comps)
    return _make_entity(eid, type_=type_, components=components, spatial_anchor=anchor)


@pytest.mark.parametrize(
    "op_type_hint,op_data,entity_specs,expected_code,expected_data",
    _operator_failure_cases,
)
def test_operator_failure_codes(
    op_type_hint, op_data, entity_specs, expected_code, expected_data
):
    """Every operator failure path returns the correct code + data."""
    from fortress_engine.engine.operators import execute_operator

    entities: dict[str, Entity] = {}
    for eid, spec in entity_specs.items():
        entities[eid] = _op_entity_spec_to_entity(eid, spec)

    # Ensure room_01 exists for anchored entities
    if "room_01" not in entities:
        entities["room_01"] = _make_entity("room_01", type_="room")

    state = WorldState(entities=entities)

    protagonist_id = "ghost" if expected_code == "protagonist_not_found" else "hero"
    if protagonist_id not in entities and expected_code != "protagonist_not_found":
        entities[protagonist_id] = _make_entity(
            protagonist_id,
            type_="player",
            components={"max_weight": 100} if "max_weight" not in str(entity_specs.get(protagonist_id, ())) else {},
            spatial_anchor="room_01",
        )
        state = WorldState(entities=entities)

    # Ensure player_controlled is set for the protagonist
    state.player_controlled_entities = [protagonist_id]
    state.active_protagonist_id = protagonist_id

    result = execute_operator(state, op_data, protagonist_id, None)

    assert result.success is False
    assert result.code == expected_code
    assert result.data == expected_data
    assert result.events_payload is None
    assert not hasattr(result, "error_message")


# The final `else: Unhandled operator type` branch in execute_operator is
# unreachable by construction: op_type is validated against _OP_TO_CLASS up
# front, operator_from_dict always returns one of the five operator classes,
# and the isinstance chain covers all of them. No test can reach it without
# monkeypatching internals, so it is intentionally not exercised.
