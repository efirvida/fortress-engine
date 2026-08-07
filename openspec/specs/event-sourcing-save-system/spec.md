# Event Sourcing Save System Specification

## Purpose

Persist effectful state transitions and reconstruct sessions across process restarts.

## Requirements

### Requirement: EventBus persistence subscriber

`EventSourcingSaveSystem` MUST subscribe to `EventBus` wildcard events, apply the persistable-event filter, and snapshot only on `game_saved`. Narration and failed actions MUST never become source records.

#### Scenario: Effectful action is recorded

- GIVEN an `action_resolved` event with `has_effects: true` and its state-change events
- WHEN the bus emits them
- THEN each persistable event is appended once

#### Scenario: Read-only action is ignored

- GIVEN `action_resolved` with `has_effects: false` and narration events
- WHEN the bus emits them
- THEN no event-log row is written

### Requirement: Snapshot-first event-sourcing load

The event log MUST remain authoritative and snapshots MUST be performance caches. Loading MUST start from the latest slot snapshot when present, then replay only tail events with `turn_number > snapshot_turn`; without a snapshot it MUST replay from the initial state. Replay MUST apply exactly `entity_transferred`, `entity_transformed`, `entity_combined`, `flag_set`, and `entity_teleported`, return final state and turn, and MUST NOT re-emit state-change/narration events.

#### Scenario: Acceptance A round trip

- GIVEN three effectful actions, a save, and a fresh orchestrator
- WHEN the fresh session loads the slot
- THEN entities, flags, active protagonists, episode, and turn equal the pre-save state

#### Scenario: Acceptance B cache is not authority

- GIVEN a snapshot at turn 25 and 25 authoritative tail actions
- WHEN the slot loads
- THEN only the tail is replayed and the final state follows the event log

#### Scenario: Replay boundary is silent

- GIVEN listeners around `save_replay_started` and `save_replay_ended`
- WHEN a load replays events
- THEN only boundary events are emitted by replay, with zero replayed state-change events

### Requirement: Slot and failure behavior

Save/load MUST preserve independent slots, reject a missing slot with a typed not-found error (or explicit empty-load result as defined by the caller), and reject unknown event types and append-only violations without mutating stored data.

#### Scenario: Acceptance C independent slots

- GIVEN distinct states saved in slots 1 and 2
- WHEN slot 1 is loaded
- THEN slot 2 remains unchanged

#### Scenario: Invalid replay event

- GIVEN an unknown event in the log
- WHEN replay is requested
- THEN a typed replay error is raised and no partial state is accepted

#### Scenario: Missing slot

- GIVEN `CARGAR 3` and no snapshot or event log for `slot_3`
- WHEN loading is requested
- THEN the state is unchanged and the caller emits exact `error_output(error_code="missing_slot")`
