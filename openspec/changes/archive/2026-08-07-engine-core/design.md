# Design: engine-core

## Technical approach

Build a synchronous, dependency-injected runtime: recursive YAML is validated by Pydantic and immediately converted to stdlib dataclasses; `WorldState` is mutated only by five pure operator functions; `TurnOrchestrator` is the sole coordinator and emitter. The engine consumes opaque entity types and components, so all world rules remain data-driven HyperEdges/MacroEdges.

## Module layout and contracts

```
src/fortress_engine/{entities,events,engine,plugins}/
entities/entity.py       Entity; ParsedCommand; GoalCondition(s); CarryOver; Episode
entities/components.py   component-key constants/helpers only (no type enum)
entities/loader.py       EntityYAML/CliqueYAML/HyperEdgeYAML + EntityLoader
events/event_types.py    EngineEvent, event_to_dict, event_from_dict
events/event_bus.py      EventHandler, EventBus
engine/state.py          WorldState
engine/operators.py      TransferOp, TransformOp, CombineOp, FlagOp, TeleportOp,
                          OperatorResult, operator_from_dict, execute_* functions
engine/graph.py          Clique, HyperEdge, MacroEdge, DualGraphEngine
engine/goal_evaluator.py GoalEvaluator
engine/episode_manager.py EpisodeManager
engine/orchestrator.py   TurnOrchestrator
plugins/parser_interface.py ParserInterface + MinimalParser
plugins/narrator_interface.py NarratorInterface + MinimalNarrator
```

These modules map respectively to the ten capabilities: entity-model, world-loading, world-state, atomic-operators, dual-graph, participation-cliques, goal-evaluator, event-system, turn-orchestrator, and plugin-contracts. No `ENTITY_TYPES` or entity-type validation may occur under `engine/`. Use `TYPE_CHECKING` imports and keep GoalCondition, CarryOver, and Episode in `entities/entity.py` to prevent graph/loader/episode circular imports.

Runtime signatures: `WorldState` fields are `entities: dict[str,Entity]`, `flag_book: dict[str,bool]`, `player_controlled_entities: list[str]`, `active_protagonist_id: str`, `current_episode_id: str`, `turn_number: int=0`; methods `get_entity`, `entity_exists`, `set_flag`, `get_flag`, `get_entities_in_container`, `get_player_inventory`, `get_inventory_weight`, `to_dict() -> dict[str,Any]`, `from_dict(cls,data)`. Operators expose `execute_transfer(state,op,protagonist_id)`, `execute_transform(state,op)`, `execute_combine(state,op,anchor_id)`, `execute_flag(state,op)`, `execute_teleport(state,op)`, and `execute_operator(state,op_data,protagonist_id,graph) -> OperatorResult`; all are plain functions and bus-free. `LIMBO_ROOM_ID = "_limbo"`; absent weight contributes zero.

`EngineEvent` is frozen with `(event_id: UUID, type: str, turn_number: int, timestamp: float, payload: dict[str,Any], protagonist_id: str|None=None, episode_id: str|None=None)`; `create(...)` uses `uuid4()` and `time.monotonic()`. `EventBus.subscribe(type,handler)`, `unsubscribe`, and `emit` are synchronous FIFO, wildcard-aware, and isolate handler exceptions.

`GoalEvaluator.__init__(conditions)`, `check(state)`, `_evaluate_condition`, `_evaluate_composite`, `output`, `side_effects`. `EpisodeManager.__init__(episodes,world_path,event_bus)`, `start_episode`, `transition_to_next`, `apply_carry_over`, `get_available_episodes`, `unload_graph` follow TDD signatures. Plugin ABCs are `ParserInterface.parse(raw_text,world_state)->ParsedCommand` and `NarratorInterface.initialize(event_bus)` plus `handle_event(event,world_state)->str|None` (the minimal narrator is a no-op); plugin discovery uses `importlib.metadata.entry_points`, never hardcoded classes.

## Graph, loading, and event design

`DualGraphEngine` indexes `_anchors`, `_macro_edges[from_anchor]`, and `_hyper_edges[anchor][verb]`; insertion/query keeps HyperEdges priority-descending and diagnoses duplicate `(verb,target,priority)` without changing selection. `resolve_special_values` maps `"player"` to the active ID and preserves `"*"`. `validate_clique` checks exact verb, subject/target/context presence, room/inventory reachability, instrument/instrument_not/instrument_any, flags, and raw component equality—without interpreting entity types. `validate_macro_edge` implements exactly `open`, `password`, `riddle`, `danger`, `danger_inverse`, and `conditional`; movement is never a micro edge.

