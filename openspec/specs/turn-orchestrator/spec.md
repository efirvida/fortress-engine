# Turn Orchestrator Specification

## Purpose

Coordinate one synchronous active-protagonist turn from input through resolution and goal checks.

## Requirements

### Requirement: Full turn cycle

`TurnOrchestrator` SHALL accept the TDD constructor dependencies and expose `execute_turn(raw_text: str) -> None`, `_validate_clique`, `_execute_operators`, and `_evaluate_goal`. It SHALL increment `WorldState.turn_number`, parse input, select a valid HyperEdge or macro movement, execute operators, emit outputs, evaluate goals, and close the turn.

#### Scenario: Successful movement

- GIVEN active player `p1` in `room-1`, an open north MacroEdge to `room-2`, and stub parser input `"ir north"`
- WHEN `execute_turn` runs
- THEN the canonical events occur in order: `turn_started`, `input_received`, `action_attempted`, `entity_teleported`, `entity_entered`, `action_resolved`, `turn_ended`

#### Scenario: Failed action

- GIVEN no valid Clique for a parsed command
- WHEN the turn executes
- THEN `error_output` is emitted, no operator state event occurs, and the turn ends without mutation

### Requirement: Single active turn and system commands

The orchestrator SHALL treat `player_controlled_entities` as a list while executing only `active_protagonist_id` in v1.0. It SHALL intercept the scoped system commands SAVE, LOAD, QUIT/TERMINAR, SWITCH/CAMBIAR, WAIT/ESPERAR, and GROUP/GRUPO without requiring full parser support.

#### Scenario: Multiple protagonists remain list-shaped

- GIVEN two player IDs
- WHEN one turn executes
- THEN only the active ID supplies context and the list remains intact

#### Scenario: Episode transition resets turn

- GIVEN a completed episode with a next episode
- WHEN `EpisodeManager.transition_to_next()` runs
- THEN carry-over is applied, the graph is replaced, the player is teleported to start, and `turn_number` is reset to 0

## Contract notes

The constructor SHALL be `TurnOrchestrator(state: WorldState, graph: DualGraphEngine, event_bus: EventBus, parser: ParserInterface, narrator: NarratorInterface, goal_evaluator: GoalEvaluator, episode_manager: EpisodeManager, repository: WorldStateRepository | None = None) -> None`.

Operators are invoked without EventBus. The orchestrator is the single emitter of operator-derived state-change events and persists only effectful action records.
