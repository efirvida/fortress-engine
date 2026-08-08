# Dual Graph — Macro Gate Result Specification (delta)

## Purpose

Replace the `(bool, str | None)` return of `validate_macro_edge` with a structured result so the engine stops emitting Spanish blocked messages and can distinguish fatal (death) from blocked without string equality.

## MODIFIED Requirements

### Requirement: Structured macro-gate result

`DualGraphEngine.validate_macro_edge` SHALL return a `MacroGateResult` dataclass instead of `(bool, str | None)`.

```python
@dataclass(frozen=True)
class MacroGateResult:
    is_valid: bool
    is_fatal: bool          # True iff edge.death_message is not None
    gate_code: str          # "" when is_valid; one of the 5 gate codes otherwise
    data: dict[str, object] # passage_name, required_text, required_item, required_flag
```

The five gate codes SHALL be flat: `text_closed`, `requires_item`, `forbids_item`, `requires_flag`, `forbids_flag`. The five Spanish literals (`"{passage_name} está cerrada."`, `"No puedes pasar por {passage_name} aún."`, `"{passage_name} está sellada."`) SHALL be removed from the module.

#### Scenario: Text gate failure carries code and data

- GIVEN a closed edge with `requires_text` and no `death_message`
- WHEN the player provides wrong text
- THEN the result is `is_valid=False, is_fatal=False, gate_code="text_closed", data={"passage_name": ...}`

#### Scenario: Lethal gate is fatal

- GIVEN an edge with `death_message` and a failed `requires_item` gate
- WHEN the gate is evaluated
- THEN `is_valid=False, is_fatal=True` and `gate_code="requires_item"`

#### Scenario: Open edge is valid

- GIVEN an edge with no failing predicates
- WHEN the gate is evaluated
- THEN `is_valid=True, is_fatal=False, gate_code=""`

#### Scenario: Correct text unlocks

- GIVEN a closed edge with `requires_text`
- WHEN the player provides the matching text
- THEN the edge flips `open=True` and the result is valid
