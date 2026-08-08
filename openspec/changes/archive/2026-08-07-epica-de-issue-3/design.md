# Design: Epic #3 — Plugins

## Technical Approach

The engine depends only on the ABCs. A function-only factory calls entry points; loading normalizes configuration/vocabulary and injects instances into the unchanged orchestrator.

```text
world.yaml + shared/vocabulary.yaml
        → EntityLoader (Pydantic → dataclasses)
        → PluginConfig → factory → entry point → plugin instance
        → TurnOrchestrator(parser, narrator)
        → parse → graph/execute → EventBus → narrator.handle_event
```

## Architecture Decisions

| Decision | Choice and rationale |
|---|---|
| Discovery | `factory.py` alone calls entry points; discovery is isolated and mockable. |
| Construction | Frozen config; `_instantiate` passes language/options, then retries without unsupported kwargs and warns for legacy plugins. |
| Language | ABCs expose `language`, default `"es"`; mismatches warn, never raise. |
| Vocabulary | Loader reads `world/shared/vocabulary.yaml`; bootstrap injects it. Precedence: override → world file → default constant. |
| Narration | Returns designer payload/world text, never generated prose. |

## Module Design

**Interfaces.** Add `__init__(language="es")` storage and abstract read-only `language` to both ABCs. Minimal implementations call `super()` and retain all current behavior.

**`classic_parser.py`.** `ClassicParser(language="es", vocabulary: Vocabulary | dict | None = None)` builds verb lookup, stopwords, routing prepositions, speech markers, and speech verbs. Canonical inventory:

| Canonical | Synonyms/standalone |
|---|---|
| `ir` | ATRAVESAR, IR, CRUZAR, PASAR |
| `tomar` | TOMAR, COGER |
| `dejar` | SOLTAR, DEJAR |
| `abrir` | ABRIR |
| `matar` | MATAR, ASESINAR |
| `mirar` | OBSERVAR, MIRAR |
| `examinar` | LEER, VER, EXAMINAR |
| `romper` | ROMPER, FORZAR, DESTROZAR |
| `interrogar` | PREGUNTAR, INTERROGAR |
| `inventario` | INVENTARIO |
| `dar` | REGALAR, DAR |
| `con`, `a` | CON, A |
| `terminar` | ABANDONAR, TERMINAR |
| `respondiendo`, `diciendo` | RESPONDIENDO, DICIENDO |
| `ejecutar`, `salvar`, `porciento`, `todo`, `pesar`, `orinar`, `cls`, `esperar` | EJECUTAR, SALVAR, PORCIENTO, TODO, PESAR, MIAR, ORINAR, CLS, ESPERAR |

Helpers are `_normalize`, `_tokenize`, `_strip_stopwords`, `_route_prepositions`, `_extract_speech`, `_resolve_entity`. Parse output always has `subject=active_protagonist_id`, canonical/unknown `verb`, resolved-or-raw `target`, `context`, `instrument`, and normalized spoken `text`.

Resolution: normalize → tokenize → remove stopwords for command/entity phrases → lookup verb → extract speech (speech text is not filtered) → route `CON` to instrument and `A` to context → search current anchor plus inventory. Exact name wins; otherwise every input token must occur in the entity name and shortest wins. Equal-length candidates return the raw phrase unresolved. Unknown verbs never throw.

**`template_narrator.py`.** Dispatch exactly nine events: `entity_entered`, `action_output`, `error_output`, `episode_completed`, `game_over`, `system_message`, `entity_described`, `entity_examined`, `inventory_listed`. Use payload keys, world-state descriptions, then deterministic fallbacks. Defaults: `entity_entered="Entras en {entity_name}."`, `game_over="Fin del juego."`, `inventory_listed="Tienes: {items}."`; other handlers use payload text or named fallbacks. `initialize` subscribes once.

Default dict contains nine keys; payload text wins, with entered, game-over, and inventory fallbacks.

**`factory.py`.** Define `PluginNotFoundError`, frozen `PluginConfig(name, options={})`, `_resolve_entry_point(group,name)`, `_instantiate`, `create_parser`, `create_narrator`, and `list_available_plugins`. Missing names include available names in the exception. After construction, warn if non-empty plugin language differs from world language.

**`loader.py`.** Add `WorldYAML.language`, parser/narrator fields; coerce strings to `{plugin, options={}}`; validate vocabulary sections and convert to runtime `Vocabulary`. Read `worlds/<name>/shared/vocabulary.yaml`; missing file uses the default cascade.

Example:

```yaml
language: es
verbs: {IR: [ATRAVESAR, CRUZAR], TOMAR: [COGER]}
stopwords: [el, la, los, las, un, una, al, del, por]
prepositions: {instrument: [con], recipient: [a]}
speech_markers: [diciendo, respondiendo]
speech_verbs: [decir, responder]
```

## File Changes

| File | Action |
|---|---|
| `plugins/parser_interface.py`, `narrator_interface.py` | Modify ABC language contract and minimal stubs |
| `plugins/factory.py`, `classic_parser.py`, `template_narrator.py` | Create factory and production plugins |
| `plugins/__init__.py` | Export public plugin symbols |
| `entities/loader.py` | Add YAML plugin/vocabulary models and loader |
| `tests/test_plugins/*`, `tests/test_entities/*` | Add unit and integration coverage |

## Testing Strategy

| Module | Matrix |
|---|---|
| ABCs/minimal | default/override language and unchanged parsing/narration |
| Factory/loading | entry-point discovery, options/language injection, legacy fallback, missing plugin, mismatch warning, YAML string/object/default/rejection, vocabulary file/missing fallback |
| Classic parser | all 37 constants and canonical mappings, normalization, nine stopwords, routing, speech, exact/partial/shortest/ambiguous/no-match, inventory/anchor scope, unknown verb |
| Template narrator | nine handlers, payload/world/fallback precedence, unrelated `None`, idempotent subscription |
| Integration | factory-built ClassicParser + TemplateNarrator through one orchestrator turn; exact event sequence and non-`None` narration |

Every branch (`TypeError`, missing files, absent keys, `KeyError`, ambiguity, parser exception) gets a strict test. Run branch coverage after each slice; total must remain >99%.

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, executable classification, or process-integration boundary.

## Migration / Rollout

No migration. Preserve five slices: N1 ABC language, N2 factory, N3 YAML/vocabulary, N4 ClassicParser (N1/N3), N5 TemplateNarrator/integration (N1/N2/N3). Each remains revertible and under 400 lines.

## Open Questions

None. No proposal/spec decision is changed; the only implementation clarification is that world vocabulary is injected by the world-loading bootstrap because the mandated `ClassicParser` constructor has no world-path parameter.
