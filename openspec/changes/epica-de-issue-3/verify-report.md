```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:c121e0f1d965fed59637bd8b71bffd567272a8b7ea9528519d7154e1bcf476bf
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 17/17
test_command: pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q
test_exit_code: 0
test_output_hash: sha256:c121e0f1d965fed59637bd8b71bffd567272a8b7ea9538519d7154e1bcf476bf
build_command: pip install -e .
build_exit_code: 0
build_output_hash: sha256:6bbcfda86af8314a24f294adbdfea91218f0a48c4c609d4b3ba5d34cacd728fd
```

# Verification Report: epica-de-issue-3 (Plugins — Parser, Narrator, Factory, Language)

**Change**: epica-de-issue-3
**Version**: N/A (working-tree candidate; 5 apply slices N1–N5 complete, uncommitted)
**Mode**: Standard (AGENTS.md hard gate: >99% statements AND branches)

Independent requirements/runtime verification by the `sdd-verify` executor. No fixes made; findings reported only. No commits or PRs created.

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 20 (N1.1–N1.3, N2.1–N2.5, N3.1–N3.4, N4.1–N4.6, N5.1–N5.5) |
| Tasks complete | 20 |
| Tasks incomplete | 0 |

All tasks in `tasks.md` are marked `[x]`. Full-spec verification (proposal + 5 delta specs + design + tasks).

## Build & Tests Execution

**Build (import harness)**: PASSED — `python3 -c "from fortress_engine.plugins import PluginConfig, create_parser, create_narrator, ClassicParser, TemplateNarrator"` exit 0.

**Tests**: 696 passed / 0 failed / 0 skipped (exit 0)

```
696 passed, 317 warnings in 11.55s
```

**Coverage**: 100% statements / 100% branches — TOTAL 1725 stmts, 0 misses, 526 branches, 0 partials. Hard gate (>99%) PASSED.

```
Name                                                   Stmts   Miss Branch BrPart  Cover   Missing
src/fortress_engine/engine/orchestrator.py               207      0     80      0   100%
src/fortress_engine/entities/loader.py                   266      0     62      0   100%
src/fortress_engine/plugins/classic_parser.py            116      0     42      0   100%
src/fortress_engine/plugins/factory.py                    49      0      8      0   100%
src/fortress_engine/plugins/narrator_interface.py         43      0     12      0   100%
src/fortress_engine/plugins/parser_interface.py           49      0      8      0   100%
src/fortress_engine/plugins/template_narrator.py          79      0     26      0   100%
TOTAL                                                   1725      0    526      0   100%
```

## Evidence Table

| # | Check | Command | Exact result |
|---|-------|---------|--------------|
| 1 | Coverage gate (>99%) | `pytest --cov=src --cov-branch -q` | TOTAL 1725 stmts / 526 branches, 0 missed → **100%** ✔ |
| 2 | Full suite green | same run | **696 passed, 0 failed, 0 skipped**, exit 0 ✔ |
| 3 | Entry points present | `md.entry_points(group=...)` | parsers: `['classic']`; narrators: `['template']` ✔ |
| 4 | Factory injects language | `create_parser(PluginConfig('classic'),'es')` | `.language == 'es'`, ClassicParser; `'en'` → `'en'`; narrator same ✔ |
| 5 | WorldYAML keys+types | `EntityLoader(...).load_world_config()` | object form → `{'es', {'plugin':'classic','options':{}}, {'plugin':'template','options':{}}}`; legacy `parser: "classic"` coerced to same dict ✔ |
| 6 | 37-verb test table | count of `VERB_MAPPINGS` params | **38 parametrized entries** = 37 spec constants + EXAMINAR; all assert `verb == expected` + `subject == 'hero'` ✔ |
| 7 | Stopword V2 (9) | parametrized STOPWORDS | 9 params (`el la los las un una al del por`) all stripped ✔ |
| 8 | Entity resolution 4-entity | runtime + tests | exact → id; `mirar puerta` → raw phrase (2-word tie, ambiguous); `principal` → `puerta_principal` (shortest wins); `espada` in inventory → `espada`; no-match → raw ✔ |
| 9 | Speech test | `parse("abrir puerta diciendo abrete sesamo")` | `verb='abrir' target='puerta' text='abrete sesamo'` (stopwords NOT stripped in text) ✔ |
| 10 | Preposition test | `dar llave a bruja` / `matar troll con espada` | `target='llave' context='bruja'` / `target='troll' instrument='espada'` ✔ |
| 11 | TemplateNarrator 9 events | direct `handle_event` | all 9 return non-None strings (escritas above); `entity_transferred` → **None**; idempotent `initialize` ✔ |
| 12 | Back-compat | `MinimalParser()`/`MinimalNarrator()` | parse `ir norte` → verb `ir`; narrator `language == 'es'`; `test_plugin_integration.py` passes ✔ (also the `esperar` interception test passes) |
| 13 | Arch #7: only factory imports importlib.metadata | `grep -rn "importlib.metadata" src/` | Hits only in `plugins/factory.py` (lines 4,17,62,65,176) ✔ |
| 14 | No entity-type strings in plugins | `grep -rE '"(room\|item\|npc\|player\|portal)"' src/plugins/` | **zero hits** (exit 1) ✔ |
| 15 | esperar absent | `grep -ri "esperar" src/` | **zero hits in plugin modules + tests guard**; 2 hits in `engine/orchestrator.py` (pre-existing EPS pseudocode system-command table, part of `esp` extension) ✔ |
| 16 | Requirement traceability | see matrix below | 10/10 requirements, 17/17 scenarios covered by passing tests ✔ |

