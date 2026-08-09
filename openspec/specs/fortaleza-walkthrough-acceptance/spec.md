# Fortaleza Walkthrough Acceptance

## Purpose

Acceptance suite proving the real Fortaleza YAML world completes both episodes via a curated command script derived from `docs/09-walkthrough.md`, and that the game fails safely under invalid input. The walkthrough supplies order, never parser input.

## ADDED Requirements

### Requirement: Curated walkthrough

The suite MUST run curated commands for Part I (129) and Part II (235), using YAML passage names, speech forms, resolved passwords, corrected step 17/18 order, and compressed labyrinth routes. It MUST assert movement, inventory progress, each `goal == True`, transition, no canonical `game_over`, and exactly one `turn_ended` per turn; it MUST NOT parse the document verbatim.

#### Scenario: Canonical completion

- **GIVEN** the world and a fixture
- **WHEN** the curated commands run in order
- **THEN** both goals become `True`, transition occurs, no `game_over` occurs, and every turn has one `turn_ended`

### Requirement: Safe failure and recovery

The suite MUST test each anchor with invalid verbs, wrong/nonexistent objects, incorrect passwords, and non-fatal wrong weapons. Each failure MUST assert exact `error_output` type, `error_code`, and `data`; MUST emit no `game_over`; MUST leave world state unchanged except the turn counter; and permit recovery. Designed deaths MAY occur only at fatal passages.

#### Scenario: Invalid verb or object

- **GIVEN** the protagonist is at a tested anchor
- **WHEN** an unknown verb or absent/nonexistent object is submitted
- **THEN** exact `no_action` output, unchanged world state, one `turn_ended`, and subsequent recovery are observed

#### Scenario: Incorrect password

- **GIVEN** a closed password gate
- **WHEN** the wrong text is supplied
- **THEN** exact blocked output and gate data appear, with no movement, death, or state mutation

#### Scenario: Wrong weapon and designed death

- **GIVEN** a non-fatal guarded action or a documented fatal gate
- **WHEN** a wrong weapon is used
- **THEN** the non-fatal case recovers without `game_over`; the fatal case emits exactly the designed `game_over` and one `turn_ended`

### Requirement: Original-game divergences documented

Documentation MUST explain: crystal door `Agua` and key[42]/43/45, `crunch` versus `Rumpelstinskin`, center weapons, opaque-mirror bone versus Maza, bed, torch placement/count, and muralla 3 decoy.

#### Scenario: Reviewable divergence

- **GIVEN** a reviewer compares the script with `docs/09-walkthrough.md`
- **WHEN** the divergence record is consulted
- **THEN** every deviation has an explicit rationale and is not presented as original-game behavior
