# Event System Specification

## Purpose

Define immutable event facts and synchronous per-engine Observer dispatch.

## Requirements

### Requirement: Immutable serializable events

`EngineEvent` SHALL be `@dataclass(frozen=True)` with `event_id: UUID`, `type: str`, `turn_number: int`, `timestamp: float`, `payload: dict[str, Any]`, `protagonist_id: str | None`, and `episode_id: str | None`. `create(...)` SHALL use `uuid4()` and `time.monotonic()`.

#### Scenario: Event round trip

- GIVEN an event created with a JSON-compatible payload
- WHEN `event_to_dict` then `event_from_dict` is applied
- THEN UUID, type, turn, timestamp, payload, protagonist, and episode are preserved

#### Scenario: Timestamp contract

- GIVEN a monotonic timestamp serialized as a JSON number
- WHEN it is deserialized
- THEN the float value is preserved for equality/ordering within normal Python JSON round-trip precision; it is not interpreted as wall-clock time or comparable across process restarts

### Requirement: Synchronous isolated bus

`EventBus` SHALL expose `subscribe(event_type, handler)`, `unsubscribe(event_type, handler)`, and `emit(event)`. Dispatch SHALL be synchronous, FIFO by registration, support `"*"`, isolate handler exceptions, and use one bus instance per engine (not a singleton).

#### Scenario: Specific and wildcard delivery

- GIVEN handlers subscribed to `turn_started` and `*`
- WHEN that event is emitted
- THEN both run before `emit` returns

#### Scenario: One failing handler is isolated

- GIVEN the first handler raises and the second appends the event
- WHEN the bus emits
- THEN the second still runs and the exception does not escape

## Contract notes

`EngineEvent.create(event_type: str, turn_number: int, payload: dict[str, Any], protagonist_id: str | None = None, episode_id: str | None = None) -> EngineEvent`; `event_to_dict(event: EngineEvent) -> dict[str, Any]`; and `event_from_dict(data: dict[str, Any]) -> EngineEvent` are required.

Only the orchestrator emits state-change events from operator payloads; narration events are not event-sourcing records.
