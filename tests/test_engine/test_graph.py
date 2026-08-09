"""Tests for DualGraphEngine, Clique, HyperEdge, and MacroEdge.

Follows dual-graph spec, participation-cliques spec, and tdd.md SS7.1.
All tests are entity-agnostic — no entity type constants or closed sets.
"""

from fortress_engine.entities.entity import Entity, ParsedCommand
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


def _make_player(
    entity_id: str = "hero",
    spatial_anchor: str = "room_01",
) -> Entity:
    return _make_entity(
        entity_id,
        type_="player",
        components={"player_controlled": True, "max_weight": 40},
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
# Clique validation
# ===================================================================


def test_clique_validation_subject_verb_target():
    """Clique with subject, verb, target — all present in the same room."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine

    engine = DualGraphEngine()

    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01", components={"mood": "hostile"})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll})

    clique = Clique(subject="hero", verb="matar", target="troll")
    # We need a fake HyperEdge just for validate_clique signature
    from fortress_engine.engine.graph import HyperEdge
    he = HyperEdge(hyper_edge_id="test-1", name="Kill", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_rejects_wrong_verb():
    """Clique rejects when verb does not match."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll})
    clique = Clique(subject="hero", verb="matar", target="troll")
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="hablar", target="troll")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_rejects_target_in_different_anchor():
    """Clique rejects when target is not in the same anchor or inventory."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_02")
    room = _make_entity("room_01", type_="room")
    room2 = _make_entity("room_02", type_="room")
    engine.add_anchor(room)
    engine.add_anchor(room2)

    state = _minimal_state(hero, room, extras={"troll": troll, "room_02": room2})
    clique = Clique(subject="hero", verb="matar", target="troll")
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_validation_instrument_required():
    """Clique with specific instrument — only valid if item is in inventory."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    sword = _make_entity("sword", type_="item", spatial_anchor="hero", components={"portable": True})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll, "sword": sword})

    clique = Clique(subject="hero", verb="matar", target="troll", instrument="sword")
    he = HyperEdge(hyper_edge_id="test-1", name="Kill", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll", instrument="sword")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_rejects_missing_instrument():
    """Clique with required instrument fails if player doesn't have it."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    sword = _make_entity("sword", type_="item", spatial_anchor="room_02", components={"portable": True})
    room = _make_entity("room_01", type_="room")
    room2 = _make_entity("room_02", type_="room")
    engine.add_anchor(room)
    engine.add_anchor(room2)

    state = _minimal_state(hero, room, extras={"troll": troll, "sword": sword, "room_02": room2})

    clique = Clique(subject="hero", verb="matar", target="troll", instrument="sword")
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll", instrument="sword")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_validation_instrument_not():
    """Clique with instrument_not — rejects if player carries that item."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    sword = _make_entity("sword", type_="item", spatial_anchor="hero", components={"portable": True})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll, "sword": sword})

    clique = Clique(subject="hero", verb="matar", target="troll", instrument_not="sword")
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll")

    # Sword IS in inventory → clique should fail
    assert engine.validate_clique(he, parsed, state) is False

    # Remove sword → clique should pass
    state.entities["sword"].spatial_anchor = "room_02"
    state.entities["room_02"] = _make_entity("room_02", type_="room")
    assert engine.validate_clique(he, parsed, state) is True


def test_clique_validation_instrument_any():
    """Clique with instrument_any — forms with any portable item in inventory."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    stick = _make_entity("stick", type_="item", spatial_anchor="hero", components={"portable": True})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll, "stick": stick})

    clique = Clique(subject="hero", verb="matar", target="troll", instrument="*", instrument_any=True)
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=0, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll", instrument="stick")

    assert engine.validate_clique(he, parsed, state) is True

    # Remove all portable items from inventory → should fail
    state.entities["stick"].spatial_anchor = "room_01"
    assert engine.validate_clique(he, parsed, state) is False


def test_clique_validation_flag_required():
    """Clique with flag — requires flag to be True."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="abrir", target="room_01", flag="door_unlocked")
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="abrir", target="room_01")

    # Flag not set → should fail
    assert engine.validate_clique(he, parsed, state) is False

    # Set flag → should pass
    state.set_flag("door_unlocked", True)
    assert engine.validate_clique(he, parsed, state) is True


def test_clique_validation_flag_not():
    """Clique with flag_not — requires flag to be False/absent."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="entrar", target="room_01", flag_not="guard_alive")
    he = HyperEdge(hyper_edge_id="test-1", name="X", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="entrar", target="room_01")

    # Flag not set → should pass (flag_not is satisfied)
    assert engine.validate_clique(he, parsed, state) is True

    # Set flag → should fail
    state.set_flag("guard_alive", True)
    assert engine.validate_clique(he, parsed, state) is False


def test_clique_validation_component_predicate():
    """Clique with component — verifies entity.components[key] == value."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    door = _make_entity("door", type_="door", spatial_anchor="room_01", components={"state": "closed"})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"door": door})

    # Clique requires door to be closed
    clique_closed = Clique(subject="hero", verb="abrir", target="door", component={"state": "closed"})
    he_closed = HyperEdge(hyper_edge_id="test-1", name="Open", priority=10, clique=clique_closed, operators=[])
    parsed = ParsedCommand(subject="hero", verb="abrir", target="door")

    assert engine.validate_clique(he_closed, parsed, state) is True

    # Clique requires door to be open (it's closed → fails)
    clique_open = Clique(subject="hero", verb="abrir", target="door", component={"state": "open"})
    he_open = HyperEdge(hyper_edge_id="test-2", name="Close", priority=10, clique=clique_open, operators=[])

    assert engine.validate_clique(he_open, parsed, state) is False

    # Change door state → component predicate now satisfied
    state.entities["door"].components["state"] = "open"
    assert engine.validate_clique(he_open, parsed, state) is True


