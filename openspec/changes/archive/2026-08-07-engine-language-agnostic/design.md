# Design: engine-language-agnostic

## Technical Approach

The engine stops constructing user-facing text and stops assuming command words. It emits flat `error_code` + `data` for every failure; the narrator renders text from a `messages` dict (world vocabulary or `DEFAULT_SPANISH_MESSAGES`). Movement verbs and system command words come from the injected `Vocabulary`; the parser and narrator interfaces are untouched.

```text
input ──► parser (canonical verb tokens)
            │
            ▼
   orchestrator ── vocabulary.movement_verbs ──► movement? → graph.validate_macro_edge → MacroGateResult(is_valid, is_fatal, gate_code, data)
            │                    │
            │                    └─ system_commands ──► system command? → handlers (save/load/quit/wait/group/switch-prefix)
            │
            ├─ no clique ──► error_output {error_code: no_action, data: {verb}}
            ├─ operator fail ─► error_output {error_code: operator_failed, data: {op_code, ...}}
            │
            ▼
   narrator.handle_event ── messages[error_output.<code>].format(**data) ──► player text
```

## Architecture Decisions

| Decision | Choice and rationale |
|---|---|
| Text ownership | Engine emits `error_code` + `data`; narrator renders from `messages` (world vocabulary or `DEFAULT_SPANISH_MESSAGES`). No `message` payload key ever emitted by the engine. |
| Code namespace | Flat codes, no namespace — matches the existing `error_code` field; narrator keys templates by the flat code. |
| Movement | Orchestrator reads `vocabulary.movement_verbs` (default `{"ir", "abrir"}`) instead of hardcoded `("ir", "abrir")`. Parser unchanged. |
| System commands | Orchestrator reads `vocabulary.system_commands` (default Spanish set) instead of `_SYSTEM_COMMANDS`/`_SYSTEM_PREFIXES`. `switch` remains a PREFIX command (strip `"cambiar a "`-equivalent surface). |
| Death-vs-block | `MacroGateResult.is_fatal` replaces string equality `death_msg == edge.death_message`. |
| `OperatorResult` | `code` + `data` only; `error_message` removed immediately (user decision). |
| `system_message` | `code` only, no `message` back-compat (user decision). |
| Vocabulary back-compat | New sections optional; `extra="forbid"` preserved; absent → engine defaults. |

## Module Design

### `engine/graph.py` — MacroGateResult

```python
@dataclass(frozen=True)
class MacroGateResult:
    is_valid: bool
    is_fatal: bool          # True iff edge.death_message is not None
    gate_code: str          # "" when is_valid; one of the 5 codes otherwise
    data: dict[str, object] # passage_name, required_text, required_item, required_flag
```

`validate_macro_edge(edge, state, text) -> MacroGateResult`:

| Gate | gate_code | data keys |
|---|---|---|
| text gate closed | `text_closed` | `passage_name`, `required_text` |
| requires_item missing | `requires_item` | `passage_name`, `required_item` |
| forbids_item present | `forbids_item` | `passage_name`, `forbids_item` |
| requires_flag missing | `requires_flag` | `passage_name`, `required_flag` |
| forbids_flag present | `forbids_flag` | `passage_name`, `forbids_flag` |

`is_fatal = edge.death_message is not None`. On success: `is_valid=True, is_fatal=False, gate_code="", data={"passage_name": ...}`. The 5 Spanish literals are removed. `_normalize_text` stays (generic NFKD — not language-specific).

### `engine/operators.py` — OperatorResult code

```python
@dataclass(frozen=True)
class OperatorResult:
    success: bool
    code: str | None = None
    data: dict[str, object] = dc_field(default_factory=dict)
    events_payload: dict[str, Any] | None = None
    # error_message: REMOVED (user decision)
```

Per-operator failure → flat code + data:

| Operator | Failure | code | data |
|---|---|---|---|
| TRANSFER | entity missing | `entity_not_found` | `{entity_id}` |
| TRANSFER | wrong from_container | `entity_not_in_container` | `{entity_id, container_id}` |
| TRANSFER | to_container missing | `container_not_found` | `{container_id}` |
| TRANSFER | non-portable item | `not_portable` | `{entity_id}` |
| TRANSFER | item heavier than capacity | `not_portable` | `{entity_id, item_weight, max_capacity}` |
| TRANSFER | inventory would exceed capacity | `too_heavy` | `{entity_id, current_weight, item_weight, max_capacity}` |
| TRANSFORM | entity missing | `entity_not_found` | `{entity_id}` |
| TRANSFORM | value mismatch | `transform_component_missing` | `{entity_id, component}` |
| COMBINE | input missing | `combine_inputs_missing` | `{input_entity_id}` |
| COMBINE | output missing | `combine_inputs_missing` | `{output_entity_id}` |
| FLAG | — | — (always succeeds) | — |
| TELEPORT | entity missing | `teleport_entity_not_found` | `{entity_id}` |
| TELEPORT | anchor missing | `teleport_anchor_not_found` | `{to_anchor}` |
| dispatch | unknown type | `unknown_operator` | `{op_type}` |
| dispatch | unhandled (unreachable) | `unhandled_operator` | `{op_type}` |

