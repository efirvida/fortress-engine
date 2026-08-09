# World YAML Extensions — Fortaleza corrections (delta)

## Purpose

Correct the Fortaleza world data so the curated walkthrough is executable and the Part II goal is reachable, while preserving deliberate divergences from the original game.

## ADDED Requirements

### Requirement: Resolved gates and instruments

World data MUST resolve the five affected sites: `Abrete Sesamo`, `Nombus Rostomelaris`, `Luz`, and `Agua`, plus `Ariete` as the wall-breaker without the spurious text gate. It MUST support `abrir`, wire world vocabulary into parsing, place `antorcha_3` for the curated sequence, and use capacity 40.

#### Scenario: Corrected gates open
- **GIVEN** corrected YAML is loaded and validated
- **WHEN** the canonical script reaches the affected gates
- **THEN** gates open with the decoded passwords and the wall breaks with `Ariete`

### Requirement: Part II original model

Part II MUST model Hacha → árbol de marfil → Maza (37) → muralla → `otra_orilla_del_rio_negro`; `marmidosa` remains for esfera, carcelero, and hechicero; muralla 3 remains a decoy.

#### Scenario: Maza chain produces the wall break
- **GIVEN** corrected Part II YAML is loaded
- **WHEN** the script breaks the ivory tree with Hacha, takes Maza, and breaks the wall
- **THEN** Maza is created and transferred within capacity 40, the wall opens to `otra_orilla_del_rio_negro`, and `muralla_rota` is set

### Requirement: Supported goal shape

Episode goal conditions MUST use the supported atomic condition shape (implicit AND); the loader MUST NOT emit an unsupported composite `type: and` condition that the evaluator rejects. Validated during load.

#### Scenario: Goal evaluates
- **GIVEN** flattened episode goals
- **WHEN** the goal evaluator checks progress
- **THEN** conditions evaluate correctly and the episode goal can become `True`
