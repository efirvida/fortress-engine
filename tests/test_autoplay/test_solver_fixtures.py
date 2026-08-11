"""Chunk-1 fixture worlds for the Stage B solver (tests/test_autoplay/conftest.py).

RED phase: references ``build_solver_*`` builders that do not exist yet.
Each world must pass ``GraphAudit`` with zero ERROR findings so the solver
(chunk 2) can run against it, and its topology must exercise the intended
solver behaviour (item/text/flag gates, KB-only answer, far-key retrieval,
unsolvable gates).
"""

from __future__ import annotations

from pathlib import Path

from fortress_engine.autoplay import GraphAudit
from fortress_engine.entities.loader import EntityLoader


def _run_audit(world: Path) -> GraphAudit:
    loader = EntityLoader(str(world))
    episode = loader.load_episodes()[0]
    return GraphAudit(loader, episode).run()


def _errors(report) -> list:
    return [f for f in report.findings if f.severity == "ERROR"]


def _by_forward(report) -> dict[tuple[str, str], dict]:
    """Index passage records by (from_anchor, passage_name) for forward edges."""
    index: dict[tuple[str, str], dict] = {}
    for record in report.passages:
        data = record.to_dict()
        index[(data["from"], data["passage_name"])] = data
    return index


class TestSolverHappy:
    """Item gate + text gate + flag gate + goal flag, all satisfiable."""

    def test_audit_zero_errors(self, solver_happy: Path) -> None:
        report = _run_audit(solver_happy)
        assert _errors(report) == []
        assert report.reachable_rooms == {"alpha", "beta", "gamma", "delta"}
        assert report.unreachable_rooms == set()

    def test_gate_chain_topology(self, solver_happy: Path) -> None:
        passages = _by_forward(_run_audit(solver_happy))
        assert passages[("alpha", "north")]["requires_item"] == "rusty_key"
        assert passages[("beta", "east")]["requires_text"] == "open sesame"
        assert passages[("gamma", "south")]["requires_flag"] == "door_open"
        assert passages[("alpha", "north")]["open"] is True


class TestSolverKb:
    """Text-gated answer supplied ONLY through episodes/answers.yaml."""

    def test_audit_zero_errors(self, solver_kb: Path) -> None:
        report = _run_audit(solver_kb)
        assert _errors(report) == []
        assert report.reachable_rooms == {"alpha", "beta"}

    def test_text_gate_and_answers_file_present(self, solver_kb: Path) -> None:
        passages = _by_forward(_run_audit(solver_kb))
        assert passages[("alpha", "north")]["requires_text"] == "open sesame"
        assert passages[("alpha", "north")]["open"] is False
        answers = solver_kb / "episodes" / "answers.yaml"
        assert answers.is_file()
        assert "open sesame" in answers.read_text(encoding="utf-8")


class TestSolverRetrieve:
    """Key item lives in a far room off the main path (retrieval needed)."""

    def test_audit_zero_errors(self, solver_retrieve: Path) -> None:
        report = _run_audit(solver_retrieve)
        assert _errors(report) == []
        assert report.reachable_rooms == {
            "alpha", "beta", "gamma", "delta", "zeta"
        }

    def test_key_is_far_from_gate(self, solver_retrieve: Path) -> None:
        report = _run_audit(solver_retrieve)
        passages = _by_forward(report)
        assert passages[("gamma", "secret")]["requires_item"] == "master_key"
        items = {
            e.entity_id: e.spatial_anchor
            for e in EntityLoader(str(solver_retrieve)).load_items("episode-01")
        }
        assert items["master_key"] == "zeta"
        assert items["master_key"] != "gamma"


class TestSolverUnsolvable:
    """Item in an audit-unreachable room + a never-settable flag."""

    def test_audit_zero_errors(self, solver_unsolvable: Path) -> None:
        report = _run_audit(solver_unsolvable)
        assert _errors(report) == []

    def test_unreachable_vault_holds_gold_and_never_flag_gate(
        self, solver_unsolvable: Path
    ) -> None:
        report = _run_audit(solver_unsolvable)
        assert report.reachable_rooms == {
            "alpha", "beta", "gamma", "delta", "epsilon"
        }
        assert report.unreachable_rooms == {"vault", "vault_side"}
        passages = _by_forward(report)
        assert passages[("gamma", "south")]["requires_item"] == "gold_ingot"
        assert passages[("beta", "west")]["requires_flag"] == "never_flag"

    def test_warnings_are_warns_not_errors(self, solver_unsolvable: Path) -> None:
        report = _run_audit(solver_unsolvable)
        assert [(f.severity, f.category) for f in report.findings] == [
            ("WARN", "entity_in_unreachable_room"),
            ("WARN", "unreachable_room"),
            ("WARN", "unreachable_room"),
        ]
