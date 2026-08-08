# World YAML Extensions — Vocabulary Sections Specification (delta)

## Purpose

Extend the `Vocabulary` runtime dataclass and `VocabularyYAML` Pydantic model (from Epic #3) with three optional language sections: `messages`, `movement_verbs`, `system_commands`. Back-compat is automatic: absent sections default to empty and the engine applies in-code defaults.

## MODIFIED Requirements

### Requirement: Vocabulary gains messages, movement_verbs, system_commands

`VocabularyYAML` SHALL gain three optional fields: `messages: dict[str, str]`, `movement_verbs: list[str]`, `system_commands: dict[str, list[str]]`. `Vocabulary` SHALL mirror them. `extra="forbid"` SHALL be preserved so typos still fail loudly, but missing keys MUST NOT fail loading.

```yaml
# worlds/<name>/shared/vocabulary.yaml (new sections, all optional)
messages:
  error_output.no_action: "No entiendes cómo hacer '{verb}' aquí."
  error_output.blocked: "No puedes ir por ahí."
  error_output.too_heavy: "Sería demasiado peso."
movement_verbs:
  - "ir"
  - "abrir"
system_commands:
  save:    ["guardar", "save"]
  load:    ["cargar", "load"]
  quit:    ["terminar", "abandonar", "quit"]
  wait:    ["esperar", "wait"]
  group:   ["grupo", "group"]
  switch:  ["cambiar a"]
```

#### Scenario: Sections present

- GIVEN a vocabulary.yaml with `messages`, `movement_verbs`, and `system_commands`
- WHEN `EntityLoader.load_vocabulary` loads it
- THEN the `Vocabulary` exposes all three with the declared values

#### Scenario: Sections absent (back-compat)

- GIVEN an existing vocabulary.yaml (Epic #3 shape, no new sections)
- WHEN it is loaded
- THEN loading succeeds, the three new fields are empty, and the engine's in-code defaults apply

#### Scenario: Unknown section rejected

- GIVEN a vocabulary.yaml with a misspelled section name
- WHEN it is loaded
- THEN loading fails loudly (`extra="forbid"`)

## Contract notes

The `switch` surface form is a prefix (`"cambiar a"`); the orchestrator strips it to extract the protagonist name.

## ADDED Requirements

### Requirement: Fortaleza gates and instruments resolved

The Fortaleza world data SHALL resolve the five placeholder sites: `Abrete Sesamo`, `Nombus Rostomelaris`, `Luz`, `Agua`, plus `Ariete` as the wall-breaker without a spurious text gate. It SHALL support `abrir`, wire world vocabulary into parsing, place `antorcha_3` for the curated sequence, and use capacity 40.

#### Scenario: Corrected gates open

- GIVEN corrected YAML is loaded and validated
- WHEN the canonical script reaches the affected gates
- THEN gates open with the decoded passwords and the wall breaks with `Ariete`

### Requirement: Part II original model

Part II MUST model Hacha → árbol de marfil → Maza (37) → muralla → `otra_orilla_del_rio_negro`; `marmidosa` remains for esfera, carcelero, and hechicero; muralla 3 remains a decoy.

#### Scenario: Maza chain produces the wall break

- GIVEN corrected Part II YAML is loaded
- WHEN the script breaks the ivory tree with Hacha, takes Maza, and breaks the wall
- THEN Maza is created and transferred within capacity 40, the wall opens to `otra_orilla_del_rio_negro`, and `muralla_rota` is set

### Requirement: Supported goal shape

Episode goal conditions MUST use the supported atomic condition shape (implicit AND); the loader MUST NOT emit an unsupported composite `type: and` condition that the evaluator rejects. Validated during load.

#### Scenario: Goal evaluates

- GIVEN flattened episode goals
- WHEN the goal evaluator checks progress
- THEN conditions evaluate correctly and the episode goal can become `True`
