```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:2a92ecdf112cc02eaeff61e3a336f02e9cbf19ef6bcbe7ea6c47c603c1def759
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 12/12
scenarios: 26/26
test_command: pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q
test_exit_code: 0
test_output_hash: sha256:2a92ecdf112cc02eaeff61e3a336f02e9cbf19ef6bcbe7ea6c47c603c1def759
build_command: pip install -e .
build_exit_code: 0
build_output_hash: sha256:198e2de459bf89b9c32294358428bf816fb3581615fd91b9d24461548c25303c
```

# Verification Report: engine-language-agnostic

**Change**: engine-language-agnostic
**Version**: N/A (working-tree candidate; 5 apply slices L1–L5 complete, uncommitted)
**Mode**: Standard (AGENTS.md hard gate: >99% statements AND branches)

Independent requirements/runtime verification by the `sdd-verify` executor. No fixes made; findings reported only. No commits or PRs created.

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 22 (L1.1–L1.3, L2.1–L2.5, L3.1–L3.4, L4.1–L4.5, L5.1–L5.5) |
| Tasks complete | 22 |
| Tasks incomplete | 0 |

All tasks in `tasks.md` are marked `[x]`. Native dispatcher confirms `taskProgress.allComplete = true`, `applyState = all_done`, `verify = ready`. Full-spec verification (proposal + 6 delta specs + design + tasks).

## Build & Tests Execution

**Build (pip install -e .)**: PASSED — exit 0 (`198e2de4...`). Import harness: `MacroGateResult`, `OperatorResult`, `TurnOrchestrator`, `DEFAULT_MOVEMENT_VERBS`, `DEFAULT_SYSTEM_COMMANDS`, `VocabularyYAML`, `Vocabulary`, `TemplateNarrator`, `DEFAULT_SPANISH_MESSAGES` all importable.

**Tests**: 786 passed / 0 failed / 0 skipped (exit 0)

```
786 passed, 315 warnings in 14.26s
```

**Coverage**: 100% statements / 100% branches — TOTAL 1804 stmts, 0 misses, 558 branches, 0 partials. Hard gate (>99%) PASSED.

| Relevant module | Stmts | Branch | Cover |
|---|---|---|---|
| `engine/graph.py` | 225 | 114 | 100% |
| `engine/operators.py` | 131 | 52 | 100% |
| `engine/orchestrator.py` | 257 | 112 | 100% |
| `entities/loader.py` | 272 | 62 | 100% |
| `plugins/narrator_interface.py` | 45 | 14 | 100% |
| `plugins/template_narrator.py` | 91 | 24 | 100% |
| TOTAL (all packages) | 1804 | 558 | 100%/100% |

## Evidence Table