def test_clique_wildcard_target():
    """Clique with target='*' matches any entity in room or inventory."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll})

    clique = Clique(subject="hero", verb="examinar", target="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Examine", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="examinar", target="troll")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_concrete_target_rejects_different_parsed_target():
    """A concrete clique target must equal the parsed target (discrimination)."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    dragon = _make_entity("dragon", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll, "dragon": dragon})

    # Clique targets troll, but the player commanded the dragon. Both are
    # reachable in the same room, yet the (verb, target) pair must not match.
    clique = Clique(subject="hero", verb="matar", target="troll")
    he = HyperEdge(hyper_edge_id="test-1", name="Kill", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="dragon")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_concrete_target_matches_equal_parsed_target():
    """A concrete clique target matches an equal, reachable parsed target."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll})

    clique = Clique(subject="hero", verb="matar", target="troll")
    he = HyperEdge(hyper_edge_id="test-1", name="Kill", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_wildcard_target_accepts_reachable_parsed_target():
    """target='*' accepts a parsed target in the subject's room."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll})

    clique = Clique(subject="hero", verb="examinar", target="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Examine", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="examinar", target="troll")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_wildcard_target_rejects_non_reachable_parsed_target():
    """target='*' rejects a parsed target in a different room."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_02")
    room = _make_entity("room_01", type_="room")
    room2 = _make_entity("room_02", type_="room")
    engine.add_anchor(room)
    engine.add_anchor(room2)

    state = _minimal_state(hero, room, extras={"troll": troll, "room_02": room2})

    clique = Clique(subject="hero", verb="examinar", target="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Examine", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="examinar", target="troll")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_wildcard_target_rejects_missing_parsed_target():
    """target='*' requires a parsed target to exist."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="examinar", target="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Examine", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="examinar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_target_none_matches_without_and_with_target():
    """Clique.target=None matches commands both without and with a target."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"troll": troll})

    clique = Clique(subject="hero", verb="mirar", target=None)
    he = HyperEdge(hyper_edge_id="test-1", name="Look", priority=10, clique=clique, operators=[])

    parsed_no_target = ParsedCommand(subject="hero", verb="mirar", target=None)
    parsed_with_target = ParsedCommand(subject="hero", verb="mirar", target="troll")

    assert engine.validate_clique(he, parsed_no_target, state) is True
    assert engine.validate_clique(he, parsed_with_target, state) is True


def test_clique_instrument_wildcard_accepts_instrument_in_inventory():
    """instrument='*' accepts a parsed instrument in the subject's inventory."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    sword = _make_entity("sword", type_="item", spatial_anchor="hero", components={"portable": True})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"sword": sword})

    clique = Clique(subject="hero", verb="atacar", instrument="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Attack", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None, instrument="sword")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_instrument_wildcard_accepts_instrument_in_anchor():
    """instrument='*' accepts a parsed instrument in the subject's anchor."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    sword = _make_entity("sword", type_="item", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"sword": sword})

    clique = Clique(subject="hero", verb="atacar", instrument="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Attack", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None, instrument="sword")

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_instrument_wildcard_rejects_instrument_in_different_room():
    """instrument='*' rejects a parsed instrument in a different room."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    sword = _make_entity("sword", type_="item", spatial_anchor="room_02")
    room = _make_entity("room_01", type_="room")
    room2 = _make_entity("room_02", type_="room")
    engine.add_anchor(room)
    engine.add_anchor(room2)

    state = _minimal_state(hero, room, extras={"sword": sword, "room_02": room2})

    clique = Clique(subject="hero", verb="atacar", instrument="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Attack", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None, instrument="sword")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_instrument_wildcard_rejects_missing_instrument():
    """instrument='*' requires a parsed instrument to be present."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="atacar", instrument="*")
    he = HyperEdge(hyper_edge_id="test-1", name="Attack", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_component_uses_matched_target_for_wildcard():
    """Component predicate evaluates the resolved wildcard target."""
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    door = _make_entity("door", type_="door", spatial_anchor="room_01", components={"state": "closed"})
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room, extras={"door": door})

    clique = Clique(subject="hero", verb="abrir", target="*", component={"state": "closed"})
    he = HyperEdge(hyper_edge_id="test-1", name="Open", priority=10, clique=clique, operators=[])
    parsed = ParsedCommand(subject="hero", verb="abrir", target="door")

    assert engine.validate_clique(he, parsed, state) is True

    # Component no longer matches → fail
    state.entities["door"].components["state"] = "open"
    assert engine.validate_clique(he, parsed, state) is False


# ===================================================================
# HyperEdge priority ordering
# ===================================================================


def test_hyper_edges_ordered_by_priority():
    """get_hyper_edges_for_verb returns edges sorted priority descending."""
    from fortress_engine.engine.graph import Clique, HyperEdge, DualGraphEngine

    engine = DualGraphEngine()
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    for prio in [2, 10, 0, 7]:
        clique = Clique(subject="hero", verb="matar", target="troll")
        he = HyperEdge(
            hyper_edge_id=f"he-{prio}",
            name=f"Edge-{prio}",
            priority=prio,
            clique=clique,
            operators=[],
        )
        engine.add_hyper_edge("room_01", he)

    edges = engine.get_hyper_edges_for_verb("room_01", "matar")
    priorities = [e.priority for e in edges]

    assert len(edges) == 4
    assert priorities == [10, 7, 2, 0]


def test_get_hyper_edges_for_verb_empty():
    """get_hyper_edges_for_verb returns empty list for unknown room or verb."""
    from fortress_engine.engine.graph import DualGraphEngine

    engine = DualGraphEngine()
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    assert engine.get_hyper_edges_for_verb("room_01", "matar") == []
    assert engine.get_hyper_edges_for_verb("nonexistent", "matar") == []


# ===================================================================
# MacroEdge validation — MacroGateResult (L4)
# ===================================================================

import pytest
from fortress_engine.engine.graph import MacroEdge, DualGraphEngine, MacroGateResult


# -------------------------------------------------------------------
# 10 parametrized gate codes (5 gates × fatal / non-fatal)
# -------------------------------------------------------------------

_PARAM_GATES = [
    # text_closed — non-fatal
    pytest.param(
        {"requires_text": "abracadabra", "open": False, "death_message": None},
        "text_closed", False, None, "Puerta Magica",
        id="text_closed-nonfatal",
    ),
    # text_closed — fatal
    pytest.param(
        {"requires_text": "abracadabra", "open": False,
         "death_message": "The door devours you!"},
        "text_closed", True, "The door devours you!", "Puerta Magica",
        id="text_closed-fatal",
    ),
    # requires_item — non-fatal
    pytest.param(
        {"requires_item": "amulet", "death_message": None},
        "requires_item", False, None, "Tunel Oscuro",
        id="requires_item-nonfatal",
    ),
    # requires_item — fatal
    pytest.param(
        {"requires_item": "amulet",
         "death_message": "Crushed by the walls!"},
        "requires_item", True, "Crushed by the walls!", "Tunel Oscuro",
        id="requires_item-fatal",
    ),
    # forbids_item — non-fatal
    pytest.param(
        {"forbids_item": "sword", "death_message": None},
        "forbids_item", False, None, "Entrada Sagrada",
        id="forbids_item-nonfatal",
    ),
    # forbids_item — fatal
    pytest.param(
        {"forbids_item": "sword",
         "death_message": "The temple strikes you down!"},
        "forbids_item", True, "The temple strikes you down!", "Entrada Sagrada",
        id="forbids_item-fatal",
    ),
    # requires_flag — non-fatal
    pytest.param(
        {"requires_flag": "knows_secret", "death_message": None},
        "requires_flag", False, None, "Puerta Oculta",
        id="requires_flag-nonfatal",
    ),
    # requires_flag — fatal
    pytest.param(
        {"requires_flag": "knows_secret",
         "death_message": "The floor vanishes!"},
        "requires_flag", True, "The floor vanishes!", "Puerta Oculta",
        id="requires_flag-fatal",
    ),
    # forbids_flag — non-fatal
    pytest.param(
        {"forbids_flag": "cursed", "death_message": None},
        "forbids_flag", False, None, "Pasaje Sellado",
        id="forbids_flag-nonfatal",
    ),
    # forbids_flag — fatal
    pytest.param(
        {"forbids_flag": "cursed",
         "death_message": "The curse consumes you!"},
        "forbids_flag", True, "The curse consumes you!", "Pasaje Sellado",
        id="forbids_flag-fatal",
    ),
]


@pytest.mark.parametrize(
    "gate_attrs,expected_code,expected_fatal,expected_death,passage_name",
    _PARAM_GATES,
)
def test_macro_edge_parametrized_gates(
    gate_attrs, expected_code, expected_fatal, expected_death, passage_name,
):
    """Every gate code returns MacroGateResult with correct is_valid, is_fatal,
    gate_code, and data fields."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    # For forbids_flag / forbids_item, set the flag / item first so the gate
    # actually triggers.
    if "forbids_flag" in gate_attrs:
        state.set_flag(gate_attrs["forbids_flag"], True)
    if "forbids_item" in gate_attrs:
        item = _make_entity(
            gate_attrs["forbids_item"], type_="item",
            spatial_anchor="hero", components={"portable": True},
        )
        state.entities[gate_attrs["forbids_item"]] = item

    edge = MacroEdge(
        macro_edge_id="param-edge",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name=passage_name,
        passage_description="A test passage",
        **gate_attrs,
    )

    result = engine.validate_macro_edge(edge, state, text="wrong")
    assert isinstance(result, MacroGateResult)
    assert result.is_valid is False
    assert result.is_fatal == expected_fatal
    assert result.gate_code == expected_code
    assert result.data.get("passage_name") == passage_name

    # Verify relevant data keys
    if "requires_text" in gate_attrs:
        assert result.data.get("required_text") == gate_attrs["requires_text"]
    if "requires_item" in gate_attrs:
        assert result.data.get("required_item") == gate_attrs["requires_item"]
    if "forbids_item" in gate_attrs:
        assert result.data.get("forbids_item") == gate_attrs["forbids_item"]
    if "requires_flag" in gate_attrs:
        assert result.data.get("required_flag") == gate_attrs["requires_flag"]
    if "forbids_flag" in gate_attrs:
        assert result.data.get("forbids_flag") == gate_attrs["forbids_flag"]

    # Fatal edges carry death_message in data
    if expected_death is not None:
        assert result.data.get("death_message") == expected_death


