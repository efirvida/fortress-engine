# Dual Graph Specification

## Purpose

Provide indexed macro navigation and room-scoped micro action lookup without embedding world rules.

## Requirements

### Requirement: Indexed dual graph

`DualGraphEngine` SHALL maintain anchors, macro edges indexed by `from_anchor`, and HyperEdges indexed by `(anchor_id, verb)`. It SHALL expose `add_anchor`, `add_macro_edge`, `add_hyper_edge`, `build_macro_graph(anchors, macro_edges)`, `get_edges_from_anchor`, `get_macro_edge_by_passage_name`, `get_hyper_edges_for_verb`, `validate_clique`, `validate_macro_edge`, and `resolve_special_values` with the TDD signatures.

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
- WHEN `get_macro_edge_by_passage_name("room-1", "north")` runs
- THEN that edge is returned and reverse lookup is absent for a unidirectional edge

### Requirement: Generic macro edge predicates

`MacroEdge` SHALL be a dataclass with `macro_edge_id`, `from_anchor`, `to_anchor`, `direction`, `passage_name`, `passage_description`, and optional generic predicates `question`, `requires_text`, `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`, `death_message`, and mutable `open=True`. There is NO connection-type field: the world creator decides gate semantics purely by which predicate fields are set, and the engine MUST NOT name or branch on connection-type concepts (password, riddle, danger, etc.). `validate_macro_edge(edge, state, text=None)` SHALL return `tuple[bool, str | None]`; `death_message` is the only fatal-vs-blocked discriminator. A plain edge with no predicates SHALL always be passable.

#### Scenario: Text gate unlocks on correct spoken text

- GIVEN a `requires_text` edge with `open=False`
- WHEN it is validated with the matching text (case- and tilde-insensitive)
- THEN it returns `(True, None)` and flips `open` to `True`; without text or with wrong text it returns `(False, <message>)` and stays closed

#### Scenario: Item gate with and without death_message

- GIVEN a `requires_item` edge whose item is absent
- WHEN it is validated
- THEN without `death_message` it returns `(False, <blocked message>)`; with `death_message` it returns `(False, <death_message>)`

#### Scenario: Forbids-item gate is fatal with the item

- GIVEN a `forbids_item` edge with `death_message`
- WHEN the forbidden item IS in inventory
- THEN it returns `(False, <death_message>)`

#### Scenario: Flag gates block without the required flag

- GIVEN a `requires_flag` edge with an unset flag
- WHEN it is validated
- THEN it returns `(False, <blocked message>)`; setting the flag makes it pass

#### Scenario: Open edge succeeds

- GIVEN a plain edge (no predicates) from the protagonist's room
- WHEN it is validated
- THEN it returns `(True, None)`

## Contract notes

`resolve_special_values(clique_value: str | None, state: WorldState) -> str | None` returns `active_protagonist_id` for `"player"`; `"*"` remains a wildcard. No fixed entity-type set is permitted.
