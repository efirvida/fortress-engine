# Atomic Operators — OperatorResult Code Specification (delta)

## Purpose

Give `OperatorResult` a structured failure contract: a flat `code` plus `data`, with no pre-formatted message strings and no English dev-diagnostic leak to the player.

## MODIFIED Requirements

### Requirement: Structured operator failure

`OperatorResult` SHALL gain `code: str | None` and `data: dict[str, object]` fields. The `error_message` field SHALL be removed immediately (user decision — no staged removal). The `_MSG_NOT_PORTABLE` and `_MSG_TOO_HEAVY` module constants SHALL be removed. The five operators SHALL emit flat codes instead of strings: `not_portable`, `too_heavy`, `entity_not_found`, `entity_not_in_container`, `container_not_found`, `transform_component_missing`, `combine_inputs_missing`, `teleport_entity_not_found`, `teleport_anchor_not_found`, `unknown_operator`, `unhandled_operator`, `protagonist_not_found`. English dev diagnostics (e.g. `"Entity 'X' not found"`) SHALL NOT be used as player-visible text. (`flag_readonly` is intentionally absent — the FLAG operator always succeeds and has no failure path.)

```python
@dataclass(frozen=True)
class OperatorResult:
    success: bool
    code: str | None = None
    data: dict[str, object] = dc_field(default_factory=dict)
    events_payload: dict[str, Any] | None = None
    # error_message removed — use code + data
```

#### Scenario: Not-portable vs too-heavy distinguishable

- GIVEN a TRANSFER whose item is not portable
- WHEN the operator runs
- THEN the result has `success=False, code="not_portable"`
- AND a TRANSFER whose inventory would exceed capacity
- THEN the result has `success=False, code="too_heavy"`
- AND the two failures are distinguishable by `code`

#### Scenario: No player-facing diagnostics

- GIVEN an operator failure such as a missing entity
- WHEN the result is produced
- THEN `error_message` does not exist and `data` carries the entity id (`data={"entity_id": ...}`) for the narrator to render

## Contract notes

The orchestrator consumes `result.code` + `result.data` for `error_output`. Test debugging inspects `code` + `data` directly.