# -------------------------------------------------------------------
# Plain edge (no predicates) — always passable
# -------------------------------------------------------------------


def test_macro_edge_no_predicates_always_passable():
    """A plain edge with no predicates is always passable."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="plain-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A simple door",
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""
    assert result.data["passage_name"] == "Puerta"


# -------------------------------------------------------------------
# Text gate
# -------------------------------------------------------------------


def test_macro_edge_requires_text_closed_without_text():
    """Text gate, closed, no text → blocked, not fatal."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="text-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A locked door",
        requires_text="ábrete sésamo",
        open=False,
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is False
    assert result.gate_code == "text_closed"
    assert result.data["passage_name"] == "Puerta"
    assert result.data["required_text"] == "ábrete sésamo"
    assert edge.open is False


def test_macro_edge_requires_text_wrong_text():
    """Text gate, closed, wrong text → blocked, not fatal."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="text-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A locked door",
        requires_text="abrete sesamo",
        open=False,
    )

    result = engine.validate_macro_edge(edge, state, text="abracadabra")
    assert result.is_valid is False
    assert result.is_fatal is False
    assert result.gate_code == "text_closed"
    assert edge.open is False


def test_macro_edge_requires_text_wrong_text_with_death_message():
    """Text gate, wrong text + death_message → fatal."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="text-fatal-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A cursed door",
        requires_text="abrete sesamo",
        death_message="La puerta te consume.",
        open=False,
    )

    result = engine.validate_macro_edge(edge, state, text="equivocada")
    assert result.is_valid is False
    assert result.is_fatal is True
    assert result.gate_code == "text_closed"
    assert result.data["death_message"] == "La puerta te consume."
    assert edge.open is False


