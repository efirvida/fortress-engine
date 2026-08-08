# Tasks: engine-language-agnostic

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1250 (L1:150, L2:300, L3:250, L4:250, L5:300) |
| 400-line budget risk | High (3.1x budget) |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (L1) → PR 2 (L2) → PR 3 (L3) → PR 4 (L4) → PR 5 (L5) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Vocabulary +3 sections + loader back-compat | PR 1 | `pytest tests/test_entities/test_loader.py tests/test_entities/test_world_yaml_language.py --cov=src/fortress_engine/entities --cov-branch -q` | N/A (no standalone executable contract) | Revert loader.py changes |
| 2 | Orchestrator vocabulary-driven commands + error_output code+data | PR 2 | `pytest tests/test_engine/test_orchestrator.py tests/test_engine/test_orchestrator_save_load.py --cov=src/fortress_engine/engine/orchestrator.py --cov-branch -q` | N/A (requires full state/graph setup) | Revert orchestrator.py changes |
| 3 | Operators code+data + English diagnostics removed | PR 3 | `pytest tests/test_engine/test_operators.py --cov=src/fortress_engine/engine/operators.py --cov-branch -q` | `python -c "from fortress_engine.engine.operators import OperatorResult; assert not hasattr(OperatorResult(...), 'error_message')"` | Revert operators.py changes |
| 4 | MacroGateResult + death-vs-block is_fatal fix | PR 4 | `pytest tests/test_engine/test_graph.py tests/test_engine/test_orchestrator.py --cov=src/fortress_engine/engine --cov-branch -q` | N/A (behaviour change needs orchestrator) | Revert graph.py + orchestrator _handle_movement changes |
| 5 | Narrator messages dispatch + integration + cleanup | PR 5 | `pytest tests/test_plugins/ tests/test_integration/ --cov=src/fortress_engine --cov-branch -q` | `pytest tests/test_integration/test_plugin_integration.py -v -k english` | Revert template_narrator.py changes |

---

## Phase L1: Vocabulary Sections + Loader (specs/world-yaml-extensions, ~150 lines)

- [x] L1.1 RED `test_loader.py` + `test_world_yaml_language.py`: `VocabularyYAML` +3 optional fields (`messages: dict`, `movement_verbs: list`, `system_commands: dict`) round-trip, absent sections default empty (back-compat), `extra="forbid"` rejects typos; `Vocabulary` dataclass mirrors all 3; `load_vocabulary` carries them through
- [x] L1.2 GREEN `entities/loader.py`: `VocabularyYAML` +3 optional fields defaulting empty; `Vocabulary` dataclass +3 matching fields; `load_vocabulary` copies new sections
- [x] L1.3 GATE: `pytest tests/test_entities/test_loader.py tests/test_entities/test_world_yaml_language.py --cov=src/fortress_engine/entities --cov-branch -q` >99%; commit L1

## Phase L2: Orchestrator Vocabulary-Driven (specs/turn-orchestrator, ~300 lines)

**Test rewrite inventory (L2):** `test_orchestrator.py` ~9 Spanish-literal assertions → `error_code`+`data`; `test_orchestrator_save_load.py` ~4 Spanish-literal assertions → codes

- [x] L2.1 RED orchestrator tests: rewrite all Spanish-message assertions to assert `error_code`+`data` (no `message` key); vocabulary-driven system commands (English surface `save→stash`), vocabulary-driven movement verbs (English `go→go`), Spanish defaults preserved when vocabulary `None`; `_parse_save_slot` vocabulary-aware
- [x] L2.2 RED continued: `EPISODE_COMPLETED` constant used (not string literal); dead ternaries (`kind in ("guardar","save")` inside matched branch) removed; `"limbo"`→`None` in `protagonists_listed`; `system_message` emissions use `code` not `message`
- [x] L2.3 GREEN `engine/orchestrator.py`: `__init__(vocabulary: Vocabulary|None=None)`, `DEFAULT_MOVEMENT_VERBS`, `DEFAULT_SYSTEM_COMMANDS`; `_resolve_movement` consults `vocabulary.movement_verbs`; `_detect_system_command` instance method builds surface→kind map from `vocabulary.system_commands` (prefix for `switch`); all 9 `error_output` sites emit `{error_code, data, protagonist_id}` only; `_parse_save_slot` strips vocabulary surface words
- [x] L2.4 GREEN continued: `EPISODE_COMPLETED` constant replaces string literal; dead ternaries removed (L588-592, L625-629); `"limbo"`→`None` (L727); `system_message` payloads use `code` not `message`
- [x] L2.5 GATE: `pytest tests/test_engine/test_orchestrator.py tests/test_engine/test_orchestrator_save_load.py --cov=src/fortress_engine/engine/orchestrator.py --cov-branch -q` >99%; commit L2

## Phase L3: Operators Code+Data (specs/atomic-operators, ~250 lines)

**Test rewrite inventory (L3):** `test_operators.py` L91,104,145,184,219 (`"Usted no puede cargar con eso."`) → `result.code=="not_portable"`; English diagnostics (`f"Entity 'X' not found"`) removed

