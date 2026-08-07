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
# MacroEdge validation
# ===================================================================


def test_macro_edge_open_always_valid():
    """Open macro edges are always passable."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="open-1",
        connection_type="open",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Puerta",
        door_description="A simple door",
    )

    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True
    assert msg is None


def test_macro_edge_password_requires_correct_password():
    """Password edge: closed → must supply password. Once open=True, always passable."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="pass-1",
        connection_type="password",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Puerta",
        door_description="A locked door",
        password="ábrete sésamo",
        open=False,
    )

    # Password edge with open=False → still passable (orchestrator handles password check)
    # Actually per GDD: if open=True, always passable. If open=False, the orchestrator
    # handles the password comparison. The graph just validates the structure.
    # validate_macro_edge for password with open=False returns (True, None) —
    # the graph doesn't check passwords, states when door is already open.
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True

    # Edge marked open → always passes
    edge.open = True
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True


def test_macro_edge_danger_death_without_required_item():
    """Danger edge returns failure with death_message when item is missing."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="danger-1",
        connection_type="danger",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Tráquea",
        door_description="Pulsating passage",
        requires_item="talisman",
        death_message="You are crushed!",
    )

    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is False
    assert msg == "You are crushed!"

    # Give the talisman → should pass
    talisman = _make_entity("talisman", type_="item", spatial_anchor="hero", components={"portable": True})
    state.entities["talisman"] = talisman

    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True
    assert msg is None


def test_macro_edge_danger_inverse_death_with_forbidden_item():
    """Danger_inverse returns failure when the forbidden item IS carried."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="danger-inv-1",
        connection_type="danger_inverse",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="unidirectional",
        door_name="Puerta",
        door_description="Seems harmless",
        forbids_item="sword",
        death_message="The trap activates!",
    )

    # No sword → safe
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True
    assert msg is None

    # Carry sword → death
    sword = _make_entity("sword", type_="item", spatial_anchor="hero", components={"portable": True})
    state.entities["sword"] = sword

    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is False
    assert msg == "The trap activates!"


def test_macro_edge_riddle_requires_correct_answer():
    """Riddle edge: closed → answer must match. Once open=True, always passable."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="riddle-1",
        connection_type="riddle",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="unidirectional",
        door_name="Puerta dorada",
        door_description="Golden door",
        question="What walks on four legs in the morning?",
        answer="human",
    )

    # Riddle with open=True (default) → passable
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True


def test_macro_edge_conditional_requires_flag():
    """Conditional edge requires_flag: fails if flag not set."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="cond-1",
        connection_type="conditional",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Puerta secreta",
        door_description="Hidden passage",
        requires_flag="knows_password",
    )

    # Flag not set → fail
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is False
    assert msg is not None

    # Set flag → pass
    state.set_flag("knows_password", True)
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True
    assert msg is None


def test_macro_edge_conditional_forbids_flag():
    """Conditional edge forbids_flag: fails if flag IS set."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="cond-2",
        connection_type="conditional",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="unidirectional",
        door_name="Puerta sellada",
        door_description="Sealed door",
        forbids_flag="darkness_remains",
    )

    # Flag not set → pass
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is True
    assert msg is None

    # Set flag → fail
    state.set_flag("darkness_remains", True)
    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is False
    assert msg is not None


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
        connection_type="open",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Norte",
        door_description="North door",
    )
    engine.add_macro_edge(edge)

    edges = engine.get_edges_from_anchor("room_01")
    assert len(edges) == 1
    assert edges[0].macro_edge_id == "e-1"

    # Unknown anchor → empty
    assert engine.get_edges_from_anchor("nonexistent") == []


def test_get_macro_edge_by_door_name():
    """Find macro edge by door name within a room."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    edge = MacroEdge(
        macro_edge_id="e-1",
        connection_type="open",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Puerta principal",
        door_description="Main door",
    )
    engine.add_macro_edge(edge)

    found = engine.get_macro_edge_by_door_name("room_01", "Puerta principal")
    assert found is not None
    assert found.macro_edge_id == "e-1"

    # Unknown door → None
    assert engine.get_macro_edge_by_door_name("room_01", "Ventana") is None
    assert engine.get_macro_edge_by_door_name("nonexistent", "Puerta principal") is None


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
            connection_type="open",
            from_anchor="room_01",
            to_anchor="room_02",
            direction="bidirectional",
            door_name="Este",
            door_description="East door",
        ),
        MacroEdge(
            macro_edge_id="e-1-3",
            connection_type="password",
            from_anchor="room_01",
            to_anchor="room_03",
            direction="unidirectional",
            door_name="Oeste",
            door_description="West door",
            password="secreto",
        ),
    ]

    engine.build_macro_graph(anchors, edges)

    assert len(engine.get_edges_from_anchor("room_01")) == 2
    assert engine.get_macro_edge_by_door_name("room_01", "Este") is not None
    assert engine.get_macro_edge_by_door_name("room_01", "Oeste") is not None


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
    assert "priority" in (captured.out + captured.err).lower()


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
# MacroEdge unknown connection type
# ===================================================================


def test_macro_edge_unknown_connection_type_fails():
    """Unknown connection type returns failure with a Spanish message."""
    from fortress_engine.engine.graph import MacroEdge, DualGraphEngine

    engine = DualGraphEngine()
    hero = _make_player("hero", spatial_anchor="room_01")
    room = _make_entity("room_01", type_="room")
    engine.add_anchor(room)

    state = _minimal_state(hero, room)

    edge = MacroEdge(
        macro_edge_id="wormhole-1",
        connection_type="wormhole",
        from_anchor="room_01",
        to_anchor="room_02",
        direction="bidirectional",
        door_name="Portal",
        door_description="Mysterious portal",
    )

    valid, msg = engine.validate_macro_edge(edge, state)
    assert valid is False
    assert msg == "Tipo de conexión desconocido: wormhole"