def test_macro_edge_requires_text_correct_text_opens():
    """Text gate, correct text → valid and the edge opens."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="text-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A locked door",
        requires_text="abrete sesamo",
        open=False,
    )

    result = engine.validate_macro_edge(edge, state, text="abrete sesamo")
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""
    assert edge.open is True

    # Once open, a later pass (even without text) is allowed.
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""


def test_macro_edge_requires_text_open_allows_pass():
    """Text gate already open → always passable, no text required."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="text-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A locked door",
        requires_text="abrete sesamo",
        open=True,
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""


def test_macro_edge_requires_text_comparison_is_tilde_insensitive():
    """Text comparison normalises tildes on BOTH sides."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="text-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A locked door",
        requires_text="ábrete sésamo",
        open=False,
    )

    result = engine.validate_macro_edge(edge, state, text="abrete sesamo")
    assert result.is_valid is True
    assert edge.open is True

    edge2 = MacroEdge(
        macro_edge_id="text-2",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A locked door",
        requires_text="treinta y nueve",
        open=False,
    )
    result = engine.validate_macro_edge(edge2, state, text="treinta y nueve")
    assert result.is_valid is True
    assert edge2.open is True


# -------------------------------------------------------------------
# Item gates
# -------------------------------------------------------------------


def test_macro_edge_requires_item_blocks_without_item():
    """Item gate without death_message: missing item → blocked, not death."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="item-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Traquea",
        passage_description="Pulsating passage",
        requires_item="talisman",
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is False
    assert result.gate_code == "requires_item"
    assert result.data["required_item"] == "talisman"


def test_macro_edge_requires_item_kills_without_item():
    """Item gate with death_message: missing item → death."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="item-fatal-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Traquea",
        passage_description="Pulsating passage",
        requires_item="talisman",
        death_message="You are crushed!",
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is True
    assert result.gate_code == "requires_item"
    assert result.data["death_message"] == "You are crushed!"

    # Give the talisman → should pass
    talisman = _make_entity(
        "talisman", type_="item", spatial_anchor="hero",
        components={"portable": True},
    )
    state.entities["talisman"] = talisman

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""


def test_macro_edge_forbids_item_blocks_with_item():
    """Forbids-item gate without death_message: item carried → blocked."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="forbid-item-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="Seems harmless",
        forbids_item="sword",
    )

    # No sword → pass
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""

    # Carry sword → blocked
    sword = _make_entity(
        "sword", type_="item", spatial_anchor="hero",
        components={"portable": True},
    )
    state.entities["sword"] = sword

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is False
    assert result.gate_code == "forbids_item"
    assert result.data["forbids_item"] == "sword"


