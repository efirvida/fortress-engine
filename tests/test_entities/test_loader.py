"""Tests for EntityLoader — YAML loading, Pydantic validation, integrity checks.

Follows world-loading spec and tdd.md §4.12.
All tests are entity-agnostic — no entity type constants or closed sets.
"""

import pytest

from fortress_engine.entities.entity import (
    Entity, CarryOver, Episode, GoalCondition, GoalConditions,
)


# ===================================================================
# Helpers — build minimal world on disk
# ===================================================================

def _write_yaml(path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _minimal_world(tmp_path):
    """Create a valid minimal world at tmp_path.

    Layout:
        world.yaml
        episodes/episode-01.yaml
        shared/player.yaml
        episode-01/rooms/room_01.yaml
        episode-01/items/key.yaml
        episode-01/npcs/guard.yaml
        episode-01/macros/door.yaml
        episode-01/actions/pick_up.yaml
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
        base / "episode-01" / "npcs" / "guard.yaml",
        """\
entity_id: "guard"
type: "npc"
name: "Guard"
components:
  hostile: true
  combat_pattern: "troll"
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
    return base


# ===================================================================
# __init__ — rejects non-existent path
# ===================================================================


def test_init_rejects_missing_path(tmp_path):
    """EntityLoader.__init__ raises FileNotFoundError for non-existent path."""
    from fortress_engine.entities.loader import EntityLoader

    bad_path = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError, match="not found"):
        EntityLoader(str(bad_path))


# ===================================================================
# load_world_config
# ===================================================================


def test_load_world_config(tmp_path):
    """load_world_config returns world.yaml contents as dict."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    config = loader.load_world_config()

    assert config["world_id"] == "test_world"
    assert config["name"] == "Test World"
    # N3: language/parser/narrator now have defaults
    assert config["language"] == "es"
    assert config["parser"] == {"plugin": "classic", "options": {}}
    assert config["narrator"] == {"plugin": "template", "options": {}}


def test_load_world_config_rejects_bad_yaml(tmp_path):
    """load_world_config raises on malformed world.yaml."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "bad_world"
    _write_yaml(base / "world.yaml", "not: valid: yaml: [")
    loader = EntityLoader(str(base))

    with pytest.raises(ValueError, match="Invalid YAML"):
        loader.load_world_config()


# ===================================================================
# load_episodes
# ===================================================================


def test_load_episodes(tmp_path):
    """load_episodes returns list of Episode dataclasses."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()

    assert len(episodes) == 1
    ep = episodes[0]
    assert isinstance(ep, Episode)
    assert ep.id == "episode-01"
    assert ep.name == "The Beginning"
    assert ep.order == 1
    assert ep.description == "You awaken in a dark room."
    assert ep.requires == []
    assert ep.start_anchor == "room_01"
    assert isinstance(ep.goal, GoalConditions)
    assert ep.goal.output == "You escaped!"
    assert isinstance(ep.carry_over, CarryOver)


def test_load_episodes_rejects_missing_id(tmp_path):
    """load_episodes raises on episode YAML missing 'id'."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "bad"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    (base / "episodes").mkdir(parents=True)
    _write_yaml(
        base / "episodes" / "bad.yaml",
        """\
name: "No ID"
order: 1
start_anchor: "room_01"
goal:
  conditions: []
  output: "Win!"
carry_over:
  inventory: []
  flags: []
""",
    )
    loader = EntityLoader(str(base))
    with pytest.raises(ValueError, match="id"):
        loader.load_episodes()


# ===================================================================
# load_shared_entities
# ===================================================================


def test_load_shared_entities(tmp_path):
    """load_shared_entities returns Entity objects from shared/."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    entities = loader.load_shared_entities("episode-01")

    assert len(entities) == 1
    hero = entities[0]
    assert isinstance(hero, Entity)
    assert hero.entity_id == "hero"
    assert hero.type == "player"
    assert hero.name == "Hero"
    assert hero.components == {"max_weight": 20}
    assert hero.spatial_anchor is None


def test_load_shared_entities_empty_if_no_shared_dir(tmp_path):
    """load_shared_entities returns [] if shared/ doesn't exist."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "minimal"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    (base / "episodes").mkdir(parents=True)
    _write_yaml(
        base / "episodes" / "ep-01.yaml",
        """\
id: "ep-01"
name: "Ep"
order: 1
start_anchor: "r1"
goal:
  conditions: []
  output: "Win!"
carry_over:
  inventory: []
  flags: []
""",
    )
    loader = EntityLoader(str(base))
    entities = loader.load_shared_entities("ep-01")
    assert entities == []


