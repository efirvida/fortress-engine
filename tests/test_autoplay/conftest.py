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


def _room_yaml(entity_id: str, name: str, description: str | None = None) -> str:
    base = f'entity_id: "{entity_id}"\ntype: "room"\nname: "{name}"\n'
    if description is not None:
        base += f"components:\n  description: \"{description}\"\n"
    return base


def _macro_edges_yaml(edges: list[dict]) -> str:
    """Render a macros file from dicts of YAML fields.

    Optional gate fields (requires_item/forbids_item/requires_flag/
    forbids_flag/requires_text/question) and ``open`` are rendered only
    when present, so existing audit worlds (base fields only) are
    byte-unchanged.
    """
    lines = []
    for edge in edges:
        lines.append(f'- macro_edge_id: "{edge["id"]}"')
        lines.append(f'  from_anchor: "{edge["from"]}"')
        lines.append(f'  to_anchor: "{edge["to"]}"')
        lines.append(f'  direction: "{edge["direction"]}"')
        lines.append(f'  passage_name: "{edge["passage"]}"')
        for field in (
            "requires_item",
            "forbids_item",
            "requires_flag",
            "forbids_flag",
            "requires_text",
            "question",
        ):
            if field in edge:
                lines.append(f'  {field}: "{edge[field]}"')
        if "open" in edge:
            lines.append(f"  open: {str(edge['open']).lower()}")
    return "\n".join(lines) + "\n"


def _op_yaml(op: dict) -> str:
    """Render one operator dict as indented YAML lines."""
    lines = [f"    - type: {op['type']}"]
    for key, value in op.items():
        if key == "type":
            continue
        if isinstance(value, bool):
            lines.append(f"      {key}: {str(value).lower()}")
        else:
            lines.append(f'      {key}: "{value}"')
    return "\n".join(lines)


def _actions_yaml(actions: list[dict]) -> str:
    """Render an actions (hyper edge) file from dicts."""
    lines = []
    for action in actions:
        lines.append(f'- hyper_edge_id: "{action["id"]}"')
        lines.append(f'  name: "{action["name"]}"')
        lines.append(f"  priority: {action.get('priority', 10)}")
        lines.append("  clique:")
        lines.append('    subject: "player"')
        lines.append(f'    verb: "{action["verb"]}"')
        target = action.get("target")
        if target is None:
            lines.append("    target: null")
        else:
            lines.append(f'    target: "{target}"')
        if action["operators"]:
            lines.append("  operators:")
            for op in action["operators"]:
                lines.append(_op_yaml(op))
        else:
            lines.append("  operators: []")
        lines.append(f'  output: "{action.get("output", "")}"')
    return "\n".join(lines) + "\n"


def _vocabulary_yaml(
    verbs: list[str], speech_markers: list[str] | None = None
) -> str:
    """Render shared/vocabulary.yaml with the world's verbs and movement verb.

    ``speech_markers`` defaults to ``["diciendo"]``; solver_kb overrides it
    so the speech-marker seam (not the hardcoded literal) is exercised.
    """
    markers = speech_markers or ["diciendo"]
    verb_lines = "\n".join(f'  {v}: ["{v}"]' for v in verbs)
    markers_line = ", ".join(f'"{m}"' for m in markers)
    return (
        'language: "es"\n'
        "verbs:\n"
        f"{verb_lines}\n"
        "stopwords: [\"el\", \"la\", \"los\", \"las\", \"un\", \"una\", "
        "\"al\", \"del\", \"por\", \"the\", \"a\", \"to\", \"of\", \"an\"]\n"
        "prepositions:\n"
        "  instrument: []\n"
        "  recipient: []\n"
        f"speech_markers: [{markers_line}]\n"
        'speech_verbs: ["decir", "responder"]\n'
        'movement_verbs: ["ir"]\n'
        "messages: {}\n"
        "system_commands:\n"
        '  save: ["save"]\n'
    )


def _mirar_action() -> dict:
    """Room-description action (mirar with no target → {description})."""
    return {
        "id": "he_mirar",
        "name": "Mirar",
        "priority": 0,
        "verb": "mirar",
        "target": None,
        "operators": [],
        "output": "{description}",
    }


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


