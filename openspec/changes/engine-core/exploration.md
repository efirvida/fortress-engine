# Exploration: engine-core

## Current State

**Critical discrepancy**: Source files claimed as "implemented" (entity.py, components.py, event_types.py, event_bus.py) do NOT exist on disk. Stale `.pyc` caches in `__pycache__/` are remnants of prior compilation. Git log shows only 2 commits (init + docs). All test files are empty 0-byte stubs — 0 tests collected by pytest. The codebase is **effectively greenfield** for all 9 sub-issues.

Dependencies fully installed and verified: pyyaml 6.0.3, pydantic 2.13.4, sqlalchemy 2.0.51, pytest 9.1.1, alembic 1.19.0. No additional dependencies required.

## Affected Areas

| Path | Status | TDD Task |
|------|--------|----------|
| `src/fortress_engine/entities/entity.py` | Missing (stale .pyc only) | #2 |
| `src/fortress_engine/entities/components.py` | Missing (stale .pyc only) | #2 |
| `src/fortress_engine/entities/loader.py` | Missing | #3, #4 |
| `src/fortress_engine/engine/state.py` | Missing | #5 |
| `src/fortress_engine/engine/operators.py` | Missing | #6 |
| `src/fortress_engine/engine/graph.py` | Missing | #7, #8 |
| `src/fortress_engine/engine/goal_evaluator.py` | Missing | #10 |
| `src/fortress_engine/engine/orchestrator.py` | Missing | #16 |
| `src/fortress_engine/engine/episode_manager.py` | Missing | #15 |
| `src/fortress_engine/events/event_types.py` | Missing (stale .pyc only) | #9 |
| `src/fortress_engine/events/event_bus.py` | Missing (stale .pyc only) | #9 |
| `src/fortress_engine/plugins/` (all) | Empty stubs | #13, #14 |
| `src/fortress_engine/persistence/` (all) | Empty stubs | #11, #12 |
| `src/fortress_engine/cli/main.py` | Missing | #17 |
| `tests/` (all test files) | Empty 0-byte stubs | #19-30 |

## Approaches (Slicing Strategy)

All slices follow strict TDD: write failing tests → implement → verify green.

### Slice A: Entity + Event System
**Sub-issues**: #10 (entity dataclass portion), #13 (EventBus + EngineEvent)
**Files**: `entities/entity.py`, `entities/components.py`, `events/event_types.py`, `events/event_bus.py`
**Dependencies**: None (stdlib + pyyaml/pydantic installed)
**Lines**: ~180 code + ~120 tests = ~300 total. Budget risk: **Low**
**Key decisions**: `ParsedCommand` and `Entity` dataclasses; `EventBus` Observer pattern; `EngineEvent` frozen dataclass with UUID4 + monotonic timestamps

### Slice B: WorldState + 5 Operators
**Sub-issues**: #11, #12
**Files**: `engine/state.py`, `engine/operators.py`
**Dependencies**: Slice A (Entity dataclass)
**Lines**: ~200 code + ~180 tests = ~380 total. Budget risk: **Low-Medium**
**Key decisions**: `flag_book` as plain `dict[str, bool]` on WorldState (not separate FlagBook class); `OperatorResult` dataclass; `execute_operator()` factory function; TRANSFER weight validation edge cases

### Slice C: Graph Engine
**Sub-issues**: #9, #15, #16
**Files**: `engine/graph.py` (~250 lines — dataclasses + engine + validation)
**Dependencies**: Slice A (Entity), Slice B (WorldState)
**Lines**: ~250 code + ~200 tests = ~450 total. Budget risk: **High** — may need split
**Key decisions**: HyperEdge/MacroEdge/Clique dataclass placement (inline in graph.py or separate file); Clique validation 9 predicate types; MacroEdge 6 connection types with death/danger conditions

### Slice D: GoalEvaluator + YAML Loader
**Sub-issues**: #10 (loader portion), #20
**Files**: `engine/goal_evaluator.py`, `entities/loader.py`
**Dependencies**: Slice A (dataclasses), B (WorldState), C (DualGraphEngine for entity validation)
**Lines**: ~220 code + ~180 tests = ~400 total. Budget risk: **Medium**
**Key decisions**: Pydantic model placement (inline in loader.py vs separate schemas.py); GoalCondition and/or recursion depth; world validation (dangling refs, duplicate priorities, unreachable rooms)

### Slice E1: Orchestrator Core + Episode Manager
**Sub-issues**: #14
**Files**: `engine/orchestrator.py`, `engine/episode_manager.py`
**Dependencies**: All prior slices
**Lines**: ~160 code + ~120 tests = ~280 total. Budget risk: **Low**
**Key decisions**: System command interception (SAVE, LOAD, QUIT, SWITCH, WAIT, GROUP); turn cycle ordering; event emission responsibility alignment between TDD and GDD

### Slice E2: Plugins (Parser + Narrator Stubs)
**Sub-issues**: Parser/Narrator ABCs + minimal implementations
**Files**: `plugins/parser_interface.py`, `plugins/narrator_interface.py`, `plugins/classic_parser.py` (stub), `plugins/template_narrator.py` (stub)
**Dependencies**: Slice E1 (orchestrator needs them)
**Lines**: ~120 code + ~70 tests = ~190 total. Budget risk: **Low**
**Key decisions**: ClassicParser as minimal stub (accepts a few verbs) vs full implementation (37 verbs, ~180 nouns) — full impl would exceed budget; TemplateNarrator as stub that prints payload text directly

