"""Tests for GoalEvaluator — 6 atomic conditions, recursive and/or, output/side_effects.

Follows goal-evaluator spec and tdd.md §4.5.
All tests are entity-agnostic — no entity type constants or closed sets.
"""

from fortress_engine.entities.entity import Entity, GoalCondition, GoalConditions
from fortress_engine.engine.state import WorldState


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


def _state(
    entities: dict[str, Entity] | None = None,
    flags: dict[str, bool] | None = None,
) -> WorldState:
    return WorldState(
        entities=entities or {},
        flag_book=flags or {},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="ep-01",
    )


def _conditions(*items, output: str = "You win!", side_effects=None) -> GoalConditions:
    return GoalConditions(
        conditions=list(items),
        output=output,
        side_effects=side_effects or [],
    )


# ===================================================================
# entity_in_room
# ===================================================================


def test_entity_in_room_true():
    """entity_in_room: entity's spatial_anchor matches the given anchor."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "wolf": _make_entity("wolf", spatial_anchor="forest"),
        "forest": _make_entity("forest", type_="room"),
    })
    gc = GoalCondition(type="entity_in_room", params={"entity": "wolf", "room": "forest"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_entity_in_room_false():
    """entity_in_room: entity's spatial_anchor does NOT match."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "wolf": _make_entity("wolf", spatial_anchor="cave"),
        "forest": _make_entity("forest", type_="room"),
    })
    gc = GoalCondition(type="entity_in_room", params={"entity": "wolf", "room": "forest"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_entity_in_room_missing_entity_returns_false():
    """Unknown entity ID evaluates false rather than raising."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"forest": _make_entity("forest", type_="room")})
    gc = GoalCondition(type="entity_in_room", params={"entity": "ghost", "room": "forest"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


# ===================================================================
# entity_not_in_room
# ===================================================================


def test_entity_not_in_room_true():
    """entity_not_in_room: entity is NOT in the room."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "wolf": _make_entity("wolf", spatial_anchor="cave"),
        "forest": _make_entity("forest", type_="room"),
    })
    gc = GoalCondition(type="entity_not_in_room", params={"entity": "wolf", "room": "forest"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_entity_not_in_room_false():
    """entity_not_in_room: entity IS in the room — fails."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "wolf": _make_entity("wolf", spatial_anchor="forest"),
        "forest": _make_entity("forest", type_="room"),
    })
    gc = GoalCondition(type="entity_not_in_room", params={"entity": "wolf", "room": "forest"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_entity_not_in_room_missing_entity_returns_true():
    """Missing entity NOT in room — true (it's definitely not there)."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"forest": _make_entity("forest", type_="room")})
    gc = GoalCondition(type="entity_not_in_room", params={"entity": "ghost", "room": "forest"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


# ===================================================================
# entity_dead
# ===================================================================


def test_entity_dead_true():
    """entity_dead: entity's spatial_anchor is None."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"wolf": _make_entity("wolf", spatial_anchor=None)})
    gc = GoalCondition(type="entity_dead", params={"entity": "wolf"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_entity_dead_false():
    """entity_dead: entity is alive (has a spatial_anchor)."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"wolf": _make_entity("wolf", spatial_anchor="forest")})
    gc = GoalCondition(type="entity_dead", params={"entity": "wolf"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_entity_dead_missing_entity_returns_false():
    """Missing entity is not considered dead — returns false."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({})
    gc = GoalCondition(type="entity_dead", params={"entity": "ghost"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


# ===================================================================
# flag_is_set
# ===================================================================


def test_flag_is_set_true():
    """flag_is_set: flag exists and is True."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(flags={"secret_found": True})
    gc = GoalCondition(type="flag_is_set", params={"flag": "secret_found"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_flag_is_set_false():
    """flag_is_set: flag exists but is False."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(flags={"secret_found": False})
    gc = GoalCondition(type="flag_is_set", params={"flag": "secret_found"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_flag_is_set_missing_flag_returns_false():
    """flag_is_set: flag does not exist — returns False."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state()
    gc = GoalCondition(type="flag_is_set", params={"flag": "unknown"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


# ===================================================================
# flag_is_not_set
# ===================================================================


def test_flag_is_not_set_true():
    """flag_is_not_set: flag exists but is False."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(flags={"dragon_alive": False})
    gc = GoalCondition(type="flag_is_not_set", params={"flag": "dragon_alive"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_flag_is_not_set_missing_flag_returns_true():
    """flag_is_not_set: missing flag counts as not set."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state()
    gc = GoalCondition(type="flag_is_not_set", params={"flag": "secret"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_flag_is_not_set_false():
    """flag_is_not_set: flag exists and is True — fails."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(flags={"dragon_alive": True})
    gc = GoalCondition(type="flag_is_not_set", params={"flag": "dragon_alive"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


# ===================================================================
# entity_has_component
# ===================================================================


def test_entity_has_component_true():
    """entity_has_component: component matches expected value (raw == equality)."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "sword": _make_entity("sword", components={"blessed": True, "material": "steel"})
    })
    gc = GoalCondition(
        type="entity_has_component",
        params={"entity": "sword", "component": "blessed", "value": True},
    )
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_entity_has_component_false_value_mismatch():
    """entity_has_component: component exists but value differs — fails."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "sword": _make_entity("sword", components={"blessed": False})
    })
    gc = GoalCondition(
        type="entity_has_component",
        params={"entity": "sword", "component": "blessed", "value": True},
    )
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_entity_has_component_missing_component_returns_false():
    """entity_has_component: component key missing — returns False."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"sword": _make_entity("sword")})
    gc = GoalCondition(
        type="entity_has_component",
        params={"entity": "sword", "component": "blessed", "value": True},
    )
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_entity_has_component_missing_entity_returns_false():
    """entity_has_component: entity missing — returns False."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({})
    gc = GoalCondition(
        type="entity_has_component",
        params={"entity": "ghost", "component": "visible", "value": True},
    )
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


def test_entity_has_component_list_value_equality():
    """entity_has_component: list values compared with raw == (not isinstance check)."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "chest": _make_entity("chest", components={"tags": ["cold", "wet"]})
    })
    gc = GoalCondition(
        type="entity_has_component",
        params={"entity": "chest", "component": "tags", "value": ["cold", "wet"]},
    )
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is True


def test_entity_has_component_list_value_mismatch():
    """entity_has_component: list values differ — fails."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({
        "chest": _make_entity("chest", components={"tags": ["cold"]})
    })
    gc = GoalCondition(
        type="entity_has_component",
        params={"entity": "chest", "component": "tags", "value": ["cold", "wet"]},
    )
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


# ===================================================================
# Composite: and
# ===================================================================


def test_and_all_true():
    """and: all conditions true → true."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor=None)},
        flags={"door_open": True},
    )
    gc = GoalConditions(
        conditions=[
            {"and": [
                GoalCondition(type="entity_dead", params={"entity": "wolf"}),
                GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
            ]}
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is True


def test_and_one_false():
    """and: one condition false → false."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor="cave")},
        flags={"door_open": True},
    )
    gc = GoalConditions(
        conditions=[
            {"and": [
                GoalCondition(type="entity_dead", params={"entity": "wolf"}),
                GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
            ]}
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is False


def test_and_empty_returns_true():
    """and: empty list is vacuously true."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state()
    gc = GoalConditions(
        conditions=[{"and": []}],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is True


# ===================================================================
# Composite: or
# ===================================================================


def test_or_at_least_one_true():
    """or: at least one true → true."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor=None)},
        flags={"door_open": False},
    )
    gc = GoalConditions(
        conditions=[
            {"or": [
                GoalCondition(type="entity_dead", params={"entity": "wolf"}),
                GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
            ]}
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is True


def test_or_all_false():
    """or: all false → false."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor="cave")},
        flags={"door_open": False},
    )
    gc = GoalConditions(
        conditions=[
            {"or": [
                GoalCondition(type="entity_dead", params={"entity": "wolf"}),
                GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
            ]}
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is False


def test_or_empty_returns_false():
    """or: empty list is false (no alternative satisfied)."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state()
    gc = GoalConditions(
        conditions=[{"or": []}],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is False


# ===================================================================
# Nested and/or
# ===================================================================


def test_nested_and_or_true():
    """Nested: and(..., or(...)) — both branches satisfied."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor=None)},
        flags={"door_open": True, "gate_unlocked": False},
    )
    gc = GoalConditions(
        conditions=[
            {"and": [
                GoalCondition(type="entity_dead", params={"entity": "wolf"}),
                {"or": [
                    GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
                    GoalCondition(type="flag_is_set", params={"flag": "gate_unlocked"}),
                ]},
            ]}
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is True


def test_nested_or_and_false():
    """Nested: or(..., and(...)) — neither branch satisfied."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor="cave")},
        flags={"door_open": False, "gate_unlocked": False},
    )
    gc = GoalConditions(
        conditions=[
            {"or": [
                GoalCondition(type="entity_dead", params={"entity": "wolf"}),
                {"and": [
                    GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
                    GoalCondition(type="flag_is_set", params={"flag": "gate_unlocked"}),
                ]},
            ]}
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is False


# ===================================================================
# Multiple top-level conditions (implicit and)
# ===================================================================


def test_multiple_top_level_all_true():
    """Multiple top-level conditions with no composite dict → all must be true."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor=None)},
        flags={"door_open": True},
    )
    gc = GoalConditions(
        conditions=[
            GoalCondition(type="entity_dead", params={"entity": "wolf"}),
            GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is True


def test_multiple_top_level_one_false():
    """Multiple top-level — one fails → overall fails."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state(
        entities={"wolf": _make_entity("wolf", spatial_anchor=None)},
        flags={"door_open": False},
    )
    gc = GoalConditions(
        conditions=[
            GoalCondition(type="entity_dead", params={"entity": "wolf"}),
            GoalCondition(type="flag_is_set", params={"flag": "door_open"}),
        ],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is False


# ===================================================================
# Unknown condition type
# ===================================================================


def test_unknown_condition_type_returns_false():
    """Unknown condition type returns false rather than raising."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"wolf": _make_entity("wolf")})
    gc = GoalCondition(type="future_unknown_type", params={"entity": "wolf"})
    evaluator = GoalEvaluator(_conditions(gc))
    assert evaluator.check(state) is False


# ===================================================================
# output and side_effects properties
# ===================================================================


def test_output_property():
    """output property returns the victory text."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    gc = _conditions(GoalCondition(type="flag_is_set", params={"flag": "x"}),
                     output="Congratulations!")
    evaluator = GoalEvaluator(gc)
    assert evaluator.output == "Congratulations!"


def test_side_effects_property():
    """side_effects property returns the side effects list."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    effects = [{"type": "FLAG", "flag": "victory_seen", "value": True}]
    gc = GoalConditions(
        conditions=[GoalCondition(type="flag_is_set", params={"flag": "x"})],
        output="Win!",
        side_effects=effects,
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.side_effects == effects


def test_side_effects_default_empty():
    """side_effects defaults to empty list when not provided."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    gc = GoalConditions(
        conditions=[GoalCondition(type="flag_is_set", params={"flag": "x"})],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.side_effects == []


# ===================================================================
# Unknown composite key
# ===================================================================


def test_unknown_composite_key_returns_false():
    """Composite dict with unknown key (not 'and'/'or') returns false."""
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    state = _state({"wolf": _make_entity("wolf", spatial_anchor=None)})
    gc = GoalConditions(
        conditions=[{"xor": [GoalCondition(type="entity_dead", params={"entity": "wolf"})]}],
        output="Win!",
    )
    evaluator = GoalEvaluator(gc)
    assert evaluator.check(state) is False
