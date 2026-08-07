# Persistence Models Specification

## Purpose

Define the SQLAlchemy schema for the authoritative event log and snapshot cache.

## Requirements

### Requirement: Event log schema

`EventLog` MUST use table `event_log` with: `id INTEGER` primary-key autoincrement; `event_id VARCHAR(36)` non-null unique; `event_type VARCHAR(50)` non-null; `turn_number INTEGER` non-null; `timestamp FLOAT` non-null; `payload TEXT` non-null JSON; nullable `protagonist_id VARCHAR(100)` and `episode_id VARCHAR(50)`; non-null `save_slot VARCHAR(20)` default `auto`; and non-null `created_at DATETIME`. It MUST define indexes `idx_event_log_turn`, `idx_event_log_type`, and `idx_event_log_slot`.

#### Scenario: Event serialization shape

- GIVEN an `EngineEvent`
- WHEN it is persisted
- THEN `payload` is JSON encoding of `event_to_dict`, whose keys are exactly `event_id`, `type`, `turn_number`, `timestamp`, `payload`, `protagonist_id`, and `episode_id`

#### Scenario: Event identity is unique

- GIVEN two rows with the same `event_id`
- WHEN the second is inserted
- THEN the database rejects the duplicate

### Requirement: Snapshot schema and uniqueness

`SaveSnapshot` MUST use table `save_snapshots` with `id INTEGER` primary-key autoincrement, non-null `save_slot VARCHAR(20)`, `turn_number INTEGER`, `world_state_json TEXT`, and `created_at DATETIME`. The pair `(save_slot, turn_number)` MUST be unique and indexed by `idx_snapshot_slot_turn`, with newest turns queryable first.

#### Scenario: Same save replaces same turn

- GIVEN a snapshot for `slot_1` at turn 12
- WHEN another snapshot for `slot_1` at turn 12 is saved
- THEN only one logical row exists for that key and its state is the latest value

#### Scenario: Slots do not collide

- GIVEN snapshots for `slot_1` and `slot_2` at turn 12
- WHEN either slot is loaded
- THEN only that slot's snapshot is returned
