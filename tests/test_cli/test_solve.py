"""Tests for the solve subcommand.

Exit contract: 0 = completable, 1 = not completable (diagnosis),
2 = usage / missing / malformed world / unknown episode.

Mirrors ``test_audit_graph.py`` conventions: patch ``sys.argv``, assert
``SystemExit`` codes, assert stdout/stderr content.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from fortress_engine.cli.main import main
from tests.test_autoplay.conftest import build_solver_happy, build_solver_unsolvable


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_cli(args: list[str], capsys) -> tuple[int, object]:
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["fortress-engine", *args]):
            main()
    captured = capsys.readouterr()
    return exc_info.value.code, captured


# ===================================================================
# Exit code contract
# ===================================================================


class TestSolveExitCodes:
    """Exit 0/1/2 contract."""

    def test_solvable_world_exits_0(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 0
        assert "SOLVABLE" in captured.out

    def test_unsolvable_world_exits_1(self, tmp_path, capsys):
        world = build_solver_unsolvable(tmp_path)
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 1
        assert "NOT SOLVABLE" in captured.out

    def test_missing_world_exits_2(self, tmp_path, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        code, captured = _run_cli(["solve", str(empty)], capsys)
        assert code == 2
        assert "world.yaml" in captured.err

    def test_unknown_episode_exits_2(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(
            ["solve", str(world), "--episode", "episode-99"], capsys
        )
        assert code == 2
        assert "episode-99" in captured.err

    def test_missing_world_path_exits_2(self, capsys):
        code, _ = _run_cli(["solve"], capsys)
        assert code == 2

    def test_solve_help_exits_0(self, capsys):
        code, captured = _run_cli(["solve", "--help"], capsys)
        assert code == 0
        assert "world_path" in captured.out

    def test_no_episodes_world_exits_2(self, tmp_path, capsys):
        world = tmp_path / "no_episodes"
        _write(world / "world.yaml", 'world_id: "empty"\nname: "Empty"\n')
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 2
        assert "episode" in captured.err.lower()

    def test_static_errors_verdict_exits_1(self, tmp_path, capsys):
        from tests.test_autoplay.conftest import build_audit_broken

        world = build_audit_broken(tmp_path)
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 1

    def test_static_errors_human_output(self, tmp_path, capsys):
        from tests.test_autoplay.conftest import build_audit_broken

        world = build_audit_broken(tmp_path)
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 1
        assert "Static Errors:" in captured.out


# ===================================================================
# Episode selection
# ===================================================================


class TestSolveEpisodeSelection:
    """Default first loaded episode vs explicit --episode."""

    def test_default_episode_is_first_loaded(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(["solve", str(world), "--json"], capsys)
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-01"

    def test_explicit_episode_is_selected(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(
            ["solve", str(world), "--episode", "episode-01", "--json"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-01"

    def test_two_episode_world_explicit_second(self, tmp_path, capsys):
        from tests.test_autoplay.conftest import (
            _episode_yaml, _macro_edges_yaml, _room_yaml, _vocabulary_yaml,
            _entity_yaml, _write, _actions_yaml, _mirar_action,
        )
        world = tmp_path / "two_eps"
        _write(world / "world.yaml", 'world_id: "two"\nname: "Two Eps"\n')
        _write(world / "episodes" / "episode-01.yaml", _episode_yaml(
            "episode-01", "alpha",
            "    - type: flag_is_set\n      params:\n        flag: done\n",
        ))
        _write(world / "episodes" / "episode-02.yaml", _episode_yaml(
            "episode-02", "alpha",
            "    - type: flag_is_set\n      params:\n        flag: done2\n",
        ))
        _write(world / "episode-01" / "rooms" / "alpha.yaml", _room_yaml("alpha", "Alpha"))
        _write(world / "episode-02" / "rooms" / "alpha.yaml", _room_yaml("alpha", "Alpha"))
        for ep in ("episode-01", "episode-02"):
            _write(world / ep / "items" / "flag_item.yaml",
                   _entity_yaml("flag_item", "item", "Flag Item", "alpha"))
            _write(world / ep / "actions" / "actions.yaml", _actions_yaml([
                _mirar_action(),
                {"id": "set_flag", "name": "Set flag", "verb": "set",
                 "target": "flag_item", "operators": [
                     {"type": "FLAG", "flag": "done" if ep == "episode-01" else "done2", "value": True}
                 ], "output": "Flag set."},
            ]))
        _write(world / "shared" / "player.yaml", _entity_yaml("hero", "player", "Hero", None))
        _write(world / "shared" / "vocabulary.yaml", _vocabulary_yaml(["mirar", "set", "ir"]))
        code, captured = _run_cli(
            ["solve", str(world), "--episode", "episode-02", "--json"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-02"


# ===================================================================
# Output format
# ===================================================================


class TestSolveOutput:
    """Human grouping, deterministic JSON."""

    def test_human_output_shows_verdict_and_walkthrough(
        self, tmp_path, capsys,
    ):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 0
        assert "Verdict: SOLVABLE" in captured.out
        assert "Walkthrough:" in captured.out

    def test_human_output_shows_diagnosis_for_unsolvable(
        self, tmp_path, capsys,
    ):
        world = build_solver_unsolvable(tmp_path)
        code, captured = _run_cli(["solve", str(world)], capsys)
        assert code == 1
        assert "Verdict: NOT SOLVABLE" in captured.out
        assert "Unsatisfiable Gates:" in captured.out

    def test_json_is_deterministic(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        _, first = _run_cli(["solve", str(world), "--json"], capsys)
        _, second = _run_cli(["solve", str(world), "--json"], capsys)
        assert first.out == second.out
        parsed = json.loads(first.out)
        assert first.out.rstrip("\n") == json.dumps(parsed, sort_keys=True)

    def test_json_shows_completable_true_for_happy(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(["solve", str(world), "--json"], capsys)
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["completable"] is True
        assert len(payload["walkthrough"]) > 0
        assert payload["total_turns"] > 0

    def test_json_shows_diagnosis_for_unsolvable(self, tmp_path, capsys):
        world = build_solver_unsolvable(tmp_path)
        code, captured = _run_cli(["solve", str(world), "--json"], capsys)
        assert code == 1
        payload = json.loads(captured.out)
        assert payload["completable"] is False
        assert len(payload["unsatisfiable_gates"]) > 0

    def test_json_has_exactly_eight_top_level_keys(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        _, captured = _run_cli(["solve", str(world), "--json"], capsys)
        payload = json.loads(captured.out)
        assert list(payload.keys()) == sorted(payload.keys())
        assert len(payload) == 8


# ===================================================================
# --max-turns guard
# ===================================================================


class TestSolveMaxTurns:
    """The --max-turns flag truncates exploration."""

    def test_max_turns_1_not_completable(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(
            ["solve", str(world), "--max-turns", "1"], capsys
        )
        assert code == 1
        assert "NOT SOLVABLE" in captured.out

    def test_max_turns_low_yields_stuck_rooms(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        _, captured = _run_cli(
            ["solve", str(world), "--max-turns", "1", "--json"], capsys
        )
        payload = json.loads(captured.out)
        assert payload["completable"] is False
        assert len(payload["stuck_rooms"]) > 0


# ===================================================================
# --answers override
# ===================================================================


class TestSolveAnswersOverride:
    """The --answers flag replaces the default curated file."""

    def test_answers_override_is_accepted(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        answers_path = tmp_path / "custom.yaml"
        _write(answers_path, "episode-01:\n  passwords: []\n  riddle_answers: []\n")
        code, captured = _run_cli(
            ["solve", str(world), "--answers", str(answers_path), "--json"],
            capsys,
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["completable"] is True


# ===================================================================
# Integration: minimal world solves
# ===================================================================


class TestSolveIntegration:
    """End-to-end solver runs through loader→audit→solver→verdict."""

    def test_minimal_world_end_to_end(self, tmp_path, capsys):
        world = build_solver_happy(tmp_path)
        code, captured = _run_cli(
            ["solve", str(world), "--json"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["completable"] is True
        assert len(payload["walkthrough"]) > 0
        assert payload["total_turns"] > 0
        assert payload["static_errors"] == []
        assert payload["unsatisfiable_gates"] == []

    def test_minimal_kb_world_end_to_end(self, tmp_path, capsys):
        from tests.test_autoplay.conftest import build_solver_kb

        world = build_solver_kb(tmp_path)
        code, captured = _run_cli(
            ["solve", str(world), "--json"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["completable"] is True

    def test_retrieve_world_end_to_end(self, tmp_path, capsys):
        from tests.test_autoplay.conftest import build_solver_retrieve

        world = build_solver_retrieve(tmp_path)
        code, captured = _run_cli(
            ["solve", str(world), "--json"], capsys
        )
        assert code == 0
        payload = json.loads(captured.out)
        assert payload["completable"] is True


# ===================================================================
# Fortaleza smoke (no pinned findings)
# ===================================================================


class TestSolveFortalezaSmoke:
    """Solve the real worlds/fortaleza episodes — no crash, structured output.
    These are SLOW tests that exercise the full fortaleza world (~10 min each)."""

    @pytest.mark.slow
    def test_fortaleza_episode_01_no_crash(self, capsys):
        world = Path("worlds/fortaleza")
        if not (world / "world.yaml").is_file():
            pytest.skip("worlds/fortaleza not available")
        code, captured = _run_cli(
            ["solve", str(world), "--episode", "episode-01", "--json"], capsys
        )
        assert code in (0, 1)
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-01"
        assert isinstance(payload["completable"], bool)
        assert isinstance(payload["walkthrough"], list)
        assert isinstance(payload["total_turns"], int)
        assert isinstance(payload["stuck_rooms"], list)
        assert isinstance(payload["unsatisfiable_gates"], list)
        assert isinstance(payload["static_errors"], list)

    @pytest.mark.slow
    def test_fortaleza_episode_02_no_crash(self, capsys):
        world = Path("worlds/fortaleza")
        if not (world / "world.yaml").is_file():
            pytest.skip("worlds/fortaleza not available")
        code, captured = _run_cli(
            ["solve", str(world), "--episode", "episode-02", "--json"], capsys
        )
        assert code in (0, 1)
        payload = json.loads(captured.out)
        assert payload["episode"] == "episode-02"
        assert isinstance(payload["completable"], bool)
        assert isinstance(payload["walkthrough"], list)
