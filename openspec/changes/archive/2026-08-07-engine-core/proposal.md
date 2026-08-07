# Proposal: engine-core

## Intent

Build the engine foundation that loads a world and runs a turn cycle. Satisfies epic #1 acceptance: all unit tests pass; `TurnOrchestrator` loads a minimal world and executes one full turn cycle.

## Scope

**In** (sub-issues #9–#16, #20): `Entity` + Pydantic YAML loader, `WorldState` + `flag_book` dict, 5 atomic operators, `DualGraphEngine`, `HyperEdge` + `Clique` + priority resolution, `MacroEdge` + 6 connection-type predicates, `EngineEvent` + `EventBus`, `TurnOrchestrator` + `EpisodeManager`, `GoalEvaluator`, `ParserInterface` + `NarratorInterface` ABCs + minimal stub implementations sufficient for the turn cycle.

**Out**: full `ClassicParser` (37 verbs, ~180 nouns — dedicated issue), `TemplateNarrator` event→text mapping, SQLite/Alembic persistence implementation, CLI entry point, Fortaleza YAML world data (88 rooms, 120 items, 50 NPCs, 93 puzzles), v1.1 commands (`CAMBIAR A`, `GRUPO`, `ESPERAR`), cooperative multi-protagonist cliques, autonomous NPC brains, AI parser/narrator plugins.

## Capabilities

### New

| Capability | Covers |
|------------|--------|
| `entity-model` | Opaque-typed `Entity` dataclass — engine has zero type-set knowledge |
| `world-loading` | Recursive YAML scan + Pydantic schemas + validation errors |
| `world-state` | Mutable `WorldState` + `flag_book` plain dict + `to_dict`/`from_dict` |
| `atomic-operators` | 5 pure functions returning `OperatorResult(events_payload=...)` + factory |
| `dual-graph` | `DualGraphEngine`: hyper-edges indexed `(anchor, verb)`, macro edges by `from_anchor` |
| `participation-cliques` | Clique validation + priority-desc selection + `"player"` / `"*"` resolution |
| `goal-evaluator` | 6 condition types + recursive and/or composition |
| `event-system` | Frozen `EngineEvent` + `EventBus` (sync Observer, per-engine instance) |
| `turn-orchestrator` | Full turn cycle + system command interception |
| `plugin-contracts` | `ParserInterface` + `NarratorInterface` ABCs + minimal stubs |

### Modified

None — `openspec/specs/` is empty.

## Approach

**Layout** (TDD §2): `src/fortress_engine/{entities,events,engine,plugins}/`. Engine files: `state.py`, `operators.py`, `graph.py`, `goal_evaluator.py`, `episode_manager.py`, `orchestrator.py`. Tests mirror `src/` in `tests/`.

**Confirmed decisions** (all pre-decided by the user — see "Resolved Decisions"):

1. **`Entity.type` is opaque `str`** — no `EntityType` enum, no closed-set validator in the engine. Type-specific knowledge lives in YAML data, never in engine code. (Reason for previous attempt being deleted.)
2. **Pure operator model** — chosen for scalability and testability. Operators mutate `WorldState` and return `OperatorResult(events_payload=...)`. The **orchestrator is the single emitter** of state-change events: it reads `events_payload` and calls `EventBus.emit()`. This gives operators a single, bus-free contract (unit-testable without a bus) and centralises event emission in one owner — the orchestrator — so the persistence layer only has to subscribe at one point.
3. **Movement is macro-edge, not hyper-edge.** Orchestrator intercepts `IR` / `DIRIGIRSE` verbs, evaluates the matching `MacroEdge` (with all 6 predicate types), applies a `TELEPORT` operator. Macro edges never live in the micro graph.
4. **v1.0 multi-protagonist = list-shaped API, single-active turn.** `player_controlled_entities` is always a list (architecture constant #2). Orchestrator iterates `[active_protagonist_id]`. Multi-protagonist turn processing, `CAMBIAR A` / `GRUPO` / `ESPERAR`, and cooperative cliques are v1.1.
5. **`EventBus` is per-engine, not a singleton.** Constructed with the orchestrator instance. Future parallel worlds get isolated buses.
6. **Persistence filter** — only events with `has_effects: true` reach the event log (architecture constant #5). Narration events are derivable from state.
7. **Plugin stubs** — parser handles `IR <door>`, `EXAMINAR <target>`, and graceful `error_output` for unknowns. Narrator stub is a no-op that the event log + UI replace. Sufficient for orchestrator turn-cycle integration tests; full implementations are separate issues.
8. **Operator factory naming** — `execute_operator(state, op_data, ...)` dispatcher + `operator_from_dict(data)` converter (TDD §4.3).
9. **`flag_book` is a plain `dict[str, bool]` on `WorldState`** — no separate `FlagBook` class. Methods on `WorldState`: `set_flag`, `get_flag`.
10. **`turn_number`** lives on `WorldState`. `EpisodeManager.transition_to_next()` resets it to 0 on episode transition. Orchestrator increments it at `turn_started`.

**Delivery** (8 slices, auto-chain, ≤400-line PR budget):

| Slice | Files | Approx lines | Risk |
|-------|-------|--------------|------|
| A: Entity + Event | `entities/{entity,components}.py`, `events/{event_types,event_bus}.py` | ~300 | Low |
| B: WorldState + Operators | `engine/{state,operators}.py` | ~380 | Low–Med |
| C: Graph + HyperEdge + MacroEdge + Clique | `engine/graph.py` | ~451 | High (~13% over) |
| D: GoalEvaluator + EntityLoader | `engine/goal_evaluator.py`, `entities/loader.py` | ~400 | Med |
| E1: Orchestrator + EpisodeManager | `engine/{orchestrator,episode_manager}.py` | ~280 | Low |
| E2: Plugin ABCs + stubs | `plugins/*.py` | ~190 | Low |
| F: Persistence + CLI | `persistence/*`, `cli/main.py` | ~350 | Low |
| G: Acceptance — minimal world + walkthrough | `worlds/fortaleza/world.yaml`, `tests/test_integration/` | ~120 | Low |

Slice C is accepted as a single file: dataclasses + engine + Clique/MacroEdge validation are tightly coupled; splitting creates circular-import risk. Strict TDD: red → green → refactor for every slice.

## Affected Areas

| Path | Impact |
|------|--------|
| `src/fortress_engine/{entities,events,engine,plugins}/` | New |
| `src/fortress_engine/persistence/`, `cli/` | New (slice F) |
| `tests/` (mirrors `src/`) | New (~1500 lines) |
| `openspec/specs/<capability>/spec.md` | New (sdd-spec) |
| `docs/01-11/`, `docs/original-source/` | Untouched (reference only) |

## Risks

| Risk | Mitigation |
|------|------------|
| Slice C ~13% over 400-line PR budget | Single `graph.py` — dataclasses + engine + Clique/MacroEdge validation are tightly coupled; splitting creates circular imports. |
| `events_payload` schema drift between `OperatorResult` and emitted events | Typed payload keys locked in sdd-spec; integration test asserts 1 state-change event per successful operator. |
| Multi-protagonist list invariant violated by singleton code | Code review checklist: no `len(...) == 1` short-circuits, no `[0]` indexing, no `if first:` patterns — always iterate the list. |
| Stub parser too thin for orchestrator integration test | Stub covers `IR <door>` (→ macro edge), `EXAMINAR <target>` (→ action_output), graceful `error_output` for unknowns. Covers all orchestrator branching paths. |
| Event-emission race between `Entity` mutation in operator and event read by subscriber | Operators finish mutation before returning; orchestrator emits after `OperatorResult` is in hand. No shared mutable state during dispatch. |

## Rollback

Greenfield in a skeleton repo: no production data, no downstream consumers. Rollback = delete `src/fortress_engine/**` + revert `openspec/changes/engine-core/`. Per slice: revert one PR in the chained stack (strict dependency order A→G).

## Dependencies

Python 3.11+, `pyyaml`, `pydantic`, `sqlalchemy`, `pytest` (all installed per exploration). Authoritative specs: `docs/prd.md`, `docs/gdd.md`, `docs/tdd.md`, `docs/13-event-system.md`. `openspec/config.yaml` has `tdd: true`, `test_command: pytest`.

## Success Criteria

- [ ] 9 sub-issues closed via chained PRs; `pytest` exits 0 with the full engine-core test suite collected.
- [ ] `TurnOrchestrator.execute_turn("ir norte")` against a 2-room minimal world emits the canonical event sequence: `turn_started` → `input_received` → `action_attempted` → `entity_teleported` → `entity_entered` → `action_resolved` → `turn_ended`.
- [ ] No closed type-set in `engine/`: grep for `EntityType` literal or `ENTITY_TYPES` constant returns zero hits in `src/fortress_engine/`.
- [ ] `from fortress_engine.engine.operators import execute_transfer` works in an empty test with no `EventBus` instantiated — proves operators are bus-free.
- [ ] `player_controlled_entities` accessed as a list everywhere in the engine; no singleton short-circuits.
- [ ] `EpisodeManager.transition_to_next()` resets `WorldState.turn_number` to 0; integration test asserts it.

## Resolved Decisions (sdd-spec framing check)

**User pre-decided (final)**: entity type opacity (decision 1), orchestrator-as-single-state-event-emitter (decision 2), parser = ABC + minimal stub (decision 7), multi-protagonist = list + single-active in v1.0 (decision 4).

**Resolved from exploration** (final): `flag_book` is a plain `dict[str, bool]` on `WorldState` (decision 9), operator factory naming `execute_operator` + `operator_from_dict` (decision 8), orchestrator emits state-change events (decision 2), movement is macro-edge with TELEPORT (decision 3), `turn_number` reset by `EpisodeManager` (decision 10), `EventBus` is per-engine (decision 5), persistence filters to `has_effects: true` (decision 6).

**sdd-spec to confirm framing**: limbo reserved id (`"_limbo"` TDD convention), `EngineEvent.timestamp` round-trips via `event_to_dict` / `event_from_dict`, `Entity.components` value union (int / str / bool / list / dict / None).
