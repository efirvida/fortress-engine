# Atomic Operators Specification

## Purpose

Define the five world-agnostic state mutations and their bus-free result contract.

## Requirements

### Requirement: Pure operator results

Each operator SHALL mutate only `WorldState` and return `OperatorResult(success: bool, error_message: str | None = None, events_payload: dict[str, Any] | None = None)`. Operators MUST NOT receive or emit an `EventBus`; `TurnOrchestrator` is the sole state-change event emitter.

#### Scenario: Successful flag is bus-free

- GIVEN a state and `FlagOp(flag="opened", value=True)`
- WHEN `execute_flag(state, op)` runs without an EventBus
- THEN it succeeds, updates the flag, and returns payload data for `flag_set`

#### Scenario: Failed transfer has no state event

- GIVEN an item heavier than the protagonist capacity
- WHEN `execute_transfer(state, op, protagonist_id)` targets that inventory
- THEN it fails with the specified weight message, leaves the anchor unchanged, and returns no successful state-change payload

### Requirement: Five operator contracts

The system SHALL expose `execute_transfer(state, op, protagonist_id)`, `execute_transform(state, op)`, `execute_combine(state, op, anchor_id)`, `execute_flag(state, op)`, `execute_teleport(state, op)`, `operator_from_dict(data)`, and `execute_operator(state, op_data, protagonist_id, graph)`. These implement only TRANSFER, TRANSFORM, COMBINE, FLAG, and TELEPORT.

#### Scenario: Combine spawns from limbo

- GIVEN all inputs are present and output entity is anchored at `_limbo`
- WHEN `execute_combine` runs for `room-2`
- THEN inputs become destroyed (`None`), output anchors to `room-2`, and payload identifies inputs and output

#### Scenario: Transform enforces old value

- GIVEN a component value differs from `old_value`
- WHEN `execute_transform` runs
- THEN it fails and does not change the component

## Contract notes

`LIMBO_ROOM_ID` SHALL be the engine constant with value `"_limbo"`. TRANSFER weight limits apply only when destination is a protagonist inventory; other containers are unrestricted.

`TransferOp` fields are `type="TRANSFER"`, `entity`, `from_container=None`, `to_container=None`; `TransformOp` has `type`, `entity`, `component`, `old_value`, `new_value`; `CombineOp` has `type`, `input_entities`, `output_entity`; `FlagOp` has `type`, `flag`, `value`; and `TeleportOp` has `type`, `entity`, `from_anchor=None`, `to_anchor`.