def test_macro_edge_forbids_item_kills_with_item():
    """Forbids-item gate with death_message: item carried → death."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="forbid-fatal-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="unidirectional",
        passage_name="Puerta",
        passage_description="Seems harmless",
        forbids_item="sword",
        death_message="The trap activates!",
    )

    # No sword → safe
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""

    # Carry sword → death
    sword = _make_entity(
        "sword", type_="item", spatial_anchor="hero",
        components={"portable": True},
    )
    state.entities["sword"] = sword

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is True
    assert result.gate_code == "forbids_item"
    assert result.data["death_message"] == "The trap activates!"


# -------------------------------------------------------------------
# Flag gates
# -------------------------------------------------------------------


def test_macro_edge_requires_flag_blocks_without_flag():
    """Flag gate: requires_flag not set → blocked (no death_message)."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="flag-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta secreta",
        passage_description="Hidden passage",
        requires_flag="knows_password",
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is False
    assert result.gate_code == "requires_flag"
    assert result.data["required_flag"] == "knows_password"

    # Set flag → pass
    state.set_flag("knows_password", True)
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""


def test_macro_edge_requires_flag_kills_without_flag():
    """Flag gate with death_message: flag not set → death."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="flag-fatal-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A trap gate",
        requires_flag="safe_passage",
        death_message="The floor gives way!",
    )

    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is True
    assert result.gate_code == "requires_flag"
    assert result.data["death_message"] == "The floor gives way!"


def test_macro_edge_forbids_flag_blocks_with_flag():
    """Flag gate: forbids_flag set → blocked; absent → pass."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="flag-2",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="unidirectional",
        passage_name="Puerta sellada",
        passage_description="Sealed door",
        forbids_flag="darkness_remains",
    )

    # Flag not set → pass
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is True
    assert result.is_fatal is False
    assert result.gate_code == ""

    # Set flag → fail
    state.set_flag("darkness_remains", True)
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is False
    assert result.gate_code == "forbids_flag"
    assert result.data["forbids_flag"] == "darkness_remains"


def test_macro_edge_forbids_flag_kills_with_flag():
    """Flag gate with death_message: forbids_flag set → death."""
    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="flag-fatal-2",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta",
        passage_description="A cursed gate",
        forbids_flag="darkness_remains",
        death_message="You dissolve in the dark.",
    )

    state.set_flag("darkness_remains", True)
    result = engine.validate_macro_edge(edge, state)
    assert result.is_valid is False
    assert result.is_fatal is True
    assert result.gate_code == "forbids_flag"
    assert result.data["death_message"] == "You dissolve in the dark."


# -------------------------------------------------------------------
# MacroGateResult dataclass contract
# -------------------------------------------------------------------


def test_macro_gate_result_is_frozen():
    """MacroGateResult is a frozen dataclass."""
    mr = MacroGateResult(
        is_valid=False, is_fatal=True, gate_code="requires_item",
        data={"passage_name": "x"},
    )
    with pytest.raises(Exception):
        mr.is_valid = True  # frozen


def test_macro_gate_result_valid_defaults():
    """Valid result has empty gate_code and is_fatal=False."""
    mr = MacroGateResult(
        is_valid=True, is_fatal=False, gate_code="",
        data={"passage_name": "Puerta"},
    )
    assert mr.is_valid is True
    assert mr.is_fatal is False
    assert mr.gate_code == ""
    assert mr.data["passage_name"] == "Puerta"
# ===================================================================
# resolve_special_values
# ===================================================================


def test_resolve_special_values_player():
    """'player' resolves to active_protagonist_id."""
    from fortress_engine.engine.graph import DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    assert engine.resolve_special_values("player", state) == "hero"


def test_resolve_special_values_star():
    """'*' stays as '*' (wildcard)."""
    from fortress_engine.engine.graph import DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    assert engine.resolve_special_values("*", state) == "*"


def test_resolve_special_values_literal():
    """Literal entity_id is returned unchanged."""
    from fortress_engine.engine.graph import DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)
    state = _minimal_state(hero, room)

    assert engine.resolve_special_values("troll", state) == "troll"
    assert engine.resolve_special_values(None, state) is None


# ===================================================================
# Macro edge queries
# ===================================================================


def test_get_edges_from_anchor():
    """get_edges_from_anchor returns macro edges from a given room."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    edge = MacroEdge(
        macro_edge_id="e-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Norte",
        passage_description="North door",
    )
    engine.add_macro_edge(edge)

    edges = engine.get_edges_from_anchor("room_01")
    assert len(edges) == 1
    assert edges[0].macro_edge_id == "e-1"

    # Unknown anchor → empty
    assert engine.get_edges_from_anchor("nonexistent") == []


def test_get_macro_edge_by_passage_name():
    """Find macro edge by passage name within a room."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    edge = MacroEdge(
        macro_edge_id="e-1",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        passage_name="Puerta principal",
        passage_description="Main door",
    )
    engine.add_macro_edge(edge)

    found = engine.get_macro_edge_by_passage_name("room_01", "Puerta principal")
    assert found is not None
    assert found.macro_edge_id == "e-1"

    # Unknown passage → None
    assert engine.get_macro_edge_by_passage_name("room_01", "Ventana") is None
    assert engine.get_macro_edge_by_passage_name("nonexistent", "Puerta principal") is None


# ===================================================================
# build_macro_graph
# ===================================================================


