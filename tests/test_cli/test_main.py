"""Tests for main() argparse and exit codes — Phase 2 of epic-4-cli.

These tests define the contract for the CLI main function.
They MUST fail before the implementation exists (RED phase).
"""

import sys
from unittest.mock import patch

import pytest


class TestMainArgparse:
    """main() argparse structure and exit code tests."""

    def test_no_subcommand_exits_2(self):
        """Missing subcommand must exit 2 with argparse error on stderr."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine"]):
                main()
        assert exc_info.value.code == 2

    def test_unknown_subcommand_exits_2(self):
        """Unknown subcommand must exit 2 with argparse error on stderr."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "unknown"]):
                main()
        assert exc_info.value.code == 2

    def test_run_subcommand_requires_world_path(self):
        """run subcommand without world_path must exit 2."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run"]):
                main()
        assert exc_info.value.code == 2

    def test_validate_subcommand_requires_world_path(self):
        """validate subcommand without world_path must exit 2."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate"]):
                main()
        assert exc_info.value.code == 2

    def test_test_subcommand_requires_world_path(self):
        """test subcommand without world_path must exit 2."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "test"]):
                main()
        assert exc_info.value.code == 2

    def test_test_subcommand_requires_walkthrough(self):
        """test subcommand without --walkthrough must exit 2."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "test", "worlds/_test_minimal"]):
                main()
        assert exc_info.value.code == 2

    def test_run_help_exits_0(self, capsys):
        """run --help must exit 0 and show usage."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "run", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "world_path" in captured.out.lower() or "world" in captured.out.lower()

    def test_validate_help_exits_0(self, capsys):
        """validate --help must exit 0 and show usage."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "validate", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "world_path" in captured.out.lower() or "world" in captured.out.lower()

    def test_test_help_exits_0(self, capsys):
        """test --help must exit 0 and show usage."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "test", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "world_path" in captured.out.lower() or "world" in captured.out.lower()

    def test_main_help_exits_0(self, capsys):
        """--help must exit 0 and show usage."""
        from fortress_engine.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fortress-engine", "--help"]):
                main()
        assert exc_info.value.code == 0
