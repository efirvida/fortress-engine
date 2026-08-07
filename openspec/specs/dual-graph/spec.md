# Dual Graph Specification

## Purpose

Provide indexed macro navigation and room-scoped micro action lookup without embedding world rules.

## Requirements

### Requirement: Indexed dual graph

`DualGraphEngine` SHALL maintain anchors, macro edges indexed by `from_anchor`, and HyperEdges indexed by `(anchor_id, verb)`. It SHALL expose `add_anchor`, `add_macro_edge`, `add_hyper_edge`, `build_macro_graph(anchors, macro_edges)`, `get_edges_from_anchor`, `get_macro_edge_by_door_name`, `get_hyper_edges_for_verb`, `validate_clique`, `validate_macro_edge`, and `resolve_special_values` with the TDD signatures.

#### Scenario: Query room-local actions

- GIVEN two HyperEdges in different rooms and verbs
- WHEN `get_hyper_edges_for_verb("room-1", "examine")` runs
- THEN only matching room and verb edges are returned

#### Scenario: Sort action priority

- GIVEN matching edges with priorities 2 and 10
- WHEN they are queried
- THEN priority 10 precedes priority 2

### Requirement: Macro movement separation

Movement SHALL be resolved through `MacroEdge` evaluation and a TELEPORT operation; macro edges MUST NOT be inserted into the micro HyperEdge index.

#### Scenario: Find outgoing door

- GIVEN a macro edge from `room-1` named `north`
- WHEN `get_macro_edge_by_door_name("room-1", "north")` runs
- THEN that edge is returned and reverse lookup is absent for a unidirectional edge

### Requirement: Six macro connection predicates

`MacroEdge` SHALL be a dataclass with `macro_edge_id`, `connection_type`, `from_anchor`, `to_anchor`, `direction`, `door_name`, `door_description`, optional `password`, `question`, `answer`, `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`, `death_message`, and mutable `open=True`. `connection_type` SHALL support exactly `open`, `password`, `riddle`, `danger`, `danger_inverse`, and `conditional`; `validate_macro_edge(edge, state)` SHALL return `tuple[bool, str | None]`.

#### Scenario: Evaluate danger and conditional edges

- GIVEN a `danger` edge requiring an absent item and a `conditional` edge requiring an unset flag
- WHEN each edge is validated
- THEN both are rejected with their configured failure/death message

#### Scenario: Open edge succeeds

- GIVEN an `open` edge from the protagonist's room
- WHEN it is validated
- THEN it returns `(True, None)`

## Contract notes

`resolve_special_values(clique_value: str | None, state: WorldState) -> str | None` returns `active_protagonist_id` for `"player"`; `"*"` remains a wildcard. No fixed entity-type set is permitted.