def test_build_macro_graph():
    """build_macro_graph registers anchors and macro edges from lists."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()

    anchors = [
        _make_entity("room_01", type_="room"),
        _make_entity("room_02", type_="room"),
        _make_entity("room_03", type_="room"),
    ]
    edges = [
        MacroEdge(
            macro_edge_id="e-1-2",
            from_anchor="room_01",
            to_anchor="room_02",
            direction="bidirectional",
            passage_name="Este",
            passage_description="East door",
        ),
        MacroEdge(
            macro_edge_id="e-1-3",
            from_anchor="room_01",
            to_anchor="room_03",
            direction="unidirectional",
            passage_name="Oeste",
            passage_description="West door",
            requires_text="secreto",
            open=False,
        ),
    ]

    engine.build_macro_graph(anchors, edges)

    assert len(engine.get_edges_from_anchor("room_01")) == 2
    assert engine.get_macro_edge_by_passage_name("room_01", "Este") is not None
    assert engine.get_macro_edge_by_passage_name("room_01", "Oeste") is not None


# ===================================================================
# Duplicate priority warning
# ===================================================================


def test_duplicate_priority_does_not_block(capsys):
    """Duplicate (verb, target, priority) emits a warning but does not block."""
    from fortress_engine.engine.graph import Clique, HyperEdge, DualGraphEngine

    engine = DualGraphEngine()
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    clique = Clique(subject="hero", verb="matar", target="troll")
    he1 = HyperEdge(hyper_edge_id="he-1", name="A", priority=10, clique=clique, operators=[])
    he2 = HyperEdge(hyper_edge_id="he-2", name="B", priority=10, clique=clique, operators=[])

    engine.add_hyper_edge("room_01", he1)
    engine.add_hyper_edge("room_01", he2)

    captured = capsys.readouterr()
    # Warning should have been emitted to stderr or stdout
    assert "duplicate priority" in (captured.out + captured.err).lower()


# ===================================================================
# Clique failure paths (missing/malformed state)
# ===================================================================


def _build_engine_and_edge(clique, parsed):
    from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge

    engine = DualGraphEngine()
    he = HyperEdge(
        hyper_edge_id="test-fail-1",
        name="Fail",
        priority=10,
        clique=clique,
        operators=[],
    )
    return engine, he


def _make_detached_state() -> WorldState:
    """A WorldState whose active_protagonist_id is None (protagonist unset).

    ``"player"`` special values resolve to ``active_protagonist_id``; when the
    protagonist is not set the resolution yields ``None``, exercising the
    defensive ``None``-checks in validate_clique.
    """
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    return WorldState(
        entities={"room_01": room, "hero": hero},
        player_controlled_entities=["hero"],
        active_protagonist_id=None,
    )


def test_clique_rejects_missing_subject():
    """Clique without a subject resolves to None and fails closed."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    clique = Clique(subject=None, verb="matar", target=None)
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="matar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_rejects_subject_missing_from_state():
    """Concrete subject not present in the state fails closed (KeyError path)."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    clique = Clique(subject="ghost", verb="matar", target=None)
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="matar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_wildcard_target_rejects_parsed_target_missing_from_state():
    """target='*' fails when the parsed target entity is not in the state."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="examinar", target="*")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="examinar", target="ghost")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_wildcard_target_rejects_unresolvable_parsed_target():
    """target='*' fails when the parsed target special value resolves to None
    (unset active protagonist)."""
    from fortress_engine.engine.graph import Clique

    state = _make_detached_state()

    clique = Clique(subject="hero", verb="examinar", target="*")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="examinar", target="player")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_concrete_target_rejects_unresolvable_clique_target():
    """A concrete clique target resolving to None fails (unset protagonist)."""
    from fortress_engine.engine.graph import Clique

    state = _make_detached_state()

    clique = Clique(subject="hero", verb="matar", target="player")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="matar", target="player")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_concrete_target_rejects_command_without_target():
    """A concrete clique target requires the parsed command to carry a target."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room, extras={"troll": troll})

    clique = Clique(subject="hero", verb="matar", target="troll")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="matar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_concrete_target_rejects_unresolvable_parsed_target():
    """A concrete clique target fails when the parsed target resolves to None."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    troll = _make_entity("troll", type_="npc", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room, extras={"troll": troll})
    # Unset protagonist so parsed target "player" resolves to None, while the
    # clique target "troll" resolves normally.
    state.active_protagonist_id = None

    clique = Clique(subject="hero", verb="matar", target="troll")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="matar", target="player")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_concrete_target_rejects_target_missing_from_state():
    """Concrete target not present in the state fails (KeyError path)."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="matar", target="troll")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="matar", target="troll")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_accepts_target_in_subject_inventory():
    """Target anchored to the subject (inventory) satisfies reachability."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    sword = _make_entity(
        "sword", type_="item", spatial_anchor="hero", components={"portable": True}
    )
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room, extras={"sword": sword})

    clique = Clique(subject="hero", verb="usar", target="sword")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="usar", target="sword")

    assert engine.validate_clique(he, parsed, state) is True


# ===================================================================
# Clique context predicate
# ===================================================================


