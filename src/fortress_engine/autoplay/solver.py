"""Autoplay solver — Stage B completability verifier (development tool).

Chunk 1 (this module) implements ``AnswerBook``, the solver's curated
knowledge base: every selected-episode macro-edge ``requires_text`` (derived)
merged with the ``passwords``/``riddle_answers`` curated in
``episodes/answers.yaml`` (per-episode mapping) or a ``--answers`` override.

Chunk 2a (this module) adds the typed verdict dataclasses (``GateDiagnosis``,
``SolveVerdict``) and the audit precondition on the ``Solver`` driver: any
``GraphAudit`` ERROR finding yields a typed negative verdict WITHOUT ever
constructing runtime engine objects.

Chunk 2b (this module) adds the BFS walk via ``Solver.solve()``: compose a
``BlindExplorer``, install a commit hook that records every kept command
and checks the goal after each one, and drive the explorer through
audit-reachable rooms in a deterministic BFS with max-turns guard.

Chunk 2c (this module) adds key-retrieval backtracking, stuck diagnosis, and
guard-exhaustion handling.
"""

from __future__ import annotations

import unicodedata
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING

import yaml

from fortress_engine.autoplay.explorer import BlindExplorer, Discovery, ExplorationEvent
from fortress_engine.autoplay.graph_audit import Finding, GraphAudit, PassageRecord
from fortress_engine.entities.loader import EntityLoader

if TYPE_CHECKING:
    from fortress_engine.entities.entity import Episode


def normalize_answer(text: str) -> str:
    """NFKD-strip-lowercase normalization key (dedup identity).

    Mirrors the engine's own text normalization, so a curated password and a
    macro-edge answer that differ only in case or diacritics still resolve to
    one knowledge-base entry.
    """
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


@dataclass(frozen=True)
class AnswerBook:
    """Knowledge base of answers the solver may speak at text-gated passages.

    Fields:
        episode_id: the selected episode.
        world_path: world directory — source of the derived macro-edge
            answers and of the default curated file ``episodes/answers.yaml``.
        answers_path: optional override file that REPLACES the default
            curated file (the derived set still applies).
    """

    episode_id: str
    world_path: Path | str
    answers_path: Path | str | None = None

    def _answers_file(self) -> Path:
        """Resolve the curated answers file (override or default)."""
        if self.answers_path is not None:
            return Path(self.answers_path)
        return Path(self.world_path) / "episodes" / "answers.yaml"

    def _derived(self) -> list[str]:
        """Every selected-episode macro-edge ``requires_text`` (as-authored)."""
        loader = EntityLoader(str(self.world_path))
        return [
            edge.requires_text
            for edge in loader.load_macro_edges(self.episode_id)
            if edge.requires_text
        ]

    def _curated(self) -> list[str]:
        """``passwords`` + ``riddle_answers`` from the curated answers file.

        An absent file yields nothing; a non-mapping shape (or a mapping
        without this episode's entry) yields nothing either.
        """
        path = self._answers_file()
        if not path.is_file():
            return []
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return []
        entry = raw.get(self.episode_id)
        if not isinstance(entry, dict):
            return []
        curated: list[str] = []
        for key in ("passwords", "riddle_answers"):
            values = entry.get(key)
            if isinstance(values, list):
                curated.extend(
                    str(value) for value in values if isinstance(value, str)
                )
        return curated

    @property
    def answers(self) -> list[str]:
        """Merged answers, deduped and sorted by normalized key.

        The derived set is authored first, then the curated set; a duplicate
        normalized key keeps its first as-authored spelling for display.
        """
        merged = [*self._derived(), *self._curated()]
        order: list[str] = []
        seen: set[str] = set()
        for text in merged:
            key = normalize_answer(text)
            if key and key not in seen:
                seen.add(key)
                order.append(text)
        return sorted(order, key=normalize_answer)


# ---------------------------------------------------------------------------
# Typed solve verdicts (chunk 2a)
# ---------------------------------------------------------------------------

GateReason = Literal[
    "answer_not_in_kb",
    "item_unreachable",
    "item_missing_from_world",
    "item_never_acquired",
    "flag_never_set",
]


