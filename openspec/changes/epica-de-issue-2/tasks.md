# Tasks: epica de issue #2 — Persistence

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

| Unit | Slice | PR base → target | Focused test command | Lines |
|------|-------|------------------|----------------------|-------|
| 1 | P1: ABC+ORM | feat/epica-de-issue-2-p1 → feat/epica-de-issue-2 | `pytest tests/test_persistence/test_repository_abc.py tests/test_persistence/test_models.py` | ~250 |
| 2 | P2: SQLite | feat/epica-de-issue-2-p2 → feat/epica-de-issue-2-p1 | `pytest tests/test_persistence/test_sqlite_repository.py` | ~300 |
| 3 | P3: Save+Orch | feat/epica-de-issue-2-p3 → feat/epica-de-issue-2-p2 | `pytest tests/test_persistence/test_event_sourcing.py tests/test_engine/test_orchestrator_save_load.py` | ~380 |

### Suggested Work Units

| Unit | Goal | Likely PR | Runtime harness | Rollback boundary |
|------|------|-----------|-----------------|-------------------|
| 1 | ABC + ORM schema, errors, indexes | P1 | N/A — no runtime entry | Revert persistence/*.py; engine untouched |
| 2 | SQLite create_all, append, query, snapshot JSON | P2 | `pytest tests/test_persistence/ -v` | Revert sqlite_repository.py; ABC stays |
| 3 | Bus subscriber, replay, orchestrator save/load | P3 | `python -c "from fortress_engine.persistence import WorldStateRepository"` | Revert event_log.py + orchestrator diffs |

## Phase 1: P1 — ABC + ORM (TDD §4.9, §5.1-5.2, specs/persistence-abc + persistence-models)

- [x] P1.1 RED `test_persistence/test_repository_abc.py`: 5 abstract methods, no update/delete/clear in dir, RepositoryError + NonPersistableEventError + CorruptEventError + CorruptSnapshotError + InvalidSlotError, TDD §4.9
- [x] P1.2 RED `test_persistence/test_models.py`: EventLog (id PK autoincrement, event_id String(36) unique, event_type String(50), turn_number Integer, timestamp Float, payload Text, protagonist_id/episode_id nullable, save_slot default="auto", created_at DateTime), SaveSnapshot (id PK, save_slot, turn_number, world_state_json, created_at), (save_slot, turn_number) unique, 4 indexes per TDD §5.2
- [x] P1.3 GREEN `persistence/repository.py`: WorldStateRepository ABC (TDD §4.9 signatures) + 5 typed error classes (design §Interfaces)
- [x] P1.4 GREEN `persistence/models.py`: Base(DeclarativeBase), EventLog + SaveSnapshot per TDD §5.1, Index + UniqueConstraint per TDD §5.2
- [x] P1.5 REFACTOR `persistence/__init__.py`: export WorldStateRepository, RepositoryError, NonPersistableEventError, Base, EventLog, SaveSnapshot
- [x] P1.6 GATE: `pytest tests/test_persistence/test_repository_abc.py tests/test_persistence/test_models.py --cov=src/fortress_engine/persistence --cov-branch --cov-report=term-missing -q` >99%; commit P1

## Phase 2: P2 — SQLite Repository (TDD §4.10, specs/persistence-sqlite)

- [ ] P2.1 RED `test_persistence/test_sqlite_repository.py`: file round-trip (two SQLiteWorldStateRepository(:memory:)), missing snapshot → None, corrupted snapshot JSON → CorruptSnapshotError, independent slots no cross-talk
- [ ] P2.2 RED (continued): reject action_output/entity_entered/error_output → NonPersistableEventError, unknown event type reject, get_event_log(since_turn) ordered by turn+id, get_latest_turn → 0 for empty log
- [ ] P2.3 GREEN `persistence/sqlite_repository.py`: SQLiteWorldStateRepository(db_path), create_engine, Base.metadata.create_all bootstrap, append_event with persistable filter (action_resolved has_effects=true + 5 state-change types), NonPersistableEventError on reject
- [ ] P2.4 GREEN (continued): get_event_log WHERE turn>since_turn ORDER BY turn, id; get_latest_turn MAX→0; save_snapshot upsert via merge on (save_slot, turn_number); load_latest_snapshot ORDER BY turn DESC LIMIT 1 → (state,turn) or None; CorruptSnapshotError on bad JSON
- [ ] P2.5 GATE: `pytest tests/test_persistence/ --cov=src/fortress_engine/persistence --cov-branch --cov-report=term-missing -q` >99%; commit P2

## Phase 3: P3 — Save System + Orchestrator (TDD §4.11, specs/event-sourcing-save-system + turn-orchestrator)

- [ ] P3.1 RED `test_persistence/test_event_sourcing.py`: wildcard subscription → persistable events append, narration reject, snapshot on game_saved, replay from empty log (fresh+3 actions), replay from snapshot (25+25, only 25 replayed), boundary events only (no re-emission)
- [ ] P3.2 RED `test_engine/test_orchestrator_save_load.py`: GUARDAR 2 → game_saved, turn unchanged; CARGAR 1 → game_loaded + state restored; no repository → no_repository error; GUARDAR 4 / CARGAR 0 → invalid_slot; missing slot → missing_slot error
- [ ] P3.3 GREEN `persistence/event_log.py`: EventSourcingSaveSystem(event_bus, repository), subscribe "*" → _append_to_log filter, subscribe "game_saved" → snapshot via state_provider callable, replay_state direct mutation no EventBus re-emit, SAVE_REPLAY_STARTED/ENDED only
- [ ] P3.4 GREEN `engine/orchestrator.py`: retype repository WorldStateRepository | None, add save_system EventSourcingSaveSystem | None; _handle_system_command slot parse (default slot_1, 1-3 valid→slot_N, else invalid_slot); save→repository.save_snapshot+game_saved; load→snapshot+replay→replace state+game_loaded; preserve no_repository
- [ ] P3.5 RED `test_persistence/test_event_sourcing.py`: integration round-trip (3 actions, save, fresh orchestrator load), snapshot-first replay (50 actions, snapshot at 25), slot independence, append-only surface on SQLite repo
- [ ] P3.6 GATE: `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` >99% total; grep SQLAlchemy under engine/ → 0 hits; commit P3