`EntityLoader` recursively scans `world.yaml`, `episodes/`, `shared/`, and each `episode-XX/{rooms,items,npcs,actions,macros}/` (including nested action directories). Pydantic models validate first; conversion produces plain dataclasses. Integrity validation reports dangling references, duplicate priorities, undeclared predicate flags, missing `start_anchor`, invalid carry-over references, and (where applicable) unreachable rooms; no partial runtime object is returned for malformed YAML.

Operators return payloads only after successful mutation: `entity_transferred {entity_id,from_container_id,to_container_id}`, `entity_transformed {entity_id,component_key,old_value,new_value}`, `entity_combined {input_entity_ids,output_entity_id}`, `flag_set {flag_name,old_value,new_value}`, `entity_teleported {entity_id,from_anchor_id,to_anchor_id}`. The orchestrator converts each payload to exactly one state-change `EngineEvent`; one successful operator means one state-change event, and failed operators return no such payload. Narration (`action_output`, `entity_entered`, `error_output`) is not event-sourced.

## Turn flow and decisions

`execute_turn(raw_text)` increments the turn, emits `turn_started` and `input_received`, intercepts SAVE/LOAD/TERMINAR/CAMBIAR A/ESPERAR/GRUPO, then resolves active-protagonist-only input. For movement it finds a MacroEdge, validates it, emits `action_attempted`, applies TELEPORT, emits `entity_entered`, `action_resolved`; otherwise it selects the first valid priority HyperEdge, executes operators, emits optional `action_output`, resolves, evaluates the goal, transitions or emits `game_completed`, checks `player_dead` and emits `game_over`, then emits `turn_ended`. Episode transition applies carry-over, replaces the graph, teleports to `start_anchor`, and resets `turn_number=0`. Canonical payload keys are the exact schemas in `docs/13-event-system.md` §2: turn (`turn_number,active_protagonist_id`; `raw_text,protagonist_id`; `hyper_edge_id,clique,protagonist_id`; `hyper_edge_id,operators_executed,has_effects,protagonist_id`; `turn_number,actions_resolved`), world/episode (`world_id,episode_count`; `episode_id,episode_name,start_anchor_id`; `episode_id,victory_text,carry_over`; `from_episode_id,to_episode_id,carry_over_applied`; `world_id,total_turns`; `reason,turn_number`), and narration (`entity_id,entity_name,from_anchor_id,to_anchor_id,protagonist_id`; `hyper_edge_id,text,protagonist_id`; `error_code,message,protagonist_id`).

Key decisions: macro movement preserves navigation semantics; one `graph.py` is retained despite its projected ~451 lines because graph dataclasses and validation are coupled; imports remain acyclic through shared entity value objects/`TYPE_CHECKING`; list-shaped protagonists preserve future multi-player support; synchronous per-engine bus and monotonic timestamps preserve deterministic v1.0 behavior.

## Slice plan (strict TDD, auto-chain, <400 authored lines each)

| Slice | Modules | RED/GREEN tests | Est. |
|---|---|---|---:|
| A Entity/Event | entities/entity.py, components.py, events/* | entity, event serialization/bus | 300 |
| B State/Operators | engine/state.py, operators.py | state round-trip, five operators | 380 |
| C Dual graph | engine/graph.py | clique, priority, six macro predicates | 451 (exception: coupled file) |
| D Loader/Goals | entities/loader.py, engine/goal_evaluator.py | Pydantic, recursive scan, integrity, goals | 400 |
| E1 Episodes/turn | engine/episode_manager.py, orchestrator.py | movement, event order, death/transition | 280 |
| E2 Plugins | plugins/* | ABC injection, minimal parse/narrate | 190 |
| G Acceptance | worlds/_test_minimal, tests/test_integration/* | full minimal-world turn cycle | 120 |
| F deferred | persistence/ and cli/ (out of this change) | none in engine-core | 350 |

No routing, shell, subprocess, VCS, or process-integration boundary is introduced; threat matrix is N/A. No migration is required. Risks are graph slice size, payload drift, and accidental singleton protagonist assumptions; strict RED→GREEN→REFACTOR plus event-order/list-invariant integration tests mitigate them.
