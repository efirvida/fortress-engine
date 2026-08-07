"""Tests for Entity, ParsedCommand, GoalCondition/GoalConditions, CarryOver, Episode.

Follows the entity-model spec: opaque type/components, anchor=None = limbo/destroyed.
"""

from fortress_engine.entities.entity import (
    Entity,
    ParsedCommand,
    GoalCondition,
    GoalConditions,
    CarryOver,
    Episode,
)


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

def test_entity_preserves_arbitrary_type():
    """Entity.type is an opaque string — engine does not validate or restrict it."""
    e = Entity(
        entity_id="portal_01",
        type="portal",
        name="Portal of Doom",
        components={"charges": 3, "active": True},
        spatial_anchor="room_01",
    )
    assert e.type == "portal"
    assert e.entity_id == "portal_01"
    assert e.name == "Portal of Doom"


def test_entity_preserves_arbitrary_components():
    """Component values (list, int, bool, str) survive construction unchanged."""
    components = {
        "tags": ["cold", "wet"],
        "weight": 5,
        "is_open": True,
        "description": "A rusty key",
    }
    e = Entity(
        entity_id="key_01",
        type="item",
        name="Rusty Key",
        components=components,
        spatial_anchor="room_03",
    )
    assert e.components == components
    # Verify individual types are preserved
    assert e.components["tags"] == ["cold", "wet"]
    assert isinstance(e.components["weight"], int)
    assert isinstance(e.components["is_open"], bool)
    assert isinstance(e.components["description"], str)


def test_entity_spatial_anchor_none_means_limbo():
    """None spatial_anchor represents destroyed or in-limbo entity."""
    e = Entity(
        entity_id="dead_guard",
        type="npc",
        name="Dead Guard",
        components={},
        spatial_anchor=None,
    )
    assert e.spatial_anchor is None


def test_entity_spatial_anchor_is_anchor_id():
    """Non-None spatial_anchor is a valid container/anchor entity_id."""
    e = Entity(
        entity_id="player_1",
        type="player",
        name="Hero",
        components={},
        spatial_anchor="room_01",
    )
    assert e.spatial_anchor == "room_01"


def test_entity_raw_equality():
    """Entity uses default dataclass equality (field-by-field value equality)."""
    a = Entity("e1", "item", "Key", {"w": 1}, "room_01")
    b = Entity("e1", "item", "Key", {"w": 1}, "room_01")
    c = Entity("e1", "item", "Key", {"w": 2}, "room_01")
    assert a == b
    assert a != c


# ---------------------------------------------------------------------------
# ParsedCommand
# ---------------------------------------------------------------------------

def test_parsed_command_full():
    """ParsedCommand with all fields populated."""
    cmd = ParsedCommand(
        subject="player_1",
        verb="atacar",
        target="guard_01",
        context="room_15",
        instrument="espada_01",
    )
    assert cmd.subject == "player_1"
    assert cmd.verb == "atacar"
    assert cmd.target == "guard_01"
    assert cmd.context == "room_15"
    assert cmd.instrument == "espada_01"


def test_parsed_command_minimal():
    """ParsedCommand with only required fields (subject, verb, target)."""
    cmd = ParsedCommand(subject="player_1", verb="mirar", target="room_01")
    assert cmd.subject == "player_1"
    assert cmd.verb == "mirar"
    assert cmd.target == "room_01"
    assert cmd.context is None
    assert cmd.instrument is None


def test_parsed_command_subject_none():
    """Subject can be None (impersonal commands)."""
    cmd = ParsedCommand(subject=None, verb="esperar", target=None)
    assert cmd.subject is None
    assert cmd.verb == "esperar"


# ---------------------------------------------------------------------------
# GoalCondition
# ---------------------------------------------------------------------------

def test_goal_condition_basic():
    """GoalCondition holds a type and params dict."""
    gc = GoalCondition(
        type="flag_is_set",
        params={"flag": "boss_defeated"},
    )
    assert gc.type == "flag_is_set"
    assert gc.params == {"flag": "boss_defeated"}


def test_goal_condition_entity_dead():
    gc = GoalCondition(
        type="entity_dead",
        params={"entity": "guard_01"},
    )
    assert gc.type == "entity_dead"
    assert gc.params["entity"] == "guard_01"


# ---------------------------------------------------------------------------
# GoalConditions
# ---------------------------------------------------------------------------

def test_goal_conditions_simple():
    """GoalConditions with a single condition and output text."""
    gc = GoalConditions(
        conditions=[GoalCondition(type="flag_is_set", params={"flag": "won"})],
        output="You have won the game!",
    )
    assert len(gc.conditions) == 1
    assert gc.conditions[0].type == "flag_is_set"
    assert gc.output == "You have won the game!"
    # side_effects defaults to empty list
    assert gc.side_effects == []


def test_goal_conditions_composite_and():
    """GoalConditions with nested AND composite condition."""
    gc = GoalConditions(
        conditions=[
            {
                "and": [
                    GoalCondition(type="flag_is_set", params={"flag": "a"}),
                    GoalCondition(type="flag_is_set", params={"flag": "b"}),
                ]
            }
        ],
        output="Both flags set!",
    )
    assert len(gc.conditions) == 1
    inner = gc.conditions[0]
    assert isinstance(inner, dict)
    assert "and" in inner
    assert len(inner["and"]) == 2
    assert inner["and"][0].type == "flag_is_set"


def test_goal_conditions_with_side_effects():
    """GoalConditions can include side_effects list."""
    side = [{"type": "SET_FLAG", "flag": "epilogue_unlocked", "value": True}]
    gc = GoalConditions(
        conditions=[GoalCondition(type="flag_is_set", params={"flag": "x"})],
        output="Done",
        side_effects=side,
    )
    assert gc.side_effects == side


# ---------------------------------------------------------------------------
# CarryOver
# ---------------------------------------------------------------------------

def test_carry_over_default_empty():
    """CarryOver defaults: empty inventory and flags."""
    co = CarryOver()
    assert co.inventory == []
    assert co.flags == []


def test_carry_over_wildcard_inventory():
    """["*"] means carry over all items."""
    co = CarryOver(inventory=["*"], flags=["score_high"])
    assert co.inventory == ["*"]
    assert co.flags == ["score_high"]


def test_carry_over_specific_items():
    co = CarryOver(inventory=["sword_01", "key_03"], flags=[])
    assert len(co.inventory) == 2


# ---------------------------------------------------------------------------
# Episode
# ---------------------------------------------------------------------------

def test_episode_structure():
    """Episode dataclass with all required fields."""
    goal = GoalConditions(
        conditions=[GoalCondition(type="flag_is_set", params={"flag": "done"})],
        output="Episode completed!",
    )
    carry = CarryOver(inventory=[], flags=[])
    ep = Episode(
        id="episode-01",
        name="The Beginning",
        order=1,
        description="First episode of the saga.",
        requires=[],
        start_anchor="room_01",
        goal=goal,
        carry_over=carry,
    )
    assert ep.id == "episode-01"
    assert ep.name == "The Beginning"
    assert ep.order == 1
    assert ep.description == "First episode of the saga."
    assert ep.requires == []
    assert ep.start_anchor == "room_01"
    assert ep.goal == goal
    assert ep.carry_over == carry