# ===================================================================
# Stage B solver fixture worlds (explorer-solver / chunk 1)
#
# Each world passes GraphAudit with zero ERROR findings so the solver
# (chunk 2) can run against it.  All passages are bidirectional so the
# explorer/solver can navigate back through discovered crossings.
# ===================================================================

_TAKE_RUSTY_KEY = {
    "id": "he_take_key",
    "name": "Coger llave",
    "verb": "coger",
    "target": "rusty_key",
    "operators": [
        {
            "type": "TRANSFER",
            "entity": "rusty_key",
            "from_container": "alpha",
            "to_container": "hero",
        }
    ],
    "output": "Tomas la llave.",
}


def build_solver_happy(tmp_path: Path) -> Path:
    """Completable world with an item gate, a text gate, a flag gate and a
    goal flag — the deterministic solver-happy walkthrough (chunk 2):

    take rusty_key -> go north -> go east (open sesame) -> pull lever ->
    go south -> finish.
    """
    world = tmp_path / "solver_happy"
    _write(world / "world.yaml", 'world_id: "solver_happy"\nname: "Happy"\n')
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
    _write(
        world / "episode-01" / "rooms" / "alpha.yaml",
        _room_yaml(
            "alpha", "Alpha", "A dark hall. A gate to the north blocks the way."
        ),
    )
    _write(
        world / "episode-01" / "rooms" / "beta.yaml",
        _room_yaml(
            "beta", "Beta", "A corridor. An east gate stands shut."
        ),
    )
    _write(
        world / "episode-01" / "rooms" / "gamma.yaml",
        _room_yaml(
            "gamma", "Gamma", "A chamber. A south gate leads onward."
        ),
    )
    _write(
        world / "episode-01" / "rooms" / "delta.yaml",
        _room_yaml("delta", "Delta", "The inner sanctum."),
    )
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "alpha_to_beta", "from": "alpha", "to": "beta",
                 "direction": "bidirectional", "passage": "north",
                 "requires_item": "rusty_key"},
                {"id": "beta_to_gamma", "from": "beta", "to": "gamma",
                 "direction": "bidirectional", "passage": "east",
                 "requires_text": "open sesame", "open": False},
                {"id": "gamma_to_delta", "from": "gamma", "to": "delta",
                 "direction": "bidirectional", "passage": "south",
                 "requires_flag": "door_open"},
            ]
        ),
    )
    _write(
        world / "episode-01" / "items" / "rusty_key.yaml",
        _entity_yaml("rusty_key", "item", "Rusty Key", "alpha"),
    )
    _write(
        world / "episode-01" / "npcs" / "lever_obj.yaml",
        _entity_yaml("lever_obj", "npc", "Lever Handle", "gamma"),
    )
    _write(
        world / "episode-01" / "npcs" / "goal_shrine.yaml",
        _entity_yaml("goal_shrine", "npc", "Goal Shrine", "delta"),
    )
    _write(
        world / "episode-01" / "actions" / "actions.yaml",
        _actions_yaml(
            [
                _mirar_action(),
                _TAKE_RUSTY_KEY,
                {
                    "id": "he_lever",
                    "name": "Pull lever",
                    "verb": "lever",
                    "target": "lever_obj",
                    "operators": [
                        {"type": "FLAG", "flag": "door_open", "value": True}
                    ],
                    "output": "Tiras de la palanca.",
                },
                {
                    "id": "he_finish",
                    "name": "Finish quest",
                    "verb": "finish",
                    "target": "goal_shrine",
                    "operators": [
                        {"type": "FLAG", "flag": "quest_done", "value": True}
                    ],
                    "output": "Mision completada.",
                },
            ]
        ),
    )
    _write(
        world / "shared" / "player.yaml",
        _entity_yaml("hero", "player", "Hero", None),
    )
    _write(
        world / "shared" / "vocabulary.yaml",
        _vocabulary_yaml(["coger", "mirar", "lever", "finish", "ir"]),
    )
    return world


