# Persistence SQLite Specification

## Purpose

Provide the v1.0 concrete repository backed by SQLite.

## Requirements

### Requirement: SQLite repository bootstrap and storage

`SQLiteWorldStateRepository(db_path)` MUST implement `WorldStateRepository`, create parent storage as needed, and bootstrap only with `Base.metadata.create_all`. It MUST serialize events through `event_to_dict` and snapshots through `WorldState.to_dict`; Alembic MUST NOT be required.

#### Scenario: File round trip

- GIVEN a repository at a writable file path
- WHEN an event and snapshot are appended and saved, then a new repository opens the same path
- THEN both are queryable with equivalent event/state values

#### Scenario: Missing snapshot

- GIVEN a valid repository with no snapshot for `slot_1`
- WHEN `load_latest_snapshot("slot_1")` is called
- THEN it returns `None`

### Requirement: Snapshot cache integrity

The repository MUST load the newest snapshot for a slot and MUST raise a typed persistence error when its JSON is corrupted; it MUST NOT silently treat corruption as a missing slot.

#### Scenario: Corrupted snapshot

- GIVEN a snapshot row whose `world_state_json` is invalid JSON or not a valid `WorldState`
- WHEN it is loaded
- THEN a typed corruption error is raised

#### Scenario: Independent slots

- GIVEN different states saved to `slot_1` and `slot_2`
- WHEN each slot is loaded
- THEN each returns its own state and turn with no cross-talk