- [x] L3.1 RED operator tests: parametrized test for every operator failure path → correct `code`+`data` (TRANSFER: `not_portable`, `too_heavy`, `entity_not_found`, `entity_not_in_container`, `container_not_found`; TRANSFORM: `entity_not_found`, `transform_component_missing`; COMBINE: `combine_inputs_missing`; TELEPORT: `teleport_entity_not_found`, `teleport_anchor_not_found`; dispatch: `unknown_operator`, `unhandled_operator`); `protagonist_not_found` in execute_operator dispatch
- [x] L3.2 RED continued: assert `error_message` attribute removed from `OperatorResult`; no English dev diagnostics in operator result data; FLAG always-succeeds path unchanged
- [x] L3.3 GREEN `engine/operators.py`: `OperatorResult` → `code: str|None` + `data: dict` (remove `error_message`); `_MSG_NOT_PORTABLE`/`_MSG_TOO_HEAVY` deleted; all operators emit flat `code`+`data` per design table; English `f"Entity 'X' not found"` diagnostics removed; `execute_operator` unknown type → `unknown_operator`, unreachable fallback → `unhandled_operator`
- [x] L3.4 GATE: `pytest tests/test_engine/test_operators.py --cov=fortress_engine.engine.operators --cov-branch -q` >99% (100%); verify `hasattr(OperatorResult, 'error_message') == False` (passed); commit L3

## Phase L4: Graph MacroGateResult + Death-vs-Block (specs/dual-graph, ~250 lines)

**Test rewrite inventory (L4):** `test_graph.py` L824,957 (Spanish gate-failure strings) → `MacroGateResult` fields; orchestrator movement tests → `is_fatal` routing

- [x] L4.1 RED graph tests: `MacroGateResult` frozen dataclass; 10 parametrized gate cases (5 gates × fatal/non-fatal → `is_valid`, `is_fatal`, `gate_code`, `data`); open edge valid (`is_valid=True, gate_code=""`); correct text unlocks edge; 5 Spanish literals absent from module
- [x] L4.2 RED orchestrator tests: death-via-`is_fatal` (custom `MacroGateResult(is_fatal=True)` routes to `GAME_OVER` regardless of `gate_code`); non-fatal block routes to `error_output` with `error_code="blocked"`+gate data; `death_msg == edge.death_message` string equality removed
- [x] L4.3 GREEN `engine/graph.py`: `MacroGateResult(is_valid, is_fatal, gate_code, data)` dataclass; `validate_macro_edge` returns `MacroGateResult`; 5 Spanish f-strings removed; `_normalize_text` unchanged
- [x] L4.4 GREEN `engine/orchestrator.py` `_handle_movement`: consumes `gate.is_fatal` (not string equality); `gate.is_fatal=True` → `GAME_OVER` with `reason="player_death"` + `gate.data["death_message"]`; `gate.is_fatal=False` → `error_output` with `error_code="blocked"` + `gate.data`
- [x] L4.5 GATE: `pytest tests/test_engine/test_graph.py tests/test_engine/test_orchestrator.py --cov=src/fortress_engine/engine --cov-branch -q` >99%; commit L4

## Phase L5: Narrator Messages Dispatch + Integration (specs/narrator-template-v1, specs/engine-language-agnostic, ~300 lines)

**Test rewrite inventory (L5):** `test_template_narrator.py` L233,240 (`"No entiendes como hacer eso."`) → `error_code="no_action"` dispatch; `test_narrator.py` L213,221,461,467 (Spanish message asserts) → code dispatch

- [x] L5.1 RED narrator tests: `_handle_error_output` dispatches by `error_code` from `DEFAULT_SPANISH_MESSAGES`; `{placeholder}` substitution from `data`; unknown code → deterministic fallback; custom `messages` override honored; no `payload["message"]` access
- [x] L5.2 RED continued: `_handle_system_message` dispatches by `payload["code"]` only (no `message` back-compat); `system_message.<code>` templates with data substitution; "every engine code has a template" parametrized test
- [x] L5.3 RED integration: `test_plugin_integration.py` — end-to-end with English vocabulary (`movement_verbs:[go]`, `system_commands:{save:["save"]}`); `execute_turn("go north")` and `execute_turn("save")` route correctly
- [x] L5.4 GREEN `plugins/template_narrator.py`: `__init__(messages: dict|None=None)`, `DEFAULT_SPANISH_MESSAGES` constant (all `error_output.*` + `system_message.*` codes per design table); `_handle_error_output` dispatches `f"error_output.{code}"` → format(data); `_handle_system_message` dispatches `f"system_message.{code}"` → format(data); remove `error_output`/`system_message` from `_DEFAULT_TEMPLATES`
- [x] L5.5 GATE: `pytest tests/test_plugins/ tests/test_integration/ --cov=src/fortress_engine --cov-branch -q` >99%; zero Spanish user-facing literals in engine (`grep` check); zero hardcoded movement verbs (`grep` check); zero hardcoded system commands (`grep` check); commit L5