@dataclass(frozen=True)
class GateDiagnosis:
    """Why one required gate could not be satisfied at the fixed point."""

    passage: str
    predicate: str
    required: str
    reason: GateReason

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe serialization with the documented field order."""
        return {
            "passage": self.passage,
            "predicate": self.predicate,
            "required": self.required,
            "reason": self.reason,
        }


@dataclass
class SolveVerdict:
    """Typed solver outcome: completable proof or a diagnosis of why not."""

    completable: bool
    episode: str
    walkthrough: list[str]
    total_turns: int
    probe_count: int
    stuck_rooms: list[str]
    unsatisfiable_gates: list[GateDiagnosis]
    static_errors: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe serialization with exactly these 8 fields, keys sorted."""
        return {
            key: value
            for key, value in sorted(
                {
                    "completable": self.completable,
                    "episode": self.episode,
                    "walkthrough": list(self.walkthrough),
                    "total_turns": self.total_turns,
                    "probe_count": self.probe_count,
                    "stuck_rooms": list(self.stuck_rooms),
                    "unsatisfiable_gates": [
                        g.to_dict() for g in self.unsatisfiable_gates
                    ],
                    "static_errors": [f.to_dict() for f in self.static_errors],
                }.items()
            )
        }


# ---------------------------------------------------------------------------
# Solver driver (chunk 2a: audit precondition only)
# ---------------------------------------------------------------------------