def test_clique_context_entity_in_anchor_satisfies():
    """Context entity present in the subject's anchor satisfies the clique."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    candle = _make_entity("candle", type_="item", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room, extras={"candle": candle})

    clique = Clique(subject="hero", verb="leer", context="candle")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="leer", target=None)

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_context_entity_in_inventory_satisfies():
    """Context entity in the subject's inventory satisfies the clique."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    candle = _make_entity(
        "candle", type_="item", spatial_anchor="hero", components={"portable": True}
    )
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room, extras={"candle": candle})

    clique = Clique(subject="hero", verb="leer", context="candle")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="leer", target=None)

    assert engine.validate_clique(he, parsed, state) is True


def test_clique_context_entity_not_in_anchor_or_inventory_fails():
    """Context entity in a different anchor fails the clique."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    candle = _make_entity("candle", type_="item", spatial_anchor="room_02")
    room = _make_entity("room_01", type_="room")
    room2 = _make_entity("room_02", type_="room")
    state = _minimal_state(
        hero, room, extras={"candle": candle, "room_02": room2}
    )

    clique = Clique(subject="hero", verb="leer", context="candle")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="leer", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_context_entity_missing_from_state_fails():
    """Context entity not present in the state fails the clique (KeyError)."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="leer", context="ghost_candle")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="leer", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_context_resolving_to_none_is_skipped():
    """Context special value resolving to None is skipped, not a failure."""
    from fortress_engine.engine.graph import Clique

    state = _make_detached_state()

    clique = Clique(subject="hero", verb="mirar", context="player")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="mirar", target=None)

    assert engine.validate_clique(he, parsed, state) is True


# ===================================================================
# Clique instrument failure paths
# ===================================================================


