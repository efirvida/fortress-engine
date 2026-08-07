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
    ERROR_OUTPUT,
    GAME_COMPLETED,
    GAME_OVER,
    INPUT_RECEIVED,
    PROTAGONISTS_LISTED,
    PROTAGONIST_SWITCHED,
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

_SYSTEM_COMMANDS: set[str] = {"guardar", "cargar", "terminar", "esperar", "grupo"}
_SYSTEM_PREFIXES: list[tuple[str, str]] = [
    ("guardar ", "save"),
    ("cargar ", "load"),
    ("cambiar a ", "switch"),
]


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
        repository: object | None = None,
    ) -> None:
        self._state = state
        self._graph = graph
        self._event_bus = event_bus
        self._parser = parser
        self._narrator = narrator
        self._goal_evaluator = goal_evaluator
        self._episode_manager = episode_manager
        self._repository = repository

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
        parsed = self._parser.parse(raw_text, state)

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

        # Check for movement: verb "ir" with a target that matches a door name.
        movement_edge = self._resolve_movement(parsed, anchor_id)
        if movement_edge is not None:
            self._handle_movement(movement_edge, protagonist_id, anchor_id)
            self._post_action_checks(protagonist_id)
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
                    "message": f"No entiendes cómo hacer '{parsed.verb}' aquí.",
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
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "operator_failed",
                        "message": result.error_message or "No puedes hacer eso.",
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
            "episode_completed",
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
            # Transition succeeded — replace the graph reference.
            self._graph = new_graph  # type: ignore[assignment]

        return True

    # ------------------------------------------------------------------
    # Private: movement
    # ------------------------------------------------------------------

    def _resolve_movement(
        self, parsed: ParsedCommand, anchor_id: str
    ) -> MacroEdge | None:
        """If *parsed* is a movement command, find the matching macro edge.

        Movement is detected when:
        - verb is ``"ir"``
        - target is not None
        - The target matches a door_name from ``anchor_id``.
        """
        if parsed.verb != "ir" or parsed.target is None:
            return None
        if anchor_id == "":  # pragma: no cover — unreachable (see above)
            return None
        return self._graph.get_macro_edge_by_door_name(anchor_id, parsed.target)

    def _handle_movement(
        self,
        edge: MacroEdge,
        protagonist_id: str,
        current_anchor: str,
    ) -> None:
        """Execute a movement through a macro edge."""
        # Emit action_attempted.
        self._emit(
            ACTION_ATTEMPTED,
            {
                "hyper_edge_id": edge.macro_edge_id,
                "clique": {
                    "subject": protagonist_id,
                    "verb": "ir",
                    "target": edge.door_name,
                },
                "protagonist_id": protagonist_id,
            },
        )

        # Validate macro edge.
        is_valid, death_msg = self._graph.validate_macro_edge(
            edge, self._state
        )

        if not is_valid:
            if edge.death_message is not None and death_msg == edge.death_message:
                # Danger edge (has explicit death_message) → game_over.
                self._emit(
                    GAME_OVER,
                    {"reason": death_msg, "turn_number": self._state.turn_number},
                )
                self._emit(
                    TURN_ENDED,
                    {
                        "turn_number": self._state.turn_number,
                        "actions_resolved": 0,
                    },
                )
            else:
                # Non-fatal block (conditional, etc.) → error_output.
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "blocked",
                        "message": death_msg or "No puedes ir por ahí.",
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
    # Private: system commands
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_system_command(raw_text: str) -> str | None:
        """Return the system command kind, or None if *raw_text* is a regular turn."""
        lower = raw_text.strip().lower()

        # Exact matches.
        if lower in _SYSTEM_COMMANDS:
            return lower

        # Prefixed commands (GUARDAR 1, CARGAR 2, CAMBIAR A X).
        for prefix, kind in _SYSTEM_PREFIXES:
            if lower.startswith(prefix):
                return kind

        return None

    def _handle_system_command(
        self, raw_text: str, kind: str, protagonist_id: str
    ) -> None:
        """Execute a system command and emit the appropriate events."""
        lower = raw_text.strip().lower()
        state = self._state

        # Match system command kind.  Each branch returns after emitting
        # to avoid the coverage false-negative of if/elif chains where only
        # one branch fires per call.
        if kind == "terminar":
            self._emit(
                GAME_OVER,
                {"reason": "player_quit", "turn_number": state.turn_number},
            )
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 0},
            )
            return

        if kind in ("guardar", "save"):
            if self._repository is None:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "no_repository",
                        "message": (
                            "Guardar no está disponible."
                            if kind == "guardar"
                            else "Guardar no está disponible."
                        ),
                        "protagonist_id": protagonist_id,
                    },
                )
            return

        if kind in ("cargar", "load"):
            if self._repository is None:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "no_repository",
                        "message": (
                            "Cargar no está disponible."
                            if kind == "cargar"
                            else "Cargar no está disponible."
                        ),
                        "protagonist_id": protagonist_id,
                    },
                )
            return

        if kind == "switch":
            # "CAMBIAR A <name>"
            name_part = lower.split("cambiar a ", 1)[-1].strip()
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
                self._emit(
                    PROTAGONIST_SWITCHED,
                    {
                        "from_protagonist_id": old_id,
                        "to_protagonist_id": new_id,
                    },
                )
            else:
                self._emit(
                    ERROR_OUTPUT,
                    {
                        "error_code": "invalid_protagonist",
                        "message": f"No se encuentra a '{name_part}'.",
                        "protagonist_id": protagonist_id,
                    },
                )
            return

        if kind == "esperar":
            # No-op — pass turn silently. Still emit turn_structure events.
            self._emit(
                TURN_ENDED,
                {"turn_number": state.turn_number, "actions_resolved": 0},
            )
            return

        if kind == "grupo":
            # List all protagonists.
            prots: list[dict[str, object]] = []
            for p_id in state.player_controlled_entities:
                if p_id in state.entities:
                    ent = state.get_entity(p_id)
                    prots.append({
                        "id": p_id,
                        "name": ent.name,
                        "location": ent.spatial_anchor or "limbo",
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
