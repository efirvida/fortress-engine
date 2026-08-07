# World Loading Specification

## Purpose

Load a multi-file YAML world into runtime dataclasses while keeping Pydantic validation at load time only.

## Requirements

### Requirement: Recursive validated loading

`EntityLoader` SHALL scan `world_path` recursively, load `world.yaml` before entity and graph data, validate YAML with Pydantic models, and convert validated data to dataclasses. It MUST report validation and integrity errors rather than silently accepting malformed data.

#### Scenario: Load nested action files

- GIVEN a world containing `world.yaml`, room/entity files, and an action YAML nested below `actions/bonus/`
- WHEN `load_episode_data(episode_id, episode)` runs
- THEN the result includes rooms, items, NPCs, macro edges, and the nested HyperEdge

#### Scenario: Reject malformed YAML schema

- GIVEN an entity YAML missing `entity_id`
- WHEN its loader method is called
- THEN a validation error identifies the invalid input and no partial runtime entity is returned

### Requirement: Public loader contract

The loader SHALL expose the exact methods `load_world_config() -> dict[str, Any]`, `load_episodes() -> list[Episode]`, `load_shared_entities(episode_id: str) -> list[Entity]`, `load_rooms(episode_id: str) -> list[Entity]`, `load_items(episode_id: str) -> list[Entity]`, `load_npcs(episode_id: str) -> list[Entity]`, `load_macro_edges(episode_id: str) -> list[MacroEdge]`, `load_hyper_edges(episode_id: str) -> list[HyperEdge]`, `load_episode_data(episode_id: str, episode: Episode) -> dict[str, Any]`, and `validate_world() -> list[str]`.

#### Scenario: Detect dangling references

- GIVEN an action references an entity absent from the loaded world
- WHEN `validate_world()` runs
- THEN its returned error list contains a dangling-reference diagnostic

## Contract notes

`EntityYAML`, `CliqueYAML`, `HyperEdgeYAML`, and `MacroEdgeYAML` are Pydantic load schemas. `MacroEdgeYAML` models only generic predicate fields (`question`, `requires_text`, `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`, `death_message`) and sets `extra="forbid"`, so a world YAML that still writes a legacy connection-type/password/answer field fails loudly at load time instead of being silently dropped. Pydantic models MUST NOT enter runtime state, operator results, or event payloads.
