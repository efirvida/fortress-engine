"""Tests for test command — Phase 4 of epic-4-cli.

These tests define the contract for the test subcommand.
They MUST fail before the implementation exists (RED phase).
"""

from pathlib import Path
from unittest.mock import patch
import builtins

import pytest

from fortress_engine.cli.main import main


_WORLD_PATH = Path(__file__).resolve().parent.parent.parent / "worlds" / "_test_minimal"
builtins_open = builtins.open


class TestTestCommand:
    """test subcommand contract tests."""

    def test_walkthrough_achieves_goal_exits_0(self, tmp_path, capsys):
        """Walkthrough that achieves goal must print PASS and exit 0."""
        # Create a walkthrough file
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\nhuir hall\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_walkthrough_misses_goal_exits_1(self, tmp_path, capsys):
        """Walkthrough that misses goal must print FAIL and exit 1."""
        # Create a walkthrough that doesn't achieve the goal
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("mirar\nexaminar\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_test_missing_episode_exits_1(self, tmp_path, capsys):
        """Missing episode must exit 1."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                [
                    "fortress-engine",
                    "test",
                    str(_WORLD_PATH),
                    "--walkthrough",
                    str(walkthrough),
                    "--episode",
                    "nonexistent",
                ],
            ):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "episode" in captured.err.lower() or "error" in captured.err.lower()

    def test_test_skips_comments(self, tmp_path, capsys):
        """Comment lines (starting with #) must be skipped."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("# This is a comment\nir norte\n# Another comment\nhuir hall\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_test_skips_empty_lines(self, tmp_path, capsys):
        """Empty lines must be skipped."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\n\n\nhuir hall\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_test_narrator_output_printed(self, tmp_path, capsys):
        """Narrator output must be printed to stdout during test."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\nhuir hall\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        # Narrator should produce some output
        assert captured.out.strip() != ""

    def test_test_missing_walkthrough_file_exits_1(self, tmp_path, capsys):
        """Missing walkthrough file must exit 1."""
        walkthrough = tmp_path / "nonexistent.txt"

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "walkthrough" in captured.err.lower() or "error" in captured.err.lower()

    def test_test_generic_exception_exits_1(self, tmp_path, capsys):
        """Generic exception during test must exit 1."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                with patch(
                    "builtins.open",
                    side_effect=RuntimeError("Unexpected error"),
                ):
                    main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_test_build_engine_error_exits_1(self, tmp_path, capsys):
        """Build engine error must exit 1."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", "/nonexistent/path", "--walkthrough", str(walkthrough)],
            ):
                main()
        assert exc_info.value.code == 1

    def test_test_episode_switch(self, tmp_path, capsys):
        """Episode switch must work correctly."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\nhuir hall\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough), "--episode", "episode-01"],
            ):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_test_different_episode_triggers_switch(self, tmp_path, capsys):
        """When --episode differs from current, episode_manager.start_episode is called."""
        from fortress_engine.cli.main import _build_engine

        bundle = _build_engine(str(_WORLD_PATH))
        # Current episode is already "episode-01", so it won't switch.
        # But if current_episode_id is empty, it will switch.
        bundle.state.current_episode_id = ""

        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\nhuir hall\n")

        with patch(
            "sys.argv",
            ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough), "--episode", "episode-01"],
        ):
            with patch("fortress_engine.cli.main._build_engine", return_value=bundle):
                with patch.object(
                    bundle.episode_manager, "start_episode", wraps=bundle.episode_manager.start_episode
                ) as mock_start:
                    try:
                        main()
                    except SystemExit:
                        pass
                    mock_start.assert_called_once_with("episode-01", bundle.state)

    def test_test_read_walkthrough_exception(self, tmp_path, capsys):
        """Exception reading walkthrough file must exit 1."""
        walkthrough = tmp_path / "walkthrough.txt"
        walkthrough.write_text("ir norte\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["fortress-engine", "test", str(_WORLD_PATH), "--walkthrough", str(walkthrough)],
            ):
                # Only mock open for the walkthrough file, not globally
                original_open = builtins_open

                def mock_open(path, *args, **kwargs):
                    if str(path) == str(walkthrough):
                        raise IOError("Permission denied")
                    return original_open(path, *args, **kwargs)

                with patch("builtins.open", side_effect=mock_open):
                    main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()