def test_load_shared_entities_list_form(tmp_path):
    """A shared YAML file containing a LIST of entities loads every entry."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "shared_list_world"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    (base / "episodes").mkdir(parents=True)
    _write_yaml(
        base / "episodes" / "ep-01.yaml",
        """\
id: "ep-01"
name: "Ep"
order: 1
start_anchor: "r1"
goal:
  conditions: []
  output: "Win!"
carry_over:
  inventory: []
  flags: []
""",
    )
    (base / "shared").mkdir(parents=True)
    _write_yaml(
        base / "shared" / "npcs.yaml",
        """\
- entity_id: "alice"
  type: "npc"
  name: "Alice"
  components: {}
  spatial_anchor: null
- entity_id: "bob"
  type: "npc"
  name: "Bob"
  components: {}
  spatial_anchor: null
""",
    )
    loader = EntityLoader(str(base))
    entities = loader.load_shared_entities("ep-01")
    assert [e.entity_id for e in entities] == ["alice", "bob"]
    assert all(e.type == "npc" for e in entities)



# ===================================================================
# load_rooms
# ===================================================================


def test_load_rooms(tmp_path):
    """load_rooms returns Entity objects from episode-XX/rooms/."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    rooms = loader.load_rooms("episode-01")

    assert len(rooms) == 1
    room = rooms[0]
    assert isinstance(room, Entity)
    assert room.entity_id == "room_01"
    assert room.type == "room"
    assert room.name == "A Dark Cell"


# ===================================================================
# load_items
# ===================================================================


def test_load_items(tmp_path):
    """load_items returns Entity objects from episode-XX/items/."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    items = loader.load_items("episode-01")

    assert len(items) == 1
    item = items[0]
    assert item.entity_id == "rusty_key"
    assert item.type == "item"
    assert item.spatial_anchor == "room_01"


# ===================================================================
# load_npcs
# ===================================================================


def test_load_npcs(tmp_path):
    """load_npcs returns Entity objects from episode-XX/npcs/."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    npcs = loader.load_npcs("episode-01")

    assert len(npcs) == 1
    npc = npcs[0]
    assert npc.entity_id == "guard"
    assert npc.type == "npc"


# ===================================================================
# EntityYAML rejects missing entity_id
# ===================================================================


def test_entity_yaml_rejects_missing_entity_id(tmp_path):
    """EntityYAML rejects YAML missing entity_id field."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "items" / "bad_item.yaml",
        """\
type: "item"
name: "Bad Item"
""",
    )
    loader = EntityLoader(str(base))

    with pytest.raises(ValueError, match="entity_id"):
        loader.load_items("episode-01")


# ===================================================================
# load_macro_edges
# ===================================================================


def test_load_macro_edges(tmp_path):
    """load_macro_edges returns MacroEdge objects."""
    from fortress_engine.entities.loader import EntityLoader
    from fortress_engine.engine.graph import MacroEdge

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    edges = loader.load_macro_edges("episode-01")

    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, MacroEdge)
    assert edge.macro_edge_id == "door_to_hall"
    assert edge.requires_text is None
    assert edge.from_anchor == "room_01"
    assert edge.to_anchor == "room_02"


def test_load_macro_edges_rejects_legacy_connection_type(tmp_path):
    """A world YAML that still writes connection_type FAILS loudly at load
    time instead of being silently dropped."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "macros" / "legacy_door.yaml",
        """\
- macro_edge_id: "legacy_door"
  connection_type: "password"
  from_anchor: "room_01"
  to_anchor: "room_02"
  direction: "bidirectional"
  passage_name: "north"
  password: "ábrete sésamo"
  open: false
""",
    )
    loader = EntityLoader(str(base))

    with pytest.raises(ValueError, match="connection_type"):
        loader.load_macro_edges("episode-01")


def test_load_macro_edges_maps_generic_predicates(tmp_path):
    """MacroEdgeYAML maps the generic predicate fields onto the dataclass."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "macros" / "gated_door.yaml",
        """\
- macro_edge_id: "gated_door"
  from_anchor: "room_01"
  to_anchor: "room_02"
  direction: "bidirectional"
  passage_name: "este"
  question: "¿Qué es?"
  requires_text: "el sol"
  requires_item: "antorcha"
  forbids_item: "espada"
  requires_flag: "knows_secret"
  forbids_flag: "darkness_remains"
  death_message: "Has muerto."
  open: false
