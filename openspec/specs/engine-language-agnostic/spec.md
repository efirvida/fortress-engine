# Engine Language-Agnostic Specification

## Purpose

Make the engine a pure coordinator that emits structured codes and data, never user-facing text, and never assumes a language for command recognition. The parser and narrator remain the language-aware components; the world vocabulary supplies language-specific data.

## ADDED Requirements

### Requirement: Engine emits codes, narrator owns text

The engine MUST NOT construct or emit any user-facing text string. All `error_output` / `system_message` events SHALL carry a flat `error_code` (or `code`) plus a `data` dict; the narrator SHALL own the rendering. The engine SHALL NOT hardcode movement verbs, system command words, or message literals in any language.

#### Scenario: English world without engine changes

- GIVEN a world vocabulary declaring English movement verbs (`movement_verbs: ["go", "open"]`) and English system commands (`system_commands: {save: ["save"], load: ["load"]}`)
- WHEN the player types `"go north"` and `"save"`
- THEN the engine resolves movement and the save system command correctly without any engine code change

#### Scenario: Spanish default keeps working

- GIVEN a world without the new vocabulary sections
- WHEN the player types `"ir norte"` and `"guardar"`
- THEN the in-code defaults (`DEFAULT_MOVEMENT_VERBS`, `DEFAULT_SYSTEM_COMMANDS`) preserve current Spanish behavior

## ADDED Requirements

### Requirement: Flat error code contract

`error_output` codes SHALL be flat strings with no namespace. The narrator dispatches templates keyed directly by the code. Valid codes include: `parser_error`, `no_action`, `blocked`, `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`, `text_closed`, `operator_failed`, `not_portable`, `too_heavy`, `entity_not_found`, `entity_not_in_container`, `container_not_found`, `transform_component_missing`, `combine_inputs_missing`, `teleport_entity_not_found`, `teleport_anchor_not_found`, `unknown_operator`, `unhandled_operator`, `no_repository`, `invalid_slot`, `missing_slot`, `invalid_protagonist`.

#### Scenario: Narrator dispatches by flat code

- GIVEN an `error_output` event with `error_code: "too_heavy"` and `data: {}`
- WHEN the narrator handles it
- THEN it renders the `messages["error_output.too_heavy"]` template (or a fallback)

## Contract notes

This spec is the umbrella contract for the localization seam. Per-module deltas live in the modified `dual-graph`, `atomic-operators`, `turn-orchestrator`, `world-yaml-extensions`, and `narrator-template-v1` specs.