`_MSG_NOT_PORTABLE` / `_MSG_TOO_HEAVY` removed. All English `f"Entity 'X' not found"` diagnostics removed — `data` carries ids; narrator renders.

### `engine/orchestrator.py` — vocabulary-driven, code+data only

**Constructor**: `__init__(..., vocabulary: Vocabulary | None = None)` stored as `self._vocabulary`.

**Defaults** (module constants, replacing `_SYSTEM_COMMANDS`/`_SYSTEM_PREFIXES`):

```python
DEFAULT_MOVEMENT_VERBS: frozenset[str] = frozenset({"ir", "abrir"})
DEFAULT_SYSTEM_COMMANDS: dict[str, list[str]] = {
    "save":   ["guardar", "save"],
    "load":   ["cargar", "load"],
    "quit":   ["terminar", "abandonar", "quit"],
    "wait":   ["esperar", "wait"],
    "group":  ["grupo", "group"],
    "switch": ["cambiar a"],   # prefix command
}
```

Vocabulary accessors:
- `self._movement_verbs()` → `frozenset(self._vocabulary.movement_verbs)` if set else `DEFAULT_MOVEMENT_VERBS`
- `self._system_commands()` → `self._vocabulary.system_commands` if set else `DEFAULT_SYSTEM_COMMANDS`

**`_resolve_movement`**: `if parsed.verb not in self._movement_verbs() or parsed.target is None: return None`.

**`_detect_system_command`** (replaces L545-559): build a flat surface→kind map from `self._system_commands()`:
- For each kind, for each surface word: exact equality match; if the word is the `switch` surface, also match as PREFIX (strip the surface + trailing space to extract the name). Longest-surface-first ordering avoids `"cambiar a"` prefix collisions. Return the canonical kind (`save`/`load`/`quit`/`wait`/`group`/`switch`).

**`_handle_system_command`**: switch on canonical kinds:
- `quit` → `GAME_OVER {reason: "player_quit"}`
- `save` / `load` → existing logic, but `no_repository`/`invalid_slot`/`missing_slot` emit `{error_code, data}` only; dead ternaries removed
- `switch` → name extraction uses the vocabulary surface (strip the matched prefix), not the literal `"cambiar a "`
- `wait` → no-op turn
- `group` → `protagonists_listed` with `location: ent.spatial_anchor` (may be `None` — no `"limbo"` literal)

**`_parse_save_slot`**: keep slot codes `slot_1/2/3`; the prefix to strip comes from the vocabulary surfaces (or defaults). Bare command → `slot_1`; non-numeric → `slot_1`; out-of-range → `None`.

**Movement handler (`_handle_movement`)**: consumes `MacroGateResult`:

```python
gate = self._graph.validate_macro_edge(edge, state, text)
if not gate.is_valid:
    if gate.is_fatal:
        emit(GAME_OVER, {"reason": "player_death", ...})   # death via is_fatal, no string compare
    else:
        emit(ERROR_OUTPUT, {"error_code": "blocked", "data": {**gate.data, "gate_code": gate.gate_code}, "protagonist_id": ...})
```

