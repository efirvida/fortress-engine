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
