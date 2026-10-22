"""Fixture world builder for the autoplay runtime tests.

``build_solver_happy`` writes a complete, completable YAML world under
``tmp_path`` and returns the world directory. The helpers render the world's
episode, rooms, macro edges, actions and vocabulary files.
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
    when present, so worlds with base fields only render
    unchanged.
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

    ``speech_markers`` defaults to ``["diciendo"]``; a world may override it
    to use its own speech markers.
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


@pytest.fixture
def solver_happy(tmp_path: Path) -> Path:
    """Build and return the solver-happy world directory."""
    return build_solver_happy(tmp_path)
