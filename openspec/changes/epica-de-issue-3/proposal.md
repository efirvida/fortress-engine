# Proposal: epica-de-issue-3 (Plugins — Parser, Narrator, Factory, Language)

## Intent

Epic #3 closes the plugin gap left by the engine-core epic. `ParserInterface` /
`NarratorInterface` ABCs exist with `MinimalParser` / `MinimalNarrator` stubs
(issues #23 and #24 — already in `src/fortress_engine/plugins/`), but the
**actual** Classic Parser V1 (#21) and Template Narrator V1 (#25) modules do
NOT exist yet, and `pyproject.toml` entry points
(`fortress_engine.parsers/classic`, `fortress_engine.narrators/template`) point
to non-existent modules — a broken link in the plugin contract.

This change delivers the production-grade plugins plus a **plugin factory**
that resolves entry points, injects the world language, and wires both plugins
to the orchestrator via the world declaration. The factory + language
architecture is the user's new requirement (decided in this session, recorded
in Engram `sdd/epica-de-issue-3/architecture`): **the parser must know its
language, and that language must be declared in the game definition**.
Multi-language is NOT in scope for V1, but the seam MUST be designed now so
adding a new language later is an entry-point drop-in, not an engine redesign.

Closes GitHub issue **#3** (parent epic) via sub-issues **#21** (Classic
Parser V1), **#23** (NarratorInterface ABC — already implemented, gains the
`language` property here), **#24** (ParserInterface ABC — same), **#25**
(Template Narrator V1). Dependencies: engine-core (DONE), persistence
(DONE — supplies `WorldStateRepository`/`EventSourcingSaveSystem` for the
load/load_parser test path, though this proposal does not change them).

## Scope

### In Scope

