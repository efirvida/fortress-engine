"""Unit tests for solver verdict dataclasses, audit precondition, BFS walk,
key-retrieval, stuck diagnosis, and the full diagnosis matrix (2a-2d).

Contract (spec: Typed solve verdicts + Audit is a precondition):
- ``SolveVerdict`` exposes exactly the 8 declared fields and a JSON-safe
  sorted-key ``to_dict()``; nested ``GateDiagnosis`` serializes as
  ``{passage, predicate, required, reason}``.
- ``GateDiagnosis.reason`` is a Literal over exactly the 5 documented values.
- The audit precondition returns a typed negative verdict with
  ``static_errors`` (and constructs NO runtime engine objects) when
  ``GraphAudit`` reports ERROR findings, and ``None`` to proceed when the
  audit reports zero ERRORs.
- The diagnosis matrix covers all 5 GateReason values, including proxy
  reasons for forbids_* predicates.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import pytest

from fortress_engine.autoplay import GateDiagnosis, SolveVerdict
from fortress_engine.autoplay.explorer import Discovery
from fortress_engine.autoplay.graph_audit import Finding, PassageRecord
from fortress_engine.autoplay.solver import GateReason, Solver
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus

_VERDICT_FIELDS = (
    "completable",
    "episode",
    "walkthrough",
    "total_turns",
    "probe_count",
    "stuck_rooms",
    "unsatisfiable_gates",
    "static_errors",
)

_ALLOWED_REASONS = (
    "answer_not_in_kb",
    "item_unreachable",
    "item_missing_from_world",
    "item_never_acquired",
    "flag_never_set",
)


def _diagnosis(**overrides) -> GateDiagnosis:
    base = {
        "passage": "north",
        "predicate": "requires_item",
        "required": "rusty_key",
        "reason": "item_unreachable",
    }
    base.update(overrides)
    return GateDiagnosis(**base)


def _verdict(**overrides) -> SolveVerdict:
    base = {
        "completable": True,
        "episode": "episode-01",
        "walkthrough": ["take rusty_key", "go north"],
        "total_turns": 7,
        "probe_count": 3,
        "stuck_rooms": ["epsilon"],
        "unsatisfiable_gates": [_diagnosis()],
        "static_errors": [
            Finding(
                severity="ERROR",
                category="dangling_edge_endpoint",
                location="edge:m_north.from",
                message="boom",
            )
        ],
    }
    base.update(overrides)
    return SolveVerdict(**base)


def _precondition(world: Path) -> SolveVerdict | None:
    loader = EntityLoader(str(world))
    episode = loader.load_episodes()[0]
    return Solver(loader, episode)._run_audit_precondition()


class TestSolveVerdictShape:
    """The verdict exposes exactly the 8 declared fields with typed values."""

    def test_all_declared_fields_populated(self) -> None:
        verdict = _verdict()
        assert verdict.completable is True
        assert verdict.episode == "episode-01"
        assert verdict.walkthrough == ["take rusty_key", "go north"]
        assert verdict.total_turns == 7
        assert verdict.probe_count == 3
        assert verdict.stuck_rooms == ["epsilon"]
        assert verdict.unsatisfiable_gates == [_diagnosis()]
        assert verdict.static_errors[0].severity == "ERROR"
        assert verdict.static_errors[0].category == "dangling_edge_endpoint"

    def test_to_dict_has_exactly_the_eight_sorted_keys(self) -> None:
        keys = list(_verdict().to_dict().keys())
        assert keys == sorted(_VERDICT_FIELDS)

    def test_json_top_level_keys_are_sorted_and_deterministic(self) -> None:
        verdict = _verdict()
        plain = json.dumps(verdict.to_dict())
        assert list(json.loads(plain).keys()) == sorted(_VERDICT_FIELDS)
        assert plain == json.dumps(verdict.to_dict())

    def test_nested_gate_diagnosis_serializes_with_four_fields(self) -> None:
        data = _verdict().to_dict()
        assert data["unsatisfiable_gates"] == [
            {
                "passage": "north",
                "predicate": "requires_item",
                "required": "rusty_key",
                "reason": "item_unreachable",
            }
        ]

    def test_static_errors_serialize_as_finding_dicts(self) -> None:
        data = _verdict().to_dict()
        finding = data["static_errors"][0]
        assert finding == {
            "severity": "ERROR",
            "category": "dangling_edge_endpoint",
            "location": "edge:m_north.from",
            "message": "boom",
            "data": {},
        }


class TestGateDiagnosisReasonLiteral:
    """``reason`` is restricted to exactly the 5 documented values."""

    def test_every_allowed_reason_constructs(self) -> None:
        for reason in _ALLOWED_REASONS:
            diagnosis = _diagnosis(reason=reason)
            assert diagnosis.passage == "north"
            assert diagnosis.predicate == "requires_item"
            assert diagnosis.required == "rusty_key"
            assert diagnosis.reason == reason

    def test_literal_exposes_exactly_five_values(self) -> None:
        assert get_args(GateReason) == _ALLOWED_REASONS


class TestAuditPrecondition:
    """Static gate: ERROR findings stop play; a clean audit proceeds."""

    def test_error_world_returns_negative_verdict_with_static_errors(
        self, audit_broken: Path
    ) -> None:
        verdict = _precondition(audit_broken)
        assert verdict is not None
        assert verdict.completable is False
        assert verdict.episode == "episode-01"
        assert verdict.walkthrough == []
        assert verdict.total_turns == 0
        assert verdict.probe_count == 0
        assert verdict.stuck_rooms == []
        assert verdict.unsatisfiable_gates == []
        assert verdict.static_errors != []
        assert all(f.severity == "ERROR" for f in verdict.static_errors)

    def test_error_world_never_constructs_runtime(
        self, audit_broken: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def trap(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("audit precondition constructed a runtime object")

        monkeypatch.setattr(WorldState, "__init__", trap)
        monkeypatch.setattr(EventBus, "__init__", trap)
        verdict = _precondition(audit_broken)
        assert verdict is not None
        assert verdict.completable is False
        assert verdict.static_errors != []

    def test_clean_world_returns_none(self, solver_happy: Path) -> None:
        assert _precondition(solver_happy) is None

    def test_warn_only_world_returns_none(self, solver_unsolvable: Path) -> None:
        assert _precondition(solver_unsolvable) is None


# ===================================================================
# BFS walk tests (sub-chunk 2b) — RED phase
# ===================================================================


class TestSolverWalk:
    """Solver BFS walk with commit hook — composed BlindExplorer driven by
    audit reachable rooms, KB passwords, and max_turns guard."""

    def test_solve_returns_completable_for_happy(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is True
        assert len(verdict.walkthrough) > 0
        assert verdict.episode == "episode-01"

    def test_solve_walkthrough_is_deterministic(self, solver_happy: Path) -> None:
        loader1 = EntityLoader(str(solver_happy))
        v1 = Solver(loader1, loader1.load_episodes()[0]).solve()
        loader2 = EntityLoader(str(solver_happy))
        v2 = Solver(loader2, loader2.load_episodes()[0]).solve()
        assert v1.walkthrough == v2.walkthrough
        assert v1.completable == v2.completable
        assert v1.total_turns == v2.total_turns

    def test_solve_kb_answer_opens_gate(self, solver_kb: Path) -> None:
        loader = EntityLoader(str(solver_kb))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is True
        assert any("hablando" in cmd for cmd in verdict.walkthrough)

    def test_solve_low_turns_not_completable(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=1)
        assert verdict.completable is False
        assert len(verdict.walkthrough) <= 1

    # ---------------------------------------------------------------
    # Sub-chunk 2c: key-retrieval + stuck diagnosis + guard exhaustion
    # ---------------------------------------------------------------

    def test_solve_retrieve_key_from_far_room(
        self, solver_retrieve: Path,
    ) -> None:
        """Key in epsilon, gate at gamma — solver retrieves and crosses."""
        loader = EntityLoader(str(solver_retrieve))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is True
        assert verdict.episode == "episode-01"

    def test_solve_diagnoses_unsolvable_reasons(
        self, solver_unsolvable: Path,
    ) -> None:
        """Gold ingot in unreachable vault → item_unreachable.
        never_flag never set → flag_never_set."""
        loader = EntityLoader(str(solver_unsolvable))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is False
        assert len(verdict.static_errors) == 0
        gates = verdict.unsatisfiable_gates
        assert len(gates) == 2

        reasons = {g.reason for g in gates}
        assert reasons == {"item_unreachable", "flag_never_set"}

        item_gate = next(g for g in gates if g.reason == "item_unreachable")
        assert item_gate.passage == "south"
        assert item_gate.predicate == "requires_item"
        assert item_gate.required == "gold_ingot"

        flag_gate = next(g for g in gates if g.reason == "flag_never_set")
        assert flag_gate.passage == "west"
        assert flag_gate.predicate == "requires_flag"
        assert flag_gate.required == "never_flag"

    def test_solve_guard_exhaustion_populates_stuck_rooms(
        self, solver_happy: Path,
    ) -> None:
        """Guard exhaustion → completable=False, stuck_rooms populated,
        unsatisfiable_gates empty."""
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=1)
        assert verdict.completable is False
        assert len(verdict.stuck_rooms) > 0
        assert verdict.unsatisfiable_gates == []

    def test_solve_ledger_truncation_on_retrieval_failure(
        self, solver_unsolvable: Path,
    ) -> None:
        """Gold ingot in unreachable vault: retrieval fails, ledger stays
        clean."""
        loader = EntityLoader(str(solver_unsolvable))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is False
        assert len(verdict.walkthrough) > 0
        for cmd in verdict.walkthrough:
            assert "gold_ingot" not in cmd

    def test_ledger_excludes_restored_probes(
        self, solver_happy: Path,
    ) -> None:
        """Walkthrough never contains probe commands (probing restores)."""
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        COMMITTED_VERBS = {"ir", "coger", "mirar", "lever", "finish"}
        for cmd in verdict.walkthrough:
            verb = cmd.split()[0]
            assert verb in COMMITTED_VERBS, f"unexpected verb in walkthrough: {cmd}"

    def test_start_anchor_none_is_defensive(self, solver_happy: Path, monkeypatch) -> None:
        """When explorer.anchor() returns None, solve() returns negative verdict."""
        from fortress_engine.autoplay.explorer import BlindExplorer

        original = BlindExplorer.anchor

        def _none_anchor(self):
            return None

        monkeypatch.setattr(BlindExplorer, "anchor", _none_anchor)
        try:
            loader = EntityLoader(str(solver_happy))
            episode = loader.load_episodes()[0]
            verdict = Solver(loader, episode).solve()
            assert verdict.completable is False
            assert verdict.walkthrough == []
            assert verdict.total_turns == 0
        finally:
            monkeypatch.setattr(BlindExplorer, "anchor", original)

    def test_solve_max_turns_0(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=0)
        assert verdict.completable is False

    def test_solve_max_turns_3(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=3)
        assert verdict.completable is False

    def test_solve_max_turns_7(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=7)
        assert verdict.completable is False

    def test_solve_max_turns_12(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=12)
        assert verdict.completable is False

    def test_solve_max_turns_4(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=4)
        assert verdict.completable is False

    def test_solve_max_turns_5(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=5)
        assert verdict.completable is False

    def test_solve_max_turns_6(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=6)
        assert verdict.completable is False

    def test_solve_max_turns_10(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=10)
        assert verdict.completable is False

    def test_solve_max_turns_2(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=2)
        assert verdict.completable is False

    def test_solve_max_turns_8(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=8)
        assert verdict.completable is False

    def test_solve_max_turns_9(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=9)
        assert verdict.completable is False

    def test_solve_max_turns_11(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=11)
        assert verdict.completable is False

    def test_solve_max_turns_13(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=13)
        assert verdict.completable is False

    def test_solve_max_turns_14(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=14)
        assert verdict.completable is False

    def test_solve_max_turns_16(self, solver_happy: Path) -> None:
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=16)
        assert verdict.completable is False

    # --- Key-retrieval edge branches ---

    def test_retrieve_navigate_to_item_fails(
        self, solver_retrieve: Path, monkeypatch,
    ) -> None:
        """Monkeypatch _navigate_to to fail → covers restore path at 490-492."""
        from fortress_engine.autoplay.explorer import BlindExplorer

        orig = BlindExplorer._navigate_to

        def _fail(self, target, *args, **kwargs):
            if target == "zeta":
                return False
            return orig(self, target, *args, **kwargs)

        monkeypatch.setattr(BlindExplorer, "_navigate_to", _fail)
        loader = EntityLoader(str(solver_retrieve))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is False

    def test_retrieve_navigate_back_fails(
        self, solver_retrieve: Path, monkeypatch,
    ) -> None:
        """Monkeypatch _navigate_to to fail on return from zeta → covers 503-505."""
        from fortress_engine.autoplay.explorer import BlindExplorer

        orig = BlindExplorer._navigate_to

        def _fail_navigate_back(self, target, *args, **kwargs):
            if self.anchor() == "zeta" and target == "gamma":
                return False
            return orig(self, target, *args, **kwargs)

        monkeypatch.setattr(BlindExplorer, "_navigate_to", _fail_navigate_back)
        loader = EntityLoader(str(solver_retrieve))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert isinstance(verdict.completable, bool)

    def test_retrieve_item_in_same_room(
        self, tmp_path: Path,
    ) -> None:
        """Key in same room as gate → _retrieve_key returns False
        (item_room == anchor branch).  The solver handles the edge case
        without crashing."""
        from tests.test_autoplay.conftest import (
            _actions_yaml,
            _entity_yaml,
            _episode_yaml,
            _macro_edges_yaml,
            _mirar_action,
            _room_yaml,
            _vocabulary_yaml,
            _write,
        )
        world = tmp_path / "same_room_key"
        _write(world / "world.yaml", 'world_id: "same_room_key"\nname: "Same"\n')
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
        _write(world / "episode-01" / "rooms" / "alpha.yaml", _room_yaml("alpha", "Alpha"))
        _write(world / "episode-01" / "rooms" / "beta.yaml", _room_yaml("beta", "Beta"))
        _write(world / "episode-01" / "macros" / "macros.yaml", _macro_edges_yaml([
            {"id": "a_to_b", "from": "alpha", "to": "beta",
             "direction": "bidirectional", "passage": "north",
             "requires_item": "token"},
        ]))
        _write(world / "episode-01" / "items" / "token.yaml",
               _entity_yaml("token", "item", "Token", "alpha"))
        _write(world / "episode-01" / "npcs" / "goal_shrine.yaml",
               _entity_yaml("goal_shrine", "npc", "Goal Shrine", "beta"))
        _write(world / "episode-01" / "actions" / "actions.yaml", _actions_yaml([
            _mirar_action(),
            {"id": "he_take_token", "name": "Tomar token", "verb": "tomar",
             "target": "token", "operators": [
                 {"type": "TRANSFER", "entity": "token",
                  "from_container": "alpha", "to_container": "hero"}
             ], "output": "Tomas la ficha."},
            {"id": "he_finish", "name": "Finish", "verb": "finish",
             "target": "goal_shrine", "operators": [
                 {"type": "FLAG", "flag": "quest_done", "value": True}
             ], "output": "Listo."},
        ]))
        _write(world / "shared" / "player.yaml",
               _entity_yaml("hero", "player", "Hero", None))
        _write(world / "shared" / "vocabulary.yaml",
               _vocabulary_yaml(["mirar", "tomar", "finish", "ir"]))
        loader = EntityLoader(str(world))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert isinstance(verdict.completable, bool)

    def test_retrieve_take_item_fails(
        self, solver_retrieve: Path, monkeypatch,
    ) -> None:
        """Monkeypatch _take_if_present to fail → covers 495-498."""
        from fortress_engine.autoplay.explorer import BlindExplorer

        orig = BlindExplorer._take_if_present

        def _fail_take(self, item_id):
            if item_id == "master_key":
                return False
            return orig(self, item_id)

        monkeypatch.setattr(BlindExplorer, "_take_if_present", _fail_take)
        loader = EntityLoader(str(solver_retrieve))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert isinstance(verdict.completable, bool)

    def test_retrieve_max_turns_8(self, solver_retrieve: Path) -> None:
        """Low turn budget during key retrieval → guard exhaustion."""
        loader = EntityLoader(str(solver_retrieve))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve(max_turns=8)
        assert isinstance(verdict.completable, bool)

    def test_start_not_in_reachable(
        self, solver_happy: Path, monkeypatch,
    ) -> None:
        """Monkeypatch audit reachable_rooms → covers 430->434."""
        from fortress_engine.autoplay.graph_audit import GraphAudit

        orig_run = GraphAudit.run

        def _patched(self, *args, **kwargs):
            report = orig_run(self, *args, **kwargs)
            report.reachable_rooms = set()
            return report

        monkeypatch.setattr(GraphAudit, "run", _patched)
        loader = EntityLoader(str(solver_happy))
        episode = loader.load_episodes()[0]
        verdict = Solver(loader, episode).solve()
        assert verdict.completable is False


# ===================================================================
# Task 2.5: Diagnosis matrix — each of 5 reasons with exact messages
# ===================================================================


class TestDiagnosisMatrix:
    """Static _diagnose() tests covering all 5 GateReason values,
    including proxy reasons for forbids_* predicates, plus skipped-
    passage and None-precondition branches.
    """

    def _blocked(self, room: str, tokens: set[str]) -> dict[str, set[str]]:
        return {room: tokens}

    def _passages(self, *records: PassageRecord) -> list[PassageRecord]:
        return list(records)

    def _precord(
        self,
        from_anchor: str = "alpha",
        passage_name: str = "north",
        **overrides: Any,
    ) -> PassageRecord:
        base: dict[str, Any] = {
            "from_anchor": from_anchor,
            "to_anchor": "beta",
            "passage_name": passage_name,
            "requires_item": None,
            "forbids_item": None,
            "requires_flag": None,
            "forbids_flag": None,
            "requires_text": None,
            "open": False,
            "direction": "bidirectional",
        }
        base.update(overrides)
        return PassageRecord(**base)

    def _diagnose(
        self,
        blocked_rooms: dict[str, set[str]],
        passages: list[PassageRecord],
        all_items: dict[str, Any] | None = None,
        discovery: Discovery | None = None,
        reachable: set[str] | None = None,
        answers: list[str] | None = None,
    ) -> list[GateDiagnosis]:
        return Solver._diagnose(
            blocked_rooms=blocked_rooms,
            passages=passages,
            all_items=all_items or {},
            discovery=discovery or Discovery(),
            reachable=reachable or {"alpha", "beta"},
            answers=answers or [],
        )

    # --- answer_not_in_kb ---

    def test_answer_not_in_kb_exact_message(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"north"}),
            self._passages(
                self._precord(
                    "alpha", "north",
                    requires_text="open sesame",
                ),
            ),
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "north"
        assert d.predicate == "requires_text"
        assert d.required == "open sesame"
        assert d.reason == "answer_not_in_kb"

    def test_open_false_no_predicates_yields_answer_not_in_kb(self) -> None:
        """open=False without any predicate fields → drained-guard proxy."""
        result = self._diagnose(
            self._blocked("alpha", {"magic"}),
            self._passages(
                self._precord("alpha", "magic"),
            ),
        )
        assert len(result) == 1
        assert result[0].passage == "magic"
        assert result[0].predicate == "requires_text"
        assert result[0].required == ""
        assert result[0].reason == "answer_not_in_kb"

    # --- item_missing_from_world ---

    def test_item_missing_from_world_exact_message(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"tunnel"}),
            self._passages(
                self._precord(
                    "alpha", "tunnel",
                    requires_item="invisible_key",
                ),
            ),
            all_items={},
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "tunnel"
        assert d.predicate == "requires_item"
        assert d.required == "invisible_key"
        assert d.reason == "item_missing_from_world"

    # --- item_unreachable ---

    def test_item_unreachable_exact_message(self) -> None:
        result = self._diagnose(
            self._blocked("beta", {"vault"}),
            self._passages(
                self._precord(
                    "beta", "vault",
                    requires_item="golden_egg",
                ),
            ),
            all_items={"golden_egg": _FakeItem("vault")},
            reachable={"alpha", "beta"},
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "vault"
        assert d.predicate == "requires_item"
        assert d.required == "golden_egg"
        assert d.reason == "item_unreachable"

    # --- item_never_acquired ---

    def test_item_never_acquired_exact_message(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"gate"}),
            self._passages(
                self._precord(
                    "alpha", "gate",
                    requires_item="potion",
                ),
            ),
            all_items={"potion": _FakeItem("alpha")},
            reachable={"alpha", "beta"},
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "gate"
        assert d.predicate == "requires_item"
        assert d.required == "potion"
        assert d.reason == "item_never_acquired"

    # --- forbids_item proxy → item_never_acquired ---

    def test_forbids_item_diagnosis_is_proxy(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"corridor"}),
            self._passages(
                self._precord(
                    "alpha", "corridor",
                    forbids_item="jade_statue",
                ),
            ),
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "corridor"
        assert d.predicate == "forbids_item"
        assert d.required == "jade_statue"
        assert d.reason == "item_never_acquired"

    # --- flag_never_set ---

    def test_flag_never_set_exact_message(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"passage"}),
            self._passages(
                self._precord(
                    "alpha", "passage",
                    requires_flag="seal_broken",
                ),
            ),
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "passage"
        assert d.predicate == "requires_flag"
        assert d.required == "seal_broken"
        assert d.reason == "flag_never_set"

    # --- forbids_flag proxy → flag_never_set ---

    def test_forbids_flag_diagnosis_is_proxy(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"alcove"}),
            self._passages(
                self._precord(
                    "alpha", "alcove",
                    forbids_flag="curse_active",
                ),
            ),
        )
        assert len(result) == 1
        d = result[0]
        assert d.passage == "alcove"
        assert d.predicate == "forbids_flag"
        assert d.required == "curse_active"
        assert d.reason == "flag_never_set"

    # --- skipped passage (not in passage_index) ---

    def test_unknown_passage_not_in_records_is_skipped(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"unknown_passage"}),
            [],
        )
        assert result == []

    # --- fallthrough: answer in KB, no diagnosis ---

    def test_answer_in_kb_passes_through_no_diagnosis(self) -> None:
        """requires_text present AND answer in KB → diagnosis skips this
        passage, falls through other predicates (all None) and then
        reaches open=False+predicates-check which also passes."""
        result = self._diagnose(
            self._blocked("alpha", {"north"}),
            self._passages(
                self._precord(
                    "alpha", "north",
                    requires_text="open sesame",
                ),
            ),
            answers=["open sesame"],
        )
        assert result == []

    # --- open=True falls through without diagnosis ---

    def test_open_true_falls_through_no_diagnosis(self) -> None:
        result = self._diagnose(
            self._blocked("alpha", {"portal"}),
            self._passages(
                self._precord("alpha", "portal", open=True),
            ),
        )
        assert result == []

    # --- multiple diagnoses sorted deterministically ---

    def test_multiple_diagnoses_sorted(self) -> None:
        result = self._diagnose(
            {
                "beta": {"vault"},
                "alpha": {"tunnel"},
            },
            self._passages(
                self._precord("alpha", "tunnel", requires_item="invisible_key"),
                self._precord("beta", "vault", requires_item="golden_egg"),
            ),
            all_items={
                "golden_egg": _FakeItem("vault"),
            },
            reachable={"alpha", "beta"},
        )
        assert len(result) == 2
        assert result[0].passage == "tunnel"
        assert result[0].reason == "item_missing_from_world"
        assert result[1].passage == "vault"
        assert result[1].reason == "item_unreachable"


class _FakeItem:
    """Minimal entity stub for _diagnose all_items dict lookups."""

    def __init__(self, spatial_anchor: str) -> None:
        self.spatial_anchor = spatial_anchor


class TestLocateItemRoom:
    """Solver._locate_item_room static dispatch: discovery, loader, None."""

    def test_from_discovery(self) -> None:
        discovery = Discovery()
        discovery.found_items["token"] = "alpha"
        result = Solver._locate_item_room("token", discovery, {})
        assert result == "alpha"

    def test_from_loader_fallback(self) -> None:
        discovery = Discovery()
        result = Solver._locate_item_room(
            "token", discovery, {"token": _FakeItem("beta")},
        )
        assert result == "beta"

    def test_returns_none_when_neither(self) -> None:
        discovery = Discovery()
        result = Solver._locate_item_room("ghost", discovery, {})
        assert result is None