""",
    )
    loader = EntityLoader(str(base))
    edges = loader.load_macro_edges("episode-01")

    gated = [e for e in edges if e.macro_edge_id == "gated_door"]
    assert len(gated) == 1
    edge = gated[0]
    assert edge.question == "¿Qué es?"
    assert edge.requires_text == "el sol"
    assert edge.requires_item == "antorcha"
    assert edge.forbids_item == "espada"
    assert edge.requires_flag == "knows_secret"
    assert edge.forbids_flag == "darkness_remains"
    assert edge.death_message == "Has muerto."
    assert edge.open is False


# ===================================================================
# load_hyper_edges
# ===================================================================


def test_load_hyper_edges(tmp_path):
    """load_hyper_edges returns HyperEdge objects."""
    from fortress_engine.entities.loader import EntityLoader
    from fortress_engine.engine.graph import HyperEdge

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    edges = loader.load_hyper_edges("episode-01")

    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, HyperEdge)
    assert edge.hyper_edge_id == "pick_key"
    assert edge.name == "Pick up key"
    assert edge.priority == 10
    assert edge.clique.verb == "coger"
    assert edge.clique.target == "rusty_key"
    assert edge.output == "You pick up the rusty key."
    assert len(edge.operators) == 1


def test_load_hyper_edges_recursive_subdirs(tmp_path):
    """HyperEdge loading scans nested action directories recursively."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "actions" / "bonus" / "hidden.yaml",
        """\
- hyper_edge_id: "hidden_action"
  name: "Hidden"
  priority: 1
  clique:
    verb: "buscar"
    target: "*"
  operators: []
  output: "Nothing here."
""",
    )
    loader = EntityLoader(str(base))
    edges = loader.load_hyper_edges("episode-01")

    assert len(edges) == 2
    ids = {e.hyper_edge_id for e in edges}
    assert ids == {"pick_key", "hidden_action"}


# ===================================================================
# load_episode_data
# ===================================================================


def test_load_episode_data(tmp_path):
    """load_episode_data returns a dict with rooms, items, npcs, macro_edges, hyper_edges."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()
    data = loader.load_episode_data("episode-01", episodes[0])

    assert set(data.keys()) == {"rooms", "items", "npcs", "macro_edges", "hyper_edges"}
    assert len(data["rooms"]) == 1
    assert len(data["items"]) == 1
    assert len(data["npcs"]) == 1
    assert len(data["macro_edges"]) == 1
    assert len(data["hyper_edges"]) == 1


# ===================================================================
# validate_world
# ===================================================================


def test_validate_world_valid(tmp_path):
    """validate_world returns empty list for a valid world."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    loader = EntityLoader(str(base))
    problems = loader.validate_world()

    assert problems == []


def test_validate_world_missing_start_anchor_room(tmp_path):
    """validate_world detects start_anchor that does not exist."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "bad"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    _write_yaml(
        base / "episodes" / "ep-01.yaml",
        """\
id: "ep-01"
name: "Ep"
order: 1
start_anchor: "missing_room"
goal:
  conditions: []
  output: "Win"
carry_over:
  inventory: []
  flags: []
""",
    )
    (base / "shared").mkdir(parents=True)
    (base / "ep-01" / "rooms").mkdir(parents=True)
    (base / "ep-01" / "items").mkdir(parents=True)
    (base / "ep-01" / "npcs").mkdir(parents=True)
    (base / "ep-01" / "macros").mkdir(parents=True)
    (base / "ep-01" / "actions").mkdir(parents=True)

    loader = EntityLoader(str(base))
    problems = loader.validate_world()

    assert problems == [
        "Episode 'ep-01' start_anchor 'missing_room' does not exist"
    ]


def test_validate_world_dangling_spatial_anchor(tmp_path):
    """validate_world reports exactly the dangling spatial_anchor problem.

    The assertion is exact — it must fail if the dangling-reference validator
    is removed (empty list) or if any unrelated problem is reported alongside
    the expected one.
    """
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "items" / "floating.yaml",
        """\
entity_id: "floating_item"
type: "item"
name: "Floating"
spatial_anchor: "nonexistent_room"
""",
    )
    loader = EntityLoader(str(base))
    problems = loader.validate_world()

    assert problems == [
        "Entity 'floating_item' (episode 'episode-01') "
        "has dangling spatial_anchor 'nonexistent_room'"
    ]


def test_validate_world_duplicate_hyper_edge_priority(tmp_path):
    """validate_world reports exactly the duplicate (verb, target, priority) warning.

    The edge file is named ``z_dup_pick.yaml`` so it loads after ``pick_up.yaml``
    (glob is lexicographically sorted), making the reported edge order
    deterministic: 'pick_key' first, 'dup_pick' second. The assertion is exact —
    it must fail if the duplicate detector is removed.
    """
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "actions" / "z_dup_pick.yaml",
        """\