def build_solver_kb(tmp_path: Path) -> Path:
    """Text-gated world whose answer is supplied ONLY through
    ``episodes/answers.yaml`` (curated KB).  The loader must skip that file
    (filename-exact ``answers.yaml`` exemption) so the world still loads; the
    speech marker ``hablando`` (not the hardcoded literal) opens the gate.
    """
    world = tmp_path / "solver_kb"
    _write(world / "world.yaml", 'world_id: "solver_kb"\nname: "KB"\n')
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
    _write(
        world / "episode-01" / "rooms" / "alpha.yaml",
        _room_yaml(
            "alpha", "Alpha", "A doorway to the north."
        ),
    )
    _write(
        world / "episode-01" / "rooms" / "beta.yaml",
        _room_yaml("beta", "Beta", "The goal chamber."),
    )
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "alpha_to_beta", "from": "alpha", "to": "beta",
                 "direction": "bidirectional", "passage": "north",
                 "requires_text": "open sesame", "open": False},
            ]
        ),
    )
    _write(
        world / "episode-01" / "npcs" / "goal_shrine.yaml",
        _entity_yaml("goal_shrine", "npc", "Goal Shrine", "beta"),
    )
    _write(
        world / "episode-01" / "actions" / "actions.yaml",
        _actions_yaml(
            [
                _mirar_action(),
                {
                    "id": "he_finish",
                    "name": "Finish quest",
                    "verb": "finish",
                    "target": "goal_shrine",
                    "operators": [
                        {"type": "FLAG", "flag": "quest_done", "value": True}
                    ],
                    "output": "Mision completada.",
                },
            ]
        ),
    )
    _write(
        world / "shared" / "player.yaml",
        _entity_yaml("hero", "player", "Hero", None),
    )
    _write(
        world / "shared" / "vocabulary.yaml",
        _vocabulary_yaml(["mirar", "finish", "ir"], speech_markers=["hablando"]),
    )
    _write(
        world / "episodes" / "answers.yaml",
        "episode-01:\n"
        "  passwords:\n"
        '    - "open sesame"\n'
        "  riddle_answers:\n"
        '    - "el enigma del guardian"\n',
    )
    return world


def build_solver_retrieve(tmp_path: Path) -> Path:
    """Completable world whose key item lives in a far room (zeta, off the
    main path, AFTER gamma alphabetically) while the gate sits at gamma —
    the key-retrieval backtracking fires because gamma sorts BEFORE zeta
    in the BFS queue (key room visited AFTER the gate room)."""
    world = tmp_path / "solver_retrieve"
    _write(world / "world.yaml", 'world_id: "solver_retrieve"\nname: "Retrieve"\n')
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
    _write(
        world / "episode-01" / "rooms" / "alpha.yaml",
        _room_yaml("alpha", "Alpha", "A gate to the north."),
    )
    _write(
        world / "episode-01" / "rooms" / "beta.yaml",
        _room_yaml(
            "beta", "Beta", "An east passage and a south passage."
        ),
    )
    _write(
        world / "episode-01" / "rooms" / "gamma.yaml",
        _room_yaml(
            "gamma", "Gamma", "A locked secret gate."
        ),
    )
    _write(
        world / "episode-01" / "rooms" / "delta.yaml",
        _room_yaml("delta", "Delta", "The goal chamber."),
    )
    _write(
        world / "episode-01" / "rooms" / "zeta.yaml",
        _room_yaml("zeta", "Zeta", "A store room."),
    )
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "alpha_to_beta", "from": "alpha", "to": "beta",
                 "direction": "bidirectional", "passage": "north"},
                {"id": "beta_to_gamma", "from": "beta", "to": "gamma",
                 "direction": "bidirectional", "passage": "east"},
                {"id": "beta_to_zeta", "from": "beta", "to": "zeta",
                 "direction": "bidirectional", "passage": "south"},
                {"id": "gamma_to_delta", "from": "gamma", "to": "delta",
                 "direction": "bidirectional", "passage": "secret",
                 "requires_item": "master_key"},
            ]
        ),
    )
    _write(
        world / "episode-01" / "items" / "master_key.yaml",
        _entity_yaml("master_key", "item", "Master Key", "zeta"),
    )
    _write(
        world / "episode-01" / "npcs" / "goal_shrine.yaml",
        _entity_yaml("goal_shrine", "npc", "Goal Shrine", "delta"),
    )
    _write(
        world / "episode-01" / "actions" / "actions.yaml",
        _actions_yaml(
            [
                _mirar_action(),
                {
                    "id": "he_take_key",
                    "name": "Coger llave",
                    "verb": "coger",
                    "target": "master_key",
                    "operators": [
                        {
                            "type": "TRANSFER",
                            "entity": "master_key",
                            "from_container": "zeta",
                            "to_container": "hero",
                        }
                    ],
                    "output": "Tomas la llave maestra.",
                },
                {
                    "id": "he_finish",
                    "name": "Finish quest",
                    "verb": "finish",
                    "target": "goal_shrine",
                    "operators": [
                        {"type": "FLAG", "flag": "quest_done", "value": True}
                    ],
                    "output": "Mision completada.",
                },
            ]
        ),
    )
    _write(
        world / "shared" / "player.yaml",
        _entity_yaml("hero", "player", "Hero", None),
    )
    _write(
        world / "shared" / "vocabulary.yaml",
        _vocabulary_yaml(["coger", "mirar", "finish", "ir"]),
    )
    return world


