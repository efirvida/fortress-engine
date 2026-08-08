"""TurnOrchestrator — coordinate a single protagonist turn from input to resolution.

Follows turn-orchestrator spec, event-system spec §5, and tdd.md §4.1.

The orchestrator is the SINGLE emitter of state-change EngineEvents derived from
OperatorResult.events_payload.  Operators remain pure and bus-free.

Entity-agnostic: never validates entity types.  player_controlled_entities is
always a list — no singleton assumptions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fortress_engine.entities.entity import Entity, ParsedCommand
from fortress_engine.engine.graph import Clique, HyperEdge, MacroEdge
from fortress_engine.engine.operators import execute_operator
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_ATTEMPTED,
    ACTION_OUTPUT,
    ACTION_RESOLVED,
    ENTITY_ENTERED,
    ENTITY_TELEPORTED,
    EPISODE_COMPLETED,
    ERROR_OUTPUT,
    GAME_COMPLETED,
    GAME_LOADED,
    GAME_OVER,
    GAME_SAVED,
    INPUT_RECEIVED,
    PROTAGONISTS_LISTED,
    PROTAGONIST_SWITCHED,
    SAVE_REPLAY_ENDED,
    SAVE_REPLAY_STARTED,
    TURN_STARTED,
    TURN_ENDED,
    EngineEvent,
)

if TYPE_CHECKING:
    from fortress_engine.engine.goal_evaluator import GoalEvaluator
    from fortress_engine.engine.graph import DualGraphEngine
    from fortress_engine.engine.episode_manager import EpisodeManager
    from fortress_engine.plugins.parser_interface import ParserInterface
    from fortress_engine.plugins.narrator_interface import NarratorInterface
    from fortress_engine.persistence.repository import WorldStateRepository
    from fortress_engine.persistence.event_log import EventSourcingSaveSystem
    from fortress_engine.entities.loader import Vocabulary


# ---------------------------------------------------------------------------
# Token constants for operator state-change event type keys
# ---------------------------------------------------------------------------

_OP_PAYLOAD_TO_EVENT: dict[str, str] = {
    "TRANSFER": "entity_transferred",
    "TRANSFORM": "entity_transformed",
    "COMBINE": "entity_combined",
    "FLAG": "flag_set",
    "TELEPORT": "entity_teleported",
}

# Canonical keys in events_payload — used to detect operator types from
# the payload shape (fallback when op_data["type"] is not available at
# emit time).
_PAYLOAD_KEY_TO_EVENT: dict[tuple[str, ...], str] = {
    ("entity_id", "from_container_id", "to_container_id"): "entity_transferred",
    ("entity_id", "component_key", "old_value", "new_value"): "entity_transformed",
    ("input_entity_ids", "output_entity_id"): "entity_combined",
    ("flag_name", "old_value", "new_value"): "flag_set",
    ("entity_id", "from_anchor_id", "to_anchor_id"): "entity_teleported",
}


# ---------------------------------------------------------------------------
# System command patterns (case-insensitive, stripped)
# ---------------------------------------------------------------------------

DEFAULT_MOVEMENT_VERBS: frozenset[str] = frozenset({"ir", "abrir"})
DEFAULT_SYSTEM_COMMANDS: dict[str, list[str]] = {
    "save":   ["guardar", "save"],
    "load":   ["cargar", "load"],
    "quit":   ["terminar", "abandonar", "quit"],
    "wait":   ["esperar", "wait"],
    "group":  ["grupo", "group"],
    "switch": ["cambiar a"],   # prefix command
}


def _parse_save_slot(
    raw_lower: str,
    surfaces: set[str] | None = None,
) -> str | None:
    """Extract a valid save-slot name from a lowercased command string.

    Returns:
        ``"slot_1"``, ``"slot_2"``, ``"slot_3"`` for valid slots,
        or ``None`` for invalid slot numbers.
    """
    # Build the set of prefix surfaces to try.
    prefixes = surfaces or {"guardar", "cargar", "save", "load"}
    # Sort longest-first to avoid partial prefix matches.
    sorted_prefixes = sorted(prefixes, key=len, reverse=True)
    for prefix in sorted_prefixes:
        if raw_lower.startswith(prefix):
            rest = raw_lower[len(prefix):].strip()
            if not rest:
                return "slot_1"  # bare command → default slot
            try:
                num = int(rest)
            except ValueError:
                return "slot_1"  # non-numeric suffix → treat as slot_1
            if 1 <= num <= 3:
                return f"slot_{num}"
            return None  # out of range
    return "slot_1"  # pragma: no cover — only called for save/load commands


class TurnOrchestrator:
    """Synchronous turn loop: parse → validate → execute → emit → evaluate."""

    def __init__(
        self,
        state: WorldState,
        graph: DualGraphEngine,
        event_bus: EventBus,
        parser: ParserInterface,
        narrator: NarratorInterface,
        goal_evaluator: GoalEvaluator,
        episode_manager: EpisodeManager,
        repository: WorldStateRepository | None = None,
        save_system: EventSourcingSaveSystem | None = None,
        vocabulary: "Vocabulary | None" = None,
    ) -> None:
        self._state = state
        self._graph = graph
        self._event_bus = event_bus
        self._parser = parser
        self._narrator = narrator
        self._goal_evaluator = goal_evaluator
        self._episode_manager = episode_manager
        self._repository = repository
        self._save_system = save_system
        self._vocabulary = vocabulary

    # ------------------------------------------------------------------
    # Vocabulary accessors
    # ------------------------------------------------------------------

    def _movement_verbs(self) -> frozenset[str]:
        """Return movement verb set from vocabulary or default."""
        if self._vocabulary is None or not self._vocabulary.movement_verbs:
            return DEFAULT_MOVEMENT_VERBS
        return frozenset(self._vocabulary.movement_verbs)

    def _system_commands(self) -> dict[str, list[str]]:
        """Return system command surface map from vocabulary or default."""
        if self._vocabulary is None or not self._vocabulary.system_commands:
            return dict(DEFAULT_SYSTEM_COMMANDS)
        result = dict(self._vocabulary.system_commands)
        # Ensure all canonical kinds are present (fill from defaults)
        for kind, surfaces in DEFAULT_SYSTEM_COMMANDS.items():
            if kind not in result or not result[kind]:
                result[kind] = list(surfaces)
        return result

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def execute_turn(self, raw_text: str) -> None:
        """Run one complete turn cycle (14 steps)."""
        state = self._state
        protagonists = state.player_controlled_entities
        protagonist_id = state.active_protagonist_id

        # 1. Emit turn_started.
        self._emit(
            TURN_STARTED,
            {
                "turn_number": state.turn_number,
                "active_protagonist_id": protagonist_id,
            },
        )

        # 2. Check for system commands (intercepted before normal parsing).
        system_kind = self._detect_system_command(raw_text)
        if system_kind is not None:
            self._handle_system_command(raw_text, system_kind, protagonist_id)
            # System commands do NOT count as turns and do NOT emit turn_ended.
            return

        # 3. Parse input.
        # Plugin error isolation (tdd.md §9.3): a throwing parser must not
        # take down the engine.  The failure is surfaced as a structured
        # error_output; the traceback goes to stderr in debug mode only.
        try:
            parsed = self._parser.parse(raw_text, state)
        except Exception:
            self._emit(
                ERROR_OUTPUT,
                {
                    "error_code": "parser_error",
                    "data": {},
                    "protagonist_id": protagonist_id,
                },
            )
            if __debug__:
                import traceback

                traceback.print_exc()
            state.turn_number += 1
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 0},
            )
            return

        # 4. Emit input_received.
        self._emit(
            INPUT_RECEIVED,
            {"raw_text": raw_text, "protagonist_id": protagonist_id},
        )

        # 5. Get candidate hyper edges for the verb in the current anchor.
        anchor_id = state.get_entity(protagonist_id).spatial_anchor
        # Unreachable in normal gameplay — protagonist always has a
        # spatial_anchor after episode loading.
        if anchor_id is None:  # pragma: no cover
            anchor_id = ""

        # Check for movement: verb "ir"/"abrir" with a target that matches a
        # passage name.
        movement_edge = self._resolve_movement(parsed, anchor_id)
        if movement_edge is not None:
            # _handle_movement already runs _post_action_checks on every
            # path (valid move, danger death, blocked door) and emits the
            # single turn_ended for this turn.
            self._handle_movement(
                movement_edge, protagonist_id, anchor_id, parsed.text
            )
            return

        candidates = self._graph.get_hyper_edges_for_verb(anchor_id, parsed.verb)

        # 6. Validate clique for each candidate (priority desc).
        selected: HyperEdge | None = None
        for he in candidates:  # pragma: no branch — loop back-edge not taken when one candidate matches
            if self._validate_clique(he, parsed, state):
                selected = he
                break

        # 7. No clique → error_output.
        if selected is None:
            state.turn_number += 1
            self._emit(
                ERROR_OUTPUT,
                {
                    "error_code": "no_action",
                    "data": {"verb": parsed.verb, "protagonist_id": protagonist_id},
                    "protagonist_id": protagonist_id,
                },
            )
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 0},
            )
            return

        # 8. Emit action_attempted.
        self._emit(
            ACTION_ATTEMPTED,
            {
                "hyper_edge_id": selected.hyper_edge_id,
                "clique": {
                    "subject": selected.clique.subject,
                    "verb": selected.clique.verb,
                    "target": selected.clique.target,
                    "instrument": selected.clique.instrument,
                    "context": selected.clique.context,
                },
                "protagonist_id": protagonist_id,
            },
        )

        # 9. Execute operators.
        ops_executed = self._execute_operators(
            selected.operators, protagonist_id
        )

        has_effects = len(ops_executed) > 0

        # 10. Emit action_output if the edge has output text.
        if selected.output:
            self._emit(
                ACTION_OUTPUT,
                {
                    "hyper_edge_id": selected.hyper_edge_id,
                    "text": selected.output,
                    "protagonist_id": protagonist_id,
                },
            )

        # 11. Emit action_resolved.
        self._emit(
            ACTION_RESOLVED,
            {
                "hyper_edge_id": selected.hyper_edge_id,
                "operators_executed": ops_executed,
                "has_effects": has_effects,
                "protagonist_id": protagonist_id,
            },
        )

        # 12. Evaluate goal.
        if self._evaluate_goal():
            # Goal met.  The _evaluate_goal method handles episode
            # transition or game_completed internally.  Skip the
            # post-action checks (goal was already handled, and we
            # must not double-emit).
            state.turn_number += 1
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 1},
            )
            return

        # 13. Check player_dead.
        if state.get_flag("player_dead"):
            self._emit(
                GAME_OVER,
                {"reason": "player_death", "turn_number": state.turn_number},
            )
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 1},
            )
            return

        # 14. Emit turn_ended.
        state.turn_number += 1
        self._emit(
            TURN_ENDED,
            {"turn_number": state.turn_number, "actions_resolved": 1},
        )

    # ------------------------------------------------------------------
    # Private: validation
    # ------------------------------------------------------------------

    def _validate_clique(
        self, hyper_edge: HyperEdge, parsed: ParsedCommand, state: WorldState
    ) -> bool:
        """Delegate to the graph engine's clique validator."""
        return self._graph.validate_clique(hyper_edge, parsed, state)

    # ------------------------------------------------------------------
    # Private: operator execution
    # ------------------------------------------------------------------

    def _execute_operators(
        self, operators: list[dict[str, object]], protagonist_id: str
    ) -> list[str]:
        """Execute a list of operator dicts sequentially.

        Each successful operator emits its state-change event.  On failure,
        emits error_output and stops (no rollback of prior operators).

        Returns the list of operator type strings that executed successfully.
        """
        ops_executed: list[str] = []
        for op_data in operators:
            result = execute_operator(
                self._state, op_data, protagonist_id, self._graph
            )
            op_type = op_data.get("type", "")

            if result.success and result.events_payload is not None:
                # Emit the state-change event for this operator.
                event_type = _OP_PAYLOAD_TO_EVENT.get(op_type)
                if event_type is None:  # pragma: no cover — unreachable for canonical operators
                    # Fallback: detect from payload keys.  Unreachable for
                    # the 5 canonical operators (all have entries above);
                    # kept as a safety net for custom operators.
                    payload_keys = tuple(sorted(result.events_payload.keys()))  # noqa
                    event_type = _PAYLOAD_KEY_TO_EVENT.get(payload_keys)  # type: ignore[assignment]
                if event_type:  # pragma: no branch — always truthy for canonical operators
                    self._emit(
                        event_type,
                        {
                            **result.events_payload,
                            "hyper_edge_id": None,
                        },
                    )
                ops_executed.append(op_type)
            else:
                # Operator failed → emit error and stop.
                op_code = result.code
                op_data = result.data
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "operator_failed",
                        "data": (
                            {"op_code": op_code, **op_data}
                            if op_code
                            else {}
                        ),
                        "protagonist_id": protagonist_id,
                    },
                )
                return ops_executed

        return ops_executed

    # ------------------------------------------------------------------
    # Private: goal evaluation
    # ------------------------------------------------------------------

    def _evaluate_goal(self) -> bool:
        """Check whether the current episode's goal is met.

        If the goal is met, emits ``episode_completed`` and either
        transitions to the next episode or emits ``game_completed``.

        Returns ``True`` if a goal transition occurred.
        """
        if not self._goal_evaluator.check(self._state):
            return False

        goal = self._goal_evaluator._conditions

        # Emit episode_completed.
        self._emit(
            EPISODE_COMPLETED,
            {
                "episode_id": self._state.current_episode_id,
                "victory_text": goal.output,
                "carry_over": {
                    "inventory": self._episode_manager
                    ._episodes[self._state.current_episode_id]
                    .carry_over.inventory,
                    "flags": self._episode_manager
                    ._episodes[self._state.current_episode_id]
                    .carry_over.flags,
                },
            },
        )

        # Try transitioning to next episode.
        new_graph = self._episode_manager.transition_to_next(
            self._state.current_episode_id, self._state, self._graph
        )

        if new_graph is None:
            # No next episode — game completed.
            self._emit(
                GAME_COMPLETED,
                {
                    "world_id": "",
                    "total_turns": self._state.turn_number,
                },
            )
        else:
            # Transition succeeded — replace the graph reference and bind
            # the next episode's goal evaluator so the new episode is
            # evaluated against its OWN goal conditions (REQ-GOAL-001).
            self._graph = new_graph  # type: ignore[assignment]
            self._goal_evaluator = self._episode_manager.goal_evaluator_for(
                self._state.current_episode_id
            )

        return True

    # ------------------------------------------------------------------
    # Private: movement
    # ------------------------------------------------------------------

    def _resolve_movement(
        self, parsed: ParsedCommand, anchor_id: str
    ) -> MacroEdge | None:
        """If *parsed* is a movement command, find the matching macro edge.

        Movement verbs come from vocabulary (or defaults {"ir", "abrir"}).
        """
        if parsed.verb not in self._movement_verbs() or parsed.target is None:
            return None
        if anchor_id == "":  # pragma: no cover — unreachable (see above)
            return None
        return self._graph.get_macro_edge_by_passage_name(anchor_id, parsed.target)

    def _handle_movement(
        self,
        edge: MacroEdge,
        protagonist_id: str,
        current_anchor: str,
        text: str | None = None,
    ) -> None:
        """Execute a movement through a macro edge.

        *text* carries spoken text (from ABRIR ... DICIENDO/RESPONDIENDO)
        so closed edges with a ``requires_text`` gate can be evaluated and
        opened.
        """
        # Emit action_attempted.
        self._emit(
            ACTION_ATTEMPTED,
            {
                "hyper_edge_id": edge.macro_edge_id,
                "clique": {
                    "subject": protagonist_id,
                    "verb": "ir",
                    "target": edge.passage_name,
                },
                "protagonist_id": protagonist_id,
            },
        )

        # Validate macro edge — returns structured MacroGateResult (L4).
        gate = self._graph.validate_macro_edge(
            edge, self._state, text
        )

        if not gate.is_valid:
            if gate.is_fatal:
                # Fatal gate → game_over with stable reason code.  The
                # world-authored death_message flows through gate.data so a
                # narrator can render it (structured + data, never a string
                # constructed by the engine).
                self._emit(
                    GAME_OVER,
                    {
                        "reason": "player_death",
                        "turn_number": self._state.turn_number,
                        **gate.data,
                    },
                )
                self._emit(
                    TURN_ENDED,
                    {
                        "turn_number": self._state.turn_number,
                        "actions_resolved": 0,
                    },
                )
            else:
                # Non-fatal block → error_output with full gate data.
                blocked_data: dict[str, object] = {
                    **gate.data,
                    "gate_code": gate.gate_code,
                }
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "blocked",
                        "data": blocked_data,
                        "protagonist_id": protagonist_id,
                    },
                )
                self._emit(
                    TURN_ENDED,
                    {
                        "turn_number": self._state.turn_number,
                        "actions_resolved": 0,
                    },
                )
            return

        # Apply movement: TELEPORT protagonist.
        from_anchor = current_anchor
        protagonist = self._state.get_entity(protagonist_id)
        protagonist.spatial_anchor = edge.to_anchor

        # Emit entity_teleported.
        self._emit(
            ENTITY_TELEPORTED,
            {
                "entity_id": protagonist_id,
                "from_anchor_id": from_anchor,
                "to_anchor_id": edge.to_anchor,
            },
        )

        # Emit entity_entered.
        self._emit(
            ENTITY_ENTERED,
            {
                "entity_id": protagonist_id,
                "entity_name": protagonist.name,
                "from_anchor_id": from_anchor,
                "to_anchor_id": edge.to_anchor,
                "protagonist_id": protagonist_id,
            },
        )

        # Emit action_resolved.
        self._emit(
            ACTION_RESOLVED,
            {
                "hyper_edge_id": edge.macro_edge_id,
                "operators_executed": ["TELEPORT"],
                "has_effects": True,
                "protagonist_id": protagonist_id,
            },
        )

        self._post_action_checks(protagonist_id)

    # ------------------------------------------------------------------
    # Private: system commands (vocabulary-driven)
    # ------------------------------------------------------------------

    def _detect_system_command(self, raw_text: str) -> str | None:
        """Return the canonical system command kind, or None.

        Builds a flat surface→kind map from ``_system_commands()``.
        ``switch`` surfaces are matched as PREFIX (strip surface + trailing
        space).  ``save``/``load`` surfaces also allow a trailing space
        (for slot numbers like ``guardar 1``). Longest-surface-first
        ordering avoids prefix collisions.
        """
        lower = raw_text.strip().lower()
        if not lower:
            return None

        sys_cmds = self._system_commands()
        # Build (surface, kind, is_switch) triples sorted longest-first.
        entries: list[tuple[str, str, bool]] = []
        for kind, surfaces in sys_cmds.items():
            for surface in surfaces:
                sl = surface.lower()
                is_switch = kind == "switch"
                entries.append((sl, kind, is_switch))

        # Sort longest surface first to avoid partial matches.
        entries.sort(key=lambda e: len(e[0]), reverse=True)

        for surface, kind, is_switch in entries:
            if is_switch:
                # Prefix match: the surface must be followed by a space or end exactly.
                if lower.startswith(surface):
                    if len(lower) == len(surface):
                        return kind
                    if lower[len(surface)] == " ":
                        return kind
            elif kind in ("save", "load"):
                # save/load can be bare ("guardar") or with slot ("guardar 1")
                if lower == surface:
                    return kind
                if lower.startswith(surface) and len(lower) > len(surface) and lower[len(surface)] == " ":
                    return kind
            else:
                # Exact match only for quit, wait, group.
                if lower == surface:
                    return kind

        return None

    def _get_save_surfaces(self) -> set[str]:
        """Collect all save/load surface words for _parse_save_slot."""
        sc = self._system_commands()
        surfaces: set[str] = set()
        for kind in ("save", "load"):
            for s in sc.get(kind, []):
                surfaces.add(s.lower())
        return surfaces

    def _handle_system_command(
        self, raw_text: str, kind: str, protagonist_id: str
    ) -> None:
        """Execute a system command and emit the appropriate events."""
        lower = raw_text.strip().lower()
        state = self._state

        # Match system command kind.  Each branch returns after emitting
        # to avoid the coverage false-negative of if/elif chains where only
        # one branch fires per call.
        if kind == "quit":
            self._emit(
                GAME_OVER,
                {"reason": "player_quit", "turn_number": state.turn_number},
            )
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 0},
            )
            return

        if kind == "save":
            if self._repository is None or self._save_system is None:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "no_repository",
                        "data": {"command": "save"},
                        "protagonist_id": protagonist_id,
                    },
                )
                return

            slot = _parse_save_slot(lower, surfaces=self._get_save_surfaces())
            if slot is None:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "invalid_slot",
                        "data": {"slot": lower},
                        "protagonist_id": protagonist_id,
                    },
                )
                return

            self._emit(
                GAME_SAVED,
                {
                    "save_slot": slot,
                    "turn_number": state.turn_number,
                },
            )
            return

        if kind == "load":
            if self._repository is None or self._save_system is None:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "no_repository",
                        "data": {"command": "load"},
                        "protagonist_id": protagonist_id,
                    },
                )
                return

            slot = _parse_save_slot(lower, surfaces=self._get_save_surfaces())
            if slot is None:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "invalid_slot",
                        "data": {"slot": lower},
                        "protagonist_id": protagonist_id,
                    },
                )
                return

            # Reject missing slot — no snapshot AND no events.
            snapshot = self._repository.load_latest_snapshot(slot)
            if snapshot is None:
                events = self._repository.get_event_log(since_turn=0)
                if not events:
                    self._emit(
                        ERROR_OUTPUT,
                        {
                            "error_code": "missing_slot",
                            "data": {"slot": slot},
                            "protagonist_id": protagonist_id,
                        },
                    )
                    return

            # Replay state — the save system emits SAVE_REPLAY_STARTED/ENDED
            # and mutates state in place.
            self._state = self._save_system.replay_state(
                self._state, slot, self._graph
            )

            self._emit(
                GAME_LOADED,
                {
                    "save_slot": slot,
                    "turn_number": state.turn_number,
                },
            )
            return

        if kind == "switch":
            # Extract name from the raw text using the matched vocabulary surface.
            sys_cmds = self._system_commands()
            switch_surfaces = sys_cmds.get("switch", [])
            name_part = ""
            for surface in sorted(switch_surfaces, key=len, reverse=True):
                # pragma: no branch — _detect_system_command already
                # matched a surface, so at least one surface must match.
                sl = surface.lower()
                if lower.startswith(sl):  # pragma: no branch — entry is unreachable when empty surfaces
                    name_part = lower[len(sl):].strip()
                    break
            if not name_part:  # pragma: no cover — unreachable; detection already matched
                name_part = lower  # fallback

            # Find protagonist by name (case-insensitive)
            new_id: str | None = None
            for p_id in state.player_controlled_entities:
                if p_id in state.entities:
                    ent = state.get_entity(p_id)
                    if ent.name.lower() == name_part.lower():
                        new_id = p_id
                        break

            if new_id is not None and new_id != protagonist_id:
                old_id = state.active_protagonist_id
                state.active_protagonist_id = new_id
                new_ent = state.get_entity(new_id)
                self._emit(
                    PROTAGONIST_SWITCHED,
                    {
                        "from_protagonist_id": old_id,
                        "to_protagonist_id": new_id,
                        "name": new_ent.name,
                    },
                )
            else:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "invalid_protagonist",
                        "data": {"name": name_part},
                        "protagonist_id": protagonist_id,
                    },
                )
            return

        if kind == "wait":
            # No-op — pass turn silently. Still emit turn_structure events.
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 0},
            )
            return

        if kind == "group":
            # List all protagonists.
            prots: list[dict[str, object]] = []
            for p_id in state.player_controlled_entities:
                if p_id in state.entities:
                    ent = state.get_entity(p_id)
                    prots.append({
                        "id": p_id,
                        "name": ent.name,
                        "location": ent.spatial_anchor,
                        "status": "active" if p_id == protagonist_id else "inactive",
                    })
            self._emit(
                PROTAGONISTS_LISTED,
                {"protagonists": prots},
            )
            return

    # ------------------------------------------------------------------
    # Private: post-action checks (goal evaluation + player_dead)
    # ------------------------------------------------------------------

    def _post_action_checks(self, protagonist_id: str) -> None:
        """Run player_dead check after an action (movement handler).

        Goal evaluation is handled separately in ``execute_turn``.
        """
        state = self._state

        # Player dead check.  Unreachable during movement (movement is
        # pure TELEPORT with no operators that set player_dead).  This
        # check is tested through execute_turn's step 13 for micro actions.
        if state.get_flag("player_dead"):
            self._emit(
                GAME_OVER,
                {"reason": "player_death", "turn_number": state.turn_number},
            )
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 1},
            )
            return

        # Advance turn and emit turn_ended.
        state.turn_number += 1
        self._emit(
            TURN_ENDED,
            {"turn_number": state.turn_number, "actions_resolved": 1},
        )

    # ------------------------------------------------------------------
    # Private: event emission helper
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        payload: dict[str, object],
        protagonist_id: str | None = None,
    ) -> EngineEvent:
        """Create and emit an EngineEvent through the bus."""
        pid = protagonist_id or self._state.active_protagonist_id
        event = EngineEvent.create(
            event_type=event_type,
            turn_number=self._state.turn_number,
            payload=payload,
            protagonist_id=pid,
            episode_id=self._state.current_episode_id,
        )
        self._event_bus.emit(event)
        return event
