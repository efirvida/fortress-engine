# Proposal: engine-language-agnostic

## Intent

The fortress-engine currently couples the engine layer to Spanish user-facing
strings and to Spanish-language command recognition. Three Spanish literals
live in `graph.py:471-500` (5 blocked messages, no codes), two in
`operators.py:99-100` (`_MSG_NOT_PORTABLE`, `_MSG_TOO_HEAVY`), and nine in
`orchestrator.py` (no_action, blocked, no_repository×2, invalid_slot×2,
missing_slot, invalid_protagonist, operator_failed fallback). Movement
detection hardcodes `("ir", "abrir")` at `orchestrator.py:430` and `:456`,
and system command recognition hardcodes `guardar/cargar/terminar/esperar/
grupo/cambiar a` at `orchestrator.py:80-90`, `:679`, and `:101`. This makes
localization architecturally impossible and produces real defects today:

1. **Death-vs-block is decided by string equality** at
   `orchestrator.py:469` — `death_msg == edge.death_message`. The moment a
   narrator localizes the message, the engine flips the wrong branch and
   treats a fatal fall as a non-fatal block, or vice versa. This is a
   correctness bug, not a hypothetical.
2. **English dev diagnostics leak to the player** at
   `orchestrator.py:353` — `f"Entity '{entity_id}' not found"` from the
   operators is forwarded verbatim through `error_output.message` because
   `OperatorResult.error_message` is the only field. The narrator has no
   way to substitute a localized message because there is no code to key
   on.
