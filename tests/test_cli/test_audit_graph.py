"""Tests for the audit-graph subcommand.

RED phase: ``audit-graph`` is not registered in ``cli/main.py`` yet.  Mirrors
``test_validate.py`` conventions: patch ``sys.argv``, assert ``SystemExit``
codes, assert stdout/stderr content.  Exit contract: 0 = no ERROR findings,
1 = any ERROR finding, 2 = usage / missing / malformed world / unknown
episode.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from fortress_engine.cli.main import main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _episode(episode_id: str, start_anchor: str, goal_conditions: str = "") -> str:
    conditions = (
        f"  conditions:\n{goal_conditions}\n"
        if goal_conditions
        else "  conditions: []\n"
    )
    return (
        f"id: {episode_id}\n"
        "name: Episode\n"
        "order: 1\n"
        "requires: []\n"
        f"start_anchor: {start_anchor}\n"
        "goal:\n"
        f"{conditions}"
        "  output: ''\n"
        "  side_effects: []\n"
        "carry_over:\n"
        "  inventory: []\n"
        "  flags: []\n"
    )


def _room(room_id: str) -> str:
    return f'entity_id: "{room_id}"\ntype: "room"\nname: "{room_id.title()}"\n'


def _world_base(world_path: Path, world_id: str) -> None:
    _write(world_path / "world.yaml", f'world_id: "{world_id}"\nname: "{world_id.title()}"\n')


def build_clean_world(tmp_path: Path) -> Path:
    """alpha <-> beta, zero findings."""
    world = tmp_path / "clean"
    _world_base(world, "clean")
    _write(world / "episodes" / "episode-01.yaml", _episode("episode-01", "alpha"))
    _write(world / "episode-01" / "rooms" / "alpha.yaml", _room("alpha"))
    _write(world / "episode-01" / "rooms" / "beta.yaml", _room("beta"))
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        '- macro_edge_id: "alpha_to_beta"\n'
        '  from_anchor: "alpha"\n'
        '  to_anchor: "beta"\n'
        '  direction: "bidirectional"\n'
        '  passage_name: "north"\n',
    )
    return world


def build_broken_world(tmp_path: Path) -> Path:
    """start_anchor missing -> ERROR findings."""
    world = tmp_path / "broken"
    _world_base(world, "broken")
    _write(world / "episodes" / "episode-01.yaml", _episode("episode-01", "ghost"))
    _write(world / "episode-01" / "rooms" / "cell.yaml", _room("cell"))
    return world


def build_two_episode_world(tmp_path: Path) -> Path:
    """episode-01 clean; episode-02 broken (missing start anchor)."""
    world = tmp_path / "two_episodes"
    _world_base(world, "two")
    _write(world / "episodes" / "episode-01.yaml", _episode("episode-01", "alpha"))
    _write(world / "episodes" / "episode-02.yaml", _episode("episode-02", "ghost"))
    _write(world / "episode-01" / "rooms" / "alpha.yaml", _room("alpha"))
    _write(world / "episode-01" / "rooms" / "beta.yaml", _room("beta"))
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        '- macro_edge_id: "alpha_to_beta"\n'
        '  from_anchor: "alpha"\n'
        '  to_anchor: "beta"\n'
        '  direction: "bidirectional"\n'
        '  passage_name: "north"\n',
    )
    _write(world / "episode-02" / "rooms" / "cell.yaml", _room("cell"))
    return world


def build_limbo_world(tmp_path: Path) -> Path:
    """One INFO finding (entity_limbo_at_load)."""
    world = tmp_path / "limbo"
    _world_base(world, "limbo")
    _write(world / "episodes" / "episode-01.yaml", _episode("episode-01", "alpha"))
    _write(world / "episode-01" / "rooms" / "alpha.yaml", _room("alpha"))
    _write(
        world / "episode-01" / "items" / "lost_ring.yaml",
        'entity_id: "lost_ring"\ntype: "item"\nname: "Lost Ring"\nspatial_anchor: null\n',
    )
    return world


def _run_cli(args: list[str], capsys) -> int:
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["fortress-engine", *args]):
            main()
    captured = capsys.readouterr()
    return exc_info.value.code, captured


class TestAuditGraphExitCodes:
    """Exit 0/1/2 contract."""

    def test_clean_world_exits_0(self, tmp_path, capsys):
        world = build_clean_world(tmp_path)
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 0
        assert "No findings." in captured.out

    def test_broken_world_exits_1(self, tmp_path, capsys):
        world = build_broken_world(tmp_path)
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 1
        assert "start_anchor_missing" in captured.out

    def test_missing_world_exits_2(self, tmp_path, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        code, captured = _run_cli(["audit-graph", str(empty)], capsys)
        assert code == 2
        assert "world.yaml" in captured.err

    def test_malformed_world_yaml_exits_2(self, tmp_path, capsys):
        world = tmp_path / "malformed"
        _write(world / "world.yaml", "world_id: [unclosed\n")
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 2
        assert captured.err.strip() != ""

    def test_malformed_episode_yaml_exits_2(self, tmp_path, capsys):
        world = tmp_path / "bad_episode"
        _world_base(world, "bad")
        _write(world / "episodes" / "episode-01.yaml", "id: [unclosed\n")
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 2
        assert captured.err.strip() != ""

    def test_unknown_episode_exits_2(self, tmp_path, capsys):
        world = build_clean_world(tmp_path)
        code, captured = _run_cli(
            ["audit-graph", str(world), "--episode", "episode-99"], capsys
        )
        assert code == 2
        assert "episode-99" in captured.err

    def test_missing_world_path_usage_exits_2(self, capsys):
        code, _ = _run_cli(["audit-graph"], capsys)
        assert code == 2

    def test_audit_graph_help_exits_0(self, capsys):
        code, captured = _run_cli(["audit-graph", "--help"], capsys)
        assert code == 0
        assert "world_path" in captured.out

    def test_empty_world_without_episodes_exits_2(self, tmp_path, capsys):
        world = tmp_path / "no_episodes"
        _world_base(world, "empty")
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 2
        assert "episode" in captured.err.lower()


class TestAuditGraphEpisodeSelection:
    """Default first loaded episode vs explicit --episode."""

    def test_default_episode_is_first_loaded(self, tmp_path, capsys):
        world = build_two_episode_world(tmp_path)
        code, captured = _run_cli(
            ["audit-graph", str(world), "--json"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-01"

    def test_explicit_episode_is_selected(self, tmp_path, capsys):
        world = build_two_episode_world(tmp_path)
        code, captured = _run_cli(
            ["audit-graph", str(world), "--episode", "episode-02", "--json"],
            capsys,
        )
        assert code == 1
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-02"
        assert any(
            f["category"] == "start_anchor_missing" for f in payload["findings"]
        )


class TestAuditGraphOutput:
    """Human grouping, INFO filtering, deterministic JSON."""

    def test_human_output_grouped_by_severity(self, tmp_path, capsys):
        world = build_broken_world(tmp_path)
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 1
        lines = captured.out.splitlines()
        assert lines[0] == "ERROR (2)"
        assert lines[1].startswith("  [isolated_room] ")
        assert lines[2].startswith("  [start_anchor_missing] ")
        assert lines[3] == "WARN (1)"
        assert lines[4].startswith("  [unreachable_room] ")

    def test_info_hidden_without_include_info(self, tmp_path, capsys):
        world = build_limbo_world(tmp_path)
        code, captured = _run_cli(["audit-graph", str(world)], capsys)
        assert code == 0
        assert "entity_limbo_at_load" not in captured.out
        assert "No findings." in captured.out

    def test_info_shown_with_include_info(self, tmp_path, capsys):
        world = build_limbo_world(tmp_path)
        code, captured = _run_cli(
            ["audit-graph", str(world), "--include-info"], capsys
        )
        assert code == 0
        assert "INFO (1)" in captured.out
        assert "entity_limbo_at_load" in captured.out

    def test_json_omits_info_without_include_info(self, tmp_path, capsys):
        world = build_limbo_world(tmp_path)
        code, captured = _run_cli(["audit-graph", str(world), "--json"], capsys)
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["findings"] == []

    def test_json_includes_info_with_include_info(self, tmp_path, capsys):
        world = build_limbo_world(tmp_path)
        code, captured = _run_cli(
            ["audit-graph", str(world), "--json", "--include-info"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert [f["category"] for f in payload["findings"]] == [
            "entity_limbo_at_load"
        ]

    def test_json_is_deterministic_sorted_keys(self, tmp_path, capsys):
        world = build_broken_world(tmp_path)
        _, first = _run_cli(["audit-graph", str(world), "--json"], capsys)
        _, second = _run_cli(["audit-graph", str(world), "--json"], capsys)
        assert first.out == second.out
        parsed = json.loads(first.out)
        assert first.out.rstrip("\n") == json.dumps(parsed, sort_keys=True)
        assert "reachable_rooms" in parsed
        assert "unreachable_rooms" in parsed
        assert "passages" in parsed
        assert "findings" in parsed
        assert parsed["findings"][0]["severity"] == "ERROR"

    def test_json_episode_and_room_sets(self, tmp_path, capsys):
        world = build_clean_world(tmp_path)
        code, captured = _run_cli(["audit-graph", str(world), "--json"], capsys)
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-01"
        assert payload["declared_rooms"] == ["alpha", "beta"]
        assert payload["reachable_rooms"] == ["alpha", "beta"]
        assert payload["unreachable_rooms"] == []
        assert len(payload["passages"]) == 2
