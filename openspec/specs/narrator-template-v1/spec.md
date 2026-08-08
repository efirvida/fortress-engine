# Template Narrator — Message Dispatch Specification (delta)

## Purpose

Make `TemplateNarrator` the owner of localized text: it dispatches `error_output` templates by flat `error_code` and `system_message` templates by `code`, reading from an injected `messages` dict or the in-code `DEFAULT_SPANISH_MESSAGES`.

## MODIFIED Requirements

### Requirement: Error output dispatches by error_code

`TemplateNarrator.__init__` SHALL accept `messages: dict[str, str] | None = None`. `_handle_error_output` SHALL dispatch on `payload["error_code"]` and format the template with `payload["data"]`. When the code is unknown or `messages` is absent, `DEFAULT_SPANISH_MESSAGES` provides the fallback. The engine no longer sends a `message` key, so the narrator MUST NOT require one.

#### Scenario: Known error code renders

- GIVEN an `error_output` event with `error_code="too_heavy"`, `data={}`
- WHEN the narrator handles it
- THEN it renders `"Sería demasiado peso."` (from messages or default)

#### Scenario: Data placeholders render

- GIVEN an `error_output` event with `error_code="missing_slot"`, `data={"slot": "slot_2"}`
- WHEN the narrator handles it
- THEN it renders the template formatted with the slot value

#### Scenario: Unknown error code falls back

- GIVEN an `error_output` event with an unknown `error_code`
- WHEN the narrator handles it
- THEN it returns a deterministic fallback, not a crash

#### Scenario: No message key required

- GIVEN an `error_output` event with only `error_code` and `data`
- WHEN the narrator handles it
- THEN it still renders text (no `payload["message"]` access)

### Requirement: System message dispatches by code

`_handle_system_message` SHALL dispatch on `payload["code"]` exclusively (user decision: no `message`-payload back-compat). Templates SHALL be keyed like `system_message.<code>`.

#### Scenario: System code renders

- GIVEN a `system_message` event with `code="game_saved"`, `data={"slot": "slot_1"}`
- WHEN the narrator handles it
- THEN it renders the `system_message.game_saved` template formatted with data

### Requirement: System-command feedback events (W4)

`TemplateNarrator` SHALL also subscribe to and render the four system-command feedback event types: `game_saved`, `game_loaded`, `protagonist_switched`, `protagonists_listed`. The handlers SHALL render `system_message.<code>` templates from the event payload; `save_slot` payload keys SHALL alias to `slot`; `protagonists_listed` SHALL build a `names` string from the `protagonists` list. Missing or broken templates SHALL fall back deterministically without crashing.

#### Scenario: Save feedback renders

- GIVEN a `game_saved` event with `payload={"save_slot": "slot_1"}`
- WHEN the narrator handles it
- THEN it renders `"Partida guardada en la ranura slot_1."` (slot aliased from save_slot)

#### Scenario: Switch feedback renders protagonist name

- GIVEN a `protagonist_switched` event with `payload={"name": "Ana"}`
- WHEN the narrator handles it
- THEN it renders a template containing "Ana"

### Requirement: Default Spanish messages constant

`DEFAULT_SPANISH_MESSAGES` SHALL be an in-code dict covering every engine error code and system code, so a world without a `messages` section still renders Spanish text.

#### Scenario: No messages dict provided

- GIVEN a `TemplateNarrator()` with no `messages`
- WHEN it handles a known error code
- THEN it renders the Spanish default

## Contract notes

The `language` property (Epic #3) remains the injection seam; future localized worlds pass a translated `messages` dict and a matching `language`.
