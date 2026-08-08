# Delta for Plugin Contracts

## MODIFIED Requirements

### Requirement: Stable parser and narrator ABCs

`ParserInterface` SHALL be an ABC exposing `parse(raw_text: str, world_state: WorldState) -> ParsedCommand` and an abstract `language: str` property. `NarratorInterface` SHALL be an ABC exposing `initialize(event_bus)`, `handle_event(event, world_state) -> str | None`, and an abstract `language: str` property. Both interfaces SHALL accept `__init__(language: str = "es")`; implementations SHALL be swappable without engine changes and discoverable through plugin entry points rather than hardcoded world imports. (Previously: the contracts specified parsing and narration but had no language property or constructor contract.)

#### Scenario: Custom parser substitution

- GIVEN a parser implementation returning a valid `ParsedCommand`
- WHEN it is injected into `TurnOrchestrator`
- THEN the orchestrator uses it without depending on a concrete parser class

#### Scenario: Language default and override

- GIVEN a minimal parser or narrator
- WHEN it is constructed with no language or with `language="en"`
- THEN it exposes `language == "es"` by default or `language == "en"` when overridden

### Requirement: Backward-compatible minimal stubs

The minimal parser stub SHALL parse `IR <door>` into movement intent and `EXAMINAR <target>` into examination intent, and SHALL return graceful `error_output` data for unknown input. The narrator stub SHALL be a no-op/minimal implementation that does not encode template mappings. Both stubs MUST accept `language: str = "es"`, expose the selected language, and remain valid no-argument constructions. (Previously: the stubs had minimal behavior but no language constructor/property contract.)

#### Scenario: Supported parser inputs

- GIVEN `"ir norte"` or `"examinar puerta"`
- WHEN the stub parser parses it
- THEN it returns a normalized `ParsedCommand` with verb and target/direction data

#### Scenario: Unknown input is graceful

- GIVEN `"xyzzy"`
- WHEN the stub parser parses it
- THEN it returns a structured error result suitable for `error_output` and does not raise an uncaught exception

#### Scenario: Existing no-argument construction and language override

- GIVEN existing engine code constructing either minimal stub without arguments
- WHEN the stub is used, or is constructed with `language="en"`
- THEN prior behavior continues, with `language == "es"` by default or `language == "en"` when overridden