@dataclass
class Solver:
    """Audit-gated completability verifier (driver).

    Chunk 2a provides the static gate: ``GraphAudit`` first, and any ERROR
    finding returns a typed negative verdict without ever building a runtime.
    The ``BlindExplorer``-driven walk lands in chunk 2b.
    """

    loader: EntityLoader
    episode: "Episode"

    @staticmethod
    def _locate_item_room(
        item_id: str,
        discovery: Discovery,
        all_items: dict[str, Any],
    ) -> str | None:
        """Find where *item_id* lives: runtime discovery first, then loader."""
        room = discovery.found_items.get(item_id)
        if room is not None:
            return room
        entity = all_items.get(item_id)
        if entity is not None:
            return entity.spatial_anchor
        return None

    @staticmethod
    def _diagnose(
        blocked_rooms: dict[str, set[str]],
        passages: list[PassageRecord],
        all_items: dict[str, Any],
        discovery: Discovery,
        reachable: set[str],
        answers: list[str],
    ) -> list[GateDiagnosis]:
        """Produce one GateDiagnosis per blocked passage at the fixed point.

        Predicate priority order (first unsatisfied wins):
        requires_text → requires_item → forbids_item →
        requires_flag → forbids_flag.
        """
        result: list[GateDiagnosis] = []
        passage_index: dict[tuple[str, str], PassageRecord] = {}
        for p in passages:
            passage_index[(p.from_anchor, p.passage_name)] = p

        for room in sorted(blocked_rooms):
            for token in sorted(blocked_rooms[room]):
                precord = passage_index.get((room, token))
                if precord is None:
                    continue

                if precord.requires_text:
                    if not precord.requires_text or not any(
                        normalize_answer(precord.requires_text)
                        == normalize_answer(a)
                        for a in answers
                    ):
                        result.append(
                            GateDiagnosis(
                                passage=token,
                                predicate="requires_text",
                                required=precord.requires_text or "",
                                reason="answer_not_in_kb",
                            )
                        )
                        continue

                if precord.requires_item:
                    item_id = precord.requires_item
                    item_room = Solver._locate_item_room(
                        item_id, discovery, all_items,
                    )
                    if item_room is None:
                        result.append(
                            GateDiagnosis(
                                passage=token,
                                predicate="requires_item",
                                required=item_id,
                                reason="item_missing_from_world",
                            )
                        )
                    elif item_room not in reachable:
                        result.append(
                            GateDiagnosis(
                                passage=token,
                                predicate="requires_item",
                                required=item_id,
                                reason="item_unreachable",
                            )
                        )
                    else:
                        result.append(
                            GateDiagnosis(
                                passage=token,
                                predicate="requires_item",
                                required=item_id,
                                reason="item_never_acquired",
                            )
                        )
                    continue

                if precord.forbids_item:
                    result.append(
                        GateDiagnosis(
                            passage=token,
                            predicate="forbids_item",
                            required=precord.forbids_item,
                            reason="item_never_acquired",
                        )
                    )
                    continue

                if precord.requires_flag:
                    result.append(
                        GateDiagnosis(
                            passage=token,
                            predicate="requires_flag",
                            required=precord.requires_flag,
                            reason="flag_never_set",
                        )
                    )
                    continue

                if precord.forbids_flag:
                    result.append(
                        GateDiagnosis(
                            passage=token,
                            predicate="forbids_flag",
                            required=precord.forbids_flag,
                            reason="flag_never_set",
                        )
                    )
                    continue

                if not precord.open and not any(
                    getattr(precord, p, None)
                    for p in ("requires_text", "requires_item",
                              "forbids_item", "requires_flag", "forbids_flag")
                ):
                    result.append(
                        GateDiagnosis(
                            passage=token,
                            predicate="requires_text",
                            required="",
                            reason="answer_not_in_kb",
                        )
                    )

        result.sort(key=lambda g: (g.passage, g.predicate, g.required, g.reason))
        return result

    def _run_audit_precondition(self) -> SolveVerdict | None:
        """Run the static audit; stop on ERROR, otherwise signal proceed.

        Returns ``None`` when the audit reports zero ERROR findings (the walk
        may start), or a typed negative :class:`SolveVerdict` carrying the
        ERROR findings in ``static_errors`` — no ``WorldState``, ``EventBus``,
        or plugin is ever constructed on this path.
        """
        report = GraphAudit(self.loader, self.episode).run()
        errors = [
            finding
            for finding in report.findings
            if finding.severity == "ERROR"
        ]
        if not errors:
            return None
        return SolveVerdict(
            completable=False,
            episode=self.episode.id,
            walkthrough=[],
            total_turns=0,
            probe_count=0,
            stuck_rooms=[],
            unsatisfiable_gates=[],
            static_errors=errors,
        )

    def solve(self, max_turns: int = 50_000) -> SolveVerdict:
        """Compose a ``BlindExplorer`` and drive it through the audit-
        reachable rooms with the answer-book passwords and a commit hook
        that records every kept command and checks the goal.

        ``max_turns`` guards the turn budget (checked between sub-methods).
        Returns a typed ``SolveVerdict`` with the walkthrough ledger,
        turn count, completeness flag, and diagnosis (chunk 2c).
        """
        blocked = self._run_audit_precondition()
        if blocked is not None:
            return blocked

        audit = GraphAudit(self.loader, self.episode)
        report = audit.run()
        reachable = report.reachable_rooms

        kb = AnswerBook(
            episode_id=self.episode.id,
            world_path=str(self.loader._world_path),
        )

        explorer = BlindExplorer(str(self.loader._world_path), self.episode.id)
        explorer.passwords = set(kb.answers)

        ledger: list[str] = []

        def _hook(cmd: str) -> bool:
            ledger.append(cmd)
            if explorer.goal_eval.check(explorer.state):
                return False
            return True

        explorer.commit_hook = _hook

        start = explorer.anchor()
        if start is None:
            return SolveVerdict(
                completable=False,
                episode=self.episode.id,
                walkthrough=[],
                total_turns=0,
                probe_count=0,
                stuck_rooms=[],
                unsatisfiable_gates=[],
                static_errors=[],
            )

        discovery = Discovery()
        log: list[ExplorationEvent] = []

        queue: deque[str] = deque()
        visited: set[str] = set()
        in_queue: set[str] = set()

        if start in reachable:
            queue.append(start)
            in_queue.add(start)
            visited.add(start)
        for room in sorted(reachable - {start}):
            queue.append(room)
            in_queue.add(room)

        blocked_rooms: dict[str, set[str]] = {}
        room_sig: dict[str, tuple] = {}
        revisit: dict[str, int] = {}
        _MAX_REVISITS = 8
        probed_cmds: dict[str, set[str]] = {}
        probed_sets: dict[str, tuple[set[str], set[str]]] = {}

        all_items = self.loader.load_items(self.episode.id)
        all_items_by_id: dict[str, Any] = {e.entity_id: e for e in all_items}

        _MAX_RETRIEVALS_PER_GATE = 8
        key_retrievals: dict[str, int] = {}
        passage_index: dict[tuple[str, str], PassageRecord] = {}
        for p in report.passages:
            passage_index[(p.from_anchor, p.passage_name)] = p

        def _exceeded() -> bool:
            return explorer.turn_counter >= max_turns

        def _requeue(room: str) -> None:
            if room not in in_queue:
                queue.append(room)
                in_queue.add(room)

        def _retrieve_key(token: str, anchor: str) -> bool:
            """Navigate to item room, take item, return, re-run move pass."""
            precord = passage_index.get((anchor, token))
            if precord is None or not precord.requires_item:  # pragma: no branch
                return False  # defensive only — call site guarantees both
            item_id = precord.requires_item
            item_room = Solver._locate_item_room(
                item_id, discovery, all_items_by_id,
            )
            if item_room is None:
                return False
            if item_room == anchor:
                return False
            if item_room not in reachable:
                return False

            # Already at max retrievals for this gate
            gate_key = f"{anchor}:{token}"
            count = key_retrievals.get(gate_key, 0)
            if count >= _MAX_RETRIEVALS_PER_GATE:
                return False

            snap = explorer.snapshot()
            ledger_len = len(ledger)

            key_retrievals[gate_key] = count + 1

            if not explorer._navigate_to(item_room, discovery, log):
                explorer.restore(snap)
                del ledger[ledger_len:]
                return False

            if not explorer._take_if_present(item_id):
                explorer.restore(snap)
                del ledger[ledger_len:]
                discovery.found_items[item_id] = item_room
                return False

            discovery.found_items[item_id] = item_room

            if not explorer._navigate_to(anchor, discovery, log):
                explorer.restore(snap)
                del ledger[ledger_len:]
                return False

            explorer._movement_pass(
                anchor,
                {token} | blocked_rooms.get(anchor, set()),
                discovery,
                log,
                visited,
                queue,
                in_queue,
                blocked_rooms,
                room_snap,
            )
            return not (token in blocked_rooms.get(anchor, set()))

        while queue and not explorer.solved and not _exceeded():
            anchor = queue.popleft()
            in_queue.discard(anchor)

            if _exceeded():  # pragma: no branch — no _turn() between while check
                break

            if anchor != explorer.anchor():
                if not explorer._navigate_to(anchor, discovery, log):
                    revisit[anchor] = revisit.get(anchor, 0) + 1
                    if revisit[anchor] <= _MAX_REVISITS:
                        _requeue(anchor)
                    continue

            if _exceeded():
                break

            room_tokens = explorer._collect_room_tokens(anchor, discovery, log)
            room_snap = explorer.snapshot()

            explorer._take_present_items(anchor, discovery)

            if _exceeded():
                break

            before_blocked = set(blocked_rooms.get(anchor, set()))
            explorer._movement_pass(
                anchor,
                room_tokens | blocked_rooms.get(anchor, set()),
                discovery,
                log,
                visited,
                queue,
                in_queue,
                blocked_rooms,
                room_snap,
            )

            if _exceeded():
                break

            # Key-retrieval for newly blocked requires_item gates
            new_blocked = blocked_rooms.get(anchor, set()) - before_blocked
            for token in sorted(new_blocked):
                if _exceeded():
                    break
                precord = passage_index.get((anchor, token))
                if precord and precord.requires_item:
                    _retrieve_key(token, anchor)

            if _exceeded():
                break

            explorer._probe_actions(
                anchor, discovery, log, probed_cmds, probed_sets,
            )

            if _exceeded():
                break

            explorer._movement_pass(
                anchor,
                blocked_rooms.get(anchor, set()),
                discovery,
                log,
                visited,
                queue,
                in_queue,
                blocked_rooms,
                room_snap,
            )

            sig_now = explorer._progress_sig()
            for room in list(blocked_rooms):
                if room in visited and room_sig.get(room) != sig_now:
                    if revisit.get(room, 0) < _MAX_REVISITS:
                        revisit[room] = revisit.get(room, 0) + 1
                        _requeue(room)
            room_sig[anchor] = sig_now

        guard_exhausted = _exceeded()
        if explorer.solved:
            return SolveVerdict(
                completable=True,
                episode=self.episode.id,
                walkthrough=list(ledger),
                total_turns=explorer.turn_counter,
                probe_count=0,
                stuck_rooms=[],
                unsatisfiable_gates=[],
                static_errors=[],
            )

        stuck = sorted(
            set(reachable - visited) | set(blocked_rooms.keys())
        )

        if guard_exhausted:
            return SolveVerdict(
                completable=False,
                episode=self.episode.id,
                walkthrough=list(ledger),
                total_turns=explorer.turn_counter,
                probe_count=0,
                stuck_rooms=stuck,
                unsatisfiable_gates=[],
                static_errors=[],
            )

        diagnosis = self._diagnose(
            blocked_rooms,
            report.passages,
            all_items_by_id,
            discovery,
            reachable,
            kb.answers,
        )

        return SolveVerdict(
            completable=False,
            episode=self.episode.id,
            walkthrough=list(ledger),
            total_turns=explorer.turn_counter,
            probe_count=0,
            stuck_rooms=stuck,
            unsatisfiable_gates=diagnosis,
            static_errors=[],
        )
