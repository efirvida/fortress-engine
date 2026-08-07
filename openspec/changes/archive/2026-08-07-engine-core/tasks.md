# Tasks: Engine Core

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High (Slice C: 451 lines, accepted exception — coupled file)

| Unit | Slice | PR base → target | Test | Lines |
|------|-------|------------------|------|-------|
| 1 | A: Entity+Event | feat/engine-core-entity-event → feat/engine-core | `pytest tests/test_entities/ tests/test_events/` | 300 |
| 2 | B: State+Operators | feat/engine-core-state-ops → feat/engine-core-entity-event | `pytest tests/test_engine/test_{state,operators}.py` | 380 |
| 3 | C: Graph | feat/engine-core-graph → feat/engine-core-state-ops | `pytest tests/test_engine/test_graph.py` | 451 |
| 4 | D: Loader+Goals | feat/engine-core-loader → feat/engine-core-graph | `pytest tests/test_entities/test_loader.py tests/test_engine/test_goal_evaluator.py` | 400 |
| 5 | E1: Orchestrator | feat/engine-core-orch → feat/engine-core-loader | `pytest tests/test_engine/test_{orchestrator,episode_manager}.py` | 280 |
| 6 | E2: Plugins | feat/engine-core-plugins → feat/engine-core-orch | `pytest tests/test_plugins/` | 190 |
| 7 | G: Acceptance | feat/engine-core-accept → feat/engine-core-plugins | `pytest tests/test_integration/` | 120 |

### Slice A: Entity + Event

- [x] A.1 RED `test_entities/test_entity.py`: opaque type/components, anchor=None, raw equality
- [x] A.2 GREEN `entities/entity.py`: Entity, ParsedCommand, GoalCondition/GoalConditions, CarryOver, Episode
- [x] A.3 GREEN `entities/components.py`: constants only, no enum/closed-set
- [x] A.4 REFACTOR: grep-verify no EntityType/ENTITY_TYPES under entities/
- [x] A.5 RED `test_events/test_event_types.py`: frozen, uuid4/monotonic create, dict round-trip
- [x] A.6 RED `test_events/test_event_bus.py`: sub/unsub/emit, wildcard *, handler isolation, FIFO
- [x] A.7 GREEN `events/event_types.py`: frozen EngineEvent, create(), to_dict/from_dict
- [x] A.8 GREEN `events/event_bus.py`: EventHandler, EventBus per-instance sync

### Slice B: State + Operators

- [x] B.1 RED `test_engine/test_state.py`: flags (get/set/missing→False), entity queries, KeyError on missing, weight sum, to_dict/from_dict round-trip
- [x] B.2 GREEN `engine/state.py`: WorldState (entities, flag_book, player_controlled_entities:list, active_protagonist_id, current_episode_id, turn_number=0)
- [x] B.3 RED `test_engine/test_operators.py`: each op success+failure; weight, old_value, limbo, bus-free, factory
- [x] B.4 GREEN `engine/operators.py`: 5 op dataclasses, OperatorResult, 5 execute_*, execute_operator, operator_from_dict, LIMBO_ROOM_ID="_limbo"

### Slice C: Dual Graph (size exception)

- [x] C.1 RED `test_engine/test_graph.py`: priority order, 9 clique predicates, resolve_special_values, 6 macro types
- [x] C.2 GREEN `engine/graph.py`: Clique, HyperEdge, MacroEdge; DualGraphEngine all methods

### Slice D: Loader + Goals

- [x] D.1 RED `test_entities/test_loader.py`: reject bad YAML, recursive dirs, validate_world errors
- [x] D.2 GREEN `entities/loader.py`: EntityYAML/CliqueYAML/HyperEdgeYAML, EntityLoader 10 methods
- [x] D.3 RED `test_engine/test_goal_evaluator.py`: 6 atomic, recursive and/or, unknown→false
- [x] D.4 GREEN `engine/goal_evaluator.py`: GoalEvaluator + check/composite/output/side_effects

### Slice E1: Orchestrator + Episodes

- [x] E1.1 RED `test_engine/test_episode_manager.py`: transition resets turn, carry_over, teleport, graph replace
- [x] E1.2 GREEN `engine/episode_manager.py`: constructor + 4 methods
- [x] E1.3 RED `test_engine/test_orchestrator.py`: movement event order, fail→error_output, list invariant
- [x] E1.4 GREEN `engine/orchestrator.py`: TurnOrchestrator, execute_turn, single emitter from events_payload

### Slice E2: Plugins

- [x] E2.1 RED `test_plugins/test_parser.py` + `test_narrator.py`: injection, IR/EXAMINAR/unknown, no-op
- [x] E2.2 GREEN `plugins/parser_interface.py`: ParserInterface ABC + MinimalParser
- [x] E2.3 GREEN `plugins/narrator_interface.py`: NarratorInterface ABC + MinimalNarrator

### Slice G: Acceptance

- [x] G.1 RED `test_integration/test_walkthrough.py`: full cycle, canonical events, episode, list invariant
- [x] G.2 GREEN `worlds/_test_minimal/`: 2-room world + fixture; all proposal success criteria