3. **System commands and movement verbs are language-coupled** — a
   Portuguese Fortaleza could not reuse the engine without a fork. The
   parser plugin already knows its language (Epic #3) and is the natural
   place to read command words; the engine should not decide what "go"
   means in any language.

This change makes the engine emit **only structured codes + data**; the
narrator (already a swappable plugin) reads its own message templates from
the world's `shared/vocabulary.yaml`. The engine is left with three
language-agnostic surface points: (a) `error_code + data` on `error_output`,
(b) vocabulary-driven movement-verb recognition, (c) vocabulary-driven
system-command recognition. Multi-language runtime switching is explicitly
out of scope; the seam is designed so adding a second language later is a
world-data swap, not an engine change.

## Scope

### In Scope

- `src/fortress_engine/engine/graph.py` — `validate_macro_edge` returns a
  structured `MacroGateResult` dataclass: `(is_valid: bool, is_fatal: bool,
  gate_code: str, data: dict[str, object])`. Gate codes:
  `text_closed`, `requires_item`, `forbids_item`, `requires_flag`,
  `forbids_flag`. `is_fatal` is `edge.death_message is not None` (the
  structural fact, not a string match). The 5 hardcoded Spanish messages
  are removed; orchestrator reads `gate_code` + `data` (passage_name,
  required_text, required_item, required_flag) and emits an `error_output`
  with `error_code = gate_code` and structured `data`.
- `src/fortress_engine/engine/operators.py` — `OperatorResult` gains a
  `code: str | None = None` field. The two error constants
  (`_MSG_NOT_PORTABLE`, `_MSG_TOO_HEAVY`) are removed. All operators emit
  `code + data` instead of pre-formatted strings. Codes (with associated
  data keys):
  - TRANSFER: `entity_not_found` (entity_id), `entity_not_in_container`
    (entity_id, from_container), `weight_exceeds` (entity_id, weight,
    capacity), `not_portable` (entity_id), `container_not_found`
    (container_id)
  - TRANSFORM: `entity_not_found` (entity_id), `transform_component_missing`
    (entity_id, component_key)
  - COMBINE: `combine_inputs_missing` (input_entity_ids)
  - FLAG: `flag_readonly` (flag_name)
  - TELEPORT: `entity_not_found` (entity_id), `anchor_not_found`
    (from_anchor_id, to_anchor_id)
  English dev diagnostics (`f"Entity '{entity_id}' not found"` and
  similar) are removed; the `error_message` field is deprecated and the
  orchestrator ignores it (kept on the dataclass only as a debug aid for
  the apply phase's first slice; final slice deletes it).
- `src/fortress_engine/engine/orchestrator.py`:
  - All 9 Spanish literals are removed from `error_output` payloads.
    The new `error_output` payload is
    `{"error_code": str, "data": dict[str, object], "protagonist_id": str}`.
    No `message` field.
  - **Movement verb recognition** stops hardcoding `("ir", "abrir")`. The
    orchestrator consults `self._vocabulary.movement_verbs` (a `set[str]`
    of canonical verbs that the engine should treat as movement intent).
    World vocabulary default for movement verbs: `{"ir", "abrir"}` (preserves
    current behaviour for back-compat). The orchestrator constructor gains
    a `vocabulary: Vocabulary | None = None` parameter; the CLI (not in
    scope) is responsible for injecting the world's vocabulary.
  - **System command recognition** stops hardcoding
    `_SYSTEM_COMMANDS` / `_SYSTEM_PREFIXES`. The orchestrator consults
    `self._vocabulary.system_commands` (a `dict[canonical_command, list[str]]`
    of surface words; canonical commands are `save`, `load`, `quit`,
    `wait`, `group`, `switch`). `_parse_save_slot` becomes vocabulary-aware
    too — it consults the surface words for `save`/`load` to strip the
    prefix correctly in any language. Defaults preserve current behaviour.
  - **Death-vs-block fix** — orchestrator reads `gate.is_fatal` from
    `MacroGateResult`; string equality on `death_msg` is removed. This is
    the prerequisite refactor for localization and the highest-value bug
    fix in this change.
  - **Episode-completed literal → constant** —
    `self._emit("episode_completed", ...)` at
    `orchestrator.py:380` becomes
    `self._emit(EPISODE_COMPLETED, ...)`. Trivial; pure hygiene.
  - **Dead ternaries removed** — `orchestrator.py:590-591` and `:627-628`
    test `kind in ("guardar", "save")` inside a branch that has already
    matched `kind in ("guardar", "save")` (or `("cargar", "load")`).
    The conditional is unreachable. Both are simplified to the single
    Spanish-free message template reference; the dead test goes.
  - **`"limbo"` label removed** — at `orchestrator.py:727`,
    `ent.spatial_anchor or "limbo"` is replaced with
    `ent.spatial_anchor` (which may be `None`); the narrator (or a
    vocabulary message keyed on a new `limbo_location` system code)
    decides the display label.
- `src/fortress_engine/entities/loader.py`:
  - `VocabularyYAML` (Pydantic, `extra="forbid"`) gains three new
    optional fields: `messages: dict[str, str] = {}`,
    `movement_verbs: list[str] = []`, `system_commands: dict[str,
    list[str]] = {}`. All three are optional so existing
    `shared/vocabulary.yaml` files load unchanged.
  - `Vocabulary` dataclass grows the same three fields with matching
    types.
  - `load_vocabulary` updated to copy the new sections through.
- `src/fortress_engine/plugins/template_narrator.py`:
  - `__init__` accepts an optional `messages: dict[str, str] | None`
    parameter (overrides the in-code `DEFAULT_SPANISH_MESSAGES`).
  - `_handle_error_output` dispatches by `payload["error_code"]`: looks
    the code up in `messages`; falls back to
    `DEFAULT_SPANISH_MESSAGES[code]`; falls back to a generic
    "Ha ocurrido un error." if neither has the key. The
    `payload["data"]` dict feeds the `{key}` substitutions in the
    template. No more `payload["message"]` reliance.
  - `_handle_system_message` also dispatches by code when the payload
    contains `{"code": ...}` instead of `{"message": ...}`. Existing
    payloads that still ship `message` keep working (back-compat for
    the duration of the slice).
  - In-code `DEFAULT_SPANISH_MESSAGES` constant covers every
    `error_code` the engine emits: `no_action`, `blocked`,
    `no_repository`, `invalid_slot`, `missing_slot`,
    `invalid_protagonist`, `operator_failed`, `text_closed`,
    `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`,
    `not_portable`, `too_heavy`, `entity_not_found`,
    `entity_not_in_container`, `weight_exceeds`, `container_not_found`,
    `transform_component_missing`, `combine_inputs_missing`,
    `flag_readonly`, `anchor_not_found`. The orchestrator does not
    need to know any of these strings exist.
- `src/fortress_engine/plugins/classic_parser.py` /
  `parser_interface.py` / `narrator_interface.py` / `factory.py` — **no
  changes**. The parser already returns canonical verb tokens; the
  engine just stops interpreting specific verbs as movement. The
  factory already injects `language` and the vocabulary
  (`create_parser` already accepts `vocabulary=...` via the
  constructor of `ClassicParser` per Epic #3).
- Tests (mirroring `src/fortress_engine/` in `tests/`):
  - `test_graph.py` — extend `validate_macro_edge` tests to assert the
    new structured return: `result.is_valid`, `result.is_fatal`,
    `result.gate_code`, `result.data`. Existing tests at
    `test_graph.py:824` and `:957` that assert the Spanish string are
    rewritten to assert the new structure (gate_code + data). Five new
    parametrized cases — one per gate — assert `is_fatal` matches
    `edge.death_message is not None` and `data` carries the right keys.
  - `test_operators.py` — rewrite the four
    `"Usted no puede cargar con eso."` assertions at lines 91, 104,
    145, 184, 219 to assert `result.code == "not_portable"` and
    `result.data == {"entity_id": ...}`. Add a parametrized test
    asserting every operator failure path emits the correct `code +
    data` and that `error_message` is `None` (or removed in the final
    slice).
  - `test_orchestrator.py` and `test_orchestrator_save_load.py` —
    rewrite the 9 Spanish-message assertions in the orchestrator tests
    to assert `error_code + data` (and that no `message` key exists).
    Add a parametrized test that constructs a TurnOrchestrator with
    `vocabulary=...` containing English surface words for system
    commands (`save: ["save", "stash"]`) and asserts the orchestrator
    routes `"stash 2"` to the save path. Add a parametrized test for
    movement verbs from vocabulary (English: `go: ["go", "walk"]`).
    Add a test that death-vs-block discrimination uses
    `gate.is_fatal` (not string equality) — assert that a custom
    `MacroGateResult(is_valid=False, is_fatal=True, ...)` always
    routes to `GAME_OVER` regardless of the gate's `gate_code`.
  - `test_template_narrator.py` — extend `_handle_error_output` tests
    to assert the dispatch by `error_code`: given a payload
    `{"error_code": "blocked", "data": {"passage_name": "Puerta
    secreta"}}`, the result matches the Spanish template from
    `DEFAULT_SPANISH_MESSAGES["blocked"]`. Add a test that an English
    `messages` override is honored. Rewrite the
    "No entiendes como hacer eso." assertions at
    `test_template_narrator.py:233, :240` to drive
    `error_code="no_action"`.
  - `test_narrator.py` — same treatment as `test_template_narrator.py`
    for the MinimalNarrator path (lines 213, 221, 461, 467).
  - `test_loader.py` and `test_world_yaml_language.py` — add coverage
    for the three new vocabulary fields: round-trip a vocabulary YAML
    with `messages`, `movement_verbs`, `system_commands`; assert the
    `Vocabulary` dataclass carries the new sections; assert a
    vocabulary YAML without the new sections loads with empty
    defaults. Back-compat fixture: a 3-line `vocabulary.yaml` from
    before this change must still load.
  - Integration: extend `test_plugin_integration.py` with a scenario
    that builds the orchestrator with a `ClassicParser` + a vocabulary
    containing English system commands, runs `save 1` and `go north`,
    and asserts the engine routes correctly without Spanish defaults.
- Docs: flag the spec drift in `docs/tdd.md`, `docs/gdd.md`, and
  `docs/prd.md`. The docs currently describe the hardcoded Spanish
  behaviour (`tdd.md` §4.1 movement, `gdd.md` §3.2 vocabulary). The
  sdd-spec phase produces the canonical diff; this proposal
  *flags* that the docs need updates and lists the sections
  affected (no doc edits happen in the apply phase unless explicitly
  requested — the spec delta is the source of truth).

### Out of Scope (deferred)

- **Multi-language runtime switching** — `vocabulary.language` is a
  per-world constant, not a per-turn state. Mid-session
  `CAMBIAR IDIOMA` is a v1.1 candidate (already noted in Epic #3).
- **AI parser / immersive narrator** — separate epics.
- **CLI changes** (`fortress-engine run/validate/test`) — the CLI is
  a separate epic. It is the *consumer* of the orchestrator's new
  `vocabulary` parameter; until the CLI exists, tests construct
  orchestrators with the new parameter directly.
- **Fortaleza world data** (`worlds/fortaleza/**`) — separate epic.
  Worlds without the new vocabulary sections keep working through
  defaults.
- **Parser or narrator interface changes** — neither ABC grows a
  method. The narrator gains a constructor argument; the parser is
  unchanged.

## Capabilities

### New

| Capability | Covers |
|------------|--------|
| `engine-language-agnostic` | The engine's language-agnostic surface: structured error codes, vocabulary-driven movement and system-command recognition, structured macro-gate result, no Spanish literals. New spec captures the engine contract for localization. |

### Modified

| Capability | Change |
|------------|--------|
| `turn-orchestrator` | `error_output` payload drops `message` and gains `data`; movement detection consults `vocabulary.movement_verbs`; system-command detection consults `vocabulary.system_commands`; death-vs-block discrimination uses `gate.is_fatal`; `EPISODE_COMPLETED` constant replaces string literal; `vocabulary: Vocabulary \| None` constructor parameter; dead ternaries removed; `"limbo"` literal removed. |
| `narrator-template-v1` | Constructor accepts `messages: dict[str, str] \| None`; `_handle_error_output` dispatches by `error_code` against `messages` or `DEFAULT_SPANISH_MESSAGES`; `_handle_system_message` dispatches by `code` only (user decision: NO `message`-payload back-compat); no `message` key required on `error_output`. |
| `narrator-interface` | (No behavior change; constructor accepts language already — Epic #3.) |
| `world-yaml-extensions` | `VocabularyYAML` Pydantic model gains optional `messages`, `movement_verbs`, `system_commands` fields (all `extra="forbid"` preserved, so back-compat is automatic). |
| `world-loading` | `Vocabulary` dataclass + `load_vocabulary` carry the new sections through; back-compat via empty defaults. |
| `atomic-operators` | `OperatorResult` gains `code: str \| None` field; all five operators emit `code + data` instead of pre-formatted strings; `_MSG_NOT_PORTABLE` / `_MSG_TOO_HEAVY` removed; English dev diagnostics removed. |
| `dual-graph` | `validate_macro_edge` returns a `MacroGateResult(is_valid, is_fatal, gate_code, data)` dataclass instead of `(bool, str \| None)`. The 5 Spanish literals are removed. |
| `parser-classic-v1` | (No behavior change — parser still returns canonical verb tokens; the engine stops interpreting specific verbs. Spec gains a note that the engine no longer hardcodes movement verbs.) |
| `parser-interface` | (No behavior change.) |

## Approach

**Engine emits codes + data; narrator owns text.** This is the user
decision recorded in the explore phase (Engram
`sdd/engine-language-agnostic/explore`): the TemplateNarrator already
receives the full event, so dispatching by `error_code` requires no
interface change. The only new narrator surface is the
`messages: dict[str, str] | None` constructor argument, which is
optional and falls back to `DEFAULT_SPANISH_MESSAGES`.

**World vocabulary gains three sections.** Per Epic #3's
`worlds/<name>/shared/vocabulary.yaml` layout:

```yaml
# worlds/<name>/shared/vocabulary.yaml (new sections)
messages:
  error_output.no_action: "No entiendes cómo hacer '{verb}' aquí."
  error_output.blocked: "No puedes ir por ahí."
  error_output.no_repository: "Guardar no está disponible."
  error_output.invalid_slot: "Ranura inválida. Usá 1, 2, o 3."
  error_output.missing_slot: "No hay partida guardada en la ranura {slot}."
  error_output.invalid_protagonist: "No se encuentra a '{name}'."
  error_output.operator_failed: "No puedes hacer eso."
  error_output.text_closed: "{passage_name} está cerrada."
  error_output.requires_item: "No puedes pasar por {passage_name} aún."
  error_output.forbids_item: "{passage_name} está sellada."
  error_output.requires_flag: "No puedes pasar por {passage_name} aún."
  error_output.forbids_flag: "{passage_name} está sellada."
  error_output.not_portable: "Usted no puede cargar con eso."
  error_output.too_heavy: "Sería demasiado peso."
  error_output.entity_not_found: "No se encuentra."
  error_output.entity_not_in_container: "No está donde lo buscas."
  error_output.weight_exceeds: "Es demasiado pesado."
  error_output.container_not_found: "No se encuentra el destino."
  error_output.transform_component_missing: "No puedes hacer eso."
  error_output.combine_inputs_missing: "Faltan objetos para combinar."
  error_output.flag_readonly: "Eso no se puede cambiar."
  error_output.anchor_not_found: "No puedes ir ahí."
movement_verbs:
  - "ir"
  - "abrir"
system_commands:
  save:    ["guardar", "save"]
  load:    ["cargar", "load"]
  quit:    ["terminar", "abandonar", "quit"]
  wait:    ["esperar", "wait"]
  group:   ["grupo", "group"]
  switch:  ["cambiar a"]   # surface form is a prefix; orchestrator strips it
```

A world that does not supply a `messages` section (the current
default — Epic #3 ships a vocabulary YAML *without* the new sections)
keeps working because `DEFAULT_SPANISH_MESSAGES` (in-code) and
`DEFAULT_MOVEMENT_VERBS = {"ir", "abrir"}` /
`DEFAULT_SYSTEM_COMMANDS = {...}` defaults (in-code) cover every
event the engine emits. Existing test worlds and the Fortaleza
data load unchanged.

**`MacroGateResult` dataclass** (in `graph.py`):

```python
@dataclass(frozen=True)
class MacroGateResult:
    is_valid: bool
    is_fatal: bool          # True iff edge.death_message is not None
    gate_code: str          # "" when is_valid; one of the 5 gate codes otherwise
    data: dict[str, object] # passage_name, required_text, required_item, required_flag
```

The orchestrator reads `gate.is_fatal` instead of comparing
`death_msg == edge.death_message`. This is the single most important
fix in the change.

**Orchestrator constructor ripple.** `TurnOrchestrator.__init__` gains
`vocabulary: Vocabulary | None = None`. The CLI (not in scope) is
expected to construct the orchestrator with the vocabulary loaded
from `<world>/shared/vocabulary.yaml` via
`EntityLoader.load_vocabulary`. The orchestrator's tests pass a
custom vocabulary to exercise language-specific recognition; the
production call (when the CLI is built) passes the world's
vocabulary.

**`OperatorResult` shape**:

```python
@dataclass(frozen=True)
class OperatorResult:
    success: bool
    code: str | None = None
    data: dict[str, object] = dc_field(default_factory=dict)
    events_payload: dict[str, Any] | None = None
    # error_message: str | None = None  # deprecated; removed in final slice
```

The orchestrator reads `result.code` and `result.data` for
`error_output`. `error_message` is **removed immediately** (user
decision — no staged removal): the `OperatorResult` carries only
`code` + `data`, and the engine never constructs the string itself.
Test debugging inspects `result.code` + `result.data` directly
instead of a formatted string.

**Tests as the spec.** Every contract change is tested before the
code that implements it lands. The existing tests that assert
Spanish strings are rewritten to assert the new structure (this
is a test-update cost, not a behavior regression — the engine
behaves the same for a Spanish-only world; the tests stop
coupling to a particular rendering).

### Resolved Decisions (proposal-level)

1. **`error_output` payload is `error_code + data`, not
   `error_code + message`** — the engine MUST NOT construct any
   user-facing string. Even when `data` is empty (e.g.
   `operator_failed` fallback), the engine emits `data: {}` and
   the narrator picks the bare template. Justification: keeping a
   `message` field as a Spanish default in the engine would
   re-couple the engine to a language. The narrator owns text;
   the engine owns codes.

2. **The orchestrator's vocabulary is injected, not loaded
   internally** — the orchestrator's constructor takes
   `vocabulary: Vocabulary | None`. The CLI (not in scope) is
   responsible for `EntityLoader.load_vocabulary`. Justification:
   the orchestrator should not know about file paths. The factory
   / bootstrap layer owns world I/O (per arch constant — single
   seam for world loading).

3. **`"limbo"` is replaced with `None` (not a code)** — the
   orchestrator's `protagonists_listed` payload emits
   `location: spatial_anchor` which may be `None`. The narrator
   decides the display ("limbo", "nada", or a localized equivalent)
   via a new `protagonists_listed` template that handles the
   `None` case. Justification: the engine never had a "limbo"
   room — it's a display label, not a state.

4. **Three vocabulary sections are optional and back-compat** —
   existing `shared/vocabulary.yaml` files (Epic #3's
   `tests/fixtures/vocabulary/full_vocabulary.yaml` and any
   future worlds) load unchanged. `extra="forbid"` is preserved
   (so typos still fail loudly), but missing keys default to
   empty. The orchestrator's in-code defaults provide the
   Spanish defaults when the vocabulary does not.

5. **Death-vs-block uses `is_fatal`, not a code-level signal** —
   the gate result carries BOTH `is_fatal` (structural: the edge
   declared a `death_message`) and `gate_code` (which gate
   fired). The orchestrator uses `is_fatal` to route. The
   `gate_code` flows through to the narrator unchanged so the
   player sees a meaningful message. Justification: this is the
   only way to make the routing robust to localization.

6. **`error_message` is staged-removed** — present in
   `OperatorResult` for the first two slices as a deprecated
   debug field, removed in the final slice. Justification:
   staged removal keeps `git bisect` clean and gives the apply
   phase a way to assert the deprecated field is `None` (or
   formatted from `code + data`, never hardcoded).

7. **No new event type for "limbo" or "system code"** — the
   `system_message` event already exists; the narrator's
   `_handle_system_message` already accepts arbitrary payload.
   The "limbo" label becomes a narrator concern (template
   substitution for `None` location). The `error_output` event
   already exists with `error_code`; the new field is `data`.

## Affected Areas

| Path | Impact | Description |
|------|--------|-------------|
| `src/fortress_engine/engine/graph.py` | Modified | New `MacroGateResult` dataclass; `validate_macro_edge` returns the structured result; 5 Spanish literals removed. |
| `src/fortress_engine/engine/operators.py` | Modified | `OperatorResult.code` + `data` fields; `_MSG_NOT_PORTABLE`/`_MSG_TOO_HEAVY` removed; English dev diagnostics removed; all 5 operators emit codes. |
| `src/fortress_engine/engine/orchestrator.py` | Modified | New `vocabulary` constructor parameter; 9 Spanish literals removed from `error_output`; `error_output` payload becomes `{error_code, data, protagonist_id}`; movement verbs from vocabulary; system commands from vocabulary; `_parse_save_slot` vocabulary-aware; death-vs-block uses `gate.is_fatal`; `EPISODE_COMPLETED` constant; dead ternaries removed; `"limbo"` label → `None`; `is_valid, death_msg = ...` → `gate = ...`. |
| `src/fortress_engine/entities/loader.py` | Modified | `VocabularyYAML` +3 optional fields; `Vocabulary` dataclass +3 fields; `load_vocabulary` updated. |
| `src/fortress_engine/plugins/template_narrator.py` | Modified | `messages` constructor parameter; `_handle_error_output` dispatches by `error_code`; `_handle_system_message` dispatches by `code`; new `DEFAULT_SPANISH_MESSAGES` in-code constant covering every engine code. |
| `src/fortress_engine/plugins/classic_parser.py` | None | Parser already returns canonical verb tokens; the engine stops interpreting specific verbs. |
| `src/fortress_engine/plugins/parser_interface.py` | None | No change. |
| `src/fortress_engine/plugins/narrator_interface.py` | None | No change. |
| `src/fortress_engine/plugins/factory.py` | None | No change. |
| `tests/test_engine/test_graph.py` | Modified | Rewrite 2 Spanish-string assertions to structured-result assertions; add 5 parametrized gate tests. |
| `tests/test_engine/test_operators.py` | Modified | Rewrite 5 Spanish-string assertions to `code + data`; add parametrized coverage for all 5 operators. |
| `tests/test_engine/test_orchestrator.py` | Modified | Rewrite ~9 Spanish-string assertions across orchestrator tests; add vocabulary-driven system-command + movement tests; add death-vs-block-by-`is_fatal` test. |
| `tests/test_engine/test_orchestrator_save_load.py` | Modified | Spanish-string assertions become `error_code + data` assertions; add vocabulary-driven save/load test. |
| `tests/test_plugins/test_template_narrator.py` | Modified | Rewrite Spanish-string assertions; add error-code dispatch test; add `messages` override test. |
| `tests/test_plugins/test_narrator.py` | Modified | Same as `test_template_narrator.py` for the MinimalNarrator path. |
| `tests/test_entities/test_loader.py` | Modified | Round-trip tests for new vocabulary YAML sections; back-compat fixture test. |
| `tests/test_entities/test_world_yaml_language.py` | Modified | (If applicable) vocabulary YAML schema test additions. |
| `tests/test_plugins/test_plugin_integration.py` | Modified | Add end-to-end scenario with English system commands + English movement verbs. |
| `docs/tdd.md` | Flagged | §4.1 (turn orchestrator) currently documents hardcoded Spanish behaviour; spec drift to be captured by sdd-spec delta. |
| `docs/gdd.md` | Flagged | §3.2 (vocabulary) currently documents only the parser-side vocabulary fields; new sections (messages, movement_verbs, system_commands) need documentation. |
| `docs/prd.md` | Flagged | §4.4 (operator errors) currently shows Spanish error messages; spec drift to be captured. |
| `openspec/specs/turn-orchestrator/spec.md` | Modified | Delta spec: new `error_output` shape, vocabulary-driven commands, `is_fatal` routing. |
| `openspec/specs/narrator-template-v1/spec.md` | Modified | Delta spec: `messages` constructor argument, `error_code` dispatch, `DEFAULT_SPANISH_MESSAGES`. |
| `openspec/specs/world-yaml-extensions/spec.md` | Modified | Delta spec: `VocabularyYAML` +3 fields. |
| `openspec/specs/world-loading/spec.md` | Modified | Delta spec: `Vocabulary` +3 fields; `load_vocabulary` updated. |
| `openspec/specs/atomic-operators/spec.md` | Modified | Delta spec: `OperatorResult.code + data`; codes list per operator. |
| `openspec/specs/dual-graph/spec.md` | Modified | Delta spec: `MacroGateResult` shape; `validate_macro_edge` new contract. |
| `openspec/specs/engine-language-agnostic/spec.md` | New | New spec: engine's language-agnostic surface (umbrella). |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Death-vs-block string-equality fix changes behaviour** for any test that depended on the broken path | High impact, Low likelihood (only string-equality tests fail — there are none) | The fix is strictly more correct; if a test depends on the wrong branch firing, that test is asserting a bug. The apply phase rewrites the assertion to the correct branch. |
| **>99% branch coverage gate** across 5 modified modules simultaneously (graph, operators, orchestrator, loader, template_narrator) | High impact, High likelihood | Strict TDD per slice. Each slice red→green→refactor before opening the next PR. The `operator_failed` fallback branch and the new vocabulary-aware movement/system-command paths are the highest-branch surfaces — write parametrized tests for each. The orchestrator's `execute_turn` is the largest single function; the change TOUCHES the function but does not grow its cyclomatic complexity (the per-branch ternaries simplify to single calls). |
| **Test updates for removed Spanish messages** — 16+ test assertions across 5 test files change | Med impact, Med likelihood | The rewrites are mechanical: `assert result.error_message == "..."` → `assert result.code == "..." and result.data == {...}`. Each rewrite is part of the slice that introduces the new shape. The plan-budget per slice is sized to absorb the rewrites. |
| **Orchestrator constructor ripple** — new `vocabulary` parameter | Low impact, Low likelihood (only the CLI calls TurnOrchestrator; CLI is not in scope) | The parameter has a default of `None`. The orchestrator's in-code defaults activate when `None`. The orchestrator tests pass a `vocabulary=...` kwarg to exercise the vocabulary path. When the CLI is built, it is a one-line change. |
| **Vocabulary loader back-compat** — worlds with old `shared/vocabulary.yaml` must keep loading | Low impact, Low likelihood (Pydantic with `extra="forbid"` rejects unknown fields, but the 3 new fields are optional, so existing files load) | New fields default to empty; orchestrator's in-code defaults cover the gaps. `test_loader.py` gains a back-compat fixture: the current `full_vocabulary.yaml` must still parse after the change. |
| **`OperatorResult.error_message` staged-removal bisect hazard** — keeping the field as deprecated for 2 slices could leak back into a future commit | Med | The deprecation is documented in the field's docstring; the final slice adds an `assert error_message is None` to every operator test. The field is removed in the final slice, not gradually. |
| **Narrator's `DEFAULT_SPANISH_MESSAGES` drift** — adding a new `error_code` to the engine and forgetting to add a Spanish template | Med | The apply phase includes a parametrized test that asserts every code the engine emits has an entry in `DEFAULT_SPANISH_MESSAGES` (or in the world vocabulary). New engine codes are forced to come with their template. |
| **Doc drift** — `docs/tdd.md` / `gdd.md` / `prd.md` describe the old behaviour | Low impact, Med likelihood | sdd-spec phase produces the canonical delta. The apply phase does not edit docs unless explicitly requested (per project convention — the spec delta is the source of truth; the docs are reference material). A note is added to the README pointing at the spec delta. |
| **English dev diagnostics removal may hurt debugging** | Low impact, Med likelihood | `error_message` is staged-removed; the first 2 slices keep it as a debug aid (asserted equal to the formatted `code + data` template, so it's derivable). After the final slice, developers inspect events with `code + data` directly — the bus is the source of truth. |

## Rollback Plan

Each slice is a self-contained commit; rollback is per-slice:

- **Slice L1 (Vocabulary growth: `messages`, `movement_verbs`, `system_commands`)**: revert. `VocabularyYAML` and `Vocabulary` lose the 3 fields. Orchestrator continues with the hardcoded `("ir", "abrir")` and `_SYSTEM_COMMANDS` constants. No new tests; old tests pass. **Safest rollback.**
- **Slice L2 (Orchestrator consumes `vocabulary` parameter; movement and system commands from vocabulary)**: revert. Orchestrator goes back to hardcoded constants. New `vocabulary` parameter is removed. Tests that pass `vocabulary=...` are removed; old tests pass. **Behaviour-equivalent for Spanish worlds.**
- **Slice L3 (Operators: `OperatorResult.code + data`; remove 2 constants and English diagnostics)**: revert. Operators go back to `error_message`-only. Orchestrator continues to forward `error_message` as the `message` field. **Behaviour-equivalent for Spanish worlds.** Tests for new codes are removed.
- **Slice L4 (Graph: `MacroGateResult`; structured gate return)**: revert. `validate_macro_edge` returns `(bool, str | None)` again. Orchestrator's death-vs-block string-equality check returns. **Behaviour-equivalent for Spanish worlds; the death-vs-block bug is REINTRODUCED** — only acceptable if the change is being abandoned entirely. If L4 needs to roll back while L1–L3 are kept, a partial revert keeps `OperatorResult.code` and uses it as a fallback when the gate result is the old tuple shape (a 10-line shim).
- **Slice L5 (Narrator: `messages` constructor arg, `error_code` dispatch, `DEFAULT_SPANISH_MESSAGES`)**: revert. `_handle_error_output` reads `payload["message"]` again. `DEFAULT_SPANISH_MESSAGES` is removed. Engine must continue emitting `message` (L3 rollback or a backward-compat shim). **Behaviour-equivalent for Spanish worlds.**

**Order matters**: L1 → L2 → L3 → L4 → L5. L4 is the riskiest (death-vs-block fix) and should land last to maximize review confidence. L5 must land AFTER L3 + L4 because the narrator's new dispatch depends on the engine's new payload.

**No data loss**: no migration, no schema change to `world.yaml` or `world_data.sqlite`. Worlds that adopt the new vocabulary sections after the merge keep working in the new shape; worlds that do not keep working through defaults.

## Dependencies

- **Engine-core** (DONE): `Entity`, `WorldState`, `EventBus`, `EngineEvent`,
  `EpisodeManager`, `GoalEvaluator`, `DualGraphEngine`.
- **Persistence** (DONE, not modified here): `WorldStateRepository`,
  `EventSourcingSaveSystem`. The orchestrator continues to use them for
  save/load; the system-command recognition is now vocabulary-driven.
- **Plugin contracts** (DONE, not modified here): `ParserInterface`,
  `NarratorInterface`, `MinimalParser`, `MinimalNarrator`. The
  `TemplateNarrator` gains a constructor argument but no interface
  change.
- **World vocabulary** (DONE per Epic #3 N3): `VocabularyYAML` Pydantic
  model, `Vocabulary` dataclass, `EntityLoader.load_vocabulary`. This
  change extends the existing model; it does not introduce a new
  loader.
- **Authoritative docs**:
  - `docs/tdd.md` §4.1 (turn orchestrator — describes hardcoded
    `("ir", "abrir")` and `_SYSTEM_COMMANDS`; spec drift flagged)
  - `docs/gdd.md` §3.2 (vocabulary.yaml — describes parser-side fields
    only; new sections need documentation)
  - `docs/prd.md` §4.4 (operator errors — shows Spanish messages;
    spec drift flagged)
  - `docs/13-event-system.md` §2.4 (`error_output` and `system_message`
    — payload shape changes flagged)
  - `docs/07-vocabulary.md` — 37-verb reference; movement verbs in this
    list become the default for `Vocabulary.movement_verbs`.

## Success Criteria

- [ ] `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q`
      reports **>99% total branch coverage** (AGENTS.md hard gate).
- [ ] **Zero Spanish user-facing literals in the engine** —
      `grep -rE '"(No |está cerrada|está sellada|Usted |Sería |Ranura |No hay |No se encuentra |cargando |cargar |podés |podés |podrías |limbo)"' src/fortress_engine/engine/`
      returns zero hits. (Spanish may remain in `from_anchor`,
      `to_anchor`, `passage_name` if a *world YAML* uses it; this
      check targets the engine source, not the world data.)
- [ ] **Zero hardcoded movement verbs in the engine** —
      `grep -nE '"\s*(ir|abrir)\s*"' src/fortress_engine/engine/orchestrator.py`
      returns zero hits in production code (comments exempt).
- [ ] **Zero hardcoded system commands in the engine** —
      `grep -nE '"\s*(guardar|cargar|terminar|esperar|grupo|cambiar a|save|load)\s*"' src/fortress_engine/engine/orchestrator.py`
      returns zero hits in production code.
- [ ] **Structured gate result** — a test asserts
      `validate_macro_edge(edge, state, text)` returns a
      `MacroGateResult` with `is_fatal` matching
      `edge.death_message is not None` for every gate type (text,
      item, forbids_item, flag, forbids_flag) and `gate_code` is one
      of the 5 documented codes.
- [ ] **Death-vs-block uses `is_fatal`** — a parametrized test asserts
      that a custom `MacroGateResult(is_valid=False, is_fatal=True,
      gate_code="text_closed", data=...)` routes to `GAME_OVER` and a
      `(is_valid=False, is_fatal=False, ...)` routes to
      `error_output`, regardless of any string content in `data`.
- [ ] **Operator `code` field** — a parametrized test asserts that
      every documented failure path of every operator emits the
      correct `code + data` tuple, and that `error_message` is
      removed (or `None` in staged slices) — never a hardcoded
      string from the engine.
- [ ] **Vocabulary-driven system command** — a test constructs
      `TurnOrchestrator(state, graph, bus, parser, narrator,
      goal_evaluator, episode_manager, vocabulary=...)` with a
      vocabulary whose `system_commands["save"] = ["save", "stash"]`
      and asserts that `execute_turn("stash 2")` routes to the
      save-handling path (Spanish `"guardar 2"` works too via the
      default vocabulary).
- [ ] **Vocabulary-driven movement** — a test with
      `vocabulary.movement_verbs = {"go", "walk"}` asserts
      `execute_turn("go north")` resolves a movement and `execute_turn("ir norte")`
      does not (Spanish `ir` not in the test vocabulary).
- [ ] **No Spanish default in `error_output` payload** — every
      `error_output` event in every test's captured event log has
      keys `{error_code, data, protagonist_id}` and no `message`
      key.
- [ ] **Narrator dispatches by `error_code`** — a test asserts that
      `_handle_error_output({"error_code": "blocked", "data":
      {"passage_name": "Puerta secreta"}}, None)` returns the
      Spanish template from `DEFAULT_SPANISH_MESSAGES["blocked"]`
      with `{passage_name}` substituted, and that an English
      `messages` override is honored.
- [ ] **Vocabulary back-compat** — a test loads the existing
      `tests/fixtures/vocabulary/full_vocabulary.yaml` (no
      `messages`, `movement_verbs`, or `system_commands` sections)
      and asserts the resulting `Vocabulary` has empty defaults for
      the new fields.
- [ ] **Every engine code has a template** — a parametrized test
      iterates the engine's known codes and asserts each is in
      `DEFAULT_SPANISH_MESSAGES`. The test fails if a new code is
      added to the engine without a template.
- [ ] **No CLI / AI / multi-language changes** — these stay out of
      scope. The `vocabulary.language` is still a per-world
      constant; the orchestrator does not switch languages at
      runtime.
- [ ] **No closed entity-type set in the engine** —
      `grep -rE '"(room|item|npc|player|portal)"' src/fortress_engine/engine/`
      returns zero hits. (Arch constant preserved.)

## Open Decisions (RESOLVED — user confirmed before sdd-spec)

1. **`system_commands["switch"]` is a prefix** — **RESOLVED**: keep the
   special case in the orchestrator; the spec documents that
   `system_commands[switch]` is a *prefix* command (strip the prefix
   to extract the protagonist name), not an equality match.

2. **Error code namespace** — **RESOLVED**: flat codes, no namespace,
   matching the existing `error_code` field (`"no_action"`, `"blocked"`,
   `"operator_failed"`, `"requires_item"`, ...). The narrator groups by
   flat key; namespacing deferred to v1.1 if a world needs it.

3. **`system_message` `code` vs `message`** — **RESOLVED (user override)**:
   `code` ONLY from the start. No `message`-payload back-compat. Any
   emitter of `system_message` sends `code`; the narrator dispatches on
   `code` exclusively.

4. **`OperatorResult.error_message`** — **RESOLVED (user override)**:
   removed IMMEDIATELY. `OperatorResult` carries only `code` + `data`;
   no staged removal, no debug-aid field. Test debugging inspects
   `code` + `data` directly.

## Chained-PR Delivery (auto-chain, ≤400-line PR budget)

| Slice | Files | Approx lines | Risk |
|-------|-------|--------------|------|
| L1: Vocabulary YAML + dataclass grow 3 sections; loader updated; back-compat test | `entities/loader.py` + `tests/test_entities/test_loader.py` + new fixture | ~150 | Low |
| L2: Orchestrator consumes `vocabulary`; movement + system commands from vocabulary; dead ternaries removed; `EPISODE_COMPLETED` constant; `"limbo"` → `None` | `engine/orchestrator.py` + `tests/test_engine/test_orchestrator.py` + `test_orchestrator_save_load.py` | ~300 | Med (test rewrites) |
| L3: Operators emit `code + data`; 2 constants + English diagnostics removed; tests rewrite | `engine/operators.py` + `tests/test_engine/test_operators.py` | ~250 | Med |
| L4: Graph `MacroGateResult`; orchestrator uses `is_fatal` (death-vs-block fix); tests rewrite | `engine/graph.py` + `engine/orchestrator.py` (death-vs-block block) + `tests/test_engine/test_graph.py` + `tests/test_engine/test_orchestrator.py` | ~250 | Med-High (behaviour change) |
| L5: Narrator `messages` parameter, `error_code` dispatch, `DEFAULT_SPANISH_MESSAGES`; final `error_message` removal; "every code has a template" test | `plugins/template_narrator.py` + `tests/test_plugins/test_template_narrator.py` + `tests/test_plugins/test_narrator.py` | ~300 | Low |

Total: ~1250 lines across 5 PRs, each under the 400-line budget. Slice
L4 is the highest-risk (death-vs-block behaviour change) and is the
ONLY slice that could plausibly need a `coverage run` checkpoint
mid-slice. Strict TDD per slice: red → green → refactor before opening
the next PR.

## Resolved Decisions Summary (sdd-spec framing check)

**Pre-decided by user in this session** (do not revisit):
`messages` section keyed by `error_code`; `movement_verbs` and
`system_commands` sections; engine emits `code + data` only;
narrator owns text; orchestrator's vocabulary is injected; death-vs-block
fix is in scope as a prerequisite; `"limbo"` label becomes a narrator
concern; `EPISODE_COMPLETED` constant replaces string literal; dead
ternaries removed; English dev diagnostics removed (staged).

**Resolved by this proposal**: payload shape is `error_code + data`
(no `message` key); new event types are NOT introduced (existing
`error_output` / `system_message` carry the codes); `system_commands["switch"]`
is a prefix (special-cased); engine codes are flat (no namespace);
`error_message` is staged-removed.

**sdd-spec to confirm framing**: exact `VocabularyYAML` schema for the
3 new sections, exact list of every `error_code` the engine emits
and the `data` keys for each, exact `MacroGateResult` shape and the
mapping of `is_fatal` (5 cases × 2 outcomes = 10 parametrized
cases), exact `OperatorResult` shape and the per-operator
code-data catalogue, exact `DEFAULT_SPANISH_MESSAGES` keys and
template strings, exact `protagonists_listed` payload when
`spatial_anchor is None` (the narrator's job), and the precise
per-test counts in Success Criteria.
