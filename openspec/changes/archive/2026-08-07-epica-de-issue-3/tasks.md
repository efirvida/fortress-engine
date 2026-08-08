# Tasks: Epic #3 — Plugins (Parser, Narrator, Factory, Language)

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

| Unit | Slice | PR base → target | Focused test command | Lines |
|------|-------|------------------|----------------------|-------|
| 1 | N1: ABC language | feat/epica-de-issue-3-n1 → main | `pytest tests/test_plugins/test_parser.py tests/test_plugins/test_narrator.py --cov=src/fortress_engine/plugins --cov-branch -q` | ~80 |
| 2 | N2: Factory | feat/epica-de-issue-3-n2 → main | `pytest tests/test_plugins/test_factory.py tests/test_plugins/test_plugin_loading.py --cov=src/fortress_engine/plugins --cov-branch -q` | ~250 |
| 3 | N3: WorldYAML+voca | feat/epica-de-issue-3-n3 → main | `pytest tests/test_entities/test_world_yaml_language.py tests/test_entities/test_loader.py --cov=src/fortress_engine/entities --cov-branch -q` | ~250 |
| 4 | N4: ClassicParser | feat/epica-de-issue-3-n4 → main | `pytest tests/test_plugins/test_classic_parser.py --cov=src/fortress_engine/plugins --cov-branch -q` | ~400 |
| 5 | N5: Narrator+Int | feat/epica-de-issue-3-n5 → main | `pytest tests/test_plugins/ tests/test_integration/ --cov=src/fortress_engine --cov-branch -q` | ~350 |

### Suggested Work Units

| Unit | Goal | Runtime harness | Rollback boundary |
|------|------|-----------------|-------------------|
| 1 | ABC language property on both interfaces + stubs | `python -c "from fortress_engine.plugins.parser_interface import MinimalParser; assert MinimalParser().language=='es'"` | Revert parser_interface.py + narrator_interface.py |
| 2 | PluginConfig + factory + entry-point discovery | `python -c "from fortress_engine.plugins.factory import list_available_plugins; print(list_available_plugins('fortress_engine.parsers'))"` | Revert factory.py + __init__.py |
| 3 | WorldYAML + PluginConfigYAML + Vocabulary + loader | `python -c "from fortress_engine.entities.loader import EntityLoader; l=EntityLoader('tests/fixtures/minimal_world_with_lang'); c=l.load_world_config(); assert c['language']=='es'"` | Revert loader.py changes |
| 4 | ClassicParser — 37 constants + EXAMINAR + entity resolution | `python -c "from fortress_engine.plugins.classic_parser import ClassicParser; p=ClassicParser(); p.parse('ir norte',...)"` | Revert classic_parser.py + vocabulary fixture |
| 5 | TemplateNarrator 9 handlers + factory-wired orchestrator integration | `pytest tests/test_integration/ -v -k plugin` | Revert template_narrator.py + integration diffs |

> Chain strategy `pending` — orchestrator MUST ask stacked-to-main vs feature-branch-chain BEFORE sdd-apply.

---

## Phase N1: ABC Language Property (specs/plugin-contracts, TDD §4.13-4.14)

- [x] N1.1 RED `test_parser.py` + `test_narrator.py`: `language="es"` default, `language="en"` override, no-arg back-compat
- [x] N1.2 GREEN `parser_interface.py` + `narrator_interface.py`: ABC `__init__(language="es")`, abstract `language` property, update `MinimalParser` / `MinimalNarrator` to store `language`
- [x] N1.3 GATE: `pytest tests/test_plugins/test_parser.py tests/test_plugins/test_narrator.py --cov=src/fortress_engine/plugins --cov-branch --cov-report=term-missing -q` >99%; commit N1

## Phase N2: Plugin Factory (specs/plugin-factory, TDD §9.2-9.3)

- [x] N2.1 RED `test_factory.py`: `PluginConfig` frozen, `create_parser`/`create_narrator` inject language+options, missing plugin → `PluginNotFoundError` with names, language mismatch → `warnings.warn`, `TypeError` fallback on unknown kwargs
- [x] N2.2 RED `test_plugin_loading.py`: entry points `classic` + `template` discoverable and loadable
- [x] N2.3 GREEN `plugins/factory.py`: `PluginConfig` frozen dataclass, `_resolve_entry_point`, `_instantiate` with TypeError fallback, `create_parser`/`create_narrator`/`list_available_plugins`, `PluginNotFoundError`
- [x] N2.4 GREEN `plugins/__init__.py`: export `PluginConfig`, `create_parser`, `create_narrator`, `list_available_plugins`, `PluginNotFoundError`
- [x] N2.5 GATE: `pytest tests/test_plugins/test_factory.py tests/test_plugins/test_plugin_loading.py --cov=src/fortress_engine/plugins --cov-branch -q` >99%; commit N2

