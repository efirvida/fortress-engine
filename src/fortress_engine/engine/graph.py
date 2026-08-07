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

        Returns ``None`` if no matching edge is found.
        """
        for edge in self._macro_edges.get(anchor_id, []):
            if edge.passage_name == passage_name:
                return edge
        return None

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
            # At least one portable item in inventory
            portable = any(
                state.get_entity(eid).components.get("portable", False) for eid in inv
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
    ) -> tuple[bool, str | None]:
        """Evaluate *edge*'s gates against *state*.

        Returns ``(is_valid, error_or_death_message)``.

        Gates are evaluated uniformly, in order: text gate, item gates,
        then flag gates.  ``death_message`` decides fatal vs blocked: when
        a gate fails AND ``edge.death_message`` is set, the returned
        message IS the death message (fatal); otherwise a Spanish
        "blocked" message is returned.

        Semantics are decided by which predicates the world creator sets,
        never by a connection type name.  For example:

        - ``requires_text`` + ``open=False`` = a password or riddle gate;
          a correct match flips ``edge.open`` to ``True``.
        - ``requires_item`` + ``death_message`` = a lethal danger gate.
        - ``forbids_item`` + ``death_message`` = a lethal inverse gate.
        - ``requires_flag`` / ``forbids_flag`` without ``death_message``
          = a conditional (blocked) gate.

        A plain edge with no predicates is always passable.
        """
        protagonist_id = state.active_protagonist_id
        inv = set(e.entity_id for e in state.get_player_inventory(protagonist_id))

        # Text gate: a closed edge unlocks when the player says the right text.
        if edge.requires_text is not None and not edge.open:
            if text is not None and _normalize_text(text) == _normalize_text(
                edge.requires_text
            ):
                edge.open = True
            else:
                return False, (
                    edge.death_message
                    if edge.death_message is not None
                    else f"{edge.passage_name} está cerrada."
                )

        # Item gates.
        if edge.requires_item is not None and edge.requires_item not in inv:
            return False, (
                edge.death_message
                if edge.death_message is not None
                else f"No puedes pasar por {edge.passage_name} aún."
            )
        if edge.forbids_item is not None and edge.forbids_item in inv:
            return False, (
                edge.death_message
                if edge.death_message is not None
                else f"{edge.passage_name} está sellada."
            )

        # Flag gates.
        if edge.requires_flag is not None and not state.get_flag(edge.requires_flag):
            return False, (
                edge.death_message
                if edge.death_message is not None
                else f"No puedes pasar por {edge.passage_name} aún."
            )
        if edge.forbids_flag is not None and state.get_flag(edge.forbids_flag):
            return False, (
                edge.death_message
                if edge.death_message is not None
                else f"{edge.passage_name} está sellada."
            )

        return True, None

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_text(s: str) -> str:
    """Lowercase and strip diacritics for requires_text comparison.

    Mirrors the parser's normalisation (NFKD + strip combining marks) so
    YAML requires_text values that keep tildes match normalised player
    input (á→a, é→e, í→i, ó→o, ú→u, ü→u, ñ→n).
    """
    text = unicodedata.normalize("NFKD", s.strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


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