- hyper_edge_id: "dup_pick"
  name: "Duplicate"
  priority: 10
  clique:
    verb: "coger"
    target: "rusty_key"
  operators: []
  output: "Duplicate."
""",
    )
    loader = EntityLoader(str(base))
    problems = loader.validate_world()

    assert problems == [
        "Duplicate priority 10 for (verb='coger', target='rusty_key') "
        "in episode 'episode-01': edges 'pick_key' and 'dup_pick'"
    ]


# ===================================================================
# Additional coverage triangulation tests
# ===================================================================


def test_world_config_missing_file_raises(tmp_path):
    """load_world_config raises FileNotFoundError when world.yaml is absent."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "empty_world"
    base.mkdir()
    loader = EntityLoader(str(base))

    with pytest.raises(FileNotFoundError, match="world.yaml"):
        loader.load_world_config()


def test_load_episodes_empty_when_no_episodes_dir(tmp_path):
    """load_episodes returns [] when episodes/ directory doesn't exist."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "bare_world"
    base.mkdir()
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()

    assert episodes == []


def test_load_macro_edges_empty_when_no_macros_dir(tmp_path):
    """load_macro_edges returns [] when macros/ doesn't exist."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    # Remove macros dir
    import shutil
    shutil.rmtree(base / "episode-01" / "macros")
    loader = EntityLoader(str(base))
    edges = loader.load_macro_edges("episode-01")

    assert edges == []


def test_load_hyper_edges_empty_when_no_actions_dir(tmp_path):
    """load_hyper_edges returns [] when actions/ doesn't exist."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    import shutil
    shutil.rmtree(base / "episode-01" / "actions")
    loader = EntityLoader(str(base))
    edges = loader.load_hyper_edges("episode-01")

    assert edges == []


def test_load_single_macro_edge_not_list(tmp_path):
    """MacroEdge loaded from a file with a single dict (not a list)."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "macros" / "single_door.yaml",
        """\
macro_edge_id: "single_door"
from_anchor: "room_01"
to_anchor: "room_03"
direction: "unidirectional"
passage_name: "up"
""",
    )
    loader = EntityLoader(str(base))
    edges = loader.load_macro_edges("episode-01")

    assert len(edges) == 2  # original list + single dict
    single = [e for e in edges if e.macro_edge_id == "single_door"]
    assert len(single) == 1
    assert single[0].to_anchor == "room_03"


def test_load_single_hyper_edge_not_list(tmp_path):
    """HyperEdge loaded from a file with a single dict (not a list)."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "actions" / "single_edge.yaml",
        """\
hyper_edge_id: "single_edge"
name: "Single"
priority: 5
clique:
  verb: "mirar"
  target: "*"
operators: []
output: "You look around."
""",
    )
    loader = EntityLoader(str(base))
    edges = loader.load_hyper_edges("episode-01")

    assert len(edges) == 2  # original list + single dict
    single = [e for e in edges if e.hyper_edge_id == "single_edge"]
    assert len(single) == 1


def test_load_single_entity_not_list(tmp_path):
    """Entity loaded from a file with a single dict (not a list)."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "items" / "single_item.yaml",
        """\
entity_id: "single_gem"
type: "item"
name: "Gem"
components:
  weight: 2
spatial_anchor: "room_01"
""",
    )
    loader = EntityLoader(str(base))
    items = loader.load_items("episode-01")

    assert len(items) == 2  # original + single dict
    gem = [i for i in items if i.entity_id == "single_gem"]
    assert len(gem) == 1


def test_load_episodes_with_composite_goal(tmp_path):
    """Episode with composite and/or goal conditions loads correctly."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "comp_world"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    (base / "episodes").mkdir(parents=True)
    _write_yaml(
        base / "episodes" / "ep-01.yaml",
        """\
id: "ep-01"
name: "Composite Episode"
order: 1
start_anchor: "room_01"
goal:
  conditions:
    - and:
        - type: "flag_is_set"
          params:
            flag: "door_open"
        - type: "entity_dead"
          params:
            entity: "wolf"
    - type: "entity_in_room"
      params:
        entity: "hero"
        room: "room_01"
  output: "You did it!"
carry_over:
  inventory: []
  flags: []
