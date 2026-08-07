# Delta for Turn Orchestrator

## MODIFIED Requirements

### Requirement: Single active turn and system commands

The orchestrator SHALL treat `player_controlled_entities` as a list while executing only `active_protagonist_id` in v1.0. It SHALL intercept SAVE/GUARDAR, LOAD/CARGAR, QUIT/TERMINAR, SWITCH/CAMBIAR, WAIT/ESPERAR, and GROUP/GRUPO without requiring full parser support. SAVE and LOAD MUST route through injected `WorldStateRepository` and `EventSourcingSaveSystem`; slot aliases MUST map `guardar`/`save` to `slot_1`, and numbered slots 1–3 to `slot_N`. Invalid slot numbers MUST emit `error_output(error_code="invalid_slot")`. With no repository or save system, the command MUST remain alive and emit the existing `no_repository` error path; it MUST NOT increment `turn_number`.
(Previously: system commands were intercepted, but SAVE/LOAD returned only the no_repository stub and the constructor had no save-system dependency.)

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

The constructor SHALL add `save_system: EventSourcingSaveSystem | None = None` and type `repository` as `WorldStateRepository | None`. Existing full-turn behavior and list-shaped protagonist semantics remain unchanged.
