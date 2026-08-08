# Proposal: epica-de-issue-2 (Persistence — SQLAlchemy, Event Sourcing, Snapshots)

## Intent

The engine-core epic is complete: the engine runs a turn cycle against a YAML world, emits events, and is
fully tested (>99% branch coverage). It has **no persistence** — every session starts from a freshly
loaded world. Issue #2 closes that gap: a player must be able to `GUARDAR` and `CARGAR` a session,
have multiple independent save slots, and have the engine survive a process restart with full state
reconstruction.

The persistence model is **Event Sourcing** (the log of `action_resolved` events is the source of truth)
with a **snapshot cache** (a full `WorldState` JSON taken on every `game_saved` so load is O(events
since the last snapshot), not O(all events ever)). This matches the TDD §4.9-4.11 + §5 spec and
PRD §10's "log de Hiper-Aristas ejecutadas, con snapshot caché opcional" requirement.

## Scope

### In Scope

- `src/fortress_engine/persistence/repository.py` — `WorldStateRepository` ABC (5 abstract methods, per
  TDD §4.9 and PRD §10). Importing the engine never touches SQLAlchemy — the orchestrator and engine
  code only know the ABC.
- `src/fortress_engine/persistence/models.py` — SQLAlchemy 2.0 ORM `EventLog` and `SaveSnapshot` tables
  plus a `Base = DeclarativeBase`. The event log is **append-only** (enforced by the repository
  interface, not by SQL constraints — SQLite has no permission model).
- `src/fortress_engine/persistence/sqlite_repository.py` — `SQLiteWorldStateRepository(db_path)`
  implementation. Uses `Base.metadata.create_all` in `__init__` (no Alembic — issue #22 is deferred to
  v1.1 per TDD §5.3).
- `src/fortress_engine/persistence/event_log.py` — `EventSourcingSaveSystem` that subscribes to
  `EventBus` `"*"` (filtering at write time) and to `"game_saved"` (taking a snapshot on save). Owns
  the `replay_state(initial_state, graph, since_turn)` reconstruction loop.
- `src/fortress_engine/engine/orchestrator.py` — replace the `_handle_system_command("save"|"load")`
  `no_repository` error stubs with real dispatch: parse optional slot number, call repository +
  save_system, emit `GAME_SAVED` / `GAME_LOADED`, replace `self._state` on load. The
  `repository: object | None = None` parameter is retyped to `WorldStateRepository | None` and a new
  `save_system: EventSourcingSaveSystem | None = None` parameter is added.
- `tests/test_persistence/test_event_sourcing.py` — round-trip (3 actions → save → load → state
  matches), replay from empty log, replay from snapshot (50-action reconstruction), save-slot
  independence, `has_effects: true` filter, append-only enforcement, corrupted-snapshot rejection,
  in-memory SQLite (`:memory:`) for fast unit tests + a tmp-path integration test for the file
  round-trip. Plus orchestrator wiring tests for `GUARDAR`/`CARGAR` slot parsing.

### Out of Scope (deferred)