""",
    )
    (base / "shared").mkdir(parents=True)
    (base / "ep-01").mkdir(parents=True)
    for d in ["rooms", "items", "npcs", "macros", "actions"]:
        (base / "ep-01" / d).mkdir(parents=True)
    _write_yaml(
        base / "ep-01" / "rooms" / "room_01.yaml",
        "entity_id: room_01\ntype: room\nname: Start\n",
    )

    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()

    assert len(episodes) == 1
    ep = episodes[0]
    assert len(ep.goal.conditions) == 2
    # First is composite (and), second is atomic
    assert isinstance(ep.goal.conditions[0], dict)
    assert "and" in ep.goal.conditions[0]
    assert isinstance(ep.goal.conditions[1], GoalCondition)


def test_load_entities_as_list(tmp_path):
    """Entity YAML file containing a list of entities."""
    from fortress_engine.entities.loader import EntityLoader

    base = _minimal_world(tmp_path)
    _write_yaml(
        base / "episode-01" / "items" / "list_items.yaml",
        """\
- entity_id: "gem_a"
  type: "item"
  name: "Gem A"
  components:
    weight: 1
  spatial_anchor: "room_01"
- entity_id: "gem_b"
  type: "item"
  name: "Gem B"
  components:
    weight: 2
  spatial_anchor: "room_01"
""",
    )
    loader = EntityLoader(str(base))
    items = loader.load_items("episode-01")

    assert len(items) == 3  # original key + gem_a + gem_b
    ids = {i.entity_id for i in items}
    assert ids == {"rusty_key", "gem_a", "gem_b"}


def test_load_episodes_with_flat_goal_format(tmp_path):
    """Episode with flat-format goal conditions (no 'params' key)."""
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "flat_world"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    (base / "episodes").mkdir(parents=True)
    _write_yaml(
        base / "episodes" / "ep-01.yaml",
        """\
id: "ep-01"
name: "Flat Episode"
order: 1
start_anchor: "room_01"
goal:
  conditions:
    - type: "entity_in_room"
      entity: "hero"
      room: "room_01"
  output: "Victory"
carry_over:
  inventory: []
  flags: []
""",
    )
    (base / "shared").mkdir(parents=True)
    (base / "ep-01").mkdir(parents=True)
    for d in ["rooms", "items", "npcs", "macros", "actions"]:
        (base / "ep-01" / d).mkdir(parents=True)
    _write_yaml(
        base / "ep-01" / "rooms" / "room_01.yaml",
        "entity_id: room_01\ntype: room\nname: Start\n",
    )

    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()

    assert len(episodes) == 1
    ep = episodes[0]
    cond = ep.goal.conditions[0]
    assert isinstance(cond, GoalCondition)
    assert cond.type == "entity_in_room"
    assert cond.params == {"entity": "hero", "room": "room_01"}


def test_load_episodes_with_string_goal_condition(tmp_path):
    """A bare string entry in goal.conditions is tolerated and skipped.

    ``GoalConditionsYAML.conditions`` allows ``str`` entries (e.g. hand-written
    comments or placeholders). The conversion loop drops non-dict entries, so
    the resulting ``GoalConditions`` contains only the dict-derived conditions.
    """
    from fortress_engine.entities.loader import EntityLoader

    base = tmp_path / "string_cond_world"
    _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
    (base / "episodes").mkdir(parents=True)
    _write_yaml(
        base / "episodes" / "ep-01.yaml",
        """\
id: "ep-01"
name: "String Condition"
order: 1
start_anchor: "room_01"
goal:
  conditions:
    - "just a string"
    - type: "flag_is_set"
      params:
        flag: "escaped"
  output: "Win!"
carry_over:
  inventory: []
  flags: []
""",
    )
    (base / "shared").mkdir(parents=True)
    (base / "ep-01").mkdir(parents=True)
    for d in ["rooms", "items", "npcs", "macros", "actions"]:
        (base / "ep-01" / d).mkdir(parents=True)
    _write_yaml(
        base / "ep-01" / "rooms" / "room_01.yaml",
        "entity_id: room_01\ntype: room\nname: Start\n",
    )

    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()

    assert len(episodes) == 1
    conds = episodes[0].goal.conditions
    # The bare string was skipped; only the atomic dict condition survives.
    assert len(conds) == 1
    assert isinstance(conds[0], GoalCondition)
    assert conds[0].type == "flag_is_set"
    assert conds[0].params == {"flag": "escaped"}
    assert all(isinstance(c, (GoalCondition, dict)) for c in conds)