## Phase N3: WorldYAML + Vocabulary (specs/world-yaml-extensions, TDD §9.2)

- [x] N3.1 ADD `tests/fixtures/minimal_world_with_lang/` + `shared/vocabulary.yaml`; RED `test_world_yaml_language.py`: WorldYAML `language`/`parser`/`narrator` keys, string→PluginConfigYAML coercion, missing defaults, invalid rejection, `extra="forbid"` on vocabulary
- [x] N3.2 RED continued: `Vocabulary` dataclass round-trip (verbs/synonyms/stopwords/prepositions/speech_markers/language), `load_vocabulary(world_path)` → `Vocabulary` or None
- [x] N3.3 GREEN `entities/loader.py`: `PluginConfigYAML(plugin, options={})`, `VocabularyYAML`, `WorldYAML` +3 fields with Pydantic validator, `Vocabulary` dataclass, `EntityLoader.load_vocabulary(world_path)`
- [x] N3.4 GATE: `pytest tests/test_entities/test_world_yaml_language.py tests/test_entities/test_loader.py --cov=src/fortress_engine/entities --cov-branch -q` >99%; commit N3

## Phase N4: ClassicParser V1 (specs/parser-classic-v1, TDD §4.15)

- [x] N4.1 ADD `tests/fixtures/vocabulary/full_vocabulary.yaml`: 37 Fortaleza constants per spec table + `EXAMINAR`, V2 stopwords, prepositions, speech markers/verbs
- [x] N4.2 RED `test_classic_parser.py`: 37-constant verb→canonical mapping + `EXAMINAR`→`examinar`; unknown verb non-throw; normalization NFKD+Mn; 9 V2 stopwords stripped; CON→instrument, A→context; DICIENDO/RESPONDIENDO→text preserving stopwords; DECIR/RESPONDER→text
- [x] N4.3 RED continued: entity resolution — exact wins, partial (all words in name, shortest-wins), 4-entity Puerta principal/secreta/Llave/Espada fixture; scope: anchor+inventory; vocabulary load cascade (override → file → DEFAULT_SPANISH_VOCABULARY)
- [x] N4.4 GREEN `plugins/classic_parser.py`: `ClassicParser(ParserInterface)`, `__init__(language="es", vocabulary=None)`, 37+1 verb lookup + `DEFAULT_SPANISH_VOCABULARY`, `parse()` per algorithm (normalize→tokenize→strip→verb→speech→prepositions→resolve→ParsedCommand), helpers `_tokenize`, `_extract_speech`, `_route_prepositions`, `_resolve_entity`
- [x] N4.5 GREEN `plugins/__init__.py`: export `ClassicParser`
- [x] N4.6 GATE: `pytest tests/test_plugins/test_classic_parser.py --cov=src/fortress_engine/plugins --cov-branch -q` >99%; `pytest --cov=src/fortress_engine --cov-branch -q` >99% total; commit N4

## Phase N5: TemplateNarrator V1 + Integration (specs/narrator-template-v1, TDD §4.16)

- [x] N5.1 RED `test_template_narrator.py`: 9 event handlers (`entity_entered`, `action_output`, `error_output`, `episode_completed`, `game_over`, `system_message`, `entity_described`, `item_examined`, `inventory_listed`) → non-empty text; `entity_transferred` → None; `initialize` idempotent; payload/world/fallback precedence; language default/override
- [x] N5.2 GREEN `plugins/template_narrator.py`: `TemplateNarrator(NarratorInterface)`, `__init__(language="es", templates=None)`, `_templates` 9-key dict, `initialize(event_bus)` single-subscribe, `handle_event` dispatch → 9 handlers with fallback strings
- [x] N5.3 GREEN `plugins/__init__.py`: export `TemplateNarrator`
- [x] N5.4 RED `test_plugin_integration.py` extend: factory-built ClassicParser + TemplateNarrator orchestrator turn (`"coger rusty_key"`, `"ir norte"`, `"xyzzy"`), canonical event sequence + non-None narration
- [x] N5.5 GATE: `pytest tests/test_plugins/ tests/test_integration/ --cov=src/fortress_engine --cov-branch -q` >99%; grep `importlib.metadata` under `src/` → exactly 1 hit (`factory.py`); commit N5
