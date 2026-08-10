"""Static, world-agnostic macro-graph audit for autoplay (Stage A).

Deterministic loader-only diagnostic: one structural BFS over the expanded
macro edges from the episode start anchor, eleven integrity scans, and a
typed :class:`AuditReport`.  Gate predicates are **passive data** — copied
verbatim into :class:`PassageRecord` and never evaluated.  This module never
constructs ``WorldState``, ``EventBus``, plugins, or the runtime graph.

Determinism rules:
- Findings sort by ``(severity ERROR=0/WARN=1/INFO=2, category, location)``.
- Passage records sort by all ten serialized fields (``repr``-normalized so
  ``None``/booleans/strings form a total order).
- Sets serialize as sorted lists in :meth:`AuditReport.to_dict`.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from fortress_engine.entities.entity import GoalCondition, GoalConditions
from fortress_engine.entities.loader import EntityLoader

if TYPE_CHECKING:
    from fortress_engine.engine.graph import HyperEdge, MacroEdge
    from fortress_engine.entities.entity import Episode

_SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


# ---------------------------------------------------------------------------
# Typed records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single audit finding with deterministic, JSON-safe payload."""

    severity: str
    category: str
    location: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize as a JSON-safe dict."""
        return {
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "message": self.message,
            "data": self.data,
        }


@dataclass(frozen=True)
class PassageRecord:
    """Passive gate data for one expanded macro edge (never evaluated)."""

    from_anchor: str
    to_anchor: str
    passage_name: str
    requires_item: str | None
    forbids_item: str | None
    requires_flag: str | None
    forbids_flag: str | None
    requires_text: str | None
    open: bool
    direction: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize with the exact documented field order and key names."""
        return {
            "from": self.from_anchor,
            "to": self.to_anchor,
            "passage_name": self.passage_name,
            "requires_item": self.requires_item,
            "forbids_item": self.forbids_item,
            "requires_flag": self.requires_flag,
            "forbids_flag": self.forbids_flag,
            "requires_text": self.requires_text,
            "open": self.open,
            "direction": self.direction,
        }