## Requirements Coverage (per delta spec)

### plugin-contracts (MODIFIED) — 2 reqs, 5 scenarios → all COMPLIANT
- **Stable ABCs**: `ParserInterface.parse` + abstract `language`; `NarratorInterface.initialize/handle_event` + abstract `language`; `__init__(language="es")`. Tests: `test_parser_abc_has_language_abstract`, `test_narrator_abc_has_language_abstract`, `test_parser_language_default_es/override_en`, `test_narrator_...`, `test_parser_no_arg_backcompat`.
  - Scenario Custom parser substitution: `test_plugin_integration.py::test_full_turn_...` / `test_factory_orchestrator_integration_turn_structure` (orchestrator uses injected parser, no concrete import) ✔ COMPLIANT
  - Scenario Language default and override: covered above ✔ COMPLIANT
- **Backward-compatible minimal stubs**: `MinimalParser` keeps no-arg construction, `parse("ir norte")`/`parse("examinar puerta")`; `MinimalNarrator` remains no-op minimal.
  - Scenario Supported parser inputs: `test_parse_ir_norte`, `test_parse_examinar_target` ✔
  - Scenario Unknown input graceful: `test_parse_unknown_no_exception` ("xyzzy") ✔
  - Scenario No-arg construction + override: `test_parser_no_arg_backcompat`, `test_narrator_no_arg_backcompat` ✔

### parser-classic-v1 (2 reqs, 3 scenarios) → all COMPLIANT
- **Fortaleza vocabulary/parsing**: 37-constant inventory + EXAMINAR; NFKD+Mn normalization; V2 stopwords; `ParsedCommand` subject=active-protagonist; unknown verb non-throwing; scope anchor→inventory; exact>partial>shortest; equal candidates → raw phrase; CON→instrument; A→context; DICIENDO/RESPONDIENDO/DECIR/RESPONDER→text.
  - Scenario Normalize and resolve: `test_normalize_*`, `test_speech_text_normalized` (`abrir la puerta diciendo ábrete ñandú` → normalized) ✔ COMPLIANT
  - Scenario Partial matching and ambiguity: `test_entity_exact_match`, `test_entity_partial_unique_match`, `test_entity_partial_single_word` (raw when tied) ✔ COMPLIANT
- **Vocabulary load cascade**: constructor override > world file > `DEFAULT_SPANISH_VOCABULARY`.
  - Scenario Missing vocabulary file: `test_default_spanish_vocabulary` + `test_load_vocabulary_missing_file_returns_none` (loader returns None → parser default cascade) ✔ COMPLIANT

