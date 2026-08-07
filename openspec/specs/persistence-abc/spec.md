# Persistence ABC Specification

## Purpose

Define the storage seam used by the engine without exposing SQLAlchemy.

## Requirements

### Requirement: World state repository contract

`WorldStateRepository` MUST expose exactly the five persistence operations `append_event`, `get_event_log`, `get_latest_turn`, `save_snapshot`, and `load_latest_snapshot`. The event interface MUST be append-only; it MUST NOT expose update, delete, or clear-log operations.

#### Scenario: Repository contract is backend-neutral

- GIVEN an implementation of the repository
- WHEN the engine receives it through dependency injection
- THEN engine code can append/query events and save/load snapshots without importing SQLAlchemy

#### Scenario: Append-only surface

- GIVEN a repository instance
- WHEN its public attributes are inspected
- THEN `update_event`, `delete_event`, and `clear_log` are absent

### Requirement: Persistable event filtering

The repository MUST accept only `action_resolved` events whose payload has `has_effects == true` and the state-change types `entity_transferred`, `entity_transformed`, `entity_combined`, `flag_set`, and `entity_teleported`. All other event types MUST be rejected.

#### Scenario: Narration is rejected

- GIVEN an `action_output`, `entity_entered`, or `error_output` event
- WHEN `append_event` is called
- THEN the repository rejects it and stores no row

#### Scenario: Unknown event is rejected

- GIVEN an event type outside the persistable set
- WHEN `append_event` is called
- THEN a typed validation error is raised

### Requirement: Repository query semantics

`get_event_log(since_turn)` MUST return persistable events ordered by `turn_number`, then insertion order, with only turns strictly greater than `since_turn`; `get_latest_turn` MUST return `0` for an empty log.

#### Scenario: Tail query

- GIVEN events through turn 9
- WHEN `get_event_log(5)` is called
- THEN only turns 6–9 are returned in deterministic order