Note: `reason` for `GAME_OVER` on death is `"player_death"` (a stable code); the world-authored `death_message` flows in `gate.data["death_message"]` so the narrator can render it (the narrator's `game_over` handler already formats `{reason}`).

**Every error_output emission** (9 sites) drops `message`, keeps `error_code`, adds `data`:

| Site | error_code | data |
|---|---|---|
| no clique | `no_action` | `{verb, protagonist_id}` |
| operator failed | `operator_failed` | `{op_code: result.code, **result.data}` (fallback `{}` when no code) |
| movement block | `blocked` | `{passage_name, gate_code, ...gate.data}` |
| save no repo | `no_repository` | `{command: "save"}` |
| load no repo | `no_repository` | `{command: "load"}` |
| save invalid slot | `invalid_slot` | `{slot}` (raw input) |
| load invalid slot | `invalid_slot` | `{slot}` |
| missing slot | `missing_slot` | `{slot}` |
| invalid protagonist | `invalid_protagonist` | `{name}` |

**Code hygiene**: `"episode_completed"` literal → `EPISODE_COMPLETED` constant (import from event_types). Dead ternaries (L588-592, L625-629) removed. `"limbo"` → `None` in `protagonists_listed`. `system_message` emissions (if any exist) use `code` not `message` — check: the orchestrator currently emits NO `system_message` events (save/load emit `GAME_SAVED`/`GAME_LOADED`), so the code-only contract is additive.

### `entities/loader.py` — Vocabulary growth

`VocabularyYAML` (Pydantic) + `Vocabulary` (dataclass) gain three optional fields:

```python
class VocabularyYAML(BaseModel):
    model_config = ConfigDict(extra="forbid")   # preserved
    language: str | None = None
    verbs: dict[str, list[str]] = {}
    stopwords: list[str] = []
    prepositions: dict[str, list[str]] = {}
    speech_markers: list[str] = []
    speech_verbs: list[str] = []
    messages: dict[str, str] = {}                # NEW (optional)
    movement_verbs: list[str] = []               # NEW (optional)
    system_commands: dict[str, list[str]] = {}   # NEW (optional)
```

`Vocabulary` dataclass mirrors them; `load_vocabulary` carries them through; absent sections default to empty (back-compat, no migration).

### `plugins/template_narrator.py` — messages dispatch

**Constructor**: `__init__(language="es", templates=None, messages: dict[str, str] | None = None)` — `self._messages = dict(DEFAULT_SPANISH_MESSAGES)` then update with `messages` if provided.

**`DEFAULT_SPANISH_MESSAGES`** (in-code, keyed by flat code, placeholders from data):

```python
DEFAULT_SPANISH_MESSAGES: dict[str, str] = {
    "error_output.no_action": "No entiendes cómo hacer '{verb}' aquí.",
    "error_output.blocked": "No puedes ir por ahí.",
    "error_output.no_repository": "Guardar no está disponible.",
    "error_output.invalid_slot": "Ranura inválida. Usá 1, 2, o 3.",
    "error_output.missing_slot": "No hay partida guardada en la ranura {slot}.",
    "error_output.invalid_protagonist": "No se encuentra a '{name}'.",
    "error_output.operator_failed": "No puedes hacer eso.",
    "error_output.text_closed": "{passage_name} está cerrada.",
    "error_output.requires_item": "No puedes pasar por {passage_name} aún.",
    "error_output.forbids_item": "{passage_name} está sellada.",
    "error_output.requires_flag": "No puedes pasar por {passage_name} aún.",
    "error_output.forbids_flag": "{passage_name} está sellada.",
    "error_output.not_portable": "Usted no puede cargar con eso.",
    "error_output.too_heavy": "Sería demasiado peso.",
    "error_output.entity_not_found": "No se encuentra.",
    "error_output.entity_not_in_container": "No está donde lo buscas.",
    "error_output.container_not_found": "No se encuentra el destino.",
    "error_output.transform_component_missing": "No puedes hacer eso.",
    "error_output.combine_inputs_missing": "Faltan objetos para combinar.",
    "error_output.teleport_entity_not_found": "No se encuentra.",
    "error_output.teleport_anchor_not_found": "No puedes ir ahí.",
    "error_output.unknown_operator": "No puedes hacer eso.",
    "error_output.unhandled_operator": "No puedes hacer eso.",
    "system_message.game_saved": "Partida guardada en la ranura {slot}.",
    "system_message.game_loaded": "Partida cargada de la ranura {slot}.",
    "system_message.protagonist_switched": "Ahora controlas a {name}.",
    "system_message.protagonists_listed": "Grupo: {names}.",
}
```

**`_handle_error_output`**:

```python
def _handle_error_output(self, event, world_state):
    code = event.payload.get("error_code", "")
    data = event.payload.get("data", {}) or {}
    key = f"error_output.{code}"
    template = self._messages.get(key) or _FALLBACK_TEXT["error_output"]
    try:
        return template.format(**data)
    except (KeyError, IndexError, ValueError):
        return template   # deterministic fallback, no crash
```

**`_handle_system_message`**: same pattern with `payload["code"]` → `system_message.<code>` key. No `message` key access (code-only, user decision).

**Note**: the existing `error_output`/`system_message` entries in `_DEFAULT_TEMPLATES` (`"{message}"`) are superseded by the messages dispatch; they can remain for back-compat of the generic template mechanism or be removed — design decision: keep `_DEFAULT_TEMPLATES` for the 7 non-error events, remove `error_output`/`system_message` from it (their handlers no longer read `templates`).

## Data Design

Full vocabulary.yaml example (all three sections + Epic #3 sections):

```yaml
# worlds/<name>/shared/vocabulary.yaml
language: "es"
verbs:
  ir: [atravesar, cruzar, pasar]
  tomar: [coger]
  abrir: []
  # ... full 37-verb inventory ...
stopwords: [el, la, los, las, un, una, al, del, por]
prepositions:
  instrument: [con]
  recipient: [a]
speech_markers: [diciendo, respondiendo]
speech_verbs: [decir, responder]
messages:
  error_output.no_action: "No entiendes cómo hacer '{verb}' aquí."
  # ... all DEFAULT_SPANISH_MESSAGES keys, overridable ...
movement_verbs: [ir, abrir]
system_commands:
  save:    [guardar, save]
  load:    [cargar, load]
  quit:    [terminar, abandonar, quit]
  wait:    [esperar, wait]
  group:   [grupo, group]
  switch:  [cambiar a]
```

## Back-compat Design

- Worlds without the new sections: `VocabularyYAML` optional fields default empty; orchestrator uses `DEFAULT_MOVEMENT_VERBS` / `DEFAULT_SYSTEM_COMMANDS`; narrator uses `DEFAULT_SPANISH_MESSAGES`. Existing tests/fixtures load unchanged.
- `TemplateNarrator()` no-arg still works; `messages` param optional.
- `TurnOrchestrator` existing constructions (no vocabulary arg) still work.
- **Tests that assert Spanish literals must be rewritten** — mechanical change to assert `error_code` + `data` instead of the message string:
  - `tests/test_engine/test_orchestrator.py`: `"No entiendes como hacer..."` → assert `error_code == "no_action"` and `data["verb"]`
  - `tests/test_engine/test_orchestrator_save_load.py`: `"Guardar no está disponible."` / `"Ranura inválida..."` / `"No hay partida guardada..."` → assert codes
  - `tests/test_engine/test_graph.py`: gate failure asserts → assert `MacroGateResult` fields
  - `tests/test_engine/test_operators.py`: `error_message` asserts → assert `result.code` / `result.data`
  - `tests/test_plugins/test_template_narrator.py` / `test_narrator.py`: error_output/system_message handler tests → feed `error_code`+`data` payloads, assert rendered message from defaults

## Error Handling

- Unknown `error_code` → narrator returns the fallback template (no crash).
- Unknown vocabulary command surface → `_detect_system_command` returns None → normal parse path → no-action/unknown-verb handling.
- Vocabulary absent → defaults.
- `MacroGateResult` for open edge → `is_valid=True`, no emission.

## Testing Design

| Module | Matrix |
|---|---|
| graph | each gate → MacroGateResult fields; is_fatal True/False; open edge; correct-text unlock; no Spanish literals in module |
| operators | every failure path → code + data; success paths unchanged; no `error_message` attribute |
| orchestrator | movement from custom vocabulary (go/open); system commands from custom vocabulary (save/load/switch-prefix in English); default Spanish preserved; every error_output site → code+data shape; death via is_fatal; blocked via gate data; EPISODE_COMPLETED constant; no "limbo" |
| loader | new sections parse; absent sections back-compat; typo section rejected |
| narrator | error_code dispatch renders defaults; data placeholders; unknown code fallback; system code-only; custom messages override |
| integration | English vocabulary end-to-end turn (go north, save) works without engine changes |

Coverage gate: >99% branch on the full suite; every new branch (unknown code, absent vocabulary, prefix switch, fallback) gets a strict test.

## Slice Alignment (proposal L1-L5)

| Slice | Files | Depends |
|---|---|---|
| L1: vocabulary sections + loader | `entities/loader.py` + tests | — |
| L2: orchestrator vocabulary-driven | `engine/orchestrator.py` + tests | L1 |
| L3: graph MacroGateResult + operators code | `engine/graph.py`, `engine/operators.py` + tests | — (independent of L1/L2; can parallel after L2 or sequence before narrator) |
| L4: narrator messages dispatch | `plugins/template_narrator.py` + tests | L3 (error codes exist) |
| L5: final integration + cleanup | integration tests, remove leftovers | L1-L4 |

Slice L3 must land before L4 (narrator dispatches codes L3 introduces). L2's movement/system change is independent of L3's gate change, but both touch orchestrator.py — sequence L2 → L3 to avoid conflict, or combine carefully. The proposal's slice table is authoritative for ordering; this design confirms L3 before L4.

## Open Questions

None blocking. Minor: `_DEFAULT_TEMPLATES` retains `error_output`/`system_message` keys or removes them (design: remove — handlers no longer read them); verify at L4.
