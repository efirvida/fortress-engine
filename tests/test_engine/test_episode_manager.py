"""Tests for EpisodeManager — RED phase (E1.1).

EpisodeManager loads episodes from disk, applies carry_over between episodes,
and coordinates graph replacement and player teleportation.

All tests follow Strict TDD: RED first (this file), then GREEN in episode_manager.py.
"""

from fortress_engine.entities.entity import CarryOver, Episode, Entity, GoalCondition, GoalConditions
from fortress_engine.engine.graph import DualGraphEngine
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    EPISODE_STARTED,
    EPISODE_TRANSITION,
    EngineEvent,
)


# ===================================================================
# Helpers — minimal world on disk
# ===================================================================


def _write_yaml(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _make_two_episode_world(tmp_path):
    """Create a minimal world with two episodes for transition testing.

    Layout:
        world.yaml
        shared/player.yaml
        episodes/episode-01.yaml
        episode-01/rooms/room_a.yaml
        episode-01/items/key.yaml
        episode-01/macros/door.yaml
        episode-01/actions/pick_up.yaml
        episodes/episode-02.yaml
        episode-02/rooms/room_b.yaml
        episode-02/items/blade.yaml
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
        base / "shared" / "player.yaml",
        """\
entity_id: "hero"
type: "player"
name: "Hero"
components:
  max_weight: 40
spatial_anchor: null
""",
    )
    _write_yaml(
        base / "episodes" / "episode-01.yaml",
        """\
id: "episode-01"
name: "Part One"
order: 1
description: "Episode one intro."
requires: []
start_anchor: "room_a"
goal:
  conditions:
    - type: "flag_is_set"
      params:
        flag: "won_ep1"
  output: "You completed Part One!"
  side_effects: []
carry_over:
  inventory: ["rusty_key"]
  flags: ["learned_secret"]
""",
    )
    _write_yaml(
        base / "episodes" / "episode-02.yaml",
        """\
id: "episode-02"
name: "Part Two"
order: 2
description: "Episode two intro."
requires: ["episode-01"]
start_anchor: "room_b"
goal:
  conditions:
    - type: "flag_is_set"
      params:
        flag: "won_ep2"
  output: "You completed Part Two!"
  side_effects: []
carry_over:
  inventory: []
  flags: []
""",
    )
    _write_yaml(
        base / "episode-01" / "rooms" / "room_a.yaml",
        """\
entity_id: "room_a"
type: "room"
name: "Room A"
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
spatial_anchor: "room_a"
""",
    )
    _write_yaml(
        base / "episode-01" / "macros" / "door.yaml",
        """\
- macro_edge_id: "door_a_to_b"
  connection_type: "open"
  from_anchor: "room_a"
  to_anchor: "room_b"
  direction: "bidirectional"
  door_name: "north"
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
      from_container: "room_a"
      to_container: "hero"
  output: "Taken."
""",
    )
    _write_yaml(
        base / "episode-02" / "rooms" / "room_b.yaml",
        """\
entity_id: "room_b"
type: "room"
name: "Room B"
components:
  visited: false
""",
    )
    _write_yaml(
        base / "episode-02" / "items" / "blade.yaml",
        """\
entity_id: "magic_blade"
type: "item"
name: "Magic Blade"
components:
  weight: 3
spatial_anchor: "room_b"
""",
    )

    return base


# ===================================================================
# Constructor / get_available_episodes
# ===================================================================


def test_constructor_stores_episodes(tmp_path):
    """EpisodeManager stores episodes and marks no-requires episodes as available."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(world))
    episodes = loader.load_episodes()
    assert len(episodes) == 2

    bus = EventBus()
    mgr = EpisodeManager(episodes, str(world), bus)
    assert mgr is not None


def test_get_available_episodes(tmp_path):
    """Available episodes are those with empty requires list."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(world))
    episodes = loader.load_episodes()

    bus = EventBus()
    mgr = EpisodeManager(episodes, str(world), bus)

    available = mgr.get_available_episodes()
    available_ids = [ep.id for ep in available]
    assert "episode-01" in available_ids
    # episode-02 requires episode-01, so it's NOT available initially
    assert "episode-02" not in available_ids


# ===================================================================
# start_episode
# ===================================================================


def test_start_episode_loads_graph_and_teleports_player(tmp_path):
    """start_episode loads data from disk, teleports player to start_anchor,
    emits episode_started, and returns a DualGraphEngine."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(world))
    episodes = loader.load_episodes()

    bus = EventBus()
    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))

    mgr = EpisodeManager(episodes, str(world), bus)

    # Build initial state with hero at null (not placed yet).
    state = WorldState(
        entities={"hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None)},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="",
        turn_number=0,
    )

    graph = mgr.start_episode("episode-01", state)

    # Graph is returned
    assert isinstance(graph, DualGraphEngine)

    # Player was teleported to start_anchor
    assert state.get_entity("hero").spatial_anchor == "room_a"

    # State was populated with episode entities
    assert state.entity_exists("room_a")
    assert state.entity_exists("rusty_key")

    # episode_started event was emitted
    started_events = [e for e in received if e.type == EPISODE_STARTED]
    assert len(started_events) == 1
    ep = started_events[0]
    assert ep.payload["episode_id"] == "episode-01"
    assert ep.payload["start_anchor_id"] == "room_a"
    assert ep.episode_id == "episode-01"


# ===================================================================
# apply_carry_over
# ===================================================================


def test_apply_carry_over_all(tmp_path):
    """["*"] inventory transfers ALL items; ["*"] flags transfers ALL flags."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    bus = EventBus()

    mgr = EpisodeManager([], str(world), bus)

    # Build state with some items in inventory and flags set.
    hero = Entity("hero", "player", "Hero", {"max_weight": 40}, "some_room")
    item1 = Entity("item_1", "item", "Maza", {"weight": 39}, "hero")
    item2 = Entity("item_2", "item", "Escudo", {"weight": 5}, "hero")
    item3 = Entity("item_3", "item", "Piedra", {"weight": 1}, "room_x")

    state = WorldState(
        entities={
            "hero": hero,
            "item_1": item1,
            "item_2": item2,
            "item_3": item3,
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
    )
    state.set_flag("flag_a", True)
    state.set_flag("flag_b", False)
    state.set_flag("flag_c", True)

    carry = CarryOver(inventory=["*"], flags=["*"])
    mgr.apply_carry_over(carry, state)

    # All items in hero's inventory stay (they persist).
    # In practice carry_over applies during transition — items in inventory
    # remain; items NOT in inventory are lost. But for ["*"] inventory, the
    # manager preserves all entities in hero's inventory.
    inv = set(e.entity_id for e in state.get_player_inventory("hero"))
    assert "item_1" in inv
    assert "item_2" in inv
    # item_3 is NOT in hero's inventory — it stays in room_x
    assert "item_3" not in inv

    # All flags persist — flag_book stays intact because ["*"] means "keep all"
    assert state.get_flag("flag_a") is True
    assert state.get_flag("flag_b") is False
    assert state.get_flag("flag_c") is True


def test_apply_carry_over_specific(tmp_path):
    """Specific inventory/flags lists transfer only those items."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    bus = EventBus()

    mgr = EpisodeManager([], str(world), bus)

    hero = Entity("hero", "player", "Hero", {"max_weight": 40}, "some_room")
    item1 = Entity("item_1", "item", "Maza", {"weight": 39}, "hero")
    item2 = Entity("item_2", "item", "Escudo", {"weight": 5}, "hero")
    item3 = Entity("item_3", "item", "Piedra", {"weight": 1}, "hero")

    state = WorldState(
        entities={
            "hero": hero,
            "item_1": item1,
            "item_2": item2,
            "item_3": item3,
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
    )
    state.set_flag("flag_a", True)
    state.set_flag("flag_b", True)

    carry = CarryOver(inventory=["item_1"], flags=["flag_a"])
    mgr.apply_carry_over(carry, state)

    inv = set(e.entity_id for e in state.get_player_inventory("hero"))
    # Only item_1 is kept; item_2 and item_3 are removed
    assert "item_1" in inv
    assert "item_2" not in inv
    assert "item_3" not in inv

    # Only flag_a is kept; flag_b is removed
    assert state.get_flag("flag_a") is True
    assert state.get_flag("flag_b") is False  # removed, so defaults to False


def test_apply_carry_over_nothing(tmp_path):
    """Empty inventory/flags lists transfer nothing."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    bus = EventBus()

    mgr = EpisodeManager([], str(world), bus)

    hero = Entity("hero", "player", "Hero", {"max_weight": 40}, "some_room")
    item1 = Entity("item_1", "item", "Maza", {"weight": 39}, "hero")
    item2 = Entity("item_2", "item", "Escudo", {"weight": 5}, "hero")

    state = WorldState(
        entities={
            "hero": hero,
            "item_1": item1,
            "item_2": item2,
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
    )
    state.set_flag("flag_a", True)

    carry = CarryOver(inventory=[], flags=[])
    mgr.apply_carry_over(carry, state)

    inv = set(e.entity_id for e in state.get_player_inventory("hero"))
    # Nothing kept — all inventory entities removed
    assert "item_1" not in inv
    assert "item_2" not in inv

    # All flags removed
    assert state.get_flag("flag_a") is False


# ===================================================================
# transition_to_next
# ===================================================================


def test_transition_to_next(tmp_path):
    """transition_to_next applies carry_over, loads new graph,
    teleports player, resets turn_number, and emits episode_transition
    and episode_started."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(world))
    episodes = loader.load_episodes()

    bus = EventBus()
    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))

    mgr = EpisodeManager(episodes, str(world), bus)

    # Start episode-01 first to set up the state and graph
    state = WorldState(
        entities={"hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None)},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="",
        turn_number=0,
    )
    state.set_flag("learned_secret", True)
    # Give the hero the rusty_key in inventory
    state.entities["rusty_key"] = Entity("rusty_key", "item", "Rusty Key", {"weight": 1}, "hero")

    graph = mgr.start_episode("episode-01", state)
    assert state.turn_number == 0  # reset by start_episode

    # Now transition to episode-02
    received.clear()
    new_graph = mgr.transition_to_next("episode-01", state, graph)

    # New graph returned
    assert isinstance(new_graph, DualGraphEngine)

    # Player teleported to episode-02 start_anchor
    assert state.get_entity("hero").spatial_anchor == "room_b"

    # turn_number reset
    assert state.turn_number == 0

    # Carry-over applied: rusty_key was in inventory and specified in carry_over
    inv = [e.entity_id for e in state.get_player_inventory("hero")]
    assert "rusty_key" in inv

    # Carry-over flags: learned_secret stays True
    assert state.get_flag("learned_secret") is True

    # Episode transition and start events emitted
    event_types = [e.type for e in received]
    assert EPISODE_TRANSITION in event_types
    assert EPISODE_STARTED in event_types

    trans_events = [e for e in received if e.type == EPISODE_TRANSITION]
    assert len(trans_events) == 1
    assert trans_events[0].payload["from_episode_id"] == "episode-01"
    assert trans_events[0].payload["to_episode_id"] == "episode-02"

    started_events = [e for e in received if e.type == EPISODE_STARTED]
    assert len(started_events) == 1
    assert started_events[0].payload["episode_id"] == "episode-02"


def test_transition_to_next_returns_none_when_no_next_episode(tmp_path):
    """When there is no next episode, transition_to_next returns None."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(world))
    episodes = loader.load_episodes()

    bus = EventBus()
    mgr = EpisodeManager(episodes, str(world), bus)

    state = WorldState(
        entities={"hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None)},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="",
    )

    # Start episode-02 directly (which has no next episode).
    graph = mgr.start_episode("episode-02", state)

    result = mgr.transition_to_next("episode-02", state, graph)
    assert result is None


# ===================================================================
# unload_graph
# ===================================================================


def test_unload_graph_clears_internals(tmp_path):
    """unload_graph clears the graph's internal data structures."""
    from fortress_engine.engine.episode_manager import EpisodeManager

    world = _make_two_episode_world(tmp_path)
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(world))
    episodes = loader.load_episodes()

    bus = EventBus()
    mgr = EpisodeManager(episodes, str(world), bus)

    state = WorldState(
        entities={"hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None)},
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="",
    )

    graph = mgr.start_episode("episode-01", state)
    # Graph has data
    assert graph.get_edges_from_anchor("room_a") != []

    mgr.unload_graph(graph)

    # After unload, graph internals are empty
    assert graph.get_edges_from_anchor("room_a") == []
    # Hyper edges also gone
    assert graph.get_hyper_edges_for_verb("room_a", "coger") == []