@dataclass
class AuditReport:
    """Typed audit result for one episode."""

    episode: str
    declared_rooms: set[str]
    reachable_rooms: set[str]
    unreachable_rooms: set[str]
    passages: list[PassageRecord]
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        """Serialize with sets as sorted lists (JSON-safe, deterministic)."""
        return {
            "episode": self.episode,
            "declared_rooms": sorted(self.declared_rooms),
            "reachable_rooms": sorted(self.reachable_rooms),
            "unreachable_rooms": sorted(self.unreachable_rooms),
            "passages": [p.to_dict() for p in self.passages],
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Goal reference helpers
# ---------------------------------------------------------------------------


def _walk_goal_conditions(goal: GoalConditions):
    """Yield ``(path, condition)`` for every atomic goal condition.

    Composite ``and``/``or`` dicts are traversed recursively; the path is the
    index trail, e.g. ``conditions[0].or[1].flag``.  Atomic conditions nested
    inside composites arrive as raw dicts (the loader only converts the
    top level), so they are normalized before yielding.
    """
    for index, item in enumerate(goal.conditions):
        yield from _walk_goal_item(item, f"conditions[{index}]")


def _walk_goal_item(item: GoalCondition | dict[str, Any], path: str):
    """Yield atomic conditions under *item*, extending *path*."""
    if isinstance(item, dict):
        if "and" in item or "or" in item:
            for key, children in item.items():
                if key not in ("and", "or"):
                    continue
                for index, child in enumerate(children):
                    yield from _walk_goal_item(
                        child, f"{path}.{key}[{index}]"
                    )
        else:
            yield path, _as_goal_condition(item)
    else:
        yield path, item


def _as_goal_condition(item: dict[str, Any]) -> GoalCondition:
    """Normalize an atomic condition dict (flat or nested params)."""
    params = item.get("params")
    if isinstance(params, dict):
        return GoalCondition(type=item.get("type", ""), params=dict(params))
    return GoalCondition(
        type=item.get("type", ""),
        params={k: v for k, v in item.items() if k != "type"},
    )


def _goal_references(condition: "GoalCondition"):
    """Yield ``(parameter, value)`` pairs a condition type recognizes."""
    ctype = condition.type
    params = condition.params
    if ctype in ("entity_in_room", "entity_not_in_room"):
        for param in ("entity", "room"):
            if param in params:
                yield param, params[param]
    elif ctype in ("entity_dead", "entity_has_component"):
        if "entity" in params:
            yield "entity", params["entity"]
    elif ctype in ("flag_is_set", "flag_is_not_set"):
        if "flag" in params:
            yield "flag", params["flag"]


def _goal_value_known(
    parameter: str,
    value: Any,
    entity_ids: set[str],
    room_ids: set[str],
    known_flags: set[str],
) -> bool:
    """Whether a goal reference names known structural data (not judged)."""
    if parameter == "entity":
        return value in entity_ids
    if parameter == "room":
        return value in room_ids
    if parameter == "flag":
        return value in known_flags
    return True


# ---------------------------------------------------------------------------
# GraphAudit
# ---------------------------------------------------------------------------


@dataclass
class GraphAudit:
    """Static macro-graph audit over loader data for a single episode.

    Pure math: builds local adjacency from the expanded edge list, runs one
    BFS ignoring ``open`` and every predicate, scans integrity, and returns a
    typed report.  Never touches runtime engine state.
    """

    loader: EntityLoader
    episode: "Episode"

    def run(self) -> AuditReport:
        """Audit the episode and return the typed report."""
        episode_id = self.episode.id
        rooms = self.loader.load_rooms(episode_id)
        items = self.loader.load_items(episode_id)
        npcs = self.loader.load_npcs(episode_id)
        shared = self.loader.load_shared_entities(episode_id)
        edges = self.loader.load_macro_edges(episode_id)
        hyper_edges = self.loader.load_hyper_edges(episode_id)

        room_ids = {e.entity_id for e in rooms}
        entity_ids = {e.entity_id for e in rooms + items + npcs + shared}

        reachable = self._bfs(self.episode.start_anchor, room_ids, edges)
        passages = self._passage_records(edges)

        findings: list[Finding] = []
        findings.extend(self._scan_start_anchor(room_ids))
        findings.extend(self._scan_dangling_edges(edges, room_ids))
        findings.extend(
            self._scan_placed_entities(
                items + npcs, entity_ids, room_ids, reachable, episode_id
            )
        )
        findings.extend(
            self._scan_rooms(edges, room_ids, reachable, self.episode.start_anchor)
        )
        findings.extend(self._scan_duplicates(edges))
        findings.extend(self._scan_self_loops(edges))
        findings.extend(
            self._scan_goals(hyper_edges, edges, entity_ids, room_ids)
        )
        findings.sort(
            key=lambda f: (_SEVERITY_ORDER[f.severity], f.category, f.location)
        )

        return AuditReport(
            episode=episode_id,
            declared_rooms=set(room_ids),
            reachable_rooms=reachable,
            unreachable_rooms=set(room_ids) - reachable,
            passages=passages,
            findings=findings,
        )

    # -------------------------------------------------------------------
    # BFS
    # -------------------------------------------------------------------

    @staticmethod
    def _bfs(
        start: str, room_ids: set[str], edges: list["MacroEdge"]
    ) -> set[str]:
        """Reachable rooms from *start* over every edge, gates ignored.

        A missing start yields an empty set; dangling endpoints never become
        declared rooms; self-loops are visited once.
        """
        outgoing: dict[str, list["MacroEdge"]] = {}
        for edge in edges:
            outgoing.setdefault(edge.from_anchor, []).append(edge)

        if start not in room_ids:
            return set()

        reachable: set[str] = set()
        queue: deque[str] = deque([start])
        while queue:
            room = queue.popleft()
            if room in reachable:
                continue
            reachable.add(room)
            for edge in outgoing.get(room, []):
                if (
                    edge.to_anchor in room_ids
                    and edge.to_anchor not in reachable
                ):
                    queue.append(edge.to_anchor)
        return reachable

    @staticmethod
    def _passage_records(edges: list["MacroEdge"]) -> list[PassageRecord]:
        """One passive record per expanded edge, sorted by all fields."""
        records = [
            PassageRecord(
                from_anchor=e.from_anchor,
                to_anchor=e.to_anchor,
                passage_name=e.passage_name,
                requires_item=e.requires_item,
                forbids_item=e.forbids_item,
                requires_flag=e.requires_flag,
                forbids_flag=e.forbids_flag,
                requires_text=e.requires_text,
                open=e.open,
                direction=e.direction,
            )
            for e in edges
        ]
        return sorted(
            records,
            key=lambda r: tuple(
                repr(value) for value in r.to_dict().values()
            ),
        )

    # -------------------------------------------------------------------
    # Integrity scans
    # -------------------------------------------------------------------

    def _scan_start_anchor(self, room_ids: set[str]) -> list[Finding]:
        start = self.episode.start_anchor
        if start in room_ids:
            return []
        return [
            Finding(
                severity="ERROR",
                category="start_anchor_missing",
                location=f"episode:{self.episode.id}.start_anchor",
                message=f"Start anchor '{start}' is not a declared room",
                data={"episode": self.episode.id, "start": start},
            )
        ]

    @staticmethod
    def _scan_dangling_edges(
        edges: list["MacroEdge"], room_ids: set[str]
    ) -> list[Finding]:
        findings: list[Finding] = []
        for edge in edges:
            for endpoint, value in (
                ("from", edge.from_anchor),
                ("to", edge.to_anchor),
            ):
                if value in room_ids:
                    continue
                findings.append(
                    Finding(
                        severity="ERROR",
                        category="dangling_edge_endpoint",
                        location=f"edge:{edge.macro_edge_id}.{endpoint}",
                        message=(
                            f"Edge '{edge.macro_edge_id}' endpoint "
                            f"'{endpoint}' references missing anchor '{value}'"
                        ),
                        data={
                            "edge": edge.macro_edge_id,
                            "from": edge.from_anchor,
                            "to": edge.to_anchor,
                            "missing": value,
                        },
                    )
                )
        return findings

    @staticmethod
    def _scan_placed_entities(
        placed: list[Any],
        entity_ids: set[str],
        room_ids: set[str],
        reachable: set[str],
        episode_id: str,
    ) -> list[Finding]:
        """Limbo (INFO), dangling anchor (ERROR), unreachable room (WARN)."""
        findings: list[Finding] = []
        for entity in placed:
            anchor = entity.spatial_anchor
            if anchor is None:
                findings.append(
                    Finding(
                        severity="INFO",
                        category="entity_limbo_at_load",
                        location=f"entity:{entity.entity_id}.spatial_anchor",
                        message=(
                            f"Entity '{entity.entity_id}' is in limbo at "
                            "load (no spatial anchor)"
                        ),
                        data={"episode": episode_id, "entity": entity.entity_id},
                    )
                )
            elif anchor not in entity_ids:
                findings.append(
                    Finding(
                        severity="ERROR",
                        category="dangling_spatial_anchor",
                        location=f"entity:{entity.entity_id}.spatial_anchor",
                        message=(
                            f"Entity '{entity.entity_id}' is anchored to "
                            f"unknown entity '{anchor}'"
                        ),
                        data={
                            "episode": episode_id,
                            "entity": entity.entity_id,
                            "anchor": anchor,
                        },
                    )
                )
            elif anchor in room_ids and anchor not in reachable:
                findings.append(
                    Finding(
                        severity="WARN",
                        category="entity_in_unreachable_room",
                        location=f"entity:{entity.entity_id}.spatial_anchor",
                        message=(
                            f"Entity '{entity.entity_id}' is placed in "
                            f"unreachable room '{anchor}'"
                        ),
                        data={
                            "episode": episode_id,
                            "entity": entity.entity_id,
                            "anchor": anchor,
                        },
                    )
                )
        return findings

    @staticmethod
    def _scan_rooms(
        edges: list["MacroEdge"],
        room_ids: set[str],
        reachable: set[str],
        start: str,
    ) -> list[Finding]:
        """isolated (ERROR) / orphan (WARN) / unreachable (WARN) per room."""
        incoming: dict[str, int] = {}
        outgoing: dict[str, list[str]] = {}
        for edge in edges:
            outgoing.setdefault(edge.from_anchor, []).append(edge.macro_edge_id)
            incoming[edge.to_anchor] = incoming.get(edge.to_anchor, 0) + 1

        findings: list[Finding] = []
        for room in sorted(room_ids):
            has_in = incoming.get(room, 0) > 0
            out_ids = outgoing.get(room, [])
            if room != start:
                if not has_in and not out_ids:
                    findings.append(
                        Finding(
                            severity="ERROR",
                            category="isolated_room",
                            location=f"room:{room}",
                            message=(
                                f"Room '{room}' has no incoming or "
                                "outgoing edges"
                            ),
                            data={"room": room},
                        )
                    )
                elif not has_in:
                    findings.append(
                        Finding(
                            severity="WARN",
                            category="orphan_room",
                            location=f"room:{room}",
                            message=f"Room '{room}' has no incoming edges",
                            data={
                                "room": room,
                                "outgoing_edges": sorted(out_ids),
                            },
                        )
                    )
            if room not in reachable:
                findings.append(
                    Finding(
                        severity="WARN",
                        category="unreachable_room",
                        location=f"room:{room}",
                        message=(
                            f"Room '{room}' is not reachable from the "
                            "start anchor"
                        ),
                        data={"room": room},
                    )
                )
        return findings

    @staticmethod
    def _scan_duplicates(edges: list["MacroEdge"]) -> list[Finding]:
        """WARN for repeated ``(from, to, passage_name)`` edge groups."""
        grouped: dict[tuple[str, str, str], list[str]] = {}
        for edge in edges:
            key = (edge.from_anchor, edge.to_anchor, edge.passage_name)
            grouped.setdefault(key, []).append(edge.macro_edge_id)

        findings: list[Finding] = []
        for (from_anchor, to_anchor, passage), ids in grouped.items():
            if len(ids) < 2:
                continue
            findings.append(
                Finding(
                    severity="WARN",
                    category="duplicate_passage",
                    location=f"passage:{from_anchor}->{to_anchor}:{passage}",
                    message=(
                        f"Duplicate passage '{passage}' from "
                        f"'{from_anchor}' to '{to_anchor}'"
                    ),
                    data={
                        "tuple": [from_anchor, to_anchor, passage],
                        "edge_ids": sorted(ids),
                    },
                )
            )
        return findings

    @staticmethod
    def _scan_self_loops(edges: list["MacroEdge"]) -> list[Finding]:
        findings: list[Finding] = []
        for edge in edges:
            if edge.from_anchor != edge.to_anchor:
                continue
            findings.append(
                Finding(
                    severity="WARN",
                    category="self_loop_edge",
                    location=f"edge:{edge.macro_edge_id}",
                    message=(
                        f"Edge '{edge.macro_edge_id}' is a self-loop on "
                        f"anchor '{edge.from_anchor}'"
                    ),
                    data={
                        "edge": edge.macro_edge_id,
                        "anchor": edge.from_anchor,
                        "passage": edge.passage_name,
                    },
                )
            )
        return findings

    def _scan_goals(
        self,
        hyper_edges: list["HyperEdge"],
        edges: list["MacroEdge"],
        entity_ids: set[str],
        room_ids: set[str],
    ) -> list[Finding]:
        """WARN when a goal names unknown structural data (data integrity)."""
        known_flags = self._known_flags(hyper_edges, edges)
        findings: list[Finding] = []
        for path, condition in _walk_goal_conditions(self.episode.goal):
            for parameter, value in _goal_references(condition):
                if _goal_value_known(
                    parameter, value, entity_ids, room_ids, known_flags
                ):
                    continue
                findings.append(
                    Finding(
                        severity="WARN",
                        category="goal_unknown_entity",
                        location=f"goal:{path}.{parameter}",
                        message=(
                            f"Goal references unknown {parameter} '{value}'"
                        ),
                        data={
                            "goal": path,
                            "parameter": parameter,
                            "value": value,
                        },
                    )
                )
        return findings

    @staticmethod
    def _known_flags(
        hyper_edges: list["HyperEdge"], edges: list["MacroEdge"]
    ) -> set[str]:
        """Flag names from FLAG operators and macro gate predicates only."""
        flags: set[str] = set()
        for edge in edges:
            for name in (edge.requires_flag, edge.forbids_flag):
                if name is not None:
                    flags.add(name)
        for hyper_edge in hyper_edges:
            for operator in hyper_edge.operators:
                if not isinstance(operator, dict):
                    continue
                op_type = operator.get("type") or operator.get("op")
                if op_type == "FLAG":
                    flag = operator.get("flag")
                    if flag:
                        flags.add(flag)
        return flags
