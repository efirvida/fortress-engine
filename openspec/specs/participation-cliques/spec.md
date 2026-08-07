# Participation Cliques Specification

## Purpose

Validate whether parsed participants satisfy a HyperEdge and select the highest-priority valid action.

## Requirements

### Requirement: Clique contract and predicates

`Clique` SHALL be a dataclass with `subject`, `verb`, `target`, `instrument`, `context`, `instrument_not`, `instrument_any=False`, `flag=None`, `flag_not=None`, and `component: dict[str, Any] | None`. `validate_clique` SHALL enforce presence/location, exact verb, flags, instrument predicates, wildcards, and raw component equality.

#### Scenario: Resolve player and component

- GIVEN `subject="player"`, active protagonist `p1`, and target component `state="open"`
- WHEN the parsed command and state satisfy location and component equality
- THEN the Clique validates true and `player` resolves to `p1`

#### Scenario: Reject absent or forbidden instrument

- GIVEN an instrument absent from room/inventory, or equal to `instrument_not`
- WHEN the Clique is validated
- THEN it returns false

### Requirement: Wildcard and priority behavior

`target="*"` and `instrument="*"` SHALL match any appropriate entity in the current room or active protagonist inventory. `instrument_any=True` SHALL require at least one portable inventory item. Edges sharing `(verb, target)` SHALL be tried in descending priority, first valid wins.

#### Scenario: Fallback selection

- GIVEN priority 10 requires a missing sword and priority 0 accepts any instrument
- WHEN candidates are evaluated
- THEN priority 0 is selected only if its wildcard predicate forms

## Contract notes

`HyperEdge` is a dataclass with `hyper_edge_id: str`, `name: str`, `priority: int`, `clique: Clique`, `operators: list[dict[str, Any]]`, and `output: str | None`. `Clique` fields use `str | None` except `instrument_any: bool = False` and `component: dict[str, Any] | None = None`.

The engine MUST NOT implement cooperative multi-protagonist turn execution in v1.0, but the Clique data shape MAY represent additional participants.
