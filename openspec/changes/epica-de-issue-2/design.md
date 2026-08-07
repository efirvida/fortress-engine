# Design: epica de issue #2

## Technical approach

Implement persistence as a downward-only, dependency-injected pipeline:

```text
TurnOrchestrator → EventSourcingSaveSystem → WorldStateRepository (ABC)
                                               → SQLiteWorldStateRepository
```

The event log is authoritative; snapshots are performance caches. Runtime code remains
dataclass/event based and imports no SQLAlchemy. Only `sqlite_repository.py` imports ORM
types. This preserves the engine/adapter boundary required by PRD §10 and permits a later
backend without changing turn resolution.

## Architecture decisions

| Decision | Choice and rationale |
|---|---|
| Repository seam | `WorldStateRepository` is the only persistence dependency of save/load orchestration. SQLAlchemy is confined to the concrete adapter, preventing ORM leakage and making fakes straightforward. |
| Storage layout | One database per slot: `saves/slot_N/fortaleza.db`; each row also stores constant `save_slot="slot_N"` for diagnostics. This follows the TDD path and isolates slots. |
| Replay owner | The orchestrator owns snapshot selection and emits `SAVE_REPLAY_STARTED/ENDED`; the save system replays events. Replay mutates state directly and never emits through `EventBus`, preventing narration, goals, and turn-cycle side effects. |
| Persistence filter | Persist `action_resolved` only when `has_effects=True`, plus the five state-change events (`entity_transferred`, `entity_transformed`, `entity_combined`, `flag_set`, `entity_teleported`). Narration and control events are rejected. |
| Snapshot timing | `game_saved` invokes the save system snapshot handler. The handler receives an injected `state_provider` so the event remains small and the TDD two-argument constructor remains supported via an optional provider. |
| Schema bootstrap | `Base.metadata.create_all` only; Alembic is deferred to v1.1. |

## Interfaces and data model

`WorldStateRepository` exposes exactly: `append_event(event)`, `get_event_log(since_turn=0)`,
`get_latest_turn()`, `save_snapshot(state, turn, save_slot)`, and
`load_latest_snapshot(save_slot) -> tuple[WorldState,int] | None`. There are deliberately no
update/delete/clear methods. `RepositoryError` is the base typed error; use
`NonPersistableEventError`, `CorruptEventError`, `CorruptSnapshotError`, and `InvalidSlotError`
for rejected writes, bad JSON/round-trips, and invalid slots. Missing slot databases return
`None` for repository lookup; orchestrator emits exact `ERROR_OUTPUT` codes
`no_repository`, `invalid_slot`, or `save_not_found` rather than silently constructing state.

ORM columns are exact TDD §5.1: `EventLog(id Integer PK autoincrement, event_id String(36)
unique, event_type String(50), turn_number Integer, timestamp Float, payload Text,
protagonist_id String(100) nullable, episode_id String(50) nullable, save_slot String(20),
created_at DateTime)`; `SaveSnapshot(id Integer PK autoincrement, save_slot String(20),
turn_number Integer, world_state_json Text, created_at DateTime)`. Add indexes
`idx_event_log_turn/type/slot` and `idx_snapshot_slot_turn`; enforce snapshot uniqueness on
`(save_slot, turn_number)`. `event_to_dict`/`event_from_dict` and `WorldState.to_dict`/
`from_dict` are the sole serialization contracts; JSON failures raise typed errors.

## Data flow

On every bus event, the save system filters and appends the serialized event. `GUARDAR[N]`
maps to `slot_1..slot_3` (`guardar` and `save` default to slot 1), does not advance turns,
and emits `game_saved`; its handler stores the current state snapshot. `CARGAR[N]` validates
the slot, loads the newest snapshot, sets `since_turn` to its turn (or 0 with a fresh state),
replays `get_event_log(since_turn)`, replaces orchestrator state, and emits `game_loaded`.
Replay must produce zero state-change events between the replay boundary events.

## File changes and slices

| Slice | Files | Scope |
|---|---|---|
| P1 (~250 lines) | `persistence/repository.py`, `models.py`, `__init__.py` | ABC, errors, ORM/index/constraint contracts. |
| P2 (~300) | `persistence/sqlite_repository.py` | SQLite sessions, create_all, append/filter/query/snapshot JSON. |
| P3 (~380) | `persistence/event_log.py`, `engine/orchestrator.py` | subscribers, direct replay, slot routing and state replacement. |

## Testing strategy

Strict RED→GREEN per slice and the project gate (`pytest --cov-branch`, total >99%). Cover
round-trip, 50-action snapshot-first replay, slot independence, append-only API absence,
filter rejection, unknown event type, corrupted event/snapshot JSON, missing slot, invalid
slot, and no-repository compatibility. Integration tests assert exact event order, one
`game_saved` snapshot, unchanged save/load turn number, and zero `EntityTransferred` during
replay.

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, executable classification, or process boundary.

## Migration / Rollout

No migration required; new per-slot databases are bootstrapped with `create_all`. Reverting P1,
P2, or P3 independently preserves the prior `no_repository` behavior.

## Open Questions

None; exact schema and replay set are resolved by this design and the cited docs.