def build_solver_unsolvable(tmp_path: Path) -> Path:
    """Unsolvable world: the item gate needs ``gold_ingot`` which lives in an
    audit-unreachable room (``vault``/``vault_side`` cluster) and the flag gate
    needs ``never_flag`` which no hyper edge ever sets.  The goal (hero in
    ``delta``) can therefore never be reached.  Chunk 2 must diagnose exactly
    ``item_unreachable`` + ``flag_never_set``.
    """
    world = tmp_path / "solver_unsolvable"
    _write(world / "world.yaml", 'world_id: "solver_unsolvable"\nname: "Unsolvable"\n')
    _write(
        world / "episodes" / "episode-01.yaml",
        _episode_yaml(
            "episode-01",
            "alpha",
            "    - type: entity_in_room\n"
            "      params:\n"
            "        entity: hero\n"
            "        room: delta\n",
        ),
    )
    for room, desc in (
        ("alpha", "A gate to the north."),
        ("beta", "An east passage and a west passage."),
        ("gamma", "A locked south gate."),
        ("delta", "The goal chamber."),
        ("epsilon", "A sealed chamber."),
        ("vault", "A hidden vault."),
        ("vault_side", "A vault antechamber."),
    ):
        _write(
            world / "episode-01" / "rooms" / f"{room}.yaml",
            _room_yaml(room, room.title(), desc),
        )
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        _macro_edges_yaml(
            [
                {"id": "alpha_to_beta", "from": "alpha", "to": "beta",
                 "direction": "bidirectional", "passage": "north"},
                {"id": "beta_to_gamma", "from": "beta", "to": "gamma",
                 "direction": "bidirectional", "passage": "east"},
                {"id": "beta_to_epsilon", "from": "beta", "to": "epsilon",
                 "direction": "bidirectional", "passage": "west",
                 "requires_flag": "never_flag"},
                {"id": "gamma_to_delta", "from": "gamma", "to": "delta",
                 "direction": "bidirectional", "passage": "south",
                 "requires_item": "gold_ingot"},
                {"id": "vault_path", "from": "vault", "to": "vault_side",
                 "direction": "bidirectional", "passage": "path"},
            ]
        ),
    )
    _write(
        world / "episode-01" / "items" / "gold_ingot.yaml",
        _entity_yaml("gold_ingot", "item", "Gold Ingot", "vault"),
    )
    _write(
        world / "episode-01" / "actions" / "actions.yaml",
        _actions_yaml([_mirar_action()]),
    )
    _write(
        world / "shared" / "player.yaml",
        _entity_yaml("hero", "player", "Hero", None),
    )
    _write(
        world / "shared" / "vocabulary.yaml",
        _vocabulary_yaml(["mirar", "ir"]),
    )
    return world


@pytest.fixture
def solver_happy(tmp_path: Path) -> Path:
    """Build and return the solver-happy world directory."""
    return build_solver_happy(tmp_path)


@pytest.fixture
def solver_kb(tmp_path: Path) -> Path:
    """Build and return the solver-kb world directory."""
    return build_solver_kb(tmp_path)


@pytest.fixture
def solver_retrieve(tmp_path: Path) -> Path:
    """Build and return the solver-retrieve world directory."""
    return build_solver_retrieve(tmp_path)


@pytest.fixture
def solver_unsolvable(tmp_path: Path) -> Path:
    """Build and return the solver-unsolvable world directory."""
    return build_solver_unsolvable(tmp_path)
