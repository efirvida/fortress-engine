# World YAML Extensions Specification

## Purpose

Define world-declared language, plugins, and per-world vocabulary for TDD §4.15, §9.2, and GDD §3.1–§3.2.

## ADDED Requirements

### Requirement: Validate plugin configuration and language

`WorldYAML` MUST provide `language: str = "es"`, parser, and narrator configuration. `PluginConfigYAML` MUST accept `plugin` plus optional `options: dict[str, Any]`; legacy bare strings MUST coerce to the same model. Invalid plugin values MUST be rejected at load time.

#### Scenario: Parse both configuration forms

- GIVEN object-form parser/narrator fields or legacy strings
- WHEN `WorldYAML` is validated
- THEN both normalize to plugin configuration objects and absent fields default to usable Spanish configurations

### Requirement: Load per-world vocabulary

The loader MUST expose a `Vocabulary` dataclass containing verbs and synonyms, stopwords, prepositions, speech markers, and language. `load_vocabulary(world_path)` MUST read `world_path/shared/vocabulary.yaml`; a missing file MUST allow the parser's default cascade.

#### Scenario: Load vocabulary data

- GIVEN a valid `shared/vocabulary.yaml`
- WHEN vocabulary is loaded
- THEN all five vocabulary sections and their language are available as typed runtime data

#### Scenario: Default language

- GIVEN a world without `language`
- WHEN its YAML model is loaded
- THEN `language` is `"es"` and plugin construction can receive that value
