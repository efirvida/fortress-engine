"""Dual Graph Engine — macro navigation and anchor-scoped micro action lookup.

Follows dual-graph spec, participation-cliques spec, and tdd.md Suite 4.2.
Entity-agnostic: no entity type constants, no type validation.
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.entities.entity import Entity, ParsedCommand
    from fortress_engine.engine.state import WorldState


# ---------------------------------------------------------------------------
# Clique — participation predicate for a HyperEdge
# ---------------------------------------------------------------------------


@dataclass
class Clique:
    """Participation clique that must be satisfied for a HyperEdge to fire.

    All fields except ``verb`` default to ``None``.  The clique does **not**
    interpret entity types — it only checks presence, location, flags, and
    raw component equality (GDD 2.3, participation-cliques spec).

    Attributes:
        subject: Who performs the action ("player" → active protagonist).
        verb: Exact verb match required.
        target: Entity acted upon. ``"*"`` matches any entity present.
        context: Optional contextual entity (same presence rules as target).
        instrument: Required instrument entity_id, or ``"*"`` for any.
        instrument_not: Forbidden instrument — clique fails if present.
        instrument_any: ``True`` → any portable item in inventory satisfies
            instrument.
        flag: Required flag must be ``True``.
        flag_not: Forbidden flag must be ``False`` or absent.
        component: ``{key: value}`` → target entity ``components[key] == value``.
    """

    subject: str | None = None
    verb: str = ""
    target: str | None = None
    context: str | None = None
    instrument: str | None = None
    instrument_not: str | None = None
    instrument_any: bool = False
    flag: str | None = None
    flag_not: str | None = None
    component: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# HyperEdge — micro action with a Clique gate
# ---------------------------------------------------------------------------


@dataclass
class HyperEdge:
    """An anchor-scoped action gated by a participation :class:`Clique`.

    Attributes:
        hyper_edge_id: Unique identifier.
        name: Human-readable label.
        priority: Higher = evaluated first when multiple edges match.
        clique: Participation predicate.
        operators: List of operator dicts executed when the edge fires.
        output: Narration text emitted after operator execution.
    """

    hyper_edge_id: str
    name: str
    priority: int
    clique: Clique
    operators: list[dict[str, Any]] = field(default_factory=list)
    output: str | None = None


# ---------------------------------------------------------------------------
# MacroEdge — connection between two spatial anchors
# ---------------------------------------------------------------------------


@dataclass
class MacroEdge:
    """A traversable connection between two spatial anchors (rooms).

    Gates are GENERIC predicates, evaluated uniformly — there is no
    connection-type field.  The world creator decides semantics by which
    predicate fields they set:

    - ``requires_text`` + ``open=False``: a closed edge that unlocks when
      the player says the right text (e.g. a password or a riddle answer).
    - ``question``: optional riddle/puzzle text shown by the narrator. It
      is world data for narration only — never evaluated by the engine.
    - ``requires_item``/``forbids_item``: item-inventory gates.
    - ``requires_flag``/``forbids_flag``: world-flag gates.
    - ``death_message``: makes a failed gate FATAL instead of blocked.

    A plain edge with no predicate fields is always passable.

    Entity-agnostic: fields use ``from_anchor`` / ``to_anchor``.

    Attributes:
        macro_edge_id: Unique identifier.
        from_anchor: Source anchor entity_id.
        to_anchor: Destination anchor entity_id.
        direction: ``"bidirectional"`` or ``"unidirectional"``.
        passage_name: Name the player uses to reference this passage.
        passage_description: Flavour text.
        question: Optional riddle/puzzle text (narration only, not
            evaluated).
        requires_text: Text the player must say to unlock a closed edge.
        requires_item: Item that must be in the protagonist's inventory.
        forbids_item: Item that must NOT be in the inventory.
        requires_flag: World flag that must be ``True``.
        forbids_flag: World flag that must be ``False``/absent.
        death_message: Fatal consequence; if a gate fails AND this is set,
            the edge kills instead of blocking.
        open: Mutable — ``True`` means the edge is unlocked.
    """

    macro_edge_id: str
    from_anchor: str
    to_anchor: str
    direction: str
    passage_name: str
    passage_description: str = ""
    question: str | None = None
    requires_text: str | None = None
    requires_item: str | None = None
    forbids_item: str | None = None
    requires_flag: str | None = None
    forbids_flag: str | None = None
    death_message: str | None = None
    open: bool = True


# ---------------------------------------------------------------------------
# MacroGateResult — structured gate validation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MacroGateResult:
    """Structured result of macro edge gate validation.

    Replaces ``(bool, str | None)`` so that the engine can route death-vs-block
    without string equality and the narrator receives stable codes for rendering.

    Attributes:
        is_valid: ``True`` iff all gates passed.
        is_fatal: ``True`` iff a gate failed AND ``edge.death_message is not None``.
        gate_code: Empty string when ``is_valid``; otherwise one of the five
            flat codes: ``text_closed``, ``requires_item``, ``forbids_item``,
            ``requires_flag``, ``forbids_flag``.
        data: Always carries ``passage_name``.  Also carries the relevant
            predicate value (``required_text``, ``required_item``,
            ``forbids_item``, ``required_flag``, ``forbids_flag``) and
            optionally ``death_message``.
    """

    is_valid: bool
    is_fatal: bool
    gate_code: str
    data: dict[str, object]


# ---------------------------------------------------------------------------
# DualGraphEngine
# ---------------------------------------------------------------------------


class DualGraphEngine:
    """Indexed graph for macro navigation and micro action lookup.

    Anchors and macro edges define the physical topology.  HyperEdges are
    indexed by ``(anchor_id, verb)`` for O(1) lookup, kept in priority
    descending order.
    """

    def __init__(self) -> None:
        self._anchors: dict[str, Entity] = {}
        self._macro_edges: dict[str, list[MacroEdge]] = {}
        # anchor_id → { verb → [HyperEdge (priority desc)] }
        self._hyper_edges: dict[str, dict[str, list[HyperEdge]]] = {}

    # -------------------------------------------------------------------
    # Construction
    # -------------------------------------------------------------------

    def add_anchor(self, anchor: Entity) -> None:
        """Register an anchor (spatial container entity) as a macro-graph node."""
        self._anchors[anchor.entity_id] = anchor

    def add_macro_edge(self, edge: MacroEdge) -> None:
        """Register a macro edge under its ``from_anchor``."""
        self._macro_edges.setdefault(edge.from_anchor, []).append(edge)

    def add_hyper_edge(self, anchor_id: str, hyper_edge: HyperEdge) -> None:
        """Register a HyperEdge under *(anchor_id, verb)*, priority-descending.

        Duplicate ``(verb, target, priority)`` for the same anchor emits a
        warning but does not block insertion.
        """

        verb = hyper_edge.clique.verb

        # Initialise sub-dict if needed
        if anchor_id not in self._hyper_edges:
            self._hyper_edges[anchor_id] = {}
        if verb not in self._hyper_edges[anchor_id]:
            self._hyper_edges[anchor_id][verb] = []

        edge_list = self._hyper_edges[anchor_id][verb]

        # Duplicate priority check
        target = hyper_edge.clique.target
        for existing in edge_list:
            if (
                existing.priority == hyper_edge.priority
                and existing.clique.target == target
            ):
                print(
                    f"[DualGraphEngine] Warning: duplicate priority "
                    f"{hyper_edge.priority} for (verb={verb!r}, "
                    f"target={target!r}) in anchor={anchor_id!r}",
                    file=sys.stderr,
                )
                break

        # Insert maintaining priority descending order
        idx = 0
        for idx, existing in enumerate(edge_list):
            if hyper_edge.priority > existing.priority:
                break
            idx += 1
        edge_list.insert(idx, hyper_edge)

    def build_macro_graph(
        self,
        anchors: list[Entity],
        macro_edges: list[MacroEdge],
    ) -> None:
        """Build the full macro graph from anchor and edge lists."""
        for anchor in anchors:
            self.add_anchor(anchor)
        for edge in macro_edges:
            self.add_macro_edge(edge)

    # -------------------------------------------------------------------
    # Query
    # -------------------------------------------------------------------

    def get_edges_from_anchor(self, anchor_id: str) -> list[MacroEdge]:
        """Return macro edges originating from *anchor_id*."""
        return list(self._macro_edges.get(anchor_id, []))

    def get_macro_edge_by_passage_name(
        self, anchor_id: str, passage_name: str
    ) -> MacroEdge | None:
        """Find a macro edge by passage name within an anchor.

        The lookup normalizes both sides by collapsing whitespace to a
        single underscore and lowercasing, so a player can write ``"ir
        puerta principal"`` (natural Spanish, as in the original game) and
        resolve the YAML passage ``puerta_principal``.  Returns ``None`` if
        no matching edge is found.
        """
        normalized = _normalize_passage_name(passage_name)
        for edge in self._macro_edges.get(anchor_id, []):
            if _normalize_passage_name(edge.passage_name) == normalized:
                return edge
        return None

    def _open_reverse_edges(self, edge: MacroEdge) -> None:
        """Open the reverse copy of a bidirectional passage.

        The loader creates reverse edges with ``open`` copied by value, so
        opening one side must unlock the mirrored edge (they are the same
        door).  Unidirectional edges have no reverse and are untouched.
        """
        reverse = (
            f"{edge.macro_edge_id}_reverse"
            if edge.macro_edge_id.endswith("_reverse")
            else f"{edge.macro_edge_id}_reverse"
        )
        # Find the mirror: same passage, opposite direction.
        for edges in self._macro_edges.values():
            for candidate in edges:
                if candidate.macro_edge_id == reverse:
                    candidate.open = True
                    return
                if (
                    candidate.passage_name == edge.passage_name
                    and candidate.from_anchor == edge.to_anchor
                    and candidate.to_anchor == edge.from_anchor
                ):
                    candidate.open = True
                    return

    def get_hyper_edges_for_verb(self, anchor_id: str, verb: str) -> list[HyperEdge]:
        """Return HyperEdges matching *(anchor_id, verb)*, priority-descending.

        Returns an empty list if the anchor or verb is not indexed.
        """
        verb_map = self._hyper_edges.get(anchor_id, {})
        return list(verb_map.get(verb, []))

    # -------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------

    def validate_clique(
        self,
        hyper_edge: HyperEdge,
        parsed: ParsedCommand,
        state: WorldState,
    ) -> bool:
        """Check whether *parsed* satisfies the :class:`Clique` of *hyper_edge*.

        Rules (GDD 2.3, TDD 4.2):
        - **verb**: exact match.
        - **subject**: must be the active protagonist or co-located with target.
        - **target**: ``None`` imposes no constraint.  A concrete target must
          resolve equal to the parsed target and be reachable (same anchor or
          inventory).  ``"*"`` matches any reachable parsed target.
        - **context**: same presence rules as target.
        - **instrument**: if specified, must be in subject's inventory or
          room.  ``"*"`` requires a parsed instrument present in inventory or
          room; ``instrument_any`` requires at least one portable item in
          inventory.
        - **instrument_not**: clique fails if this instrument is in the
          subject's inventory or anchor.
        - **flag**: must be ``True``.
        - **flag_not**: must be ``False`` or absent.
        - **component**: target entity ``components[key] == value``.
        """
        clique = hyper_edge.clique

        # --- verb -------------------------------------------------------
        if clique.verb != parsed.verb:
            return False

        # --- resolve subject --------------------------------------------
        subject_id = self.resolve_special_values(clique.subject, state)
        if subject_id is None:
            return False

        # --- subject check ----------------------------------------------
        try:
            subject = state.get_entity(subject_id)
        except KeyError:
            return False

        # --- target -----------------------------------------------------
        # resolved_target_id is the entity the clique matched; the component
        # predicate below reuses it.
        resolved_target_id: str | None = None
        clique_target = clique.target

        if clique_target is None:
            # No target constraint: a command with or without a target matches.
            pass
        elif clique_target == "*":
            # Wildcard: the parsed target must exist and be reachable.
            if parsed.target is None:
                return False
            wildcard_id = self.resolve_special_values(parsed.target, state)
            if wildcard_id is None:
                return False
            try:
                state.get_entity(wildcard_id)
            except KeyError:
                return False
            if not _is_in_anchor_or_inventory(
                wildcard_id,
                subject_id,
                subject.spatial_anchor or "",
                state,
            ):
                return False
            resolved_target_id = wildcard_id
        else:
            # Concrete target: both clique.target and parsed.target must
            # resolve to the same entity, which must be reachable.
            expected_id = self.resolve_special_values(clique_target, state)
            if expected_id is None:
                return False
            if parsed.target is None:
                return False
            parsed_id = self.resolve_special_values(parsed.target, state)
            if parsed_id is None:
                return False
            if parsed_id != expected_id:
                return False
            try:
                state.get_entity(parsed_id)
            except KeyError:
                return False
            if not _is_in_anchor_or_inventory(
                parsed_id,
                subject_id,
                subject.spatial_anchor or "",
                state,
            ):
                return False
            resolved_target_id = parsed_id

        # --- context ----------------------------------------------------
        if clique.context is not None:
            ctx_id = self.resolve_special_values(clique.context, state)
            if ctx_id is not None:
                try:
                    state.get_entity(ctx_id)
                except KeyError:
                    return False
                if not _is_in_anchor_or_inventory(
                    ctx_id,
                    subject_id,
                    subject.spatial_anchor or "",
                    state,
                ):
                    return False

        # --- instrument ------------------------------------------------
        inv = set(e.entity_id for e in state.get_player_inventory(subject_id))
        anchor_entities = set(
            e.entity_id
            for e in state.get_entities_in_container(subject.spatial_anchor or "")
        ) - {subject_id}

        if clique.instrument_any:
            # At least one portable item in inventory.  'portable' defaults
            # to True per GDD 2.3 (same default as the TRANSFER operator).
            portable = any(
                state.get_entity(eid).components.get("portable", True) for eid in inv
            )
            if not portable:
                return False
        elif clique.instrument == "*":
            # Wildcard: a parsed instrument must be present and reachable
            # (in inventory or anchor).
            if parsed.instrument is None:
                return False
            inst_id = self.resolve_special_values(parsed.instrument, state)
            if inst_id is None:
                return False
            if inst_id not in inv and inst_id not in anchor_entities:
                return False
        elif clique.instrument is not None:
            inst_id = self.resolve_special_values(clique.instrument, state)
            if inst_id is None:
                return False
            try:
                state.get_entity(inst_id)
            except KeyError:
                return False
            if inst_id not in inv and inst_id not in anchor_entities:
                return False

        # --- instrument_not --------------------------------------------
        if clique.instrument_not is not None:
            forbidden = self.resolve_special_values(clique.instrument_not, state)
            if forbidden is not None:
                if forbidden in inv or forbidden in anchor_entities:
                    return False

        # --- flag -------------------------------------------------------
        if clique.flag is not None:
            if not state.get_flag(clique.flag):
                return False

        # --- flag_not ---------------------------------------------------
        if clique.flag_not is not None:
            if state.get_flag(clique.flag_not):
                return False

        # --- component --------------------------------------------------
        if clique.component is not None:
            if resolved_target_id is None:
                return False
            target_entity = state.get_entity(resolved_target_id)
            for key, value in clique.component.items():
                if target_entity.components.get(key) != value:
                    return False

        return True

    def validate_macro_edge(
        self, edge: MacroEdge, state: WorldState, text: str | None = None
    ) -> MacroGateResult:
        """Evaluate *edge*'s gates against *state*.

        Returns a structured :class:`MacroGateResult` with ``is_valid``,
        ``is_fatal``, ``gate_code``, and ``data``.  The engine routes
        death-vs-block via ``is_fatal``; the narrator renders text from
        the flat ``gate_code`` and ``data`` fields.

        Gates are evaluated uniformly, in order: text gate, item gates,
        then flag gates.  Semantics are decided by which predicates the
        world creator sets, never by a connection type name.

        A plain edge with no predicates is always passable.
        """
        protagonist_id = state.active_protagonist_id
        inv = set(e.entity_id for e in state.get_player_inventory(protagonist_id))

        is_fatal = edge.death_message is not None
        passage = edge.passage_name

        # Text gate: a closed edge unlocks when the player says the right text.
        if edge.requires_text is not None and not edge.open:
            if text is not None and _normalize_text(text) == _normalize_text(
                edge.requires_text
            ):
                edge.open = True
                # A bidirectional passage is the SAME door seen from both
                # sides: opening one side unlocks the reverse edge too
                # (reverse copies carry `open` by value, so propagate).
                self._open_reverse_edges(edge)
            else:
                return MacroGateResult(
                    is_valid=False,
                    is_fatal=is_fatal,
                    gate_code="text_closed",
                    data=_gate_data(
                        passage_name=passage,
                        required_text=edge.requires_text,
                        death_message=edge.death_message,
                    ),
                )

        # Item gates.
        if edge.requires_item is not None and edge.requires_item not in inv:
            return MacroGateResult(
                is_valid=False,
                is_fatal=is_fatal,
                gate_code="requires_item",
                data=_gate_data(
                    passage_name=passage,
                    required_item=edge.requires_item,
                    death_message=edge.death_message,
                ),
            )
        if edge.forbids_item is not None and edge.forbids_item in inv:
            return MacroGateResult(
                is_valid=False,
                is_fatal=is_fatal,
                gate_code="forbids_item",
                data=_gate_data(
                    passage_name=passage,
                    forbids_item=edge.forbids_item,
                    death_message=edge.death_message,
                ),
            )

        # Flag gates.
        if edge.requires_flag is not None and not state.get_flag(edge.requires_flag):
            return MacroGateResult(
                is_valid=False,
                is_fatal=is_fatal,
                gate_code="requires_flag",
                data=_gate_data(
                    passage_name=passage,
                    required_flag=edge.requires_flag,
                    death_message=edge.death_message,
                ),
            )
        if edge.forbids_flag is not None and state.get_flag(edge.forbids_flag):
            return MacroGateResult(
                is_valid=False,
                is_fatal=is_fatal,
                gate_code="forbids_flag",
                data=_gate_data(
                    passage_name=passage,
                    forbids_flag=edge.forbids_flag,
                    death_message=edge.death_message,
                ),
            )

        return MacroGateResult(
            is_valid=True,
            is_fatal=False,
            gate_code="",
            data={"passage_name": passage},
        )

    # -------------------------------------------------------------------
    # Special values
    # -------------------------------------------------------------------

    def resolve_special_values(
        self, clique_value: str | None, state: WorldState
    ) -> str | None:
        """Resolve special clique placeholders.

        - ``"player"`` → ``state.active_protagonist_id``
        - ``"*"`` → returned as ``"*"`` (wildcard)
        - Everything else → returned as-is (including ``None``).
        """
        if clique_value is None:
            return None
        if clique_value == "player":
            return state.active_protagonist_id
        if clique_value == "*":
            return "*"
        return clique_value

    def resolve_target_id(
        self, clique_target: str | None, parsed: ParsedCommand, state: WorldState
    ) -> str | None:
        """Resolve the entity the clique matched for *parsed*.

        Returns the concrete entity id the parsed target resolves to, or
        ``None`` when there is no resolvable target.  Used by wildcard
        operators (``entity: "*"``) so a generic edge can act on the
        specific item the player named.
        """
        if clique_target is None:
            return None
        if clique_target == "*":
            if parsed.target is None:
                return None
            return self.resolve_special_values(parsed.target, state)
        return self.resolve_special_values(clique_target, state)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _gate_data(**kwargs: object) -> dict[str, object]:
    """Build the ``data`` dict for a :class:`MacroGateResult`.

    Only non-``None`` values are included so the dict is always minimal.
    ``passage_name`` is always present.
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def _normalize_text(s: str) -> str:
    """Lowercase and strip diacritics for requires_text comparison.

    Mirrors the parser's normalisation (NFKD + strip combining marks) so
    YAML requires_text values that keep tildes match normalised player
    input (á→a, é→e, í→i, ó→o, ú→u, ü→u, ñ→n).
    """
    text = unicodedata.normalize("NFKD", s.strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _normalize_passage_name(s: str) -> str:
    """Normalize a passage name for lookup.

    Lowercases and collapses whitespace to a single underscore, so the
    player's natural ``"puerta principal"`` resolves the YAML passage
    ``puerta_principal``.  YAML passage names are snake_case by convention;
    entity names are NOT normalized here (they legitimately contain spaces).
    """
    return "_".join(s.strip().lower().split())


def _is_in_anchor_or_inventory(
    entity_id: str,
    protagonist_id: str,
    protagonist_anchor: str,
    state: WorldState,
) -> bool:
    """Return True if *entity_id* is in the protagonist's anchor or inventory.

    Also True when the entity **is** the current anchor (``entity_id ==
    protagonist_anchor``).
    """
    # Entity IS the anchor the protagonist is in
    if entity_id == protagonist_anchor:
        return True
    if entity_id in (
        e.entity_id for e in state.get_entities_in_container(protagonist_anchor)
    ):
        return True
    if entity_id in (e.entity_id for e in state.get_player_inventory(protagonist_id)):
        return True
    return False