- **Alembic migrations (issue #22)** — explicit v1.1. `Base.metadata.create_all` is the MVP schema
  bootstrap per TDD §5.3.
- **Auto-snapshot every N turns** — v1.1 optimization. MVP snapshots only on `game_saved`.
- **Multi-protagonist save semantics beyond the active list** — `player_controlled_entities` is already
  a list, so saves carry the full list; no per-protagonist saves in MVP.
- **Save menus, slot UI, save listing** — out of scope. The `GUARDAR [N]` / `CARGAR [N]` verb
  interface is the only entry point; a UI is a separate concern.
- **Compression of large snapshots** — Fortaleza-scale worlds are ~50-100 KB; SQLite TEXT handles it.
- **PostgreSQL / Redis / DynamoDB backends** — the ABC is the seam; a second impl is a separate epic.
- **Save-file migration across engine versions** — not a v1.0 problem; document it as a v1.1 risk.

## Capabilities

### New

| Capability | Covers |
|------------|--------|
| `persistence-abc` | `WorldStateRepository` ABC: `append_event`, `get_event_log`, `get_latest_turn`, `save_snapshot`, `load_latest_snapshot` — the single seam between engine and storage |
| `persistence-models` | SQLAlchemy 2.0 ORM: `EventLog` (append-only event source of truth), `SaveSnapshot` (per-slot cache keyed on `(save_slot, turn_number)`) |
| `persistence-sqlite` | `SQLiteWorldStateRepository` concrete impl + `Base.metadata.create_all` bootstrap, file-per-slot layout |
| `event-sourcing-save-system` | `EventSourcingSaveSystem`: `"*"` subscriber that filters + writes, `"game_saved"` subscriber that takes a snapshot, `replay_state` that reconstructs via direct `WorldState` mutation (no event bus re-emit) |

### Modified

| Capability | Change |
|------------|--------|
| `turn-orchestrator` | Save/load system commands now dispatch to `repository` + `save_system` (currently return `no_repository` error). Constructor gains `save_system: EventSourcingSaveSystem | None`. The `repository: object | None` parameter is retyped to `WorldStateRepository | None`. |

## Approach

**Repository pattern with dependency injection (per python-design-patterns §3, §7)** — the orchestrator
holds a `WorldStateRepository` reference; the engine never knows about SQLAlchemy. SQLite is the only
impl for v1.0, but the ABC is the contract (PRD restriction #7, TDD §4.9).

**Layering** (downward-only):
```
TurnOrchestrator  →  EventSourcingSaveSystem  →  WorldStateRepository (ABC)  →  SQLiteWorldStateRepository
```

**File layout (TDD §2, confirmed)**:
```
src/fortress_engine/persistence/
├── __init__.py              # module-level exports
├── repository.py            # WorldStateRepository ABC (5 abstract methods)
├── models.py                # Base, EventLog, SaveSnapshot
├── sqlite_repository.py     # SQLiteWorldStateRepository
└── event_log.py             # EventSourcingSaveSystem
```

### Resolved Decisions (proposal-level)

1. **Save slot storage: per-slot DB file** — `saves/slot_N/fortaleza.db`. The `save_slot` column on
   both `EventLog` and `SaveSnapshot` is set to a constant (`"slot_1"` for `db_path=saves/slot_1/...`).
   It's a denormalized label for debug/grep, not a multi-tenant key. This matches the TDD docstring
   (`db_path: "saves/slot_1/fortaleza.db"`) literally and gives one `.db` file per slot — easy to
   backup, list, or delete a slot. Single connection per session, single-threaded (architecture
   constant #3), no concurrent slot access. The other interpretation (one big DB, all slots in
   `save_slot` column) was rejected because the TDD docstring shows a per-slot path and because
   file-per-slot matches the GDD §2.6 file layout (`event_log.jsonl` + `snapshot_turn_42.json` per
   slot dir).

2. **Replay semantics: snapshot-first, orchestrator-owned** —
   - `GUARDAR` → orchestrator calls `repository.save_snapshot(state, turn, slot)`, emits `GAME_SAVED`.
   - `CARGAR` → orchestrator calls `repository.load_latest_snapshot(slot)`; if `None`, use fresh
     `WorldState` and `since_turn=0`; else use the loaded `(state, turn)` and `since_turn=turn`.
   - Orchestrator then calls `save_system.replay_state(state, graph, since_turn)` and replaces
     `self._state` with the returned state. Emits `GAME_LOADED` and `SAVE_REPLAY_STARTED`/
     `SAVE_REPLAY_ENDED` around the replay so a future UI can show "Cargando...".
   - The save system **does not re-emit** the original state-change events through the bus during
     replay. Replay mutates `WorldState` directly by re-applying the operator payloads from the
     persisted `action_resolved` events (the state-change events are derivable). This avoids
     re-firing narration, the goal evaluator, or the orchestrator's turn cycle. The
     `SAVE_REPLAY_STARTED` / `SAVE_REPLAY_ENDED` boundary events are the only bus traffic from
     replay, and they're for UI not for state.

3. **What gets persisted**: only `action_resolved` events with `has_effects: true` AND the
   corresponding state-change events (`entity_transferred`, `entity_transformed`, `entity_combined`,
   `flag_set`, `entity_teleported`) that the orchestrator emitted in the same dispatch. The
   `action_resolved` row is the "turn had effects" marker; the state-change rows carry the actual
   mutations and are what `replay_state` re-applies. Narration events (`action_output`,
   `entity_entered`, `entity_examined`, etc.) are **never** persisted (architecture constant #5,
   TDD §4.11 note, GDD §2.6 — they are derivable from state).

4. **Snapshot strategy: snapshot-on-save only** — `EventSourcingSaveSystem` subscribes to
   `"game_saved"` and calls `repository.save_snapshot(state, turn, slot)`. The orchestrator emits
   `GAME_SAVED` with the post-mutation state. Periodic auto-snapshot is v1.1.

5. **Append-only enforcement** — `SQLiteWorldStateRepository.append_event` is the only writer to
   `EventLog`. There is no `update_event` / `delete_event` / `clear_log` method. Tests assert this
   by calling `dir(repo)` and grepping for the absence. The repository also rejects any
   `EngineEvent` whose `type` is not in the persistable set (the same set listed in decision 3) —
   saves a future bug class.

6. **Save slot naming** — orchestrator command parsing:
   - `"guardar"`, `"guardar 1"`, `"save"` → `save_slot = "slot_1"`
   - `"guardar 2"` → `save_slot = "slot_2"`
   - `"guardar 3"` → `save_slot = "slot_3"`
   - `"cargar"`, `"cargar 1"` → load `"slot_1"`, etc.
   - Slot numbers outside 1-3 → `ERROR_OUTPUT(error_code="invalid_slot")`. Adding more slots is
     a one-line table change.

7. **Operator parameters not touched** — orchestrator's save/load does NOT change turn accounting.
   A save/load system command does not increment `turn_number` (matches current behavior — system
   commands already short-circuit before `turn_ended`).

## Affected Areas

| Path | Impact | Description |
|------|--------|-------------|
| `src/fortress_engine/persistence/__init__.py` | Modified | Add module-level exports (`WorldStateRepository`, `EventSourcingSaveSystem`, `EventLog`, `SaveSnapshot`, `Base`) |
| `src/fortress_engine/persistence/repository.py` | New | `WorldStateRepository` ABC (TDD §4.9, 5 methods) |
| `src/fortress_engine/persistence/models.py` | New | SQLAlchemy 2.0 `Base`, `EventLog`, `SaveSnapshot` |
| `src/fortress_engine/persistence/sqlite_repository.py` | New | `SQLiteWorldStateRepository` + `Base.metadata.create_all` bootstrap |
| `src/fortress_engine/persistence/event_log.py` | New | `EventSourcingSaveSystem` (EventBus subscriber + replay) |
| `src/fortress_engine/engine/orchestrator.py` | Modified | Replace `no_repository` stubs with real save/load dispatch; retype `repository`; add `save_system` param |
| `src/fortress_engine/cli/main.py` (if exists) | Modified | Optional: instantiate `SQLiteWorldStateRepository` + `EventSourcingSaveSystem` and pass to `TurnOrchestrator` |
| `tests/test_persistence/__init__.py` | Modified | Test-package marker (currently empty stub) |
| `tests/test_persistence/test_event_sourcing.py` | New | Round-trip, replay, snapshot, slot independence, `has_effects` filter, append-only, orchestrator wiring |
| `openspec/specs/persistence-*/spec.md` (4 files) | New | sdd-spec phase |
| `pyproject.toml` | None | `sqlalchemy>=2.0` already present (per exploration) |
| `docs/01-11/`, `docs/original-source/` | Untouched | Reference only |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **>99% branch coverage gate** (AGENTS.md hard gate) on 4 new modules + orchestrator changes | High impact, Med likelihood | TDD: write tests first (round-trip, replay, snapshot, all error paths) before any implementation commit. The 50-action reconstruction test and corrupted-snapshot test catch the trickiest branches. Per-slice `pytest --cov-branch` must pass before the next slice starts. |
| **Replay complexity** — `replay_state` must re-apply operator payloads to `WorldState` without re-running the orchestrator's turn cycle | Med | Replay bypasses the event bus for state mutations: it reads each persisted state-change event and mutates `WorldState` directly. The graph is only consulted to validate movement (TELEPORT destinations must exist), which is the same check the live operator does. No narration, no goal evaluation, no turn-end bookkeeping during replay. |
| **Append-only enforcement** — `EventLog` is "inmutable" per the spec, but SQLite has no permission model | Med | Repository interface has no update/delete methods. Tests assert this by introspecting `dir(repo)`. A docstring on `EventLog` ORM class reiterates the invariant. |
| **Snapshot corruption** — partial write leaves the JSON in an invalid state | Low | Snapshot is a single `INSERT`/`UPDATE` row in a single transaction; SQLite's atomicity covers the row. Tests assert `load_latest_snapshot` raises a typed error on JSON parse failure (no silent None return). |
| **Orchestrator parameter creep** — adding `save_system` and retyping `repository` touches all integration tests | Low | The current `repository: object | None = None` typing is loose, so existing test code that passes `None` keeps working. New optional `save_system: EventSourcingSaveSystem | None = None` defaults to None and the save/load stubs fall through to the existing `no_repository` error. |
| **Event log grows unboundedly** | Low (for MVP) | Document the size assumption (~50-100 KB for Fortaleza). The save system could expose a `compact(slot)` method later; not in v1.0. |
| **Test runtime with 50-action replay** | Low | In-memory SQLite (`:memory:`) + small world → sub-second. Integration test uses `tmp_path`. |
| **Test isolation between save slots** | Low | Each test gets a fresh `tmp_path` / `:memory:` connection. Slot independence test creates two repos with different paths and asserts zero cross-talk. |

## Rollback Plan

Each slice is a self-contained commit (per `work-unit-commits`) so rollback is per-slice:

- **Slice P1 (ABC + ORM models)**: revert the commit. Engine still works without persistence (orchestrator's
  `repository: object | None = None` default keeps the `no_repository` error path alive).
- **Slice P2 (SQLite impl)**: revert. P1's ABC stays in the codebase but no impl exists; nothing imports it.
- **Slice P3 (Save system + orchestrator wiring)**: revert. Orchestrator's save/load reverts to
  `no_repository` error; `_handle_system_command` keeps its stub shape.

No data loss risk: MVP creates fresh `.db` files in `saves/slot_*/`; deleting them is safe.
No migration risk: `create_all` is idempotent, schema is small, no existing users.

## Dependencies

- **Runtime**: `sqlalchemy>=2.0` (already in `pyproject.toml` per exploration; `pyyaml`, `pydantic`
  also already present).
- **Authoritative specs**: `docs/tdd.md` §4.9-4.11 + §5, `docs/13-event-system.md` §8,
  `docs/prd.md` §10, `docs/gdd.md` §2.6.
- **Engine-core dependency** (DONE): `EngineEvent` with `event_to_dict`/`event_from_dict`,
  `WorldState` with `to_dict`/`from_dict`, `EventBus.subscribe("*", ...)`, orchestrator's
  `repository: object | None = None` integration point.

## Success Criteria

- [ ] 3 sub-issues closed via chained PRs; `pytest` exits 0 with the full engine + persistence
      test suite collected.
- [ ] `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` reports
      **>99% total branch coverage** (AGENTS.md hard gate).
- [ ] **Round-trip test**: execute 3 state-changing actions, save to slot_1, instantiate a fresh
      `TurnOrchestrator` against the same `SQLiteWorldStateRepository` (different session),
      `CARGAR 1`, and assert `state.entities`, `state.flag_book`, and `state.turn_number` match
      the pre-save values exactly.
- [ ] **Snapshot-first replay test**: persist 50 actions, take a snapshot at turn 25, persist 25
      more actions, load from slot_1, assert replay applies only the 25 post-snapshot actions and
      the final state matches.
- [ ] **Slot independence test**: write to slot_1, write to slot_2, load slot_1, assert
      slot_2's state did not leak.
- [ ] **Append-only test**: `SQLiteWorldStateRepository` exposes no `update_event` or
      `delete_event` method (introspect `dir`).
- [ ] **Filter test**: `EntityEntered` / `ActionOutput` / `ErrorOutput` narration events are NEVER
      written to the event log (assert by counting rows after a turn cycle).
- [ ] **No event bus re-emission during replay**: subscribe to `EntityTransferred` during a load,
      assert zero emissions between `SAVE_REPLAY_STARTED` and `SAVE_REPLAY_ENDED`.
- [ ] No closed type-set in `engine/`: grep for `SQLAlchemy` import in `src/fortress_engine/engine/`
      returns zero hits — engine code only knows the `WorldStateRepository` ABC.
- [ ] `Base.metadata.create_all` is the only schema bootstrap; no `alembic` import anywhere in
      `src/fortress_engine/`.

## Chained-PR Delivery (auto-chain, ≤400-line PR budget)

| Slice | Files | Approx lines | TDD sub-issue | Risk |
|-------|-------|--------------|---------------|------|
| P1: ABC + ORM models | `persistence/repository.py`, `persistence/models.py`, `persistence/__init__.py`, `tests/test_persistence/test_repository_abc.py`, `tests/test_persistence/test_models.py` | ~250 | #17 (part 1) | Low |
| P2: SQLite impl | `persistence/sqlite_repository.py`, `tests/test_persistence/test_sqlite_repository.py` | ~300 | #17 (part 2) | Low |
| P3: Save system + orchestrator wiring | `persistence/event_log.py`, `engine/orchestrator.py` (modified), `tests/test_persistence/test_event_sourcing.py`, `tests/test_engine/test_orchestrator_save_load.py` | ~380 | #18, #19 | Low–Med |

Total: ~930 lines across 3 PRs, each well under the 400-line budget. Slice P3 is borderline (~380)
because of the orchestrator integration tests, but the orchestrator change itself is small
(~30 lines: parse slot, dispatch to repository, emit events, replace state on load). Strict TDD
per slice: red → green → refactor before opening the next PR.

## Resolved Decisions Summary (sdd-spec framing check)

**Pre-decided by TDD / PRD / GDD** (no debate): ABC shape (5 methods, TDD §4.9), `create_all` for
MVP (TDD §5.3), `has_effects: true` filter (TDD §4.11 note, GDD §2.6, architecture constant #5),
event log as source of truth / snapshot as cache (PRD §10, TDD §4.11), orchestrator as the single
emitter + persistence subscriber (engine-core decision #2 in the archived proposal).

**Resolved by this proposal**: per-slot DB file (decision 1), snapshot-first replay with
orchestrator-owned flow and direct state mutation during replay (decision 2), write filter
includes state-change events (decision 3), snapshot-on-save only (decision 4), append-only
enforced via interface not SQL (decision 5), slot naming `"guardar" → slot_1` (decision 6),
save/load does not increment `turn_number` (decision 7).

**sdd-spec to confirm**: exact `EventLog` column types and indexes (mirrors GDD §2.6), exact
JSON payload shape persisted (via `event_to_dict`), snapshot row uniqueness key (`(save_slot,
turn_number)`), and the precise set of replayable state-change event types
(`entity_transferred`, `entity_transformed`, `entity_combined`, `flag_set`, `entity_teleported`).