### narrator-template-v1 (2 reqs, 3 scenarios) → COMPLIANT with WARNING (event naming)
- **World-data narration**: 9 event handlers, unrelated → None; payload/world/fallback precedence.
  - Scenario Narrate the nine supported events: 9 handler tests all assert non-empty strings ✔ **COMPLIANT** — note: code names the 9th event `entity_examined` (match to engine taxonomy `ENTITY_EXAMINED`), delta spec/design named it `item_examined`; test `test_handle_item_examined` covers engine's true broadcast event. Spec wording lingering inconsistency.
  - Scenario Ignore unrelated: `test_handle_entity_transferred_returns_none`, `test_handle_unknown_event_returns_none` ✔ COMPLIANT
- **Idempotent subscription**: exactly 9 subscriptions, repeatable.
  - Scenario Initialize twice: `test_initialize_subscribes_to_nine_events`, `test_initialize_idempotent` ✔ COMPLIANT

### plugin-factory (2 reqs, 3 scenarios) → all COMPLIANT
- **Resolve + instantiate**: frozen `PluginConfig`; `create_parser/narrator`; `list_available_plugins`; `_resolve_entry_point` via `importlib.metadata`; `PluginNotFoundError` w/ available names.
  - Scenario inject language + options: `test_create_parser_injects_language`, `test_create_parser_passes_options`, narrator equivalents ✔ COMPLIANT
  - Scenario missing plugin: `test_create_parser_missing_plugin_raises_with_available_names` ✔ COMPLIANT
- **Best-effort compat/warnings**: TypeError fallback retries with warnings; mismatch `warnings.warn`; V1 no raise; `strict_language` deferred.
  - Scenario legacy/mismatch: `test_instantiate_typeerror_from_legacy_fallback`, `test_create_parser_language_mismatch_warns`, `test_create_parser_no_warning_...` ✔ COMPLIANT

### world-yaml-extensions (2 reqs, 3 scenarios) → all COMPLIANT
- **WorldYAML language/parser/narrator + coercion**: `language="es"` default; string→`PluginConfigYAML`; invalid values rejected.
  - Scenario parse both forms: `test_parser_bare_string_coerced`, `test_parser_dict_form_passes_through_validator`, `test_invalid_plugin_type_rejected` ✔ COMPLIANT
- **Vocabulary dataclass + loader**: 5 sections + language; `load_vocabulary(world_path)` reads `shared/vocabulary.yaml`; missing → None.
  - Scenario load data: `test_load_vocabulary_happy_path` ✔ COMPLIANT
  - Scenario default language: `test_defaults_when_missing` / `test_minimal_world_yaml_still_valid` ✔ COMPLIANT

**Compliance summary (actual specs)**: 10 requirements · 17 scenarios
| Result | Count |
|---|---|
| ✅ COMPLIANT | 16 |
| ⚠️ PARTIAL / naming drift | 1 (narrator "item_examined" name factor — behavior proven) |
| ❌ FAILING / UNTESTED | 0 |

## Correctness (Static Evidence)

| Implementation | Status | Notes |
|---|---|---|
| `parser_interface.py` language property + `MinimalParser` | ✅ | abstract property enforced; default "es" |
| `narrator_interface.py` language + `MinimalNarrator` | ✅ | idempotent init, None-return paths |
| `classic_parser.py` (37+1 verbs, routing, speech, entity resolution) | ✅ | matches design algorithm 1–7; no entity-type branching |
| `template_narrator.py` (9 handlers, dispatch, fallbacks, idempotent) | ✅ | dispatch dict built after class; non-spec event → None |
| `factory.py` (PluginConfig, create_*, _resolve, _instantiate, warnings) | ✅ | only module importing `importlib.metadata` |
| `loader.py` (WorldYAML +3, PluginConfigYAML, VocabularyYAML, Vocabulary, load_vocabulary) | ✅ | Pydantic only at load; runtime dataclasses |
| `pyproject.toml` entry points | ✅ | `parsers/classic`, `narrators/template` already declared, now point to real modules |

## Type / Design Coherence

