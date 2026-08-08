"""Tests for validate command — Phase 3 of epic-4-cli.

These tests define the contract for the validate subcommand.
They MUST fail before the implementation exists (RED phase).
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from fortress_engine.cli.main import main


_WORLD_PATH = Path(__file__).resolve().parent.parent.parent / "worlds" / "_test_minimal"


class TestValidateCommand:
    """validate subcommand contract tests."""

    def test_validate_valid_world_exits_0(self, capsys):
        """Valid world must print 'World validation passed.' and exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate", str(_WORLD_PATH)]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "World validation passed." in captured.out

    def test_validate_broken_world_exits_1(self, tmp_path, capsys):
        """Broken world must print problem to stderr and exit 1."""
        # Create a world with a dangling spatial_anchor
        broken = tmp_path / "broken"
        broken.mkdir()
        (broken / "world.yaml").write_text("world_id: broken\nname: Broken\n")
        episodes_dir = broken / "episodes"
        episodes_dir.mkdir()
        (episodes_dir / "episode-01.yaml").write_text(
            "id: episode-01\n"
            "name: Broken Episode\n"
            "order: 1\n"
            "description: A broken episode\n"
            "requires: []\n"
            "start_anchor: nonexistent_room\n"
            "goal:\n"
            "  conditions: []\n"
            "  output: ''\n"
            "  side_effects: []\n"
            "carry_over:\n"
            "  inventory: []\n"
            "  flags: []\n"
        )

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate", str(broken)]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.err.strip() != ""

    def test_validate_verbose_shows_details(self, capsys):
        """--verbose flag must be accepted (behavior TBD)."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate", str(_WORLD_PATH), "--verbose"]):
                main()
        assert exc_info.value.code == 0

    def test_validate_missing_world_exits_1(self, tmp_path, capsys):
        """Missing world.yaml must exit 1 with error."""
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate", str(empty)]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "world.yaml" in captured.err.lower() or "error" in captured.err.lower()

    def test_validate_generic_exception_exits_1(self, tmp_path, capsys):
        """Generic exception during validation must exit 1."""
        # Create a world that causes a generic exception
        broken = tmp_path / "broken"
        broken.mkdir()
        (broken / "world.yaml").write_text("world_id: broken\nname: Broken\n")

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate", str(broken)]):
                with patch(
                    "fortress_engine.entities.loader.EntityLoader.validate_world",
                    side_effect=RuntimeError("Unexpected error"),
                ):
                    main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()
