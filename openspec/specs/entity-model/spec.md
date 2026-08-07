# Entity Model Specification

## Purpose

Define the runtime entity value used by every world. Runtime objects use dataclasses; entity semantics come from components and graph data, not inheritance.

## Requirements

### Requirement: Opaque entity values

The system SHALL provide `Entity` as a dataclass with fields `entity_id: str`, `type: str`, `name: str`, `components: dict[str, Any]`, and `spatial_anchor: str | None`. `type` MUST be treated as an opaque string: the engine MUST NOT define or validate a closed entity-type set. Component values MUST remain opaque and be compared as raw values.

#### Scenario: Preserve arbitrary type and components

- GIVEN an entity with `type="portal"` and components containing a list, integer, boolean, and string
- WHEN it is constructed and inspected
- THEN all values and the opaque type are preserved without engine validation

#### Scenario: Represent limbo or destruction

- GIVEN an entity whose `spatial_anchor` is `None`
- WHEN the engine evaluates its location
- THEN it treats the entity as destroyed or outside a container, without deleting its identity

### Requirement: Runtime composition

The system SHALL express behavior through components and HyperEdges, not entity subclasses or world-specific conditionals.

#### Scenario: Component predicate uses raw equality

- GIVEN `components["tags"] == ["cold", "wet"]`
- WHEN a Clique component predicate expects that list
- THEN validation succeeds only when the raw value compares equal with `==`

## Contract notes

- `Entity` is a stdlib `@dataclass`.
- `components` values are opaque YAML values (including `str`, `int`, `bool`, and `list`); the engine MUST NOT narrow or coerce their types.
- `None` is a valid spatial anchor state; `_limbo` is the reserved room identifier for spawned outputs (defined by the operator contract).