def test_clique_instrument_wildcard_rejects_unresolvable_instrument():
    """instrument='*' fails when the parsed instrument resolves to None."""
    from fortress_engine.engine.graph import Clique

    state = _make_detached_state()

    clique = Clique(subject="hero", verb="atacar", instrument="*")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None, instrument="player")

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_instrument_concrete_rejects_unresolvable_instrument():
    """Concrete instrument resolving to None fails the clique."""
    from fortress_engine.engine.graph import Clique

    state = _make_detached_state()

    clique = Clique(subject="hero", verb="atacar", instrument="player")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_instrument_concrete_rejects_instrument_missing_from_state():
    """Concrete instrument not present in the state fails (KeyError path)."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room)

    clique = Clique(subject="hero", verb="atacar", instrument="ghost_sword")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="atacar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


def test_clique_instrument_not_resolving_to_none_is_skipped():
    """instrument_not that resolves to None is skipped, not a failure.

    ``"player"`` resolves to ``state.active_protagonist_id``; with an unset
    protagonist the resolution is ``None``, so the forbidden check is
    vacuous and the clique must pass.
    """
    from fortress_engine.engine.graph import Clique

    state = _make_detached_state()  # active_protagonist_id=None

    clique = Clique(subject="hero", verb="mirar", instrument_not="player")
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="mirar", target=None)

    assert engine.validate_clique(he, parsed, state) is True


# ===================================================================
# Clique component predicate failure path
# ===================================================================


def test_clique_component_without_target_constraint_fails():
    """Component predicate requires a matched target; none → fails."""
    from fortress_engine.engine.graph import Clique

    hero = _make_player("hero", spatial_anchor="room_01")
    door = _make_entity(
        "door", type_="door", spatial_anchor="room_01", components={"state": "closed"}
    )
    room = _make_entity("room_01", type_="room")
    state = _minimal_state(hero, room, extras={"door": door})

    # No target/wildcard constraint, so no resolved target is available for the
    # component predicate.
    clique = Clique(subject="hero", verb="girar", component={"state": "closed"})
    engine, he = _build_engine_and_edge(clique, None)
    parsed = ParsedCommand(subject="hero", verb="girar", target=None)

    assert engine.validate_clique(he, parsed, state) is False


# ===================================================================
# MacroEdge model contract
# ===================================================================


def test_macro_edge_carries_only_generic_predicates():
    """MacroEdge carries generic predicates — legacy connection-type,
    password, and answer fields are absent from the dataclass and are
    rejected at load time by ``extra="forbid"`` (see loader tests)."""
    from dataclasses import fields

    from fortress_engine.engine.graph import MacroEdge

    names = {f.name for f in fields(MacroEdge)}
    assert "requires_text" in names
    assert "question" in names
    assert "requires_item" in names
    assert "forbids_item" in names
    assert "requires_flag" in names
    assert "forbids_flag" in names
    assert "death_message" in names
    assert "open" in names


# ===================================================================
# resolve_target_id (wildcard operator binding)
# ===================================================================


def test_resolve_target_id_none_clique_target():
    """A clique with no target constraint resolves to None (no binding)."""
    from fortress_engine.engine.graph import DualGraphEngine
    from fortress_engine.plugins.parser_interface import ParsedCommand

    engine = DualGraphEngine()
    state = _make_detached_state()
    parsed = ParsedCommand(subject="hero", verb="mirar", target="algo")

    assert engine.resolve_target_id(None, parsed, state) is None


def test_resolve_target_id_wildcard_resolves_parsed_target():
    """A wildcard clique target resolves the parsed target to its entity id."""
    from fortress_engine.engine.graph import DualGraphEngine
    from fortress_engine.plugins.parser_interface import ParsedCommand

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    key = _make_entity("key", components={"weight": 1}, spatial_anchor="hero")
    state = WorldState(
        entities={"room_01": hero, "key": key},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
    )
    parsed = ParsedCommand(subject="hero", verb="dejar", target="key")

    assert engine.resolve_target_id("*", parsed, state) == "key"


def test_resolve_target_id_wildcard_missing_parsed_target():
    """A wildcard clique with no parsed target resolves to None."""
    from fortress_engine.engine.graph import DualGraphEngine
    from fortress_engine.plugins.parser_interface import ParsedCommand

    engine = DualGraphEngine()
    state = _make_detached_state()
    parsed = ParsedCommand(subject="hero", verb="dejar", target=None)

    assert engine.resolve_target_id("*", parsed, state) is None


def test_resolve_target_id_concrete_returns_clique_value():
    """A concrete clique target resolves through special values (e.g.
    ``"player"`` → protagonist id)."""
    from fortress_engine.engine.graph import DualGraphEngine
    from fortress_engine.plugins.parser_interface import ParsedCommand

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    state = WorldState(
        entities={"room_01": hero},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
    )
    parsed = ParsedCommand(subject="hero", verb="matar", target="ciclope")

    assert engine.resolve_target_id("player", parsed, state) == "hero"


# ===================================================================
# Passage name normalization (natural player input)
# ===================================================================


def test_passage_lookup_normalizes_spaces_to_underscore():
    """``get_macro_edge_by_passage_name`` resolves natural player input
    with spaces ("puerta principal") to a snake_case YAML passage
    ("puerta_principal")."""
    from fortress_engine.engine.graph import (
        Clique,
        DualGraphEngine,
        HyperEdge,
        MacroEdge,
    )

    engine = DualGraphEngine()
    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    engine.add_anchor(room_a)
    engine.add_anchor(room_b)
    engine.add_macro_edge(
        MacroEdge(
            macro_edge_id="a_to_b",
            from_anchor="room_a",
            to_anchor="room_b",
            direction="bidirectional",
            passage_name="puerta_principal",
        )
    )

    assert engine.get_macro_edge_by_passage_name(
        "room_a", "puerta principal"
    ) is not None
    assert engine.get_macro_edge_by_passage_name(
        "room_a", "puerta_principal"
    ) is not None
    assert engine.get_macro_edge_by_passage_name(
        "room_a", "puerta  principal"
    ) is not None


def test_passage_lookup_normalization_is_case_insensitive():
    """Passage lookup is case-insensitive: 'Puerta Principal' matches."""
    from fortress_engine.engine.graph import (
        DualGraphEngine,
        MacroEdge,
    )

    engine = DualGraphEngine()
    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    engine.add_anchor(room_a)
    engine.add_anchor(room_b)
    engine.add_macro_edge(
        MacroEdge(
            macro_edge_id="a_to_b",
            from_anchor="room_a",
            to_anchor="room_b",
            direction="bidirectional",
            passage_name="puerta_principal",
        )
    )

    assert engine.get_macro_edge_by_passage_name(
        "room_a", "Puerta Principal"
    ) is not None


def test_passage_lookup_no_match_returns_none():
    """A passage name that does not exist still returns None."""
    from fortress_engine.engine.graph import DualGraphEngine

    engine = DualGraphEngine()
    room_a = _make_entity("room_a", type_="room")
    engine.add_anchor(room_a)

    assert engine.get_macro_edge_by_passage_name("room_a", "pasaje_fantasma") is None


def test_open_reverse_edges_propagates_to_mirror_by_anchors():
    """``_open_reverse_edges`` falls back to matching the mirror by passage
    name and swapped anchors when the ``_reverse`` id is not present."""
    from fortress_engine.engine.graph import DualGraphEngine, MacroEdge

    engine = DualGraphEngine()
    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    engine.add_anchor(room_a)
    engine.add_anchor(room_b)
    fwd = MacroEdge(
        macro_edge_id="custom_door",
        from_anchor="room_a",
        to_anchor="room_b",
        direction="bidirectional",
        passage_name="pasillo",
        open=False,
    )
    mirror = MacroEdge(
        macro_edge_id="custom_door_mirror",  # NOT <id>_reverse
        from_anchor="room_b",
        to_anchor="room_a",
        direction="bidirectional",
        passage_name="pasillo",
        open=False,
    )
    engine.add_macro_edge(fwd)
    engine.add_macro_edge(mirror)

    engine._open_reverse_edges(fwd)

    assert mirror.open is True


def test_open_reverse_edges_no_mirror_is_noop():
    """``_open_reverse_edges`` on an edge with no mirror is a no-op."""
    from fortress_engine.engine.graph import DualGraphEngine, MacroEdge

    engine = DualGraphEngine()
    room_a = _make_entity("room_a", type_="room")
    room_b = _make_entity("room_b", type_="room")
    engine.add_anchor(room_a)
    engine.add_anchor(room_b)
    fwd = MacroEdge(
        macro_edge_id="one_way",
        from_anchor="room_a",
        to_anchor="room_b",
        direction="unidirectional",
        passage_name="salida",
        open=False,
    )
    engine.add_macro_edge(fwd)

    # Must not raise and must not touch anything.
    engine._open_reverse_edges(fwd)
    assert fwd.open is False
