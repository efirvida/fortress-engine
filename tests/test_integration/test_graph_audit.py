"""Integration tests for the autoplay graph audit against real worlds.

- ``worlds/_test_minimal`` audits clean (zero findings).
- ``worlds/fortaleza`` episodes audit without crashing; assertions are
  structural and category-only because the world is mid-rewrite and exact
  findings must never be pinned here.
"""

from __future__ import annotations

from pathlib import Path

from fortress_engine.autoplay import AuditReport, GraphAudit
from fortress_engine.entities.loader import EntityLoader

_WORLD_PATH = "worlds/fortaleza"
_MINIMAL_PATH = "worlds/_test_minimal"

_SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}
_CATEGORY_CATALOG = {
    "start_anchor_missing",
    "dangling_edge_endpoint",
    "dangling_spatial_anchor",
    "isolated_room",
    "orphan_room",
    "unreachable_room",
    "duplicate_passage",
    "self_loop_edge",
    "goal_unknown_entity",
    "entity_in_unreachable_room",
    "entity_limbo_at_load",
}


def _audit(world_path: str, episode_id: str) -> AuditReport:
    loader = EntityLoader(world_path)
    episode = next(ep for ep in loader.load_episodes() if ep.id == episode_id)
    return GraphAudit(loader, episode).run()


def _assert_structural_invariants(report: AuditReport) -> None:
    assert isinstance(report, AuditReport)
    assert report.unreachable_rooms == (
        report.declared_rooms - report.reachable_rooms
    )
    assert report.reachable_rooms <= report.declared_rooms
    for finding in report.findings:
        assert finding.severity in _SEVERITY_ORDER
        assert finding.category in _CATEGORY_CATALOG
        assert finding.location
        assert isinstance(finding.data, dict)
    ranked = [
        (
            _SEVERITY_ORDER[f.severity],
            f.category,
            f.location,
        )
        for f in report.findings
    ]
    assert ranked == sorted(ranked)


class TestMinimalWorldAudit:
    """The minimal world must audit clean."""

    def test_minimal_world_zero_findings(self) -> None:
        report = _audit(_MINIMAL_PATH, "episode-01")
        assert report.episode == "episode-01"
        assert report.declared_rooms == {"cell", "hall"}
        assert report.reachable_rooms == {"cell", "hall"}
        assert report.unreachable_rooms == set()
        assert report.findings == []
        assert len(report.passages) == 2

    def test_minimal_world_report_is_json_safe(self) -> None:
        import json

        payload = _audit(_MINIMAL_PATH, "episode-01").to_dict()
        assert json.dumps(payload, sort_keys=True)
        assert payload["declared_rooms"] == ["cell", "hall"]


class TestFortalezaAudit:
    """Fortaleza episodes audit without crashing; no pinned findings."""

    def test_episode_01_audits_without_crash(self) -> None:
        report = _audit(_WORLD_PATH, "episode-01")
        assert report.episode == "episode-01"
        assert report.declared_rooms
        assert report.passages
        _assert_structural_invariants(report)

    def test_episode_01_start_anchor_is_reachable(self) -> None:
        loader = EntityLoader(_WORLD_PATH)
        episode = next(ep for ep in loader.load_episodes() if ep.id == "episode-01")
        report = _audit(_WORLD_PATH, "episode-01")
        assert episode.start_anchor in report.reachable_rooms

    def test_episode_02_audits_without_crash(self) -> None:
        report = _audit(_WORLD_PATH, "episode-02")
        assert report.episode == "episode-02"
        assert report.declared_rooms
        _assert_structural_invariants(report)

    def test_episode_02_start_anchor_is_reachable(self) -> None:
        loader = EntityLoader(_WORLD_PATH)
        episode = next(ep for ep in loader.load_episodes() if ep.id == "episode-02")
        report = _audit(_WORLD_PATH, "episode-02")
        assert episode.start_anchor in report.reachable_rooms

    def test_fortaleza_rooms_are_under_documented_catalog(self) -> None:
        """Categories must never drift beyond the 11-finding catalog."""
        for episode_id in ("episode-01", "episode-02"):
            report = _audit(_WORLD_PATH, episode_id)
            for finding in report.findings:
                assert finding.category in _CATEGORY_CATALOG

    def test_fortaleza_fixture_dirs_exist(self) -> None:
        """Guard against path drift in the smoke worlds."""
        assert Path(_WORLD_PATH).is_dir()
        assert Path(_MINIMAL_PATH).is_dir()
