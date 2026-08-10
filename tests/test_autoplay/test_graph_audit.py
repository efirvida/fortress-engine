"""Unit tests for the static autoplay graph audit.

RED phase: references ``fortress_engine.autoplay.graph_audit`` which does not
exist yet.  Every finding category, both BFS branches, passive gate data,
report arithmetic, and ordering guarantees from the design are pinned here
with exact severity/location/message/data assertions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from fortress_engine.autoplay import AuditReport, Finding, GraphAudit, PassageRecord
from fortress_engine.autoplay.graph_audit import _goal_value_known
from fortress_engine.entities.loader import EntityLoader


def _run_audit(world: Path) -> AuditReport:
    loader = EntityLoader(str(world))
    episode = loader.load_episodes()[0]
    return GraphAudit(loader, episode).run()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_base_world(
    tmp_path: Path,
    name: str,
    start_anchor: str,
    rooms: list[str],
    goal_conditions: str = "",
) -> Path:
    world = tmp_path / name
    _write(world / "world.yaml", f'world_id: "{name}"\nname: "{name.title()}"\n')
    if goal_conditions:
        goal_block = f"  conditions:\n{goal_conditions}\n"
    else:
        goal_block = "  conditions: []\n"
    _write(
        world / "episodes" / "episode-01.yaml",
        f"id: episode-01\n"
        "name: Episode\n"
        "order: 1\n"
        "requires: []\n"
        f"start_anchor: {start_anchor}\n"
        "goal:\n"
        f"{goal_block}"
        "  output: ''\n"
        "  side_effects: []\n"
        "carry_over:\n"
        "  inventory: []\n"
        "  flags: []\n",
    )
    for room in rooms:
        _write(
            world / "episode-01" / "rooms" / f"{room}.yaml",
            f'entity_id: "{room}"\ntype: "room"\nname: "{room.title()}"\n',
        )
    return world


class TestHappyWorld:
    """audit_happy — zero findings, non-Spanish identifiers."""

    def test_happy_world_zero_findings(self, audit_happy: Path) -> None:
        report = _run_audit(audit_happy)
        assert report.episode == "episode-01"
        assert report.declared_rooms == {"alpha", "beta"}
        assert report.reachable_rooms == {"alpha", "beta"}
        assert report.unreachable_rooms == set()
        assert report.findings == []

    def test_happy_world_two_passages_from_bidirectional_expansion(
        self, audit_happy: Path
    ) -> None:
        report = _run_audit(audit_happy)
        assert [p.to_dict()["from"] for p in report.passages] == ["alpha", "beta"]
        assert [p.to_dict()["to"] for p in report.passages] == ["beta", "alpha"]
        assert [p.to_dict()["passage_name"] for p in report.passages] == [
            "north",
            "north",
        ]


class TestBFS:
    """Single structural BFS: gates are never evaluated."""

    def _gated_world(self, tmp_path: Path) -> Path:
        world = _write_base_world(tmp_path, "gated", "alpha", ["alpha", "beta"])
        _write(
            world / "episode-01" / "macros" / "macros.yaml",
            '- macro_edge_id: "a_to_b"\n'
            '  from_anchor: "alpha"\n'
            '  to_anchor: "beta"\n'
            '  direction: "unidirectional"\n'
            '  passage_name: "portal"\n'
            '  requires_item: "key"\n'
            '  forbids_item: "axe"\n'
            '  requires_flag: "door_open"\n'
            '  forbids_flag: "sealed"\n'
            '  requires_text: "open sesame"\n'
            "  open: false\n",
        )
        _write(
            world / "episode-01" / "items" / "key.yaml",
            'entity_id: "key"\ntype: "item"\nname: "Key"\nspatial_anchor: "alpha"\n',
        )
        _write(
            world / "shared" / "player.yaml",
            'entity_id: "hero"\ntype: "player"\nname: "Hero"\nspatial_anchor: null\n',
        )
        return world

    def test_gated_path_is_structurally_reachable(self, tmp_path: Path) -> None:
        report = _run_audit(self._gated_world(tmp_path))
        assert report.reachable_rooms == {"alpha", "beta"}
        assert report.unreachable_rooms == set()
        assert report.findings == []

    def test_passive_predicates_copied_verbatim(self, tmp_path: Path) -> None:
        report = _run_audit(self._gated_world(tmp_path))
        assert len(report.passages) == 1
        record = report.passages[0]
        assert record.to_dict() == {
            "from": "alpha",
            "to": "beta",
            "passage_name": "portal",
            "requires_item": "key",
            "forbids_item": "axe",
            "requires_flag": "door_open",
            "forbids_flag": "sealed",
            "requires_text": "open sesame",
            "open": False,
            "direction": "unidirectional",
        }

    def test_passage_record_field_order(self, audit_happy: Path) -> None:
        report = _run_audit(audit_happy)
        keys = list(report.passages[0].to_dict().keys())
        assert keys == [
            "from",
            "to",
            "passage_name",
            "requires_item",
            "forbids_item",
            "requires_flag",
            "forbids_flag",
            "requires_text",
            "open",
            "direction",
        ]

    def test_absent_predicates_serialize_as_none(self, audit_happy: Path) -> None:
        report = _run_audit(audit_happy)
        record = report.passages[0].to_dict()
        assert record["requires_item"] is None
        assert record["forbids_item"] is None
        assert record["requires_flag"] is None
        assert record["forbids_flag"] is None
        assert record["requires_text"] is None
        assert record["open"] is True
        assert record["direction"] == "bidirectional"

    def test_missing_start_yields_empty_reachable_and_finding(
        self, audit_broken: Path
    ) -> None:
        report = _run_audit(audit_broken)
        assert report.reachable_rooms == set()
        assert report.unreachable_rooms == report.declared_rooms
        start = next(
            f for f in report.findings if f.category == "start_anchor_missing"
        )
        assert start.severity == "ERROR"
        assert start.location == "episode:episode-01.start_anchor"
        assert start.message == "Start anchor 'ghost' is not a declared room"
        assert start.data == {"episode": "episode-01", "start": "ghost"}

    def test_self_loop_enqueued_once(self, tmp_path: Path) -> None:
        world = _write_base_world(tmp_path, "loop", "alpha", ["alpha"])
        _write(
            world / "episode-01" / "macros" / "macros.yaml",
            '- macro_edge_id: "m_loop"\n'
            '  from_anchor: "alpha"\n'
            '  to_anchor: "alpha"\n'
            '  direction: "unidirectional"\n'
            '  passage_name: "loop"\n',
        )
        report = _run_audit(world)
        assert report.reachable_rooms == {"alpha"}
        assert report.unreachable_rooms == set()
        loop = next(f for f in report.findings if f.category == "self_loop_edge")
        assert loop.severity == "WARN"
        assert loop.location == "edge:m_loop"
        assert loop.message == "Edge 'm_loop' is a self-loop on anchor 'alpha'"
        assert loop.data == {"edge": "m_loop", "anchor": "alpha", "passage": "loop"}

    def test_diamond_graph_visits_each_room_once(self, tmp_path: Path) -> None:
        """A destination reachable via two paths must still be visited once."""
        world = _write_base_world(
            tmp_path, "diamond", "alpha", ["alpha", "beta", "gamma", "delta"]
        )
        edges = []
        for index, (frm, to) in enumerate(
            [("alpha", "beta"), ("alpha", "gamma"), ("beta", "delta"), ("gamma", "delta")]
        ):
            edges.append(
                f'- macro_edge_id: "m_{index}"\n'
                f'  from_anchor: "{frm}"\n'
                f'  to_anchor: "{to}"\n'
                '  direction: "unidirectional"\n'
                f'  passage_name: "p_{frm}_{to}"\n'
            )
        _write(world / "episode-01" / "macros" / "macros.yaml", "\n".join(edges))
        report = _run_audit(world)
        assert report.reachable_rooms == {"alpha", "beta", "gamma", "delta"}
        assert report.unreachable_rooms == set()
        assert report.findings == []

    def test_disconnected_room_absent_from_reachable(self, audit_disconnected: Path) -> None:
        report = _run_audit(audit_disconnected)
        assert report.reachable_rooms == {"alpha", "beta"}
        assert report.unreachable_rooms == {"gamma"}

    def test_report_set_arithmetic_holds(self, audit_disconnected: Path) -> None:
        report = _run_audit(audit_disconnected)
        assert report.unreachable_rooms == (
            report.declared_rooms - report.reachable_rooms
        )


class TestFindingCatalog:
    """Exact severity/location/message/data for every category."""

    def test_broken_world_full_ordered_catalog(self, audit_broken: Path) -> None:
        report = _run_audit(audit_broken)
        assert [(f.severity, f.category, f.location) for f in report.findings] == [
            ("ERROR", "dangling_edge_endpoint", "edge:m_alpha_missing.from"),
            ("ERROR", "dangling_edge_endpoint", "edge:m_alpha_missing.to"),
            ("ERROR", "dangling_edge_endpoint", "edge:m_dup_a.from"),
            ("ERROR", "dangling_edge_endpoint", "edge:m_dup_b.from"),
            ("ERROR", "dangling_edge_endpoint", "edge:m_loop.from"),
            ("ERROR", "dangling_edge_endpoint", "edge:m_loop.to"),
            ("ERROR", "dangling_spatial_anchor", "entity:trinket.spatial_anchor"),
            ("ERROR", "isolated_room", "room:isolated"),
            ("ERROR", "start_anchor_missing", "episode:episode-01.start_anchor"),
            ("WARN", "duplicate_passage", "passage:alpha->sink:duplicate_pass"),
            ("WARN", "goal_unknown_entity", "goal:conditions[0].entity"),
            ("WARN", "goal_unknown_entity", "goal:conditions[0].room"),
            ("WARN", "goal_unknown_entity", "goal:conditions[1].flag"),
            ("WARN", "orphan_room", "room:orphan"),
            ("WARN", "self_loop_edge", "edge:m_loop"),
            ("WARN", "unreachable_room", "room:isolated"),
            ("WARN", "unreachable_room", "room:orphan"),
            ("WARN", "unreachable_room", "room:sink"),
        ]

    def test_dangling_edge_endpoint_payloads(self, audit_broken: Path) -> None:
        report = _run_audit(audit_broken)
        dangling = [
            f for f in report.findings if f.category == "dangling_edge_endpoint"
        ]
        assert len(dangling) == 6
        by_location = {f.location: f for f in dangling}
        missing_from = by_location["edge:m_alpha_missing.from"]
        assert missing_from.severity == "ERROR"
        assert (
            missing_from.message
            == "Edge 'm_alpha_missing' endpoint 'from' references missing anchor 'alpha'"
        )
        assert missing_from.data == {
            "edge": "m_alpha_missing",
            "from": "alpha",
            "to": "missing",
            "missing": "alpha",
        }
        missing_to = by_location["edge:m_alpha_missing.to"]
        assert missing_to.message == (
            "Edge 'm_alpha_missing' endpoint 'to' references missing anchor 'missing'"
        )
        assert missing_to.data == {
            "edge": "m_alpha_missing",
            "from": "alpha",
            "to": "missing",
            "missing": "missing",
        }

    def test_dangling_spatial_anchor_payload(self, audit_broken: Path) -> None:
        report = _run_audit(audit_broken)
        finding = next(
            f for f in report.findings if f.category == "dangling_spatial_anchor"
        )
        assert finding.severity == "ERROR"
        assert finding.location == "entity:trinket.spatial_anchor"
        assert (
            finding.message
            == "Entity 'trinket' is anchored to unknown entity 'ghost_room'"
        )
        assert finding.data == {
            "episode": "episode-01",
            "entity": "trinket",
            "anchor": "ghost_room",
        }

    def test_isolated_and_orphan_are_mutually_exclusive(self, audit_broken: Path) -> None:
        report = _run_audit(audit_broken)
        isolated = next(f for f in report.findings if f.category == "isolated_room")
        orphan = next(f for f in report.findings if f.category == "orphan_room")
        assert isolated.severity == "ERROR"
        assert isolated.location == "room:isolated"
        assert isolated.message == "Room 'isolated' has no incoming or outgoing edges"
        assert isolated.data == {"room": "isolated"}
        assert orphan.severity == "WARN"
        assert orphan.location == "room:orphan"
        assert orphan.message == "Room 'orphan' has no incoming edges"
        assert orphan.data == {"room": "orphan", "outgoing_edges": ["m_orphan_sink"]}

    def test_duplicate_passage_payload_with_sorted_edge_ids(
        self, audit_broken: Path
    ) -> None:
        report = _run_audit(audit_broken)
        finding = next(
            f for f in report.findings if f.category == "duplicate_passage"
        )
        assert finding.severity == "WARN"
        assert finding.location == "passage:alpha->sink:duplicate_pass"
        assert (
            finding.message
            == "Duplicate passage 'duplicate_pass' from 'alpha' to 'sink'"
        )
        assert finding.data == {
            "tuple": ["alpha", "sink", "duplicate_pass"],
            "edge_ids": ["m_dup_a", "m_dup_b"],
        }

    def test_goal_unknown_entity_payloads(self, audit_broken: Path) -> None:
        report = _run_audit(audit_broken)
        goals = [
            f for f in report.findings if f.category == "goal_unknown_entity"
        ]
        assert len(goals) == 3
        entity = goals[0]
        assert entity.severity == "WARN"
        assert entity.location == "goal:conditions[0].entity"
        assert entity.message == "Goal references unknown entity 'ghost_entity'"
        assert entity.data == {
            "goal": "conditions[0]",
            "parameter": "entity",
            "value": "ghost_entity",
        }
        room = goals[1]
        assert room.location == "goal:conditions[0].room"
        assert room.message == "Goal references unknown room 'ghost_room'"
        assert room.data == {
            "goal": "conditions[0]",
            "parameter": "room",
            "value": "ghost_room",
        }
        flag = goals[2]
        assert flag.location == "goal:conditions[1].flag"
        assert flag.message == "Goal references unknown flag 'ghost_flag'"
        assert flag.data == {
            "goal": "conditions[1]",
            "parameter": "flag",
            "value": "ghost_flag",
        }

    def test_goal_unknown_entity_recursive_and_or_path(
        self, tmp_path: Path
    ) -> None:
        world = _write_base_world(tmp_path, "composite", "alpha", ["alpha"])
        _write(
            world / "episode-01" / "macros" / "macros.yaml",
            '- macro_edge_id: "a_to_a"\n'
            '  from_anchor: "alpha"\n'
            '  to_anchor: "alpha"\n'
            '  direction: "unidirectional"\n'
            '  passage_name: "loop"\n'
            '  requires_flag: "door_open"\n',
        )
        # Goal: or(flag ghost_inner, flag real_flag) and entity_dead dragon.
        # door_open and real_flag are known (macro predicate + FLAG operator);
        # ghost_inner is unknown and must surface at path conditions[0].or[0].
        _write(
            world / "episodes" / "episode-01.yaml",
            "id: episode-01\n"
            "name: Episode\n"
            "order: 1\n"
            "requires: []\n"
            "start_anchor: alpha\n"
            "goal:\n"
            "  conditions:\n"
            "    - or:\n"
            "        - type: flag_is_set\n"
            "          params:\n"
            "            flag: ghost_inner\n"
            "        - type: flag_is_set\n"
            "          params:\n"
            "            flag: real_flag\n"
            "    - and:\n"
            "        - type: entity_dead\n"
            "          params:\n"
            "            entity: dragon\n"
            "  output: ''\n"
            "  side_effects: []\n"
            "carry_over:\n"
            "  inventory: []\n"
            "  flags: []\n",
        )
        _write(
            world / "episode-01" / "actions" / "quest.yaml",
            "- hyper_edge_id: he_set\n"
            "  name: Set\n"
            "  priority: 10\n"
            "  clique:\n"
            "    subject: player\n"
            "    verb: set\n"
            "  operators:\n"
            "    - type: FLAG\n"
            "      flag: real_flag\n"
            "      value: true\n"
            "  output: ''\n",
        )
        _write(
            world / "episode-01" / "npcs" / "dragon.yaml",
            'entity_id: "dragon"\ntype: "npc"\nname: "Dragon"\nspatial_anchor: "alpha"\n',
        )
        report = _run_audit(world)
        goals = [
            f for f in report.findings if f.category == "goal_unknown_entity"
        ]
        assert len(goals) == 1
        assert goals[0].location == "goal:conditions[0].or[0].flag"
        assert goals[0].data == {
            "goal": "conditions[0].or[0]",
            "parameter": "flag",
            "value": "ghost_inner",
        }

    def test_macro_predicate_flags_are_known(self, tmp_path: Path) -> None:
        world = _write_base_world(
            tmp_path,
            "macro_known",
            "alpha",
            ["alpha"],
            "    - type: flag_is_set\n"
            "      params:\n"
            "        flag: door_open\n",
        )
        _write(
            world / "episode-01" / "macros" / "macros.yaml",
            '- macro_edge_id: "a_to_a"\n'
            '  from_anchor: "alpha"\n'
            '  to_anchor: "alpha"\n'
            '  direction: "unidirectional"\n'
            '  passage_name: "loop"\n'
            '  requires_flag: "door_open"\n',
        )
        report = _run_audit(world)
        assert all(
            f.category != "goal_unknown_entity" for f in report.findings
        )
        assert [f.category for f in report.findings] == ["self_loop_edge"]

    def test_goal_scan_branch_coverage(self, tmp_path: Path) -> None:
        """Flat/nested atomics, absent params, unknown types, extra keys."""
        world = _write_base_world(tmp_path, "goal_branches", "alpha", ["alpha"])
        _write(
            world / "episodes" / "episode-01.yaml",
            "id: episode-01\n"
            "name: Episode\n"
            "order: 1\n"
            "requires: []\n"
            "start_anchor: alpha\n"
            "goal:\n"
            "  conditions:\n"
            "    - or:\n"
            "        - type: flag_is_set\n"
            "          flag: ghost_flat\n"
            "        - type: entity_dead\n"
            "          params: {}\n"
            "        - type: mystery_condition\n"
            "          params: {}\n"
            "      note: composite extra key\n"
            "    - and:\n"
            "        - type: entity_not_in_room\n"
            "          params:\n"
            "            entity: dragon\n"
            "        - type: flag_is_set\n"
            "          params: {}\n"
            "        - type: entity_has_component\n"
            "          params:\n"
            "            entity: dragon\n"
            "            component: hp\n"
            "            value: 5\n"
            "  output: ''\n"
            "  side_effects: []\n"
            "carry_over:\n"
            "  inventory: []\n"
            "  flags: []\n",
        )
        _write(
            world / "episode-01" / "npcs" / "dragon.yaml",
            'entity_id: "dragon"\ntype: "npc"\nname: "Dragon"\nspatial_anchor: "alpha"\n',
        )
        _write(
            world / "episode-01" / "actions" / "quest.yaml",
            "- hyper_edge_id: he_transform\n"
            "  name: Transform\n"
            "  priority: 10\n"
            "  clique:\n"
            "    subject: player\n"
            "    verb: hit\n"
            "  operators:\n"
            "    - type: TRANSFORM\n"
            "      entity: dragon\n"
            "      component: hp\n"
            "      old_value: 5\n"
            "      new_value: 0\n"
            "    - type: FLAG\n"
            "      value: true\n"
            "  output: ''\n",
        )
        report = _run_audit(world)
        assert [(f.category, f.location, f.data) for f in report.findings] == [
            (
                "goal_unknown_entity",
                "goal:conditions[0].or[0].flag",
                {"goal": "conditions[0].or[0]", "parameter": "flag",
                 "value": "ghost_flat"},
            )
        ]

    def test_goal_value_known_defensive_parameter(self) -> None:
        """Unknown parameters are treated as known (never judged)."""
        assert _goal_value_known("mystery", "x", set(), set(), set()) is True

    def test_known_flags_ignores_non_dict_operators(self) -> None:
        """Non-dict operator entries are skipped defensively."""
        from types import SimpleNamespace

        fake_hyper_edge = SimpleNamespace(
            operators=[42, {"type": "FLAG", "flag": "real_flag"}]
        )
        known = GraphAudit._known_flags([fake_hyper_edge], [])
        assert known == {"real_flag"}

    def test_entity_in_unreachable_room_overlaps_unreachable(
        self, audit_disconnected: Path
    ) -> None:
        report = _run_audit(audit_disconnected)
        assert [(f.severity, f.category, f.location) for f in report.findings] == [
            ("ERROR", "isolated_room", "room:gamma"),
            ("WARN", "entity_in_unreachable_room", "entity:gamma_coin.spatial_anchor"),
            ("WARN", "unreachable_room", "room:gamma"),
        ]
        placed = report.findings[1]
        assert (
            placed.message
            == "Entity 'gamma_coin' is placed in unreachable room 'gamma'"
        )
        assert placed.data == {
            "episode": "episode-01",
            "entity": "gamma_coin",
            "anchor": "gamma",
        }

    def test_limbo_is_info_and_never_dangling(self, audit_limbo: Path) -> None:
        report = _run_audit(audit_limbo)
        assert [(f.severity, f.category) for f in report.findings] == [
            ("INFO", "entity_limbo_at_load")
        ]
        limbo = report.findings[0]
        assert limbo.location == "entity:lost_ring.spatial_anchor"
        assert (
            limbo.message
            == "Entity 'lost_ring' is in limbo at load (no spatial anchor)"
        )
        assert limbo.data == {"episode": "episode-01", "entity": "lost_ring"}
        assert not any(
            f.category == "dangling_spatial_anchor" for f in report.findings
        )


class TestReportSerialization:
    """Sets serialize as sorted lists; JSON is deterministic."""

    def test_to_dict_serializes_sets_as_sorted_lists(
        self, audit_broken: Path
    ) -> None:
        report = _run_audit(audit_broken)
        payload = report.to_dict()
        assert payload["episode"] == "episode-01"
        assert payload["declared_rooms"] == ["isolated", "orphan", "sink"]
        assert payload["reachable_rooms"] == []
        assert payload["unreachable_rooms"] == ["isolated", "orphan", "sink"]
        assert isinstance(payload["passages"], list)
        assert isinstance(payload["findings"], list)

    def test_json_dump_is_deterministic_and_sorted_keys(
        self, audit_broken: Path
    ) -> None:
        report = _run_audit(audit_broken)
        first = json.dumps(report.to_dict(), sort_keys=True)
        second = json.dumps(_run_audit(audit_broken).to_dict(), sort_keys=True)
        assert first == second
        assert json.loads(first)["findings"][0]["severity"] == "ERROR"

    def test_passages_sort_by_all_fields(self, audit_happy: Path) -> None:
        report = _run_audit(audit_happy)
        serialized = [p.to_dict() for p in report.passages]
        assert [p["from"] for p in serialized] == ["alpha", "beta"]
        assert [p["to"] for p in serialized] == ["beta", "alpha"]
        # Deterministic: a second run yields the identical order.
        assert [p.to_dict() for p in _run_audit(audit_happy).passages] == serialized

    def test_passage_order_independent_of_declaration_order(
        self, tmp_path: Path
    ) -> None:
        def build(order: list[tuple[str, str]]) -> Path:
            world = _write_base_world(tmp_path / f"order_{order[0][0]}", "order", "a", ["a", "b", "c"])
            edges = "".join(
                f'- macro_edge_id: "{frm}_to_{to}"\n'
                f'  from_anchor: "{frm}"\n'
                f'  to_anchor: "{to}"\n'
                '  direction: "unidirectional"\n'
                f'  passage_name: "p_{frm}_{to}"\n'
                for frm, to in order
            )
            _write(world / "episode-01" / "macros" / "macros.yaml", edges)
            return world

        forward = build([("a", "b"), ("b", "c")])
        reversed_ = build([("b", "c"), ("a", "b")])
        forward_serialized = [p.to_dict() for p in _run_audit(forward).passages]
        reversed_serialized = [p.to_dict() for p in _run_audit(reversed_).passages]
        assert forward_serialized == reversed_serialized
        assert [p["from"] for p in forward_serialized] == ["a", "b"]

    def test_dangling_edges_still_produce_passage_records(
        self, audit_broken: Path
    ) -> None:
        report = _run_audit(audit_broken)
        assert len(report.passages) == 5


class TestPurity:
    """The audit must never construct or import the runtime engine."""

    def test_module_never_imports_runtime_engine(self) -> None:
        # Load graph_audit.py directly (bypassing autoplay/__init__.py, which
        # eagerly imports the runtime-dependent explorer) and assert no
        # runtime engine module is pulled in as a side effect.
        repo_root = Path(__file__).resolve().parent.parent.parent
        module_path = repo_root / "src" / "fortress_engine" / "autoplay" / "graph_audit.py"
        code = (
            "import importlib.util, sys\n"
            f"spec = importlib.util.spec_from_file_location("
            f"'ga_module', r'{module_path}')\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "sys.modules['ga_module'] = module\n"
            "spec.loader.exec_module(module)\n"
            "forbidden = ["
            "'fortress_engine.engine.state',"
            "'fortress_engine.events.event_bus',"
            "'fortress_engine.engine.orchestrator',"
            "'fortress_engine.engine.episode_manager',"
            "'fortress_engine.plugins.factory',"
            "]\n"
            "bad = [m for m in forbidden if m in sys.modules]\n"
            "assert not bad, bad\n"
            "assert not hasattr(module, 'WorldState')\n"
            "assert not hasattr(module, 'EventBus')\n"
        )
        subprocess.run(
            [sys.executable, "-c", code],
            check=True,
            capture_output=True,
            cwd=str(repo_root),
        )

    def test_findings_are_typed_dataclasses_with_json_safe_data(
        self, audit_broken: Path
    ) -> None:
        report = _run_audit(audit_broken)
        for finding in report.findings:
            assert isinstance(finding, Finding)
            assert isinstance(finding.data, dict)
            json.dumps(finding.data)  # must not raise
        assert isinstance(report, AuditReport)
        assert isinstance(report.passages[0], PassageRecord)
