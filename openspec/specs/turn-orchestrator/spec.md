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

The orchestrator SHALL treat `player_controlled_entities` as a list while executing only `active_protagonist_id` in v1.0. It SHALL intercept SAVE/GUARDAR, LOAD/CARGAR, QUIT/TERMINAR, SWITCH/CAMBIAR, WAIT/ESPERAR, and GROUP/GRUPO without requiring full parser support. SAVE and LOAD MUST route through injected `WorldStateRepository` and `EventSourcingSaveSystem`; slot aliases MUST map `guardar`/`save` to `slot_1`, and numbered slots 1–3 to `slot_N`. Invalid slot numbers MUST emit `error_output(error_code="invalid_slot")`. With no repository or save system, the command MUST remain alive and emit the existing `no_repository` error path; it MUST NOT increment `turn_number`.

#### Scenario: Multiple protagonists remain list-shaped

- GIVEN two player IDs
- WHEN one turn executes
- THEN only the active ID supplies context and the list remains intact

#### Scenario: Episode transition resets turn

- GIVEN a completed episode with a next episode
- WHEN `EpisodeManager.transition_to_next()` runs
- THEN carry-over is applied, the graph is replaced, the player is teleported to start, and `turn_number` is reset to 0

#### Scenario: Save dispatch

- GIVEN injected repository and save system and command `GUARDAR 2`
- WHEN `execute_turn` runs
- THEN slot 2 is saved, `game_saved` is emitted, and turn number is unchanged

#### Scenario: Load dispatch

- GIVEN a saved slot and injected repository/save system
- WHEN `CARGAR 1` runs
- THEN snapshot plus event-log tail reconstructs state, `game_loaded` is emitted, and turn number is restored

#### Scenario: No repository stays alive

- GIVEN no repository or save system
- WHEN SAVE or LOAD is executed
- THEN exact `no_repository` error output is emitted and the orchestrator remains usable for later turns

#### Scenario: Invalid slot

- GIVEN command `GUARDAR 4` or `CARGAR 0`
- WHEN the command is handled
- THEN exact `invalid_slot` error output is emitted and no persistence call occurs

## Contract notes

The constructor SHALL be `TurnOrchestrator(state: WorldState, graph: DualGraphEngine, event_bus: EventBus, parser: ParserInterface, narrator: NarratorInterface, goal_evaluator: GoalEvaluator, episode_manager: EpisodeManager, repository: WorldStateRepository | None = None, save_system: EventSourcingSaveSystem | None = None) -> None`.

Operators are invoked without EventBus. The orchestrator is the single emitter of operator-derived state-change events and persists only effectful action records.
