# World State Specification

## Purpose

Define the mutable, serializable state container shared by operators, graph validation, goals, and plugins.

## Requirements

### Requirement: Mutable world state and flags

`WorldState` SHALL be a dataclass with `entities: dict[str, Entity]`, `flag_book: dict[str, bool]`, `player_controlled_entities: list[str]`, `active_protagonist_id: str`, `current_episode_id: str`, and `turn_number: int = 0`. The protagonist field MUST always be list-shaped, even with one protagonist.

#### Scenario: Read and mutate state

- GIVEN a state containing an entity and no `alarm` flag
- WHEN `get_entity`, `set_flag("alarm", True)`, and `get_flag("alarm")` are called
- THEN the entity is returned, the flag is stored, and the result is `True`

#### Scenario: Missing flag defaults false

- GIVEN a state with no `unknown` key
- WHEN `get_flag("unknown")` is called
- THEN it returns `False` without mutating the flag book

### Requirement: Snapshot round trip

The system SHALL provide `entity_exists`, `get_entities_in_container`, `get_player_inventory`, `get_inventory_weight`, `to_dict() -> dict[str, Any]`, and `@classmethod from_dict(data: dict[str, Any]) -> WorldState`. Serialization SHALL be JSON-compatible and preserve all state fields and opaque component values.

#### Scenario: Round-trip fidelity

- GIVEN a state with entities, flags, two player IDs, active episode, and turn 7
- WHEN it is converted with `to_dict` and reconstructed with `from_dict`
- THEN the reconstructed state is value-equivalent, including list order and components

## Contract notes

`get_entity` raises `KeyError` for an unknown ID. Inventory weight sums the `weight` component of inventory entities; absent weight contributes zero.
