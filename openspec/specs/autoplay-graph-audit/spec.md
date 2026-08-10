# Autoplay Graph Audit Specification

## Purpose

Stage A is deterministic, world-agnostic YAML auditing. It finds disconnection
before puzzle analysis and never plays the world.

## Requirements

### Requirement: Pure typed audit report

`GraphAudit.run()` MUST return an `AuditReport` dataclass containing `episode`,
`declared_rooms`, `reachable_rooms`, `unreachable_rooms`, passive gate data, and
typed findings (`severity`, `category`, `location`, `message`, `data`). It MUST use loader
data only; it MUST NOT construct `WorldState`, `EventBus`, or plugins, or execute turns.
`unreachable_rooms` MUST equal `declared_rooms - reachable_rooms`.

#### Scenario: Static run returns the report seam
- GIVEN a valid YAML world and selected episode
- WHEN `GraphAudit.run()` executes
- THEN it returns the typed report without constructing runtime engine objects

### Requirement: Single structural reachability

The audit MUST perform one BFS from `start_anchor` over all macro edges. Every edge counts
as a path regardless of open state or item, flag, or text predicates; the audit
MUST NOT test conditions or solve puzzles. Missing start yields no rooms and a
`start_anchor_missing` finding.

#### Scenario: A gated path is still structurally reachable
- GIVEN an item/flag/text-protected path from acquisition room C to use room J
- WHEN the audit runs
- THEN every room on that declared path is in `reachable_rooms`, without evaluating its gate

#### Scenario: Disconnected rooms remain unreachable
- GIVEN a declared room with no path from `start_anchor`
- WHEN the audit runs
- THEN it is absent from `reachable_rooms` and present in `unreachable_rooms`

### Requirement: Structural finding catalog

Findings MUST be deterministic and use this catalog:

| Severity | Category — condition → data |
|---|---|
| ERROR | `start_anchor_missing` — start absent → episode/start |
| ERROR | `dangling_edge_endpoint` — edge endpoint is not a room → edge/from/to/missing |
| ERROR | `dangling_spatial_anchor` — non-null entity anchor is absent → episode/entity/anchor |
| ERROR | `isolated_room` — no in/out edge, not start → room |
| WARN | `orphan_room` — no incoming edge, not start → room/outgoing_edges |
| WARN | `unreachable_room` — absent from reachable set → room |
| WARN | `duplicate_passage` — duplicate `(from,to,passage_name)` → tuple/edge_ids |
| WARN | `self_loop_edge` — `from == to` → edge/anchor/passage |
| WARN | `goal_unknown_entity` — goal names unknown entity/room/flag → goal/parameter |
| WARN | `entity_in_unreachable_room` — `spatial_anchor` is unreachable → episode/entity/anchor |
| INFO | `entity_limbo_at_load` — `spatial_anchor` is null → episode/entity |

#### Scenario: Broken fixture preserves severity and identifying data
- GIVEN `audit_broken` contains each ERROR condition and warning shape
- WHEN the audit runs
- THEN each emitted category has the specified severity, location, and identifying data

#### Scenario: Limbo is legal
- GIVEN `audit_limbo` loads an entity with `spatial_anchor: null`
- WHEN the audit runs
- THEN it emits `entity_limbo_at_load` at INFO and never `dangling_spatial_anchor`

### Requirement: Structural integrity keeps gates passive

Gate predicates MUST be copied as passive data in each passage record for Stage B. The
audit MUST NOT judge gate satisfiability, item existence, flag setters, cross-episode
carry-over, or puzzle completion. Goal references MAY produce `goal_unknown_entity` only
when names are absent from loaded structural data; this is data integrity, not evaluation.

#### Scenario: Unknown gate data is not evaluated
- GIVEN a passage with arbitrary item/flag/text predicates and a goal naming an unknown flag
- WHEN the audit runs
- THEN raw predicates are reported unchanged, no gate-specific finding is emitted, and the goal finding identifies the unknown flag

### Requirement: World-agnostic verification

The audit MUST accept arbitrary identifiers and vocabulary. Fixtures MUST include
`audit_happy` (zero findings), `audit_broken`, `audit_disconnected` (unreachable rooms and
entities in them), and `audit_limbo`; tests MUST cover every category and both reachability
branches. CLI tests MUST mirror `test_validate.py`; minimal-world integration MUST be
clean; Fortaleza integration MUST not crash or pin exact findings; branch coverage MUST
exceed 99%.

#### Scenario: Foreign identifiers remain valid
- GIVEN `audit_happy` uses non-Spanish identifiers
- WHEN the audit runs
- THEN it returns zero findings without world-specific assumptions
