"""Action domain — world-agnostic candidate commands and an advisory heuristic.

Dev tooling for the definition-driven solver (docs/15-solver-planner-design.md,
including its "Design reconciliation", which supersedes the Grounding text).

* ``candidates`` turns the macro/hyper edges the world defines into command
  strings and verifies each one with the real parser (``runtime.parse``).
  Nothing is dropped silently: commands the parser cannot reproduce are
  recorded as ``unrenderable`` and edges whose participants are absent as
  ``skipped``, each with a reason.
* The delete-free model (``ActionDomain.h`` / ``rank``) is ADVISORY ONLY. It
  orders candidates but never removes one, never reports an impossibility and
  never returns an infinite cost: a fact the model cannot derive gets
  ``UNREACHED_COST`` because the model under-approximates the engine
  (deletions, failed preconditions and unmodelled operators are invisible to it).
* The ground-truth transition stays the real engine behind ``GameRuntime``.

No world vocabulary, ids or entity types appear here: words come from the
world's ``Vocabulary``, the protagonist from ``runtime.protagonist_id``, and
``Entity.type`` is never read.
"""

from __future__ import annotations

import itertools
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fortress_engine.autoplay.runtime import GameRuntime
    from fortress_engine.engine.graph import HyperEdge, MacroEdge

# Relaxed facts, as tuples: ("at", anchor), ("loc", entity, container),
# ("gone", entity), ("flag", name), ("comp", entity, key, repr(value)) and the
# derived ("here", entity) = within reach of the protagonist.
Fact = tuple[Any, ...]

# Advisory stand-in for "the relaxed model cannot derive this goal atom".
UNREACHED_COST = 100.0


@dataclass(frozen=True)
class CommandSpec:
    """What a command means, independent of its rendering."""

    kind: str  # "move" | "act"
    verb: str
    target: str | None = None
    context: str | None = None
    instrument: str | None = None
    passage: str | None = None
    speech: str | None = None
    edge_id: str = ""


@dataclass(frozen=True)
class RAction:
    """A grounded action with its relaxed preconditions/additions.

    ``command`` is ``None`` only in the static relaxed model; every action in
    a :class:`CandidateSet` was rendered and verified by the parser.
    """

    spec: CommandSpec
    pre: frozenset[Fact]
    add: frozenset[Fact]
    command: str | None = None


@dataclass(frozen=True)
class Rejected:
    """A spec that is not a candidate right now, with the reason."""

    spec: CommandSpec
    reason: str


@dataclass(frozen=True)
class CandidateSet:
    """Candidate commands for the current state, plus everything left out."""

    actions: tuple[RAction, ...] = ()
    unrenderable: tuple[Rejected, ...] = ()
    skipped: tuple[Rejected, ...] = ()

    def commands(self) -> tuple[str, ...]:
        """Distinct rendered commands in order (several edges may share one)."""
        return tuple(dict.fromkeys(a.command for a in self.actions if a.command))


def _fold(text: str) -> str:
    """Lowercase and strip diacritics, as the engine does for spoken text."""
    text = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _split(item: Any) -> tuple[str, Any]:
    """Return ``("and"|"or", children)`` or ``(condition type, params)``."""
    if isinstance(item, dict):
        for op in ("and", "or"):
            if op in item:
                return op, item[op]
        kind, params = item.get("type"), item.get("params") or item
    else:  # a GoalCondition; the loader only produces these two shapes
        kind, params = item.type, item.params
    if kind in ("and", "or"):
        return kind, params.get("conditions", [])
    return kind, params


def _goal_fact(kind: str, params: dict[str, Any], protagonist: str) -> Fact | None:
    """Map a positive goal atom to a relaxed fact; negative atoms map to None."""
    entity = params.get("entity")
    if kind == "flag_is_set":
        return ("flag", params.get("flag"))
    if kind == "entity_in_room":
        if entity == protagonist:
            return ("at", params.get("room"))
        return ("loc", entity, params.get("room"))
    if kind == "entity_dead":
        return ("gone", entity)
    if kind == "entity_has_component":
        return ("comp", entity, params.get("component"), repr(params.get("value")))
    return None


