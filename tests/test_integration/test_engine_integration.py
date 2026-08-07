"""Integration tests — prove the engine pieces work TOGETHER.

These tests exercise the real glue, not unit-level mocks:
  loader → graph → state → operators → EventBus.

A minimal world is built on disk (same style as tests/test_entities/test_loader.py)
and loaded through :class:`EntityLoader`; every assertion runs against the
resulting runtime dataclasses. No production code is stubbed.

Follows tdd.md end-to-end flows (load → build graph → validate clique →
execute operator → emit event).
"""

import json

from fortress_engine.entities.entity import ParsedCommand
from fortress_engine.engine.graph import DualGraphEngine
from fortress_engine.engine.operators import execute_operator
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ENTITY_TRANSFERRED,
    EngineEvent,
    event_to_dict,
)


# ===================================================================
# Helpers — minimal world on disk
# ===================================================================

def _write_yaml(path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _minimal_world(tmp_path):
    """Create a valid minimal world at tmp_path.

    Layout (mirrors tests/test_entities/test_loader.py):
        world.yaml
        episodes/episode-01.yaml
        shared/player.yaml
        episode-01/rooms/room_01.yaml
        episode-01/items/key.yaml
        episode-01/macros/door.yaml
        episode-01/actions/pick_up.yaml        (coger rusty_key, priority 10)
        episode-01/actions/z_low_priority.yaml (coger rusty_key, priority 5)
    """
    base = tmp_path / "test_world"

    _write_yaml(
        base / "world.yaml",
        """\
world_id: "test_world"
name: "Test World"
""",
    )
    _write_yaml(
        base / "episodes" / "episode-01.yaml",
        """\
id: "episode-01"
name: "The Beginning"
order: 1
description: "You awaken in a dark room."
requires: []
start_anchor: "room_01"
goal:
  conditions:
    - type: "flag_is_set"
      params:
        flag: "escaped"
  output: "You escaped!"
  side_effects: []
carry_over:
  inventory: []
  flags: []
""",
    )
    _write_yaml(
        base / "shared" / "player.yaml",
        """\
entity_id: "hero"
type: "player"
name: "Hero"
components:
  max_weight: 20
spatial_anchor: null
""",
    )
    _write_yaml(
        base / "episode-01" / "rooms" / "room_01.yaml",
        """\
entity_id: "room_01"
type: "room"
name: "A Dark Cell"
components:
  visited: false
""",
    )
    _write_yaml(
        base / "episode-01" / "items" / "key.yaml",
        """\
entity_id: "rusty_key"
type: "item"
name: "Rusty Key"
components:
  weight: 1
  key_id: 15
spatial_anchor: "room_01"
""",
    )
    _write_yaml(
        base / "episode-01" / "macros" / "doors.yaml",
        """\
- macro_edge_id: "door_to_hall"
  from_anchor: "room_01"
  to_anchor: "room_02"
  direction: "bidirectional"
  passage_name: "north"
  passage_description: "A heavy iron door."
""",
    )
    _write_yaml(
        base / "episode-01" / "actions" / "pick_up.yaml",
        """\
- hyper_edge_id: "pick_key"
  name: "Pick up key"
  priority: 10
  clique:
    subject: "player"
    verb: "coger"
    target: "rusty_key"
  operators:
    - type: "TRANSFER"
      entity: "rusty_key"
      from_container: "room_01"
      to_container: "hero"
  output: "You pick up the rusty key."
""",
    )
    _write_yaml(
        base / "episode-01" / "actions" / "z_low_priority.yaml",
        """\
- hyper_edge_id: "low_pick"
  name: "Try key"
  priority: 5
  clique:
    subject: "player"
    verb: "coger"
    target: "rusty_key"
  operators: []
  output: "It does nothing."
""",
    )
    return base


def _load_episode_data(base):
    """Load world.yaml + episode-01 data via EntityLoader."""
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()
    assert len(episodes) == 1
    data = loader.load_episode_data("episode-01", episodes[0])
    data["shared_entities"] = loader.load_shared_entities("episode-01")
    return data


def _build_graph(data) -> DualGraphEngine:
    """Build a DualGraphEngine from loaded rooms, macro edges and hyper edges.

    Hyper edges are registered under ``room_01`` — the anchor where the
    ``rusty_key`` target lives and where the action is performed. This mirrors
    the orchestrator's job of scoping hyper edges to their anchor.
    """
    graph = DualGraphEngine()
    graph.build_macro_graph(data["rooms"], data["macro_edges"])
    for he in data["hyper_edges"]:
        graph.add_hyper_edge("room_01", he)
    return graph


def _build_state(data) -> WorldState:
    """Build a WorldState from loaded entities.

    The hero is placed at the episode start anchor (``room_01``) — the
    orchestrator's episode-start responsibility — so the clique can resolve
    target reachability against the same anchor.
    """
    entities = {
        e.entity_id: e
        for e in (
            data["rooms"] + data["items"] + data["shared_entities"]
        )
    }
    entities["hero"].spatial_anchor = "room_01"
    return WorldState(
        entities=entities,
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
    )


# ===================================================================
# Loader → Graph
# ===================================================================


def test_loader_to_graph_macro_and_hyper_edges(tmp_path):
    """Loaded data feeds DualGraphEngine: macro edges by anchor, hyper edges
    by verb, priority-descending."""
    data = _load_episode_data(_minimal_world(tmp_path))
    graph = _build_graph(data)

    macro_edges = graph.get_edges_from_anchor("room_01")
    assert [e.macro_edge_id for e in macro_edges] == ["door_to_hall"]

    hyper_edges = graph.get_hyper_edges_for_verb("room_01", "coger")
    assert [he.hyper_edge_id for he in hyper_edges] == ["pick_key", "low_pick"]
    assert [he.priority for he in hyper_edges] == [10, 5]

    # Unrelated verb / anchor stay empty.
    assert graph.get_hyper_edges_for_verb("room_01", "usar") == []
    assert graph.get_hyper_edges_for_verb("room_99", "coger") == []


# ===================================================================
# Graph + State
# ===================================================================


def test_graph_state_clique_forms_and_rejects(tmp_path):
    """A loaded hyper edge's clique forms for a valid command targeting
    ``rusty_key`` in the same anchor, and rejects an invalid one."""
    data = _load_episode_data(_minimal_world(tmp_path))
    graph = _build_graph(data)
    state = _build_state(data)

    pick_edge = graph.get_hyper_edges_for_verb("room_01", "coger")[0]
    assert pick_edge.hyper_edge_id == "pick_key"

    valid = ParsedCommand(subject="hero", verb="coger", target="rusty_key")
    assert graph.validate_clique(pick_edge, valid, state) is True

    # Wrong verb → rejected.
    wrong_verb = ParsedCommand(subject="hero", verb="usar", target="rusty_key")
    assert graph.validate_clique(pick_edge, wrong_verb, state) is False

    # Wrong target (same room, different entity) → rejected (discrimination).
    wrong_target = ParsedCommand(subject="hero", verb="coger", target="room_01")
    assert graph.validate_clique(pick_edge, wrong_target, state) is False


# ===================================================================
# Operators + State
# ===================================================================


def test_operators_state_transfer_from_loaded_edge(tmp_path):
    """The TRANSFER operator from the loaded hyper edge mutates state and
    returns the entity_transferred contract payload."""
    data = _load_episode_data(_minimal_world(tmp_path))
    graph = _build_graph(data)
    state = _build_state(data)

    pick_edge = graph.get_hyper_edges_for_verb("room_01", "coger")[0]
    op_data = pick_edge.operators[0]
    assert op_data == {
        "type": "TRANSFER",
        "entity": "rusty_key",
        "from_container": "room_01",
        "to_container": "hero",
    }

    result = execute_operator(state, op_data, "hero", graph)

    assert result.success is True
    assert result.error_message is None
    # State mutated: rusty_key now in the hero's inventory.
    assert state.get_entity("rusty_key").spatial_anchor == "hero"
    assert [e.entity_id for e in state.get_player_inventory("hero")] == [
        "rusty_key"
    ]
    # Payload matches the entity_transferred contract keys (13-event-system §2.3).
    assert result.events_payload == {
        "entity_id": "rusty_key",
        "from_container_id": "room_01",
        "to_container_id": "hero",
    }


# ===================================================================
# EventBus (full path)
# ===================================================================


def test_event_bus_receives_state_change_event(tmp_path):
    """The operator payload becomes a JSON-primitive EngineEvent on the bus."""
    data = _load_episode_data(_minimal_world(tmp_path))
    graph = _build_graph(data)
    state = _build_state(data)

    pick_edge = graph.get_hyper_edges_for_verb("room_01", "coger")[0]
    result = execute_operator(state, pick_edge.operators[0], "hero", graph)
    assert result.success is True
    payload = result.events_payload
    assert payload is not None

    # Orchestrator role: wrap the payload in a state-change EngineEvent.
    event = EngineEvent.create(
        ENTITY_TRANSFERRED,
        turn_number=1,
        payload=payload,
        protagonist_id="hero",
        episode_id="episode-01",
    )

    bus = EventBus()
    received: list[EngineEvent] = []
    bus.subscribe(ENTITY_TRANSFERRED, lambda e: received.append(e))
    bus.emit(event)

    assert received == [event]

    # Event shape is correct.
    assert isinstance(event, EngineEvent)
    assert event.type == ENTITY_TRANSFERRED
    assert event.turn_number == 1
    assert event.protagonist_id == "hero"
    assert event.episode_id == "episode-01"

    # Payload keys are JSON primitives — serializable end to end.
    event_dict = event_to_dict(event)
    json_str = json.dumps(event_dict)
    assert isinstance(json_str, str)
    assert json.loads(json_str)["payload"] == payload
