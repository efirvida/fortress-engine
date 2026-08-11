"""Explorer additive default-off hooks (solver seams, explorer-solver 2.1).

RED phase: references ``BlindExplorer`` attributes and behaviour that do not
exist yet — ``commit_hook``/``solved``/``_commit``, ``turn_counter``,
``ExplorationEvent.gate_code``, ``_speech_marker()``, and sorted iteration.

The hooks must be byte-identical no-ops when unused: a no-op hook produces
the same exploration as ``None``, ``solved`` never flips, and every event the
old code produced keeps its exact (command, ok, error_code) shape.
"""

from __future__ import annotations

from pathlib import Path

from fortress_engine.autoplay import BlindExplorer


def _explore(world: Path, episode: str = "episode-01"):
    ex = BlindExplorer(world, episode)
    discovery, log = ex.explore()
    return ex, discovery, log


def _log_signature(log) -> list[tuple]:
    return [(ev.command, ev.ok, ev.error_code, ev.gate_code) for ev in log]


class TestDefaultOff:
    """Hooks default off — behavior byte-identical when unused."""

    def test_noop_hook_equals_no_hook(self, solver_happy: Path) -> None:
        ex_default, d1, log1 = _explore(solver_happy)
        ex_noop = BlindExplorer(solver_happy, "episode-01")
        ex_noop.commit_hook = lambda cmd: True
        discovery, log2 = ex_noop.explore()

        assert _log_signature(log1) == _log_signature(log2)
        assert d1.visited_rooms == discovery.visited_rooms
        assert d1.crossed_passages == discovery.crossed_passages

    def test_solved_stays_false_without_hook(self, solver_happy: Path) -> None:
        ex, _, _ = _explore(solver_happy)
        assert ex.solved is False

    def test_turn_counter_zero_before_play(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        assert ex.turn_counter == 0


class TestCommitHook:
    """commit_hook contract: called per kept command, False stops the run."""

    def test_hook_receives_kept_commands(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        committed: list[str] = []
        ex.commit_hook = lambda cmd: committed.append(cmd) or True
        ex.explore()
        assert any("coger rusty_key" in c for c in committed)
        assert any(c.startswith("ir ") for c in committed)

    def test_hook_false_flips_solved(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        ex.commit_hook = lambda cmd: False
        discovery, log = ex.explore()
        assert ex.solved is True
        # The run stops at the first keep point — not the full topology.
        assert discovery.visited_rooms == {"alpha"}


class TestTurnCounter:
    """turn_counter increments per _turn, including restored probes."""

    def test_increments_per_turn(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        assert ex.turn_counter == 0
        ex._turn("mirar")
        assert ex.turn_counter == 1
        ex._turn("ir north")
        assert ex.turn_counter == 2

    def test_counts_unlogged_probes(self, solver_happy: Path) -> None:
        ex, _, log = _explore(solver_happy)
        assert ex.turn_counter > len(log)


class TestGateCode:
    """ExplorationEvent.gate_code — nested in ERROR_OUTPUT payload data."""

    def test_requires_item_gate_code(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        ev = ex._turn("ir north")
        assert ev.error_code == "blocked"
        assert ev.gate_code == "requires_item"

    def test_text_closed_gate_code(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        ex._turn("coger rusty_key")
        ex._turn("ir north")
        ev = ex._turn("ir east")
        assert ev.error_code == "blocked"
        assert ev.gate_code == "text_closed"

    def test_ok_events_carry_no_gate_code(self, solver_happy: Path) -> None:
        ex = BlindExplorer(solver_happy, "episode-01")
        ev = ex._turn("mirar")
        assert ev.ok is True
        assert ev.error_code is None
        assert ev.gate_code is None


class TestSpeechMarker:
    """_speech_marker — vocabulary marker or the documented fallback."""

    def test_uses_vocabulary_marker(self, solver_kb: Path) -> None:
        ex = BlindExplorer(solver_kb, "episode-01")
        assert ex._speech_marker() == "hablando"

    def test_fallback_without_vocabulary(self, audit_limbo: Path) -> None:
        ex = BlindExplorer(audit_limbo, "episode-01")
        assert ex._speech_marker() == "diciendo"


class TestDeterminism:
    """Sorted iteration keeps exploration byte-deterministic across runs."""

    def test_two_runs_identical_log_and_discovery(self, solver_happy: Path) -> None:
        _, d1, log1 = _explore(solver_happy)
        _, d2, log2 = _explore(solver_happy)
        assert _log_signature(log1) == _log_signature(log2)
        assert d1.crossed_passages == d2.crossed_passages
        assert d1.visited_rooms == d2.visited_rooms
