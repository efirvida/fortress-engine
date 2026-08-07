# Plugin Contracts Specification

## Purpose

Keep parsing and narration replaceable while supplying only the minimal engine-core implementations.

## Requirements

### Requirement: Stable parser and narrator ABCs

`ParserInterface` SHALL be an ABC exposing `parse(raw_text: str, world_state: WorldState) -> ParsedCommand`. `NarratorInterface` SHALL be an ABC exposing `narrate(result: Any, world_state: WorldState) -> str`. Implementations SHALL be swappable without engine changes and SHALL be discoverable through plugin entry points rather than hardcoded world imports.

#### Scenario: Custom parser substitution

- GIVEN a parser implementation returning a valid `ParsedCommand`
- WHEN it is injected into `TurnOrchestrator`
- THEN the orchestrator uses it without depending on a concrete parser class

### Requirement: Minimal stubs

The minimal parser stub SHALL parse `IR <door>` into movement intent and `EXAMINAR <target>` into examination intent, and SHALL return graceful `error_output` data for unknown input. The narrator stub SHALL be a no-op/minimal implementation that does not encode template mappings.

#### Scenario: Supported parser inputs

- GIVEN `"ir norte"` or `"examinar puerta"`
- WHEN the stub parser parses it
- THEN it returns a normalized `ParsedCommand` with verb and target/direction data

#### Scenario: Unknown input is graceful

- GIVEN `"xyzzy"`
- WHEN the stub parser parses it
- THEN it returns a structured error result suitable for `error_output` and does not raise an uncaught exception

## Contract notes

`ParsedCommand` is a dataclass with `subject`, `verb`, `target`, `context=None`, and `instrument=None`. Full 37-verb parsing and template narration are out of scope.
