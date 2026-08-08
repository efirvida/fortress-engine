"""EventSourcingSaveSystem — EventBus subscriber that persists state-change events
and provides snapshot-first replay.

TDD §4.11 — the save system bridges the EventBus and the WorldStateRepository,
filtering persistable events and coordinating snapshot-on-save.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from fortress_engine.events.event_types import (
    ENTITY_TRANSFERRED,
    ENTITY_TRANSFORMED,
    ENTITY_COMBINED,
    ENTITY_TELEPORTED,
    FLAG_SET,
    GAME_SAVED,
    SAVE_REPLAY_ENDED,
    SAVE_REPLAY_STARTED,
    EngineEvent,
)

if TYPE_CHECKING:
    from fortress_engine.engine.state import WorldState
    from fortress_engine.events.event_bus import EventBus
    from fortress_engine.persistence.repository import WorldStateRepository


# ---------------------------------------------------------------------------
# Persistable filter — same logic as sqlite_repository._is_persistable
# ---------------------------------------------------------------------------

# State-change events are always persistable.
_STATE_CHANGE_TYPES: frozenset[str] = frozenset(
    {
        ENTITY_TRANSFERRED,
        ENTITY_TRANSFORMED,
        ENTITY_COMBINED,
        FLAG_SET,
        ENTITY_TELEPORTED,
    }
)


def _is_persistable(event: EngineEvent) -> bool:
    """Return True if *event* should be recorded in the event log."""
    etype: str = event.type

    if etype in _STATE_CHANGE_TYPES:
        return True

    if etype == "action_resolved":
        return bool(event.payload.get("has_effects"))

    return False


# ---------------------------------------------------------------------------
# Replay helpers — apply state-change events directly to state
# ---------------------------------------------------------------------------


def _apply_state_change(
    state: WorldState, event: EngineEvent, graph: object | None = None
) -> None:
    """Apply a single state-change event to *state* in place.

    This mutates state WITHOUT emitting through EventBus.  Only the five
    canonical state-change event types are handled; unknown types raise
    ValueError.
    """
    etype = event.type
    payload = event.payload

    if etype == ENTITY_TRANSFERRED:
        entity = state.get_entity(payload["entity_id"])
        entity.spatial_anchor = payload["to_container_id"]

    elif etype == ENTITY_TRANSFORMED:
        entity = state.get_entity(payload["entity_id"])
        entity.components[payload["component_key"]] = payload["new_value"]

    elif etype == ENTITY_COMBINED:
        # Infer anchor from first input entity's current location.
        input_ids: list[str] = payload["input_entity_ids"]
        if input_ids:
            first_input = state.get_entity(input_ids[0])
            anchor = first_input.spatial_anchor
        else:
            anchor = None  # pragma: no cover — unreachable for valid events

        # Destroy inputs (send to limbo).
        for eid in input_ids:
            state.get_entity(eid).spatial_anchor = None

        # Anchor output.
        output = state.get_entity(payload["output_entity_id"])
        output.spatial_anchor = anchor

    elif etype == FLAG_SET:
        state.set_flag(payload["flag_name"], payload["new_value"])

    elif etype == ENTITY_TELEPORTED:
        entity = state.get_entity(payload["entity_id"])
        entity.spatial_anchor = payload["to_anchor_id"]

    else:  # pragma: no cover — dispatch covers all 5 _STATE_CHANGE_TYPES
        raise ValueError(f"Unknown state-change event type: {etype}")


# ---------------------------------------------------------------------------
# EventSourcingSaveSystem
# ---------------------------------------------------------------------------


class EventSourcingSaveSystem:
    """Subscribes to EventBus to persist state-change events and snapshot on save.

    Parameters:
        event_bus: The bus to subscribe to.
        repository: Where events and snapshots are stored.
        state_provider: Optional callable returning the current WorldState.
            Required for snapshot-on-save (the ``game_saved`` handler needs it).
            When absent, ``game_saved`` is a no-op.
    """

    def __init__(
        self,
        event_bus: EventBus,
        repository: WorldStateRepository,
        state_provider: Callable[[], WorldState] | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._state_provider = state_provider

        # Subscribe to all events — persist persistable ones.
        event_bus.subscribe("*", self._on_event)
        # Subscribe to game_saved — snapshot on save.
        event_bus.subscribe(GAME_SAVED, self._on_game_saved)

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _on_event(self, event: EngineEvent) -> None:
        """Wildcard handler: persist persistable events to the event log."""
        if _is_persistable(event):
            self._repository.append_event(event)

    def _on_game_saved(self, event: EngineEvent) -> None:
        """game_saved handler: snapshot current state.

        The *event* payload carries ``save_slot`` (default ``"slot_1"``).
        The actual state is obtained from ``self._state_provider``.
        """
        if self._state_provider is None:
            return

        state = self._state_provider()
        save_slot = event.payload.get("save_slot", "slot_1")
        self._repository.save_snapshot(state, state.turn_number, save_slot)

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay_state(
        self, state: WorldState, save_slot: str, graph: object | None = None
    ) -> WorldState:
        """Load *save_slot* and replay events into *state*.

        Algorithm (design §Replay owner):
          1. Emit ``SAVE_REPLAY_STARTED``.
          2. Load the latest snapshot for *save_slot*.
          3. If a snapshot exists, copy its fields into *state* and set
             ``since_turn`` to the snapshot turn.
          4. Otherwise, start from the current (presumably fresh) state and
             ``since_turn=0``.
          5. Fetch events with ``turn_number > since_turn`` from the log.
          6. Apply each state-change event directly to *state* — **no**
             EventBus re-emission.
          7. Emit ``SAVE_REPLAY_ENDED``.

        Only ``SAVE_REPLAY_STARTED`` and ``SAVE_REPLAY_ENDED`` are emitted
        during replay.  No state-change, narration, or action events are
        re-emitted.

        Returns:
            The mutated *state* (same object).
        """
        # 1. Boundary start.
        self._event_bus.emit(
            EngineEvent.create(
                SAVE_REPLAY_STARTED,
                state.turn_number,
                {"save_slot": save_slot},
            )
        )

        # 2. Load snapshot.
        snapshot = self._repository.load_latest_snapshot(save_slot)

        if snapshot is not None:
            saved_state, snapshot_turn = snapshot
            # Copy snapshot fields into the existing state object.
            state.entities = saved_state.entities
            state.flag_book = saved_state.flag_book
            state.player_controlled_entities = list(
                saved_state.player_controlled_entities
            )
            state.active_protagonist_id = saved_state.active_protagonist_id
            state.current_episode_id = saved_state.current_episode_id
            state.turn_number = saved_state.turn_number
            since_turn = snapshot_turn
        else:
            since_turn = 0

        # 3. Replay tail events (direct mutation, no EventBus).
        events = self._repository.get_event_log(since_turn)
        for event in events:
            if event.type in _STATE_CHANGE_TYPES:
                _apply_state_change(state, event, graph)
            elif event.type == "action_resolved":
                # action_resolved is persistable but has no state effect
                # during replay — skip it.
                pass
            else:
                # Unknown event type in log — corruption.
                from fortress_engine.persistence.repository import (
                    CorruptEventError,
                )
                raise CorruptEventError(
                    str(event.event_id),
                    f"unknown event type '{event.type}' in event log",
                )
            # Update turn_number to track progress.
            if event.turn_number > state.turn_number:
                state.turn_number = event.turn_number

        # 4. Boundary end.
        self._event_bus.emit(
            EngineEvent.create(
                SAVE_REPLAY_ENDED,
                state.turn_number,
                {
                    "save_slot": save_slot,
                    "turn_number": state.turn_number,
                },
            )
        )

        return state