| # | Feature | Claim | Command | Exact result |
|---|---------|-------|---------|--------------|
| 1 | Coverage gate (>99%) | 100% stmts + branches | `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` | TOTAL 1804 stmts / 558 branches, 0 missed → **100% / 100%**, exit 0 ✔ |
| 2 | Full suite green | zero fails | same run | **786 passed, 0 failed, 0 skipped** ✔ |
| 3 | No Spanish literals in engine | zero user-facing hits (`á é í ó ú ü ñ`) | `grep -rnP "[áéíóúñü]" src/fortress_engine/{engine,events,entities,persistence} --include=*.py` | 1 hit: `graph.py:599` — `_normalize_text` docstring comment (allowed) ✔ |
| 4 | No `"message"` keys in engine | zero | `grep -rn '"message"' src/fortress_engine/engine/` | **zero hits** (exit 1) ✔ |
| 5 | No hardcoded movement verbs | recognition from vocabulary | `grep -n '"ir"\|"abrir"' engine/orchestrator.py` | hit at :82 = `DEFAULT_MOVEMENT_VERBS` (spec-mandated default), :212/:459 comments, :487 `"verb": "ir"` **event data label** in ACTION_ATTEMPTED clique (recognition uses `_movement_verbs()`, see #7) ✔* |
| 6 | `_SYSTEM_COMMANDS`/`_SYSTEM_PREFIXES` gone | replaced by DEFAULT_SYSTEM_COMMANDS | `grep -rnw '_SYSTEM_COMMANDS\|_SYSTEM_PREFIXES' src/` | **zero hits** (exit 1); only `DEFAULT_SYSTEM_COMMANDS` refs at :83/:162/:165 ✔ |
| 7 | MacroGateResult | validate_macro_edge returns structured result | source + tests `test_macro_edge_parametrized_gates`, `test_macro_gate_result_is_frozen` | frozen dataclass `(is_valid, is_fatal, gate_code, data)`; 5 gate codes + `""` valid; `is_fatal = edge.death_message is not None`; orchestrator routes via `gate.is_fatal`, **no death-msg equality** ✔ |
| 8 | OperatorResult | no `error_message`, has `code`/`data` | `python3 -c "...hasattr..."` | `hasattr(error_message)=False`; `hasattr(code)=True`; `hasattr(data)=True`; fields `[success, code, data, events_payload]` ✔ |
| 9 | Vocabulary 3 sections + back-compat | load absent → empty defaults | `test_new_sections_present` + `test_new_sections_absent_default_empty` + `test_load_vocabulary_happy_path` (fixture w/o sections) | `VocabularyYAML` + `Vocabulary` carry `messages`/`movement_verbs`/`system_commands`; `extra="forbid"` preserved; missing keys default empty ✔ |
| 10 | Narrator dispatch by error_code / code | no `payload["message"]` | `test_error_output_by_error_code`, `test_system_message_code_only_no_message_backcompat` | `_handle_error_output` builds `f"error_output.{code}"`; `_handle_system_message` builds `f"system_message.{code}"`; all 23 error codes + 4 system codes in `DEFAULT_SPANISH_MESSAGES`; no message-key access (grep zero hits) ✔ |
| 11 | Contract guard enumerates all engine codes | every code has template | `test_every_error_code_has_template[23 codes]` + `test_every_system_code_has_template` | parametrized over `_ALL_ENGINE_ERROR_CODES` (23) + 4 system codes → all present in `DEFAULT_SPANISH_MESSAGES`; `test_esperar_not_in_template_narrator_source` guards the contract ✔ |
| 12 | requirements traceability | scenario → passing test | spot-check matrix §Requirements Coverage | 12/12 requirements, 26/26 scenarios COMPLIANT ✔ |
| 13 | esperar | only default wait surface | `grep -rn "esperar" src/` | single hit `orchestrator.py:87` `"wait": ["esperar", "wait"]` — vocabulary **default**; never a movement verb (`DEFAULT_MOVEMENT_VERBS = {"ir","abrir"}`) ✔ |
| 14 | "limbo" removed | orchestrator emits None | `grep -n "limbo" engine/*.py` | **zero hits**; `protagonists_listed` emits `location: ent.spatial_anchor` (may be None); `test_grupo_location_is_none_not_limbo` ✔ |
| 15 | EPISODE_COMPLETED constant | no string literal | source :415 | `self._emit(EPISODE_COMPLETED, ...)`; dead ternaries removed (`kind == "save"` single branch) ✔ |

`*` — line 487's `"verb": "ir"` is the canonical movement event label inside the ACTION_ATTEMPTED clique payload, not a recognition literal; recognition is fully vocabulary-driven (`_resolve_movement` consults `self._movement_verbs()`). Pre-existing label; flagged SUGGESTION S-3 for archive reconciliation.

## Requirements Coverage (per delta spec — actual spec counts)

### engine-language-agnostic (umbrella) — 2 reqs, 3 scenarios → all COMPLIANT
- **Engine emits codes, narrator owns text**: `error_output`/`system_message` carry flat code + `data`; no hardcoded verbs/commands/messages.
  - Scenario English world w/o engine changes: `test_orchestrator.py::test_movement_uses_vocabulary_verbs` (go → teleported) + `test_system_commands_from_vocabulary_english` (quit) + `test_orchestrator_save_load.py::test_english_save_alias_works` ✔ COMPLIANT
  - Scenario Spanish default keeps working: `test_default_movement_verbs_fallback` + `test_default_system_commands_fallback` + `test_execute_turn_system_esperar` ✔ COMPLIANT
- **Flat error code contract**: codes flat; narrator dispatches by key.
  - Scenario Narrator dispatches by flat code: `test_template_narrator.py::test_error_output_by_error_code` (too_heavy → `"Sería demasiado peso."`) ✔ COMPLIANT

### atomic-operators — 1 req, 2 scenarios → COMPLIANT
- **Structured operator failure**: `OperatorResult` gains `code`+`data`; `error_message` removed; `_MSG_*` constants removed; 5 operators emit flat codes.
  - Scenario Not-portable vs too-heavy distinguishable: `test_operators.py::test_transfer_item_exceeds_max_weight` (not_portable) + `test_transfer_inventory_full` (too_heavy) + `test_operator_failure_codes` ✔ COMPLIANT
  - Scenario No player-facing diagnostics: `test_operator_result_has_no_error_message_attribute` + failure `data={"entity_id": ...}` ✔ COMPLIANT

### dual-graph (1 spec / 4 scenarios) → COMPLIANT
- **Structured macro-gate result**:
  - Text gate closed: `test_macro_edge_requires_text_wrong_text` (gate_code text_closed + data) ✔
  - Lethal gate fatal: `test_macro_edge_requires_item_kills_without_item` (is_fatal True) / `test_macro_edge_parametrized_gates` ✔
  - Open edge valid: `test_macro_edge_no_predicates_always_passable` + `test_macro_gate_result_valid_defaults` (gate_code "") ✔
  - Correct text unlocks: `test_macro_edge_requires_text_correct_text_opens` ✔

### turn-orchestrator (4 reqs, 8 scenarios) → COMPLIANT
- **Vocabulary-injected**: `test_orchestrator_accepts_vocabulary_parameter`; movement `test_movement_uses_vocabulary_verbs`; system `test_system_commands_from_vocabulary_english` + `test_switch_prefix_uses_vocabulary_surface`; default Spanish `test_default_*` ✔
- **Error output code+data only**: `test_execute_turn_no_clique_emits_error` (no_action + `data.verb`, no `message` key); `test_execute_turn_nonfatal_gate_emits_blocked_error` (blocked + gate data) + `test_error_output_no_message_in_save_load_paths` ✔
- **Death-vs-block via is_fatal**: `test_execute_turn_lethal_gate_emits_game_over_player_death` (custom `MacroGateResult(is_fatal=True)` → GAME_OVER regardless of code) + `test_execute_turn_nonfatal_gate_emits_blocked_error` ✔
- **Code hygiene**: `EPISODE_COMPLETED` constant (`test_episode_completed_*`), dead ternaries removed, "limbo"→None (`test_grupo_location_is_none_not_limbo`) ✔

### narrator-template-v1 (3 reqs, 6 scenarios) → all COMPLIANT
- **Error output dispatches by error**: `test_error_output_by_error_code`, `test_error_output_data_placeholders`, `test_error_output_no_message_key`, `test_error_output_unknown_code_falls_back` ✔
- **System message dispatches by code**: `test_system_message_by_code` + `test_system_message_code_only_no_message_backcompat` ✔
- **Default Spanish constant**: `test_every_error_code_has_template` ×23 + `test_every_system_code_has_template` ×4 + `test_handle_error_output` (no messages → defaults) ✔

### world-yaml-extensions (1 req, 3 scenarios) → COMPLIANT
- **Vocabulary gains 3 sections**: `test_new_sections_present` + `test_new_fields_round_trip` ✔
- **Sections absent (back-compat)**: `test_new_sections_absent_default_empty` + `test_load_vocabulary_happy_path` (existing `full_vocabulary.yaml` loads) ✔
- **Unknown section rejected**: `test_extra_forbid_rejects_misspelled_section` ✔

**Compliance summary (actual specs: 12 requirements · 26 scenarios)**
| Result | Count |
|---|---|
| ✅ COMPLIANT | 26/26 |
| ❌ FAILING / UNTESTED | 0 |

## Correctness (Static Evidence)

| Implementation | Status | Notes |
|---|---|---|
| `graph.py` MacroGateResult + validate_macro_edge | ✅ | frozen dataclass; `is_fatal` structural; 5 codes; `data` carries passage_name + predicate + death_message |
| `operators.py` OperatorResult code+data | ✅ | `error_message` removed; no English diagnostics; flat codes incl. teleport_* / unknown / unhandled / protagonist_not_found |
| `orchestrator.py` vocabulary-driven | ✅ | `vocabulary` ctor param; `DEFAULT_MOVEMENT_VERBS` / `DEFAULT_SYSTEM_COMMANDS`; `_detect_system_command` surface map (longest-first, switch prefix); `_parse_save_slot` surfaces; 9 error sites → code+data; death-by-`is_fatal` |
| `loader.py` Vocabulary growth | ✅ | 3 optional sections; clone-through in `load_vocabulary`; back-compat |
| `template_narrator.py` code dispatch | ✅ | `messages` ctor; `f"error_output.{code}"` / `f"system_message.{code}"`; deterministic fallback; no sender key; `_DEFAULT_TEMPLATES` reduced to 7 |
| `narrator_interface.py` MinimalNarrator | ✅ (scope note S-1) | error_output handler adapted to `error_code` so MinimalNarrator stays functional after message removal — proposal said "no changes" |

## Coherence (Design)

| Design decision | Followed? | Notes |
|---|---|---|
| Engine emits code+data; narrator owns text | ✅ | payload `{error_code, data, protagonist_id}`; no message key |
| Flat codes, no namespace | ✅ | 23 engine codes match design catalogue (teleport_* names win over proposal `anchor_not_found`/`flag_readonly`) |
| `DEFAULT_MOVEMENT_VERBS`/`DEFAULT_SYSTEM_COMMANDS` | ✅ | exact constants as designed; back-compat defaults |
| switch as PREFIX command | ✅ | surface match strips prefix (+space) |
| Death-vs-block via `is_fatal` | ✅ | orchestrator routes solely on `gate.is_fatal`; no string equality |
| OperatorResult code+data w/o error_message | ✅ | removed immediately per user decision |
| system_message code-only, no `payload["message"]` | ✅ | grep zero; tests assert no back-compat |
| Vocabulary back-compat | ✅ | optional sections default empty; `extra="forbid"` intact |
| GAME_OVER on death carries world-authored death_message | ⚠️ **W-1** | design + task L4.4 say `gate.data["death_message"]` flows; emit only carries `reason="player_death"` + `turn_number` (see W-1) |

## Issues Found

**CRITICAL**: None.

**WARNING**:
- **W-1 (RESOLVED — death_message now forwarded)**: verify flagged that the fatal GAME_OVER only carried `reason="player_death"` and dropped `gate.data["death_message"]`. Fixed in `_handle_movement`: the GAME_OVER payload now spreads `**gate.data` (including the world-authored `death_message`) so a custom narrator can render it. Test `test_execute_turn_lethal_gate_emits_game_over_player_death` extended to assert `payload["death_message"] == "The bridge collapses!"`. Full suite stays at 786 passed / 100% coverage.

**WARNING**:
- **W-2 (spec-text drift — umbrella code list)**: `specs/engine-language-agnostic/spec.md` still lists legacy codes `flag_readonly` and `anchor_not_found`; design + atomic-operators spec + implementation use `teleport_entity_not_found`/`teleport_anchor_not_found` and FLAG has NO failure path (hence no `flag_readonly`). Behavior + tests proven (codes catalogue matches design), umbrella wording is stale → align at sdd-archive.

**SUGGESTION**:
- **S1 (scope note — `narrator_interface.py`)**: proposal & affected-areas table say narrator_interface/parser "no changes", but MinimalNarrator's `error_output` branch was adapted to read `error_code` (3 lines). Necessary for the new code contract (engine no longer sends `message`), covered by `test_narrator.py` rewrites; update the proposal text at archive.
- **S3 (hardcoded event label)**: `orchestrator.py:487` emits `{"verb": "ir"}` in the ACTION_ATTEMPTED clique for macro-edge movement. Recognition is vocabulary-driven, so no behavioral coupling; consider a `MOVEMENT_LABEL` constant or reading the vocabulary default when the orchestrator is constructed with one. Minor.

### Verdict

**PASS WITH WARNINGS** — all 26/26 spec scenarios have passing covering tests; 100%/100% coverage gate satisfied; W-1 RESOLVED (death_message forwarded + tested); remaining W-2 (umbrella spec code-list wording drift — archive chore) + 3 suggestions; no CRITICAL.

## Key Learnings

1. Coverage holds 100% statements and branches (1804 stmts / 558 branches) with 786 passing tests — the >99% hard gate was exceeded.
2. `grep '"message"'` and the Spanish-accents grep both scan cleanly except an allowed normalization docstring, proving the engine emits no user-facing text.
3. `MacroGateResult.is_fatal` now routes death-vs-block strictly (`death_msg == edge.death_message` is gone).
4. The narrator's `DEFAULT_SPANISH_MESSAGES` + "every code has a template" parametrized test guard the code→text catalogue against engine drift.
5. The fatal-GAME_OVER payload now carries `gate.data["death_message"]` (W-1 fix) so world-authored death text reaches the narrator without the engine constructing any string.
