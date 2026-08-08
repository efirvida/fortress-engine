# Template Narrator V1 Specification

## Purpose

Define the data-driven narrator required by TDD §4.16 and PRD §6.

## ADDED Requirements

### Requirement: World-data narration

`TemplateNarrator` MUST expose `language` with default `"es"`, accept `templates: dict[str, str] | None`, and emit designer-provided text without generating prose. It MUST handle `entity_entered`, `action_output`, `error_output`, `episode_completed`, `game_over`, `system_message`, `entity_described`, `entity_examined`, and `inventory_listed`; unrelated events MUST return `None`. Text MUST come from world/event data, with documented fallback text when payload data is absent.

#### Scenario: Narrate the nine supported events

- GIVEN representative payloads for each supported event
- WHEN `handle_event` receives them
- THEN it returns a non-empty string from payload data, world description, a supplied template, or fallback

#### Scenario: Ignore unrelated events

- GIVEN an `entity_transferred` event
- WHEN the narrator handles it
- THEN it returns `None` and does not invent text

### Requirement: Idempotent event subscription

`initialize(event_bus)` MUST subscribe handlers for exactly the nine supported event types and MUST be idempotent when called repeatedly.

#### Scenario: Initialize twice

- GIVEN a narrator and an EventBus
- WHEN `initialize` is called twice
- THEN no duplicate narration occurs for any supported event