- `src/fortress_engine/plugins/classic_parser.py` — `ClassicParser` implementing
  `ParserInterface`. 37 verbs (canonical Fortaleza set, see "Open Decisions
  #1"), partial matching of entity names against current anchor + inventory,
  tilde/enye/dieresis normalization (NFKD + Mn strip), stopword filtering,
  preposition routing (`CON` → `instrument`, `A` → `context`),
  speech-marker routing (`DICIENDO`/`RESPONDIENDO` → `text`; `DECIR`/
  `RESPONDER` as standalone verbs also fill `text`). Loads vocabulary from
  `shared/vocabulary.yaml` by default; constructor accepts an override.
- `src/fortress_engine/plugins/template_narrator.py` — `TemplateNarrator`
  implementing `NarratorInterface`. Text comes directly from world data
  (HyperEdge `output`, room `components.description`, payload fields). Nine
  event handlers per TDD §4.16: `entity_entered`, `action_output`,
  `error_output`, `episode_completed`, `game_over`, `system_message`,
  `entity_described`, `entity_examined`, `inventory_listed`. Optional
  `templates` dict for system messages (default = in-code English/Fallback
  templates — V1 uses Spanish defaults because the world is Spanish; the
  `language` property lets V2 worlds override).
- `src/fortress_engine/plugins/factory.py` — two functions:
  - `create_parser(plugin_config: PluginConfig, world_language: str) -> ParserInterface`
  - `create_narrator(plugin_config: PluginConfig, world_language: str) -> NarratorInterface`
  Resolution: `importlib.metadata.entry_points(group=...)` (arch constant #7
  preserved), then `ep.load()(language=world_language, **plugin_config.options)`.
  If the loaded class' `__init__` does not accept `language`, factory falls
  back to default-construction and logs a warning. (Strict per-plugin
  `language` validation is deferred to V1.1 — see Open Decisions #3.)
- `src/fortress_engine/plugins/parser_interface.py` — `ParserInterface` ABC
  gains `language: str` abstract property and `__init__(self, language: str = "es")`.
  `MinimalParser` updated to accept and store `language` (default `"es"` for
  backwards compat with existing tests).
- `src/fortress_engine/plugins/narrator_interface.py` — same treatment for
  `NarratorInterface` and `MinimalNarrator`.
- `src/fortress_engine/entities/loader.py` — `WorldYAML` Pydantic model gains
  `language: str = "es"`, `parser: str | PluginConfigYAML = PluginConfigYAML()`,
  `narrator: str | PluginConfigYAML = PluginConfigYAML()`. Pydantic coercion
  accepts both the legacy `parser: "classic"` string (TDD §9.2 form) AND the
  new `parser: {plugin: "classic"}` object (architecture decision form). The
  dict form opens the door to per-plugin options later (e.g.
  `parser: {plugin: "classic", options: {stopword_set: "v2"}}`) without
  schema changes.
- `src/fortress_engine/entities/loader.py` — `EntityLoader.load_shared_entities`
  (or a new `load_vocabulary`) loads `shared/vocabulary.yaml` into a
  `Vocabulary` dataclass: verbs → list of synonyms, stopwords (set),
  prepositions, speech markers. Used by `ClassicParser` when no override is
  injected.
- `src/fortress_engine/plugins/factory.py` — internal helpers
  `_resolve_entry_point(group, name)` (private, returns the class) and
  `list_available_plugins(group)` (for diagnostics / `--list-plugins`).
  These replace TDD §9.2's top-level `load_parser` / `load_narrator`
  functions — see "Open Decisions" for the rationale and the deviation note.
- `src/fortress_engine/plugins/__init__.py` — module-level exports for the
  new public symbols (`PluginConfig`, `create_parser`, `create_narrator`,
  `ClassicParser`, `TemplateNarrator`).
- Tests (mirroring `src/fortress_engine/plugins/` in `tests/test_plugins/`):
  - `test_classic_parser.py` — verb set, normalization, stopword stripping,
    preposition routing (CON→instrument, A→context), speech-marker routing,
    entity name resolution (exact + partial match, multi-word, no-match,
    ambiguity resolution), subject=active_protagonist_id, language default.
  - `test_template_narrator.py` — all 9 event handlers, payload-key fallbacks,
    `None` for non-narrated event types, idempotent `initialize`.
  - `test_factory.py` — `create_parser`/`create_narrator` resolve via entry
    points, `language` is injected, missing plugin raises `PluginNotFoundError`,
    unknown `language` value passes through (no engine validation yet), legacy
    `parser: "classic"` string form still works (back-compat).
  - `test_plugin_loading.py` — entry-point discovery from the installed
    `fortress-engine` distribution, asserts `classic` and `template` are
    present and instantiate cleanly.
  - `test_world_yaml_language.py` (new in `tests/test_entities/`) — WorldYAML
    parses `language`, `parser: {plugin: ...}`, `narrator: {plugin: ...}`,
    legacy string form, missing fields default sensibly, invalid `plugin`
    value rejected at load time.
  - `test_parser.py` and `test_narrator.py` — extended to verify the
    `language` property default + override.
  - Integration: extend `test_plugin_integration.py` with a scenario that
    builds the orchestrator via the factory and runs a turn cycle end-to-end
    with `ClassicParser` + `TemplateNarrator`.

### Out of Scope (deferred)

- **V2 expanded parser** (PRD §5) — different stopword set / partial match
  refinements. Open Decisions #2 picks V2 in V1 to skip this branch.
- **V3 AI parser / V2 immersive narrator** (PRD §5-6) — requires a
  different runtime (LLM client), separate epic.
- **Multiple language switching inside one play session** — `language` is a
  per-world constant, not a per-turn state. Mid-session `CAMBIAR IDIOMA` is
  a v1.1 candidate.
- **Fortaleza world data** (`worlds/fortaleza/**`) — separate epic (TDD
  §12, roadmap #18). The 88 rooms / 450+ HyperEdges need a focused effort
  and a design pass for the Fortaleza-specific QA choices.
- **CLI changes** — `fortress-engine run/validate/test` is TDD §10.2 and
  lives in `src/fortress_engine/cli/`. The factory is the API the CLI will
  call; the CLI itself is owned by a later epic (or by the world-loading
  epic when the first world is wired in).
- **Engine-core changes beyond `WorldYAML` and `loader.py`** — the
  orchestrator already accepts a `ParserInterface` and `NarratorInterface`
  via constructor injection. No orchestrator changes are needed.

## Capabilities

### New

| Capability | Covers |
|------------|--------|
| `parser-classic-v1` | `ClassicParser` plugin — 37-verb Spanish parser, partial entity-name matching, tilde normalization, stopword filtering, preposition routing, speech-marker routing. Loads vocabulary from `shared/vocabulary.yaml`. |
| `narrator-template-v1` | `TemplateNarrator` plugin — 9 event handlers, text from world data (HyperEdge `output`, room `description`, payload fields). Default Spanish templates, swappable via constructor. |
| `plugin-factory` | `create_parser` / `create_narrator` functions; entry-point resolution via `importlib.metadata`; `language` injection; `PluginConfig` dataclass accepting both legacy string and new object form. |
| `vocabulary-loader` | `Vocabulary` dataclass + loader for `shared/vocabulary.yaml` (verbs + synonyms, stopwords, prepositions, speech markers). |
| `world-yaml-extensions` | `WorldYAML` Pydantic model gains `language`, `parser`, `narrator` keys. Both legacy string and new object form supported. |

### Modified

| Capability | Change |
|------------|--------|
| `plugin-contracts` | `ParserInterface` / `NarratorInterface` gain a `language: str` abstract property and a constructor parameter. `MinimalParser` / `MinimalNarrator` updated to accept and store `language` (default `"es"` for back-compat with existing tests). |

## Approach

**Plugin factory + language injection** (user decision — Engram
`sdd/epica-de-issue-3/architecture`). The factory is the only piece of code in
the engine that calls `importlib.metadata.entry_points` for plugins; the rest
of the engine talks to `ParserInterface` / `NarratorInterface` interfaces.
This preserves arch constant #7 (entry-point discovery) AND adds the
language-awareness layer without polluting the engine or the plugins.

**World declaration shape** (GDD §3 / TDD §9.2 + user decision):
```yaml
# worlds/<name>/world.yaml
world_id: "mi-aventura"
name: "Mi Aventura"
language: "es"                          # NEW — default "es" if absent
parser:
  plugin: "classic"                     # NEW form (TDD §9.2 used bare string)
  options: {}                           # optional per-plugin options
narrator:
  plugin: "template"
  options: {}
```

**File layout** (TDD §2 confirmed):
```
src/fortress_engine/plugins/
├── __init__.py            # exports: ParserInterface, NarratorInterface,
│                          #          MinimalParser, MinimalNarrator,
│                          #          ClassicParser, TemplateNarrator,
│                          #          PluginConfig, create_parser, create_narrator
├── parser_interface.py    # MODIFIED: + language abstract property + __init__ param
├── narrator_interface.py  # MODIFIED: same
├── classic_parser.py      # NEW
├── template_narrator.py   # NEW
└── factory.py             # NEW — create_parser, create_narrator,
                           #        _resolve_entry_point, list_available_plugins

src/fortress_engine/entities/loader.py   # MODIFIED: WorldYAML +3 keys, PluginConfigYAML, VocabularyYAML
                                          # + new load_vocabulary() method

shared/   # NOT a Python module — YAML data lives in the world's own dir
# worlds/<name>/shared/vocabulary.yaml   # per-world vocabulary (Fortaleza-specific later)
```

**Plugin instantiation** (the core factory pattern):
```python
@dataclass(frozen=True)
class PluginConfig:
    name: str
    options: dict[str, Any] = field(default_factory=dict)

def create_parser(
    plugin_config: PluginConfig, world_language: str
) -> ParserInterface:
    cls = _resolve_entry_point("fortress_engine.parsers", plugin_config.name)
    return _instantiate(cls, world_language, plugin_config.options)
```

`_resolve_entry_point` is a thin wrapper over `entry_points(group=...)` —
this is the ONLY code that imports from `importlib.metadata` for plugins,
keeping the discovery seam narrow and testable.

**`ClassicParser` algorithm** (per TDD §4.15 algorithm, with original
37-verb set from `docs/07-vocabulary.md`):
1. Normalize: `lowercase()` + NFKD + strip combining marks (tildes,
   dieresis) + replace `ñ`→`n`. Same as `MinimalParser._normalize`.
2. Tokenize on whitespace.
3. Strip stopwords (V2 expanded set — see Open Decisions #2).
4. Identify verb: first non-stopword token; must be in `self._verbs`. If
   not, return `ParsedCommand(subject=..., verb=token, target=None)` —
   orchestrator handles the no-clique path.
5. Speech-marker scan: if `DICIENDO` or `RESPONDIENDO` appears in the
   remaining tokens, split everything after into `text` (kept verbatim
   with stop words — spoken content). Same for standalone `DECIR` /
   `RESPONDER` verbs.
6. Preposition scan: tokens after `CON` → `instrument`; token after `A`
   (followed by a noun) → `context` (recipient). `AL` is a stopword in
   V2, so it does not participate in routing.
7. Entity name resolution: for the remaining noun-phrase target, search
   the protagonist's current anchor + inventory for an entity whose name
   (after normalization + partial-match: every input word appears in
   the entity name, per `Equals` in `EQSTRING.PAS:44-67`) matches.
   - Exact match wins over partial.
   - Among partials, prefer shortest name (most specific match).
   - Ties: ambiguous → return target as the raw phrase (no entity_id
     resolved); the orchestrator's clique validation surfaces the miss.
8. Return `ParsedCommand(subject=active_protagonist_id, verb=verb, target=entity_id_or_phrase, context=..., instrument=..., text=...)`.

**`TemplateNarrator` handlers** (9 events, per TDD §4.16):
- `entity_entered` → text from `payload["entity_name"]` + a generic prefix
  (default: "Entras en {entity_name}."). If `world_state` is provided and
  the target entity has `components.description`, append it.
- `action_output` → text from `payload["text"]`.
- `error_output` → text from `payload["message"]`, optionally wrapped
  (default: no wrap; engine produces the Spanish message).
- `episode_completed` → text from `payload["victory_text"]`.
- `game_over` → text from a `templates[reason]` key, or a default fallback.
- `system_message` → text from `payload["message"]`.
- `entity_described` / `entity_examined` → text from `payload["description"]`.
- `inventory_listed` → for MVP: a placeholder "Tienes: ..." with names
  joined (or a placeholder when payload has no `items` key — depends on
  how the inventory command is implemented in a future slice; the contract
  is `payload["items"]: list[str]`).

**Language validation** (Open Decisions #3): V1 the engine does NOT
cross-check `world.yaml.language` against `plugin.language` (the
plugin's own language property). The factory passes `world_language`
unconditionally. A warning is emitted via Python `warnings.warn(...)` if
the plugin's `language` property is non-empty and differs from
`world_language`. Strict mode (raising on mismatch) is a v1.1 flag.

**Vocabulary loading**: `EntityLoader.load_vocabulary(world_path)` returns
a `Vocabulary` dataclass. Default location: `<world>/shared/vocabulary.yaml`.
The ClassicParser constructor accepts an optional `vocabulary: Vocabulary`
parameter; the orchestrator (or future CLI) injects the loaded vocabulary.
If the world has no `vocabulary.yaml`, the parser falls back to a
hard-coded `DEFAULT_SPANISH_VOCABULARY` constant in
`classic_parser.py` — the same 37-verb set + V2 stopwords — so worlds
without a vocabulary file still work.

### Resolved Decisions (proposal-level)

1. **Factory supersedes TDD §9.2 `load_parser`/`load_narrator`** — those
   top-level functions are not implemented at all (orchestrator takes
   pre-built instances via constructor injection). The factory
   (`create_parser`/`create_narrator`) is the entry-point for CLI and
   future EpisodeManager use. The bare entry-point discovery is a
   private helper inside `factory.py` (`_resolve_entry_point`). The
   TDD docstring's `load_parser("classic")` becomes
   `create_parser(PluginConfig(name="classic"), "es")` — strictly more
   capable, backwards-compatible at the entry-point level (same group,
   same names).

2. **`language` is a constructor parameter with a default** — `def __init__(self, language: str = "es")`.
   This keeps every existing test of `MinimalParser()` /
   `MinimalNarrator()` green. New code passes `language` explicitly via
   the factory.

3. **Both `parser: "classic"` (string) and `parser: {plugin: "classic"}`
   (object) accepted by `WorldYAML`** — the string form is the TDD §9.2
   shape; the object form is the user's decision. Pydantic coerces the
   string to `PluginConfigYAML(name=<string>, options={})` so downstream
   code only deals with one shape. The object form is the future (it
   supports `options: {stopword_set: "v2"}` without a schema bump).

4. **Plugin config options: `dict[str, Any]` passed as kwargs to
   `__init__`** — the factory does `cls(language=world_language,
   **plugin_config.options)`. Plugins that don't accept a kwarg raise
   `TypeError` → factory catches, emits a warning, and retries without
   the unknown kwarg (best-effort). Strict per-option validation is v1.1.

5. **Vocabulary lives in `worlds/<name>/shared/vocabulary.yaml`** (per
   GDD §3.1 directory layout) — not in the engine's `shared/`. Worlds
   that don't supply it use the in-code `DEFAULT_SPANISH_VOCABULARY`.

6. **Plugin discovery never imports concrete classes** — the factory
   only uses `entry_points(group=...)` + `ep.load()`. Direct imports
   (`from fortress_engine.plugins.classic_parser import ClassicParser`)
   exist only inside the plugin module itself (the `__init__` of
   `classic_parser.py` defines `ClassicParser`) and inside the test
   suite (tests import directly — arch constant #7 exempts tests).

## Affected Areas

| Path | Impact | Description |
|------|--------|-------------|
| `src/fortress_engine/plugins/parser_interface.py` | Modified | Add `language: str` abstract property + `__init__(self, language: str = "es")`. `MinimalParser` updated. |
| `src/fortress_engine/plugins/narrator_interface.py` | Modified | Same treatment. |
| `src/fortress_engine/plugins/classic_parser.py` | New | `ClassicParser(ParserInterface)` — 37 verbs, normalization, stopwords, preposition/speech routing, entity name resolution. |
| `src/fortress_engine/plugins/template_narrator.py` | New | `TemplateNarrator(NarratorInterface)` — 9 event handlers, text from world data. |
| `src/fortress_engine/plugins/factory.py` | New | `PluginConfig` dataclass, `create_parser`, `create_narrator`, `_resolve_entry_point`, `list_available_plugins`. |
| `src/fortress_engine/plugins/__init__.py` | Modified | Module-level exports. |
| `src/fortress_engine/entities/loader.py` | Modified | `WorldYAML` +3 keys; `PluginConfigYAML`; `VocabularyYAML`; `Vocabulary` dataclass; `load_vocabulary(world_path)` method. |
| `tests/test_plugins/test_classic_parser.py` | New | ~400 lines — 37 verb set, normalization, stopwords, partial match, ambiguity, preposition/speech routing, language default. |
| `tests/test_plugins/test_template_narrator.py` | New | ~250 lines — 9 handlers + non-narrated event types + idempotency. |
| `tests/test_plugins/test_factory.py` | New | ~200 lines — entry-point resolution, language injection, missing-plugin error, legacy string form. |
| `tests/test_plugins/test_plugin_loading.py` | New | ~100 lines — entry points declared in `pyproject.toml` are discoverable. |
| `tests/test_plugins/test_parser.py` | Modified | Add `language` property assertions. |
| `tests/test_plugins/test_narrator.py` | Modified | Same. |
| `tests/test_plugins/test_plugin_integration.py` | Modified | Add factory-built orchestrator scenario. |
| `tests/test_entities/test_world_yaml_language.py` | New | ~150 lines — WorldYAML extensions, legacy + new form, defaults, validation. |
| `tests/fixtures/vocabulary/` (test-only) | New | Minimal vocabulary.yaml fixture for parser tests. |
| `pyproject.toml` | None | Entry points already declared. |
| `openspec/specs/plugin-contracts/spec.md` | Modified | `language` requirement + scenario. |
| `openspec/specs/parser-classic-v1/spec.md` | New | sdd-spec phase. |
| `openspec/specs/narrator-template-v1/spec.md` | New | sdd-spec phase. |
| `openspec/specs/plugin-factory/spec.md` | New | sdd-spec phase. |
| `openspec/specs/world-yaml-extensions/spec.md` | New | sdd-spec phase. |
| `docs/01-11/`, `docs/original-source/` | Untouched | Reference only. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **>99% branch coverage gate** (AGENTS.md hard gate) on 3 new modules + `factory.py` + `loader.py` extensions | High impact, High likelihood | Strict TDD: red→green→refactor per module. `ClassicParser` has the most branches (37-verb dispatch, 2 routing paths, partial match, ambiguity, language default) — write tests first covering each verb class (movement, item, NPC, system), each routing case (CON, A, DICIENDO, DECIR), each entity-match outcome (exact, partial, no-match, ambiguous), and each language default. Per-slice `pytest --cov-branch` must pass before opening the next slice. |
| **Entity name resolution ambiguity** — multi-word Spanish names (e.g. "Puerta principal" vs "Puerta secreta") can match the same partial input ("puerta") | High impact, Med likelihood | Implement the original Fortaleza `Equals` semantics (per `docs/07-vocabulary.md` §"Comparación de Strings"): every input word must appear in the entity name. Among matches, prefer the SHORTEST entity name (most specific). Document the rule in the spec; test with a 4-entity fixture where 2 share a prefix. If two entities have the same length, the parser returns the raw phrase (no resolution) — orchestrator's no-clique path handles the error. |
| **`vocabulary.yaml` location** — per-world (`worlds/<name>/shared/`) vs engine-level (`src/fortress_engine/data/`) | Med | Per-world wins because each game may have its own verb set (PRD §5 extensibility). Engine-level `DEFAULT_SPANISH_VOCABULARY` constant in `classic_parser.py` covers worlds without the file. Spec documents the precedence (override > default). |
| **Test isolation with Spanish entity fixtures** — tests need realistic Spanish entity names; shared fixtures might leak between test files | Med | Per-test `tmp_path` minimal worlds (same pattern as `test_plugin_integration._make_minimal_world`). Reuse a `spanish_entity_fixture.py` helper under `tests/fixtures/`. |
| **Factory kwargs + plugin signature drift** — adding `language` to plugin constructors breaks older plugins that don't accept it | Low (no existing third-party plugins) | Default-construction fallback in `_instantiate` (try with `language=...`; on `TypeError`, retry without). Emit a `DeprecationWarning`-style warning. Test the fallback path. |
| **Pydantic v2 `model_dump()` changes the WorldYAML output shape** — the existing `load_world_config` returns a dict that may have new keys | Low | `load_world_config` already uses `model.model_dump()`; new fields just add keys. The orchestrator and CLI don't yet consume `parser`/`narrator`/`language` so back-compat is preserved. The factory is the new consumer. |
| **`pyproject.toml` entry points point to non-existent modules today** — `pip install -e .` works (entry points are string references, not eager imports), but `entry_points(group=...)` queries can fail at plugin-load time | Low | The factory's `entry_points` query happens at runtime, not at install time. New code adds the modules; existing setup is unaffected. The `test_plugin_loading.py` test asserts the entry points resolve post-fix. |

## Rollback Plan

Each slice is a self-contained commit; rollback is per-slice:

- **Slice N1 (language property on ABCs)**: revert. `MinimalParser` /
  `MinimalNarrator` reverts to no-arg `__init__`. Engine still works with
  the stubs. New tests lose `language` assertions but old tests still pass.
- **Slice N2 (factory + PluginConfig)**: revert. Orchestrator still
  accepts pre-built plugins via constructor injection. Existing
  `test_plugin_integration.py` keeps working.
- **Slice N3 (ClassicParser + tests)**: revert. `MinimalParser` remains
  the parser. Engine still runs the integration test fixture.
- **Slice N4 (TemplateNarrator + tests)**: revert. `MinimalNarrator`
  remains. Same reasoning.
- **Slice N5 (WorldYAML extensions + vocabulary loader)**: revert.
  `WorldYAML` reverts to the 2-key form. Old `world.yaml` files still
  load; new fields are ignored (Pydantic with no `extra="forbid"`) — but
  this slice DOES add `extra="forbid"`, so revert BEFORE merging any
  world that uses the new keys.

No data loss: no migration, no schema change. World files that adopt the
new keys after this slice lands keep working in the new shape.

## Dependencies

- **Runtime**: `pyyaml>=6.0` (already in `pyproject.toml`) for
  `vocabulary.yaml`. `importlib.metadata` is stdlib in Python 3.11+.
- **Engine-core** (DONE): `ParserInterface` ABC, `NarratorInterface` ABC,
  `ParsedCommand` dataclass, `Entity` dataclass with `name`,
  `WorldState.get_entity` / `get_player_inventory` / `get_entities_in_container`.
- **Persistence** (DONE, not modified here): tests may instantiate a
  repository but this proposal does not change `persistence/`.
- **Authoritative specs**:
  - `docs/prd.md` §5 (parser), §6 (narrator), §7 (vocabulary mentions)
  - `docs/gdd.md` §3.1 (world.yaml layout), §3.2 (vocabulary.yaml), line 1297 (language)
  - `docs/tdd.md` §4.13 (parser interface), §4.14 (narrator interface),
    §4.15 (classic parser), §4.16 (template narrator), §8 (pyproject
    deps), §9.2 (load_parser/load_narrator — supersede, see Resolved
    Decisions #1)
  - `docs/07-vocabulary.md` — authoritative verb list and stopword set
  - `docs/12-engine-gap-analysis.md` P7 — open question on stopword V1 vs V2

## Success Criteria

- [ ] 4 sub-issues closed via chained PRs; `pytest` exits 0 with the
      full engine + plugins test suite collected.
- [ ] `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q`
      reports **>99% total branch coverage** (AGENTS.md hard gate).
- [ ] **Entry-point loading test**: `entry_points(group="fortress_engine.parsers")`
      returns at least `classic`; `entry_points(group="fortress_engine.narrators")`
      returns at least `template`. Both instantiate without error.
- [ ] **Language injection test**: `create_parser(PluginConfig("classic"), "es")`
      returns a `ParserInterface` whose `.language == "es"`. Same for
      `create_narrator(PluginConfig("template"), "es")` and a non-`"es"`
      value.
- [ ] **WorldYAML test**: a YAML with
      `language: "es"`, `parser: {plugin: "classic", options: {}}`,
      `narrator: {plugin: "template"}` parses via `EntityLoader.load_world_config`
      and the dict exposes all three keys with the expected types. A
      legacy `parser: "classic"` (bare string) also parses (coerced to
      `PluginConfigYAML`).
- [ ] **Orchestrator integration test**: build a `TurnOrchestrator` with
      `parser = create_parser(PluginConfig("classic"), "es")` and
      `narrator = create_narrator(PluginConfig("template"), "es")`,
      execute `"coger rusty_key"` and `"ir norte"` against a minimal
      world, assert canonical event sequence fires and `TemplateNarrator`
      produces non-`None` text for `entity_entered` and `action_output`.
- [ ] **37-verb test**: parametrized test asserts all 37 canonical
      Fortaleza verbs (per `docs/07-vocabulary.md`) parse to
      `verb=<expected>` with a non-`None` `subject`.
- [ ] **Stopword V2 test**: a parametrized test asserts the 9 V2 stopwords
      (`el`, `la`, `los`, `las`, `un`, `una`, `al`, `del`, `por`) are
      stripped from the target.
- [ ] **Entity resolution test**: a 4-entity fixture (Puerta principal,
      Puerta secreta, Llave oxidada, Espada) parses "ir puerta" to
      target=`None` (ambiguous), "ir puerta principal" to
      target=`puerta_principal` (exact wins), "ir p" to
      target=`puerta_principal` (partial + shortest-wins).
- [ ] **Speech test**: "abrir puerta diciendo abrete sesamo" parses to
      `verb="abrir"`, `target="puerta"`, `text="abrete sesamo"` (text is
      normalized, no stopword stripping inside text).
- [ ] **Preposition test**: "dar llave a bruja" parses to
      `target="llave"`, `context="bruja"`. "matar troll con espada"
      parses to `target="troll"`, `instrument="espada"`.
- [ ] **TemplateNarrator 9-event test**: every event type the TDD §4.16
      lists has a handler test that asserts a non-`None` string for a
      representative payload; an unrelated event type
      (`entity_transferred`) returns `None`.
- [ ] **Language warning test**: `create_parser(PluginConfig("classic"), "en")`
      when the loaded plugin reports `language="es"` emits a `warnings.warn`
      (captured via `pytest.warns`). Default `"es"` does not warn.
- [ ] **Back-compat test**: `MinimalParser()` and `MinimalNarrator()` with
      no args still construct and parse identically to the pre-change
      behavior (no `language` required). The existing
      `test_plugin_integration.py` passes unmodified.
- [ ] No new entry-point discovery outside `factory.py`: `grep -r
      'importlib.metadata' src/fortress_engine/` returns exactly one
      hit (in `plugins/factory.py`). Plugins are still loadable via
      entry points; the engine does not hardcode any plugin imports
      (arch constant #7).
- [ ] No closed entity-type set in `src/fortress_engine/plugins/`:
      `grep -rE '"(room|item|npc|player|portal)"' src/fortress_engine/plugins/`
      returns zero hits. The engine's spatial vocabulary
      (`spatial_anchor`, `from_anchor`, `to_anchor`, `start_anchor`)
      stays the only seam.

## Open Decisions (need user confirmation before sdd-spec)

1. **Verb set** — TDD §4.15 lists a generic 37-verb set
   (IR, TOMAR, COGER, MATAR, DAR, ABRIR, CERRAR, ROMPER, INTERROGAR,
   EXAMINAR, MIRAR, INVENTARIO, DEJAR, PONER, ENCENDER, APAGAR, LLENAR,
   VACIAR, EMPUJAR, TIRAR, GOLPEAR, ATACAR, HABLAR, DECIR, GRITAR, LEER,
   COMER, BEBER, USAR, TOCAR, OLER, ESCUCHAR, CAVAR, SALTAR, TREPAR,
   NADAR, ESPERAR). `docs/07-vocabulary.md` lists the ORIGINAL Fortaleza
   37 verb constants with synonym groups (ATRAVESAR/IR, TOMAR/COGER,
   SOLTAR/DEJAR, OBSERVAR/MIRAR, LEER/VER, ROMPER/FORZAR/DESTROZAR,
   PREGUNTAR/INTERROGAR, REGALAR/DAR, MATAR/ASESINAR, etc.).
   **RECOMMENDATION**: implement the original Fortaleza verb set with
   synonym groups (one canonical verb per group, synonyms map to it).
   Justification: the engine's purpose is to replicate Fortaleza;
   `docs/07-vocabulary.md` is the authoritative spec for the verb list
   (TDD's class names/sets are suggestions per AGENTS.md); the original
   verbs include ABANDONAR, TERMINAR, RESPONDER, etc. that the generic
   TDD list omits, and omits verbs like CERRAR/ENCENDER that the
   original uses differently (the original uses a CERRAR-less world
   because doors toggle open/closed implicitly).

2. **Stopwords — V1 exact vs V2 expanded** (PRD §5, docs P7).
   - V1 (per `docs/07-vocabulary.md`): `{LA, EL, POR, AL}` (4 words).
   - V2 (per PRD §5, currently in `MinimalParser`): adds `{UN, UNA, DEL, LOS, LAS}` (9 words).
   **RECOMMENDATION**: implement V2 in `ClassicParser` (9 stopwords).
   Justification: (a) `MinimalParser` already uses V2 — V1 would create
   a back-compat break; (b) V2 is strictly more capable (V1 ⊂ V2); (c)
   better UX (no surprise on `coger una llave`); (d) `docs/12-engine-gap-analysis.md`
   P7 is the only obstacle, and the engine-gap analysis explicitly
   leaves the answer open. Document the deviation from TDD §4.15's V1
   suggestion in the spec ("`ClassicParser` follows PRD V2 stopwords
   for consistency with `MinimalParser`; the original Fortaleza V1
   set is a strict subset and would also work, but V2 is the canonical
   V1 engine default").

3. **Language validation strictness** — engine checks
   `world.yaml.language == plugin.language`?
   - Strict (raise `LanguageMismatchError` on mismatch): safest, blocks
     misconfiguration early.
   - Warn-level (emit `warnings.warn`, do not block): flexible, lets
     worlds experiment.
   - Off: factory passes `language` through unconditionally.
   **RECOMMENDATION**: warn-level at load time, strict mode as a v1.1
   flag on `PluginConfig.options.strict_language: true`. Justification:
   V1 the engine does not have enough world diversity to know which
   languages are "valid" for which plugins — warning gives the
   developer feedback without blocking. The factory test suite asserts
   the warning fires; a v1.1 spec will add the strict option.

## Chained-PR Delivery (auto-chain, ≤400-line PR budget)

| Slice | Files | Approx lines | Sub-issue | Risk |
|-------|-------|--------------|-----------|------|
| N1: ABC language property | `plugins/parser_interface.py`, `plugins/narrator_interface.py` + tests | ~80 | #23, #24 (extension) | Low |
| N2: Plugin factory + PluginConfig | `plugins/factory.py`, `plugins/__init__.py`, `tests/test_plugins/test_factory.py` | ~250 | new (architecture) | Low |
| N3: WorldYAML extensions + vocabulary loader | `entities/loader.py` + tests | ~250 | new (world config) | Med |
| N4: ClassicParser V1 | `plugins/classic_parser.py` + tests + vocabulary fixture | ~400 | #21 | Med-High (37 verbs + 5 routing paths + entity resolution) |
| N5: TemplateNarrator V1 + orchestrator integration | `plugins/template_narrator.py` + tests + extended integration | ~350 | #25 | Low |

Total: ~1330 lines across 5 PRs, each under the 400-line budget. Slice N4
is the most complex (~400 lines including tests) and is the only slice
likely to need a `coverage run` checkpoint mid-slice. Strict TDD per
slice: red → green → refactor before opening the next PR.

## Resolved Decisions Summary (sdd-spec framing check)

**Pre-decided by TDD / PRD / GDD** (no debate): ABC shape (TDD §4.13,
§4.14), `entry_points` discovery (TDD §9.2, arch constant #7), event types
the narrator handles (TDD §4.16, 13-event-system.md §2.4), tilde
normalization algorithm (per `docs/07-vocabulary.md` + `MinimalParser`).

**Pre-decided by user this session** (do not revisit): plugin factory
+ language in world.yaml (decision in Engram
`sdd/epica-de-issue-3/architecture`); factory is functions, not class
(project convention); `language` is a constructor parameter on parser
and narrator; factory does not replace entry points, it layers on top;
future multi-language is entry-point-per-language + world declaration.

**Resolved by this proposal** (recommendations in "Open Decisions"):
verb set is the original Fortaleza 37 (Open #1), stopwords are V2
expanded (Open #2), language validation is warn-level (Open #3).
Each recommendation has rationale; the user can override at sdd-spec
review.

**sdd-spec to confirm framing**: exact `VocabularyYAML` schema and
Pydantic coercion rules for `PluginConfigYAML`, exact list of 37 verbs
with synonym group mappings, exact 9 events the `TemplateNarrator`
handles, exact `Entity` matching algorithm (shortest-match-wins,
ambiguity fallback), exact warning message and category for language
mismatch, and the precise per-test counts in `Success Criteria`.
