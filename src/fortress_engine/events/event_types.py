"""EngineEvent frozen dataclass, factory, serialization, and event type constants.

Follows event-system spec and 13-event-system.md §2–3.
"""

from __future__ import annotations

import time as _time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Event type constants (34 events, 6 categories — 13-event-system.md §2)
# ---------------------------------------------------------------------------

# World events — §2.1
WORLD_LOADED: str = "world_loaded"
EPISODE_STARTED: str = "episode_started"
EPISODE_COMPLETED: str = "episode_completed"
EPISODE_TRANSITION: str = "episode_transition"
GAME_COMPLETED: str = "game_completed"
GAME_OVER: str = "game_over"

# Turn events — §2.2
TURN_STARTED: str = "turn_started"
INPUT_RECEIVED: str = "input_received"
ACTION_ATTEMPTED: str = "action_attempted"
ACTION_RESOLVED: str = "action_resolved"
ENTITY_TURN_STARTED: str = "entity_turn_started"
ENTITY_TURN_ENDED: str = "entity_turn_ended"
TURN_ENDED: str = "turn_ended"

# State-change events — §2.3
ENTITY_TRANSFERRED: str = "entity_transferred"
ENTITY_TRANSFORMED: str = "entity_transformed"
ENTITY_COMBINED: str = "entity_combined"
FLAG_SET: str = "flag_set"
ENTITY_TELEPORTED: str = "entity_teleported"

# Narration events — §2.4
ENTITY_ENTERED: str = "entity_entered"
ENTITY_DESCRIBED: str = "entity_described"
ENTITY_EXAMINED: str = "entity_examined"
INVENTORY_LISTED: str = "inventory_listed"
PROTAGONISTS_LISTED: str = "protagonists_listed"
ACTION_OUTPUT: str = "action_output"
ERROR_OUTPUT: str = "error_output"
SYSTEM_MESSAGE: str = "system_message"

# Entity events — §2.5
ENTITY_ACTED: str = "entity_acted"
ENTITY_OUTPUT: str = "entity_output"
ENTITY_DESTROYED: str = "entity_destroyed"

# Meta-game events — §2.6
GAME_SAVED: str = "game_saved"
GAME_LOADED: str = "game_loaded"
PROTAGONIST_SWITCHED: str = "protagonist_switched"
SAVE_REPLAY_STARTED: str = "save_replay_started"
SAVE_REPLAY_ENDED: str = "save_replay_ended"


# ---------------------------------------------------------------------------
# Event categories (34 events in 6 categories — 13-event-system.md §2)
# ---------------------------------------------------------------------------

EVENT_CATEGORIES: dict[str, list[str]] = {
    # World events — §2.1
    "world": [
        WORLD_LOADED,
        EPISODE_STARTED,
        EPISODE_COMPLETED,
        EPISODE_TRANSITION,
        GAME_COMPLETED,
        GAME_OVER,
    ],
    # Turn events — §2.2
    "turn": [
        TURN_STARTED,
        INPUT_RECEIVED,
        ACTION_ATTEMPTED,
        ACTION_RESOLVED,
        ENTITY_TURN_STARTED,
        ENTITY_TURN_ENDED,
        TURN_ENDED,
    ],
    # State-change events — §2.3
    "state_change": [
        ENTITY_TRANSFERRED,
        ENTITY_TRANSFORMED,
        ENTITY_COMBINED,
        FLAG_SET,
        ENTITY_TELEPORTED,
    ],
    # Narration events — §2.4
    "narration": [
        ENTITY_ENTERED,
        ENTITY_DESCRIBED,
        ENTITY_EXAMINED,
        INVENTORY_LISTED,
        PROTAGONISTS_LISTED,
        ACTION_OUTPUT,
        ERROR_OUTPUT,
        SYSTEM_MESSAGE,
    ],
    # Entity events — §2.5
    "entity": [
        ENTITY_ACTED,
        ENTITY_OUTPUT,
        ENTITY_ENTERED,
        ENTITY_DESTROYED,
    ],
    # Meta-game events — §2.6
    "meta_game": [
        GAME_SAVED,
        GAME_LOADED,
        PROTAGONIST_SWITCHED,
        SAVE_REPLAY_STARTED,
        SAVE_REPLAY_ENDED,
    ],
}


# ---------------------------------------------------------------------------
# EngineEvent
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineEvent:
    """Immutable event emitted by the engine.

    Attributes:
        event_id: Global unique identifier (UUID4).
        type: Event type string from the taxonomy in 13-event-system.md §2.
        turn_number: Turn when the event was emitted.
        timestamp: time.monotonic() for monotonic ordering.
        payload: Type-specific data dict (JSON-compatible primitives only).
        protagonist_id: Related protagonist, or None for global events.
        episode_id: Current episode, or None if before/after episode context.
    """

    event_id: UUID
    type: str
    turn_number: int
    timestamp: float
    payload: dict[str, Any]
    protagonist_id: str | None = None
    episode_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        turn_number: int,
        payload: dict[str, Any],
        protagonist_id: str | None = None,
        episode_id: str | None = None,
    ) -> EngineEvent:
        """Factory: create an EngineEvent with a fresh UUID4 and monotonic timestamp."""
        return cls(
            event_id=uuid4(),
            type=event_type,
            turn_number=turn_number,
            timestamp=_time.monotonic(),
            payload=payload,
            protagonist_id=protagonist_id,
            episode_id=episode_id,
        )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def event_to_dict(event: EngineEvent) -> dict[str, Any]:
    """Serialize an EngineEvent to a JSON-compatible dict."""
    return {
        "event_id": str(event.event_id),
        "type": event.type,
        "turn_number": event.turn_number,
        "timestamp": event.timestamp,
        "payload": event.payload,
        "protagonist_id": event.protagonist_id,
        "episode_id": event.episode_id,
    }


def event_from_dict(data: dict[str, Any]) -> EngineEvent:
    """Deserialize a dict (from event_to_dict) back to an EngineEvent."""
    return EngineEvent(
        event_id=UUID(data["event_id"]),
        type=data["type"],
        turn_number=data["turn_number"],
        timestamp=data["timestamp"],
        payload=data["payload"],
        protagonist_id=data.get("protagonist_id"),
        episode_id=data.get("episode_id"),
    )