| Design decision | Followed? | Notes |
|---|---|---|
| Only factory sees entry points | ✅ Yes | grep evidence #13 |
| Frozen PluginConfig + best-effort kwargs | ✅ Yes | `dataclass(frozen=True)`; TypeError fallback |
| ABC `language` default "es", mismatch warns | ✅ Yes | `warnings.warn`; real plugins accept injected language, so no unexpected mismatch |
| Vocabulary override → world file → default | ✅ Yes | `ClassicParser(vocabulary=None)` default constant; `load_vocabulary` None → cascade |
| Narration = payload/world text, never prose | ✅ Yes | handlers format payload keys; deterministic Spanish fallbacks |
| Integration: factory-built installer through turn | ⚠️ Partial | `ir norte` + `xyzzy` proven through factory-built orchestrator; `cocker` path only tested with `MinimalParser` (factory+clique verb mismatch) — see WARNING W-3 |
| Event naming (spec `item_examined` vs engine `entity_examined`) | ⚠️ Deviation | code/engine taxonomy authoritative; spec text stale |

## Issues Found

**CRITICAL**: None.

**WARNING**:
- **W1 (proposal/design drift — integration criteria)**: Proposal success criteria require executing `"coger rusty_key"` through the factory-built orchestrator (ClassicParser + TemplateNarrator) and asserting `action_output` narration. The implemented tests only run `"ir norte"` and `"xyzzy"` through that factory path; the `coger` run uses `MinimalParser` (whose bare verb `coger` matches the fixture clique). Running `"coger rusty_key"` through the factory + current minimal world fixture yields `error_output` (inventory unchanged) because `ClassicParser` canonicalizes `coger` → `tomar` (per its spec table) while the fixture hyper-edge clique declares verb `coger`. Behavior proven: when the clique verb is the GDD-canonical `tomar`, the full sequence `turn_started → input_received → action_attempted → entity_transferred → action_output → action_resolved → turn_ended` fires and narration = `Tomas la llave.`. Root cause is fixture/verb, not engine bug; the fixture (and the proposal text) should use canonical verbs as GDD requires.
- **W2 (spec/design naming): `TemplateNarrator` 9th event is implemented as `entity_examined` (the engine's actual broadcast event constant in `events/event_types.py`, matching `_NARRATED_EVENTS` of `MinimalNarrator`) while delta spec + design + task N5.1 say `item_examined`. The TDD docstring also says `item_examined`. Behavior AND test coverage exist (test named "test_handle_item_examined" feeding `ENTITY_EXAMINED`), so this is a docs/spec wording drift, not behavior.** Recommend aligning the spec wording at sdd-archive.

**SUGGESTION**:
- S1: Proposal Success Criteria bullet ’`ir puerta` → target=None (ambig.)’ and ’`ir p` → `puerta_principal`’ describe prefix-style matching; implemented (per spec: whole-word subset matching; equal-length → raw phrase, no char-prefix) returns `puerta` raw / `p` raw. Spec/design were the authority — reconcile proposal bullet wording in archive.
- S2: 317 warnings are mostly intentional `RuntimeWarning` fallback-mismatch tests (proven below); ~3 `DeprecationWarning` come from `sqltheme`/`utcnow` on Python 3.14 in the **pre-existing persistence test suite** (epica-2), not this epic. `-W error::DeprecationWarning` fails 28 persistence tests — environment-level, pre-existing, outside scope.
- S3: the apply slices for N1–N5 are uncommitted (`git status`: loader/plug interfaces modified, new plugin modules untracked); slice commits are still expected per tasks before the PR chain.

### Verdict

**PASS WITH WARNINGS** — all specifications scenarios have passing covering tests; 100%/100% coverage gate satisfied; 2 WARNING-level deviations (integration fixture verb canonicalization, narrator event-name drift) and 3 suggestions; no CRITICAL.

## Key Learnings

1. The 99% branch-coverage hard gate passed at 100% statements and 100% branches across 1725 lines.
2. ClassicParser canonicalizes verbs, so world edge cliques must use canonical verbs like `tomar` even when the player types `coger`.
3. Engine event taxonomy uses `entity_examined`, not the spec's `item_examined`, creating a wording drift between specs and implementation.
4. Factories resolve plugins via `importlib.metadata` in exactly one module, preserving the plugin discovery architecture constant.
5. Python 3.14 triggers SQLAlchemy `utcnow()` deprecation warnings in pre-existing persistence tests.