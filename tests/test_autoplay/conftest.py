"""Fixture world builders for the autoplay graph audit.

Each builder writes a complete YAML world under ``tmp_path`` and returns the
world directory.  The worlds are designed per the explorer-graph-audit design
document:

- ``audit_happy``: non-Spanish identifiers, zero findings, both BFS branches
  exercised by the other worlds.
- ``audit_broken``: every ERROR condition plus the WARN shapes (orphan,
  unreachable, duplicate passage, self-loop, unknown goal references).
- ``audit_disconnected``: reachable cluster plus an unreachable room with a
  placed entity in it.
- ``audit_limbo``: a placed item with ``spatial_anchor: null`` (legal limbo).
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _episode_yaml(episode_id: str, start_anchor: str, goal_conditions: str) -> str:
    if goal_conditions:
        conditions_block = f"  conditions:\n{goal_conditions}\n"
    else:
        conditions_block = "  conditions: []\n"
    return (
        f"id: {episode_id}\n"
        "name: Episode\n"
        "order: 1\n"
        "requires: []\n"
        f"start_anchor: {start_anchor}\n"
        "goal:\n"
        f"{conditions_block}"
        "  output: ''\n"
        "  side_effects: []\n"
        "carry_over:\n"
        "  inventory: []\n"
        "  flags: []\n"
    )


def _room_yaml(entity_id: str, name: str) -> str:
    return f'entity_id: "{entity_id}"\ntype: "room"\nname: "{name}"\n'


def _macro_edges_yaml(edges: list[dict]) -> str:
    """Render a macros file from dicts of YAML fields."""
    lines = []
    for edge in edges:
        lines.append(f'- macro_edge_id: "{edge["id"]}"')
        lines.append(f'  from_anchor: "{edge["from"]}"')
        lines.append(f'  to_anchor: "{edge["to"]}"')
        lines.append(f'  direction: "{edge["direction"]}"')
        lines.append(f'  passage_name: "{edge["passage"]}"')
    return "\n".join(lines) + "\n"


def _entity_yaml(entity_id: str, etype: str, name: str, anchor: str | None) -> str:
    anchor_line = f"spatial_anchor: \"{anchor}\"\n" if anchor is not None else "spatial_anchor: null\n"
    return (
        f'entity_id: "{entity_id}"\n'
        f'type: "{etype}"\n'
        f'name: "{name}"\n'
        f"{anchor_line}"
    )


def build_audit_happy(tmp_path: Path) -> Path:
    """Zero-finding world using non-Spanish identifiers.

    Goal references are known (``golden_key``/``alpha`` structural, and
    ``quest_done`` is set by a FLAG operator), so no goal finding fires.
    """
    world = tmp_path / "audit_happy"
    _write(world / "world.yaml", 'world_id: "happy"\nname: "Happy World"\n')
    _write(
        world / "episodes" / "episode-01.yaml",
        _episode_yaml(
            "episode-01",
            "alpha",
            "    - type: entity_in_room\n"
            "      params:\n"
            "        entity: golden_key\n"
            "        room: alpha\n"
            "    - type: flag_is_set\n"
            "      params:\n"
            "        flag: quest_done\n",
        ),
    )
    _write(world / "episode-01" / "rooms" / "alpha.yaml", _room_yaml("alpha", "Alpha Room"))
    _write(world / "episode-01" / "rooms" / "beta.yaml", _room_yaml("beta", "Beta Room"))
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "alpha_to_beta", "from": "alpha", "to": "beta",
                 "direction": "bidirectional", "passage": "north"},
            ]
        ),
    )
    _write(
        world / "episode-01" / "items" / "golden_key.yaml",
        _entity_yaml("golden_key", "item", "Golden Key", "alpha"),
    )
    _write(
        world / "episode-01" / "npcs" / "wise_owl.yaml",
        _entity_yaml("wise_owl", "npc", "Wise Owl", "beta"),
    )
    _write(
        world / "episode-01" / "actions" / "quest.yaml",
        "- hyper_edge_id: he_quest_done\n"
        "  name: Finish quest\n"
        "  priority: 10\n"
        "  clique:\n"
        "    subject: player\n"
        "    verb: finish\n"
        "  operators:\n"
        "    - type: FLAG\n"
        "      flag: quest_done\n"
        "      value: true\n"
        "  output: ''\n",
    )
    _write(
        world / "shared" / "player.yaml",
        _entity_yaml("hero", "player", "Hero", None),
    )
    return world


def build_audit_broken(tmp_path: Path) -> Path:
    """World exercising every ERROR condition and several WARN shapes.

    ``start_anchor: ghost`` is missing; rooms ``isolated``, ``orphan`` and
    ``sink`` exist; edges reference the undeclared anchor ``alpha``; the item
    ``trinket`` is anchored to the unknown ``ghost_room``; the goal references
    unknown entity/room/flag values.
    """
    world = tmp_path / "audit_broken"
    _write(world / "world.yaml", 'world_id: "broken"\nname: "Broken World"\n')
    _write(
        world / "episodes" / "episode-01.yaml",
        _episode_yaml(
            "episode-01",
            "ghost",
            "    - type: entity_in_room\n"
            "      params:\n"
            "        entity: ghost_entity\n"
            "        room: ghost_room\n"
            "    - type: flag_is_set\n"
            "      params:\n"
            "        flag: ghost_flag\n",
        ),
    )
    for room in ("isolated", "orphan", "sink"):
        _write(
            world / "episode-01" / "rooms" / f"{room}.yaml",
            _room_yaml(room, room.title()),
        )
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "m_orphan_sink", "from": "orphan", "to": "sink",
                 "direction": "unidirectional", "passage": "path"},
                {"id": "m_alpha_missing", "from": "alpha", "to": "missing",
                 "direction": "unidirectional", "passage": "nowhere"},
                {"id": "m_dup_a", "from": "alpha", "to": "sink",
                 "direction": "unidirectional", "passage": "duplicate_pass"},
                {"id": "m_dup_b", "from": "alpha", "to": "sink",
                 "direction": "unidirectional", "passage": "duplicate_pass"},
                {"id": "m_loop", "from": "alpha", "to": "alpha",
                 "direction": "unidirectional", "passage": "loop"},
            ]
        ),
    )
    _write(
        world / "episode-01" / "items" / "trinket.yaml",
        _entity_yaml("trinket", "item", "Trinket", "ghost_room"),
    )
    return world


def build_audit_disconnected(tmp_path: Path) -> Path:
    """Reachable ``alpha``/``beta`` cluster plus disconnected room ``gamma``.

    ``gamma`` has no edges (isolated AND unreachable) and holds ``gamma_coin``,
    which exercises ``entity_in_unreachable_room`` overlapping
    ``unreachable_room`` and ``isolated_room``.
    """
    world = tmp_path / "audit_disconnected"
    _write(world / "world.yaml", 'world_id: "disconnected"\nname: "Disconnected World"\n')
    _write(
        world / "episodes" / "episode-01.yaml",
        _episode_yaml(
            "episode-01",
            "alpha",
            "    - type: flag_is_set\n"
            "      params:\n"
            "        flag: quest_done\n",
        ),
    )
    for room in ("alpha", "beta", "gamma"):
        _write(
            world / "episode-01" / "rooms" / f"{room}.yaml",
            _room_yaml(room, room.title()),
        )
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "alpha_to_beta", "from": "alpha", "to": "beta",
                 "direction": "bidirectional", "passage": "east"},
            ]
        ),
    )
    _write(
        world / "episode-01" / "items" / "gamma_coin.yaml",
        _entity_yaml("gamma_coin", "item", "Gamma Coin", "gamma"),
    )
    _write(
        world / "episode-01" / "actions" / "quest.yaml",
        "- hyper_edge_id: he_quest_done\n"
        "  name: Finish quest\n"
        "  priority: 10\n"
        "  clique:\n"
        "    subject: player\n"
        "    verb: finish\n"
        "  operators:\n"
        "    - type: FLAG\n"
        "      flag: quest_done\n"
        "      value: true\n"
        "  output: ''\n",
    )
    _write(
        world / "shared" / "player.yaml",
        _entity_yaml("hero", "player", "Hero", None),
    )
    return world


def build_audit_limbo(tmp_path: Path) -> Path:
    """World where a placed item is in limbo at load (null spatial_anchor).

    The start room exists, so the only finding is the INFO
    ``entity_limbo_at_load``; the null anchor must never be reported as
    dangling.
    """
    world = tmp_path / "audit_limbo"
    _write(world / "world.yaml", 'world_id: "limbo"\nname: "Limbo World"\n')
    _write(
        world / "episodes" / "episode-01.yaml",
        _episode_yaml("episode-01", "alpha", ""),
    )
    _write(world / "episode-01" / "rooms" / "alpha.yaml", _room_yaml("alpha", "Alpha Room"))
    _write(
        world / "episode-01" / "items" / "lost_ring.yaml",
        _entity_yaml("lost_ring", "item", "Lost Ring", None),
    )
    return world


@pytest.fixture
def audit_happy(tmp_path: Path) -> Path:
    """Build and return the zero-finding world directory."""
    return build_audit_happy(tmp_path)


@pytest.fixture
def audit_broken(tmp_path: Path) -> Path:
    """Build and return the broken world directory."""
    return build_audit_broken(tmp_path)


@pytest.fixture
def audit_disconnected(tmp_path: Path) -> Path:
    """Build and return the disconnected world directory."""
    return build_audit_disconnected(tmp_path)


@pytest.fixture
def audit_limbo(tmp_path: Path) -> Path:
    """Build and return the limbo world directory."""
    return build_audit_limbo(tmp_path)