### Slice F: Persistence + CLI
**Sub-issues**: Persistence infrastructure + CLI entry points
**Files**: `persistence/models.py`, `persistence/repository.py`, `persistence/sqlite_repository.py`, `persistence/event_log.py`, `cli/main.py`
**Dependencies**: Slice E1 (orchestrator emits events)
**Lines**: ~200 code + ~150 tests = ~350 total. Budget risk: **Low**
**Key decisions**: `Base.metadata.create_all()` for MVP (not Alembic migrations); event persistence filter (`has_effects: true` only vs all events); snapshot as JSON cache, not source of truth

### Slice G: Acceptance
**Files**: `worlds/fortaleza/world.yaml` (minimal), `tests/test_integration/test_walkthrough.py`
**Lines**: ~20 data + ~100 test = ~120 total. Budget risk: **Low**

## Recommendation

Proceed with 8-slice auto-chain delivery (splitting E into E1+E2 for budget compliance). Slice C at 451 lines is ~12% over budget — tolerable as a single PR given its high cohesion (graph dataclasses + engine + validation are tightly coupled). If strict 400-line compliance is required, split MacroEdge predicate evaluation into a follow-on slice.

**First blocking action**: Confirm whether entity + event source files should already exist. If the user intended them to exist but they were deleted, Slice A shrinks to a verification pass. If greenfield, Slice A creates them from scratch.

## Risks

1. **Source file recovery**: `.pyc` cache suggests entity.py/components.py/event_types.py/event_bus.py existed and were compiled. User must confirm whether to restore from cache or rewrite.
2. **Event emission conflict**: GDD §2.4/Event System §2.3 says StateContainer emits state-change events; TDD §4.3 says operators are pure, orchestrator emits. This architectural conflict must be resolved before Slice B implementation or event sourcing will be inconsistent.
3. **Slice C budget (~451 lines)**: 3 closely-coupled concerns (dataclasses + engine + validation). Splitting would create artificial test dependencies. Accept the slight overage or split MacroEdge predicates into follow-on.
4. **ClassicParser scope**: Full implementation is ~250 lines. For MVP, implement as minimal stub (~30 lines) that handles a few verbs. Defer full parser to a dedicated issue.
5. **EpisodeManager graph lifecycle**: Unload/reload during episode transition must handle entity reference cleanup to avoid stale DualGraphEngine references in the orchestrator.

## Open Questions

1. **Who emits state-change events?** TDD says orchestrator; Event System says StateContainer. The proposal must resolve this — recommended: StateContainer/WorldState emits via a callback to EventBus, keeping operators pure per TDD.

2. **How does movement work?** MacroEdges connect rooms; HyperEdges define actions inside rooms. When the player types "IR NORTE", does the orchestrator: (a) intercept movement commands → evaluate MacroEdges → TELEPORT, OR (b) treat movement as a HyperEdge in the Micro graph? GDD §2.5 step 4 implies HyperEdge path; GDD §2.2 describes MacroEdge evaluation. Recommend: orchestrator intercepts movement, evaluates MacroEdges, emits TELEPORT — MacroEdges are NOT HyperEdges.

3. **Entity deduplication on episode transition**: Player entity must survive graph unload/reload. Should EpisodeManager preserve the player entity in WorldState independently of the episode graph being unloaded, or should it be part of the carry_over mechanism? Recommend: player entity is shared/ data that persists across episodes — it's loaded once at world init, not per-episode.

4. **turn_number reset**: Event System §9.3 step 7 shows turn_number resetting to 1 after episode transition. TDD §3.5 stores it on WorldState. Who resets it — orchestrator on `episode_started`, or EpisodeManager during `transition_to_next()`? Recommend: EpisodeManager resets it during transition (clean separation of concerns).

5. **Stub plugins depth**: For Slice E2, should parser/narrator be full implementations or minimal stubs? Full ClassicParser is ~250 lines alone. Recommend: minimal stubs that satisfy ABC contracts for MVP; full implementations in dedicated issue post-engine-core.

## Key Learnings

1. The `.pyc` cache files for entity.py, components.py, event_types.py, and event_bus.py indicate prior source compilation, but the source files are missing from disk and git — this is a recovery/rewrite situation, not a verification pass.
2. The GDD/TDD event emission responsibility conflict (StateContainer vs orchestrator) is the highest-risk architectural decision for the engine-core implementation — it affects operators, event sourcing, and testing strategy.
3. DualGraphEngine + HyperEdge/Clique + MacroEdge are ~250 lines of tightly coupled code sharing the same dataclasses — splitting into separate files would create circular dependency risks; a single graph.py file is the safer design.
4. ClassicParser full implementation (37 verbs, ~180 nouns, partial name matching, tilde normalization, stopwords) is a self-contained ~250-line module that should be its own issue, not crammed into an engine-core slice alongside orchestrator.
5. The 400-line review budget is achievable across 7-8 slices with one borderline slice (Slice C at ~451 lines) — auto-chain delivery with chained PRs is the appropriate strategy.
