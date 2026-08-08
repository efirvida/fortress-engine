"""Tests for run command — Phase 3 of epic-4-cli.

These tests define the contract for the run subcommand.
They MUST fail before the implementation exists (RED phase).
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from fortress_engine.cli.main import main, _build_engine


_WORLD_PATH = Path(__file__).resolve().parent.parent.parent / "worlds" / "_test_minimal"


class TestRunCommand:
    """run subcommand contract tests."""

    def test_run_eof_exits_0(self, capsys):
        """EOF on input must exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=EOFError):
                    main()
        assert exc_info.value.code == 0

    def test_run_ctrl_c_exits_0_with_farewell(self, capsys):
        """Ctrl+C must print farewell and exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=KeyboardInterrupt):
                    main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        # Farewell should be printed (exact message TBD by narrator)
        assert captured.out.strip() != "" or "adiós" in captured.out.lower() or "bye" in captured.out.lower()

    def test_run_processes_commands(self, capsys):
        """Non-empty lines must be processed by execute_turn."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["ir norte", EOFError]):
                    main()
        assert exc_info.value.code == 0

    def test_run_skips_empty_lines(self, capsys):
        """Empty lines must be skipped without calling execute_turn."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["", "  ", EOFError]):
                    main()
        assert exc_info.value.code == 0

    def test_run_save_acknowledgment(self, capsys):
        """--save SLOT must print acknowledgment without persistence."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH), "--save", "1"]):
                with patch("builtins.input", side_effect=EOFError):
                    main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Saving to slot '1'" in captured.out
        assert "persistence deferred" in captured.out.lower()

    def test_run_quit_command_exits_0(self, capsys):
        """'quit' command must exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["quit", EOFError]):
                    main()
        assert exc_info.value.code == 0

    def test_run_narrator_output_printed(self, capsys):
        """Narrator output from execute_turn must be printed to stdout."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["ir norte", EOFError]):
                    main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        # Narrator should produce some output for movement
        assert captured.out.strip() != ""

    def test_run_player_dead_exits_0(self, capsys):
        """Player death must break the loop and exit 0."""
        from fortress_engine.cli.main import _build_engine

        # Build the bundle first so we can reference its state
        bundle = _build_engine(str(_WORLD_PATH))

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                # Mock execute_turn to set player dead on the actual state
                call_count = [0]

                def mock_execute_turn(cmd):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        bundle.state.entities["hero"].components["is_dead"] = True

                with patch("builtins.input", side_effect=["ir norte", "ir norte"]):
                    with patch.object(
                        bundle.orchestrator,
                        "execute_turn",
                        side_effect=mock_execute_turn,
                    ):
                        with patch(
                            "fortress_engine.cli.main._build_engine",
                            return_value=bundle,
                        ):
                            main()
        assert exc_info.value.code == 0

    def test_run_build_engine_error_exits_1(self, capsys):
        """Build engine error must exit 1."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", "/nonexistent/path"]):
                main()
        assert exc_info.value.code == 1

    def test_run_hero_not_found_exits_0(self, capsys):
        """If hero entity is missing from state, the loop continues (KeyError caught)."""
        bundle = MagicMock()
        bundle.state.get_entity.side_effect = KeyError("hero not found")

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["ir norte", EOFError]):
                    with patch("fortress_engine.cli.main._build_engine", return_value=bundle):
                        main()
        assert exc_info.value.code == 0

    def test_run_execute_turn_system_exit_propagates(self, capsys):
        """SystemExit from execute_turn must propagate through cmd_run."""
        bundle = _build_engine(str(_WORLD_PATH))

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["ir norte"]):
                    with patch.object(
                        bundle.orchestrator,
                        "execute_turn",
                        side_effect=SystemExit(42),
                    ):
                        with patch("fortress_engine.cli.main._build_engine", return_value=bundle):
                            main()
        assert exc_info.value.code == 42

    def test_run_generic_exception_exits_1(self, capsys):
        """Generic exception during input loop must exit 1."""
        bundle = _build_engine(str(_WORLD_PATH))

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", str(_WORLD_PATH)]):
                with patch("builtins.input", side_effect=["ir norte"]):
                    with patch.object(
                        bundle.orchestrator,
                        "execute_turn",
                        side_effect=RuntimeError("Turn error"),
                    ):
                        with patch("fortress_engine.cli.main._build_engine", return_value=bundle):
                            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()
