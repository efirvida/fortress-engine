# Turn Orchestrator — Vocabulary-Driven Specification (delta)

## Purpose

Remove every Spanish literal and language-coupled command recognition from the orchestrator. The orchestrator becomes a pure coordinator: it reads movement verbs and system commands from the injected vocabulary, emits `error_code` + `data` only, and routes death-vs-block via `is_fatal`.

## MODIFIED Requirements

### Requirement: Vocabulary-injected orchestrator

`TurnOrchestrator.__init__` SHALL accept `vocabulary: Vocabulary | None = None`. When `None`, the in-code defaults apply: `DEFAULT_MOVEMENT_VERBS = {"ir", "abrir"}` and `DEFAULT_SYSTEM_COMMANDS` covering `save`, `load`, `quit`, `wait`, `group`, `switch` with the Spanish surface words (`guardar`, `cargar`, `terminar`, `abandonar`, `esperar`, `grupo`, `cambiar a`).

#### Scenario: Movement from vocabulary

- GIVEN an orchestrator built with a vocabulary declaring `movement_verbs: ["go", "open"]`
- WHEN the player types `"go north"`
- THEN movement resolution matches and the turn proceeds

#### Scenario: System commands from vocabulary

- GIVEN a vocabulary declaring `system_commands: {save: ["save"], load: ["load"], quit: ["quit"], wait: ["wait"], group: ["group"], switch: ["switch to"]}`
- WHEN the player types `"save"` and `"switch to ana"`
- THEN the save system command and the protagonist switch resolve correctly

#### Scenario: Default vocabulary keeps Spanish

- GIVEN an orchestrator with no vocabulary
- WHEN the player types `"ir norte"` and `"guardar"`
- THEN the Spanish defaults apply

### Requirement: Error output carries code and data only

Every `error_output` event SHALL carry `error_code` (flat) and `data` (dict). The `message` payload key SHALL be removed from engine emissions. The nine Spanish literals (`"No entiendes cómo hacer ..."`, `"No puedes ir por ahí."`, `"Guardar no está disponible."`, `"Ranura inválida. Usá 1, 2, o 3."`, `"Cargar no está disponible."`, `"No hay partida guardada en la ranura ..."`, `"No se encuentra a ..."`, `"No puedes hacer eso."`) SHALL be removed. The `operator_failed` fallback SHALL emit `error_code="operator_failed", data={}` when the operator result has no code.

#### Scenario: No-action failure carries verb data

- GIVEN a verb with no matching hyper edge
- WHEN the turn emits `error_output`
- THEN `error_code="no_action"` and `data={"verb": parsed.verb, "protagonist_id": ...}`

#### Scenario: Blocked gate failure carries gate data

- GIVEN a failed movement gate
- WHEN the turn emits `error_output`
- THEN `error_code="blocked"` and `data` includes the gate fields (`passage_name`, `gate_code`, ...) for the narrator to render

### Requirement: Death-vs-block via is_fatal

The orchestrator SHALL route movement failures using `gate.is_fatal` from the `MacroGateResult`, never by string equality with `edge.death_message`.

#### Scenario: Death routes to game_over

- GIVEN a lethal gate failure
- WHEN the turn handles the failed movement
- THEN `GAME_OVER` fires with `reason` from structured data, not a message string

#### Scenario: Block routes to error_output

- GIVEN a non-fatal blocked gate
- WHEN the turn handles the failed movement
- THEN `error_output` fires with `error_code="blocked"` and the gate data

### Requirement: Code hygiene

The `EPISODE_COMPLETED` constant SHALL replace the `"episode_completed"` string literal. The dead ternary branches in save/load no-repository paths SHALL be removed. The `"limbo"` label SHALL be removed — `protagonists_listed` emits `location: spatial_anchor` which may be `None`; the narrator renders the display.

#### Scenario: System message emits code not message

- GIVEN a save/load/switch system notification
- WHEN the orchestrator emits `system_message`
- THEN the payload carries `code` (flat) and `data`, never a `message` text

## Contract notes

The CLI (future epic) constructs the orchestrator with the vocabulary loaded via `EntityLoader.load_vocabulary`. Tests inject custom vocabularies to exercise language-specific recognition.
