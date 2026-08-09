# Dual Graph — Bidirectional macro edges (delta)

## Purpose

Complete the specified bidirectional semantics for macro edges: an edge declared `direction: bidirectional` MUST be traversable in both directions with equivalent gate semantics.

## MODIFIED Requirements

### Requirement: Structured macro-gate result

For `direction == "bidirectional"`, the macro graph MUST allow both directions and preserve predicates/outcomes. `unidirectional` edges MUST NOT gain reverse routes. A dedicated round-trip test and a follow-up issue MUST be provided.

#### Scenario: Round trip
- **GIVEN** a loaded bidirectional edge
- **WHEN** the protagonist crosses it and returns through the same passage
- **THEN** both movements succeed with equivalent gate semantics

#### Scenario: Unidirectional stays one-way
- **GIVEN** a loaded unidirectional edge
- **WHEN** the protagonist attempts the reverse route
- **THEN** the reverse movement is not available

#### Scenario: Text gate failure carries code and data
- **GIVEN** a closed bidirectional text gate
- **WHEN** the wrong text is supplied in either direction
- **THEN** the failure carries the gate code and data, with no movement or death

#### Scenario: Correct text unlocks
- **GIVEN** a closed bidirectional text gate
- **WHEN** the correct text is supplied from either side
- **THEN** the gate opens and both directions become traversable