def _goal_facts(item: Any, protagonist: str) -> Iterator[Fact]:
    kind, body = _split(item)
    if kind in ("and", "or"):
        for child in body:
            yield from _goal_facts(child, protagonist)
    else:
        fact = _goal_fact(kind, body, protagonist)
        if fact is not None:
            yield fact


def _goal_cost(item: Any, cost: dict[Fact, float], protagonist: str) -> float:
    kind, body = _split(item)
    if kind in ("and", "or"):
        parts = [_goal_cost(child, cost, protagonist) for child in body]
        return sum(parts) if kind == "and" else min(parts, default=0.0)
    fact = _goal_fact(kind, body, protagonist)
    return 0.0 if fact is None else cost.get(fact, UNREACHED_COST)


class ActionDomain:
    """Candidate generation plus the advisory delete-free model of one runtime."""

    def __init__(self, runtime: GameRuntime) -> None:
        self._rt = runtime
        self._pid = runtime.protagonist_id
        voc = runtime.vocabulary
        self._prepositions = voc.prepositions if voc else {}
        self._movement = list(voc.movement_verbs) if voc else []
        self._markers = list(voc.speech_markers) if voc else []

        graph = runtime.graph
        self._macro = tuple(graph.iter_macro_edges())
        # Rooms are whatever the macro graph connects — never found by type.
        self._endpoints = {a for e in self._macro for a in (e.from_anchor, e.to_anchor)}
        # An edge registered under several anchors is one edge.
        self._hyper = tuple({id(e): e for e in graph.iter_hyper_edges()}.values())
        self._verbs = tuple(dict.fromkeys(e.clique.verb for e in self._hyper))

        universe = sorted(
            eid for eid in runtime.state.entities
            if eid != self._pid and eid not in self._endpoints
        )
        self.actions: tuple[RAction, ...] = tuple(
            self._move(edge) for edge in self._macro
        ) + tuple(a for edge in self._hyper for a in self._ground(edge, universe))

        episode = next(
            e for e in runtime.loader.load_episodes() if e.id == runtime.episode_id
        )
        self._goal = tuple(episode.goal.conditions)
        facts = {f for a in self.actions for f in a.pre | a.add}
        facts.update(f for item in self._goal for f in _goal_facts(item, self._pid))
        self._tracked: dict[str, set[str]] = {}
        for fact in facts:
            if fact[0] == "comp":
                self._tracked.setdefault(fact[1], set()).add(fact[2])

    # ------------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------------

    def candidates(self) -> CandidateSet:
        """Rendered, parser-verified commands for the current state."""
        rt, here = self._rt, self._rt.anchor()
        if here is None:
            return CandidateSet()
        present = {
            eid for eid, e in rt.state.entities.items()
            if eid != self._pid and e.spatial_anchor in (here, self._pid)
        }
        universe = sorted(present)
        actions: list[RAction] = []
        unrenderable: list[Rejected] = []
        skipped: list[Rejected] = []

        def render(action: RAction) -> None:
            command, reason = self._render(action.spec)
            if command is None:
                unrenderable.append(Rejected(action.spec, reason))
            else:
                actions.append(replace(action, command=command))

        for edge in self._macro:
            if edge.from_anchor == here:
                render(self._move(edge))
        for verb in self._verbs:
            for edge in rt.graph.get_hyper_edges_for_verb(here, verb):
                c = edge.clique
                slots = (("target", c.target), ("context", c.context),
                         ("instrument", c.instrument))
                absent = next(
                    (f"{slot} {ref!r} not present" for slot, ref in slots
                     if ref not in (None, "*", "player", self._pid)
                     and ref not in present),
                    None,
                )
                wildcard = next(
                    (slot for slot in ("target", "instrument")
                     if getattr(c, slot) == "*"),
                    None,
                )
                if absent is None and wildcard is not None and not universe:
                    absent = f"no entity present for {wildcard} wildcard"
                if absent is not None:
                    spec = self._spec(edge, c.target, c.context, c.instrument)
                    skipped.append(Rejected(spec, absent))
                    continue
                for action in self._ground(edge, universe):
                    render(action)
        return CandidateSet(tuple(actions), tuple(unrenderable), tuple(skipped))

    # ------------------------------------------------------------------
    # Grounding
    # ------------------------------------------------------------------

    def _move(self, edge: MacroEdge) -> RAction:
        # A closed text gate is opened by speaking its text; an open one is not.
        speech = edge.requires_text if not edge.open else None
        pre = {("at", edge.from_anchor)}
        if edge.requires_item is not None:
            pre.add(("loc", edge.requires_item, self._pid))
        if edge.requires_flag is not None:
            pre.add(("flag", edge.requires_flag))
        spec = CommandSpec(
            "move", self._movement[0] if self._movement else "",
            passage=edge.passage_name, speech=speech, edge_id=edge.macro_edge_id,
        )
        return RAction(spec, frozenset(pre), frozenset({("at", edge.to_anchor)}))

    def _spec(self, edge: HyperEdge, target, context, instrument) -> CommandSpec:
        def resolve(ref: str | None) -> str | None:
            return self._pid if ref == "player" else ref

        return CommandSpec(
            "act", edge.clique.verb, resolve(target), resolve(context),
            resolve(instrument), edge_id=edge.hyper_edge_id,
        )

    def _ground(self, edge: HyperEdge, universe: list[str]) -> Iterator[RAction]:
        """One action per grounding of the target/instrument wildcards."""
        c = edge.clique
        targets = universe if c.target == "*" else [c.target]
        instruments = universe if c.instrument == "*" else [c.instrument]
        for target, instrument in itertools.product(targets, instruments):
            spec = self._spec(edge, target, c.context, instrument)
            pre, add = self._effects(edge, spec)
            yield RAction(spec, frozenset(pre), frozenset(add))

    def _effects(self, edge: HyperEdge, spec: CommandSpec) -> tuple[set[Fact], set[Fact]]:
        """Static reading of the clique and the five operators (additions only)."""
        c, target = edge.clique, spec.target
        pre: set[Fact] = {
            ("here", ref) for ref in (spec.target, spec.context, spec.instrument)
            if ref is not None and ref != self._pid
        }
        if c.flag is not None:
            pre.add(("flag", c.flag))
        if c.component and target is not None:
            pre.update(("comp", target, k, repr(v)) for k, v in c.component.items())
        add: set[Fact] = set()
        for op in edge.operators:
            kind = op.get("type")
            entity = target if op.get("entity") == "*" else op.get("entity")
            if kind == "TRANSFER" and entity is not None:
                to = op.get("to_container")
                add.add(("gone", entity) if to is None else ("loc", entity, to))
            elif kind == "TRANSFORM" and entity is not None:
                key = op.get("component")
                if op.get("old_value") is not None:
                    pre.add(("comp", entity, key, repr(op["old_value"])))
                add.add(("comp", entity, key, repr(op.get("new_value"))))
            elif kind == "COMBINE":
                for source in op.get("input_entities") or []:
                    pre.add(("here", source))
                    add.add(("gone", source))
                add.add(("here", op.get("output_entity")))
            elif kind == "FLAG" and op.get("value"):
                add.add(("flag", op.get("flag")))
            elif kind == "TELEPORT" and entity is not None:
                to = op.get("to_anchor")
                add.add(("at", to) if entity == self._pid else ("loc", entity, to))
        return pre, add

    # ------------------------------------------------------------------
    # Rendering (verified by the real parser)
    # ------------------------------------------------------------------

    def _render(self, spec: CommandSpec) -> tuple[str | None, str]:
        """Return ``(command, "")`` or ``(None, reason)``."""
        rt = self._rt
        if spec.kind == "move":
            if not self._movement:
                return None, "no movement verb in vocabulary"
            words = [spec.verb, spec.passage]
            if spec.speech is not None:
                if not self._markers:
                    return None, "no speech marker in vocabulary"
                words += [self._markers[0], spec.speech]
            command = " ".join(words)
            parsed = rt.parse(command)
            if parsed.verb not in self._movement:
                return None, (
                    f"parser resolved verb {parsed.verb!r}, "
                    f"expected one of {self._movement!r}"
                )
            if parsed.target != spec.passage:
                return None, (
                    f"parser resolved target {parsed.target!r}, "
                    f"expected {spec.passage!r}"
                )
            if spec.speech is not None and _fold(parsed.text or "") != _fold(spec.speech):
                return None, (
                    f"parser resolved text {parsed.text!r}, expected {spec.speech!r}"
                )
            return command, ""

        names = rt.state.entities
        words = [spec.verb]
        if spec.target is not None:
            words.append(names[spec.target].name)
        for role, preposition_kind, ref in (
            ("context", "recipient", spec.context),
            ("instrument", "instrument", spec.instrument),
        ):
            if ref is None:
                continue
            prepositions = self._prepositions.get(preposition_kind)
            if not prepositions:
                return None, f"no {preposition_kind} preposition in vocabulary"
            words += [prepositions[0], names[ref].name]
        command = " ".join(words)
        parsed = rt.parse(command)
        for role, want in (
            ("verb", spec.verb), ("target", spec.target),
            ("context", spec.context), ("instrument", spec.instrument),
        ):
            got = getattr(parsed, role)
            if got != want:
                return None, f"parser resolved {role} {got!r}, expected {want!r}"
        return command, ""

    # ------------------------------------------------------------------
    # Advisory delete-free heuristic
    # ------------------------------------------------------------------

    def facts(self) -> frozenset[Fact]:
        """Relaxed facts of the runtime's current state."""
        state, facts = self._rt.state, set()
        for eid, entity in state.entities.items():
            if eid == self._pid:
                if entity.spatial_anchor is not None:
                    facts.add(("at", entity.spatial_anchor))
            elif eid not in self._endpoints:
                if entity.spatial_anchor is None:
                    facts.add(("gone", eid))
                else:
                    facts.add(("loc", eid, entity.spatial_anchor))
                for key in self._tracked.get(eid, ()):
                    if key in entity.components:
                        facts.add(("comp", eid, key, repr(entity.components[key])))
        facts.update(("flag", name) for name, value in state.flag_book.items() if value)
        return frozenset(facts)

    def _costs(self, facts: frozenset[Fact]) -> dict[Fact, float]:
        """h-add cost of every fact reachable in the delete-free closure."""
        cost: dict[Fact, float] = {fact: 0.0 for fact in facts}
        changed = True
        while changed:
            changed = False
            for action in self.actions:
                pre = [cost.get(p) for p in action.pre]
                if None in pre:
                    continue
                total = 1.0 + sum(pre)
                for fact in action.add:
                    if total < cost.get(fact, float("inf")):
                        cost[fact] = total
                        changed = True
            # ("here", e): e is carried, or shares the room the protagonist is at.
            for fact in [f for f in cost if f[0] == "loc"]:
                _, entity, container = fact
                if container == self._pid:
                    reach = cost[fact]
                elif ("at", container) in cost:
                    reach = cost[fact] + cost[("at", container)]
                else:
                    continue
                if reach < cost.get(("here", entity), float("inf")):
                    cost[("here", entity)] = reach
                    changed = True
        return cost

    def _total(self, cost: dict[Fact, float]) -> float:
        return sum(_goal_cost(item, cost, self._pid) for item in self._goal)

    def h(self, facts: frozenset[Fact]) -> float:
        """Advisory estimate of the remaining effort; finite and pure."""
        return self._total(self._costs(facts))

    def rank(self, candidates: CandidateSet, facts: frozenset[Fact]) -> CandidateSet:
        """Reorder ``candidates.actions`` best-first; never removes any.

        Enabled actions (every relaxed precondition already true) come first,
        then lower estimated cost after the action, then the original order.
        """
        base = self._costs(facts)
        current = self._total(base)

        def key(entry: tuple[int, RAction]) -> tuple[int, float, int]:
            index, action = entry
            missing = sum(1 for p in action.pre if base.get(p, float("inf")) > 0)
            after = current if action.add <= facts else self.h(facts | action.add)
            return missing, after, index

        ordered = sorted(enumerate(candidates.actions), key=key)
        return replace(candidates, actions=tuple(a for _, a in ordered))


def candidates(runtime: GameRuntime) -> CandidateSet:
    """Candidate commands for *runtime*'s current state (see :class:`ActionDomain`)."""
    return ActionDomain(runtime).candidates()
