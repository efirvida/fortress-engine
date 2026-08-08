# Plugin Factory Specification

## Purpose

Define the language-aware entry-point boundary required by TDD §9.2, §9.3, and architecture constant #7.

## ADDED Requirements

### Requirement: Resolve and instantiate plugins

The factory MUST provide frozen `PluginConfig(name, options={})`, `create_parser`, `create_narrator`, and `list_available_plugins`. Only the factory MAY call `importlib.metadata.entry_points`; it MUST resolve the appropriate group and load the named entry point. Missing names MUST raise `PluginNotFoundError`.

#### Scenario: Factory injects language and options

- GIVEN a registered plugin and `PluginConfig(name="classic", options={...})`
- WHEN `create_parser` or `create_narrator` is called with `world_language`
- THEN the loaded class receives `language=world_language` and options as keyword arguments

#### Scenario: Missing plugin

- GIVEN a name absent from the requested entry-point group
- WHEN the factory function is called
- THEN `PluginNotFoundError` is raised and available names support diagnostics

### Requirement: Best-effort compatibility and language warnings

The factory MUST retry construction without an unsupported keyword after a `TypeError`, issuing a warning. It MUST issue `warnings.warn` when a non-empty plugin language differs from `world_language`; V1 MUST NOT raise for this mismatch. `strict_language` remains deferred to v1.1 through `PluginConfig.options`.

#### Scenario: Legacy plugin and mismatch

- GIVEN a plugin that rejects `language` or an option
- WHEN construction is attempted
- THEN fallback construction succeeds when possible and warning(s) are emitted
