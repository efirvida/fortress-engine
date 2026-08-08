"""Narrator interface ABC — contract for narrator plugins.

Follows plugin-contracts spec and tdd.md §4.14.
The MinimalNarrator implementation is included in this module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.events.event_bus import EventBus
    from fortress_engine.events.event_types import EngineEvent
    from fortress_engine.engine.state import WorldState


# ---------------------------------------------------------------------------
# Events the minimal narrator produces output for
# ---------------------------------------------------------------------------

_NARRATED_EVENTS: frozenset[str] = frozenset({
    "action_output",
    "entity_entered",
    "entity_examined",
    "error_output",
})


class NarratorInterface(ABC):
    """Abstract narrator that produces output from engine events."""

    def __init__(self, language: str = "es") -> None:
        self._language = language

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language code this narrator operates in (e.g. 'es', 'en')."""
        ...

    @abstractmethod
    def initialize(self, event_bus: EventBus) -> None:
        """Register event handlers on the bus."""
        ...

    @abstractmethod
    def handle_event(
        self, event: EngineEvent, world_state: WorldState
    ) -> str | None:
        """Process an engine event and return narration text, or None."""
        ...


class MinimalNarrator(NarratorInterface):
    """Minimal narrator — produces plain text for key narration events.

    Does NOT encode template mappings.  Output is derived directly from
    event payload fields.

    Subscribes to: ``action_output``, ``entity_entered``,
    ``entity_examined``, ``error_output``.

    Returns ``None`` for all other event types.
    """

    def __init__(self, language: str = "es") -> None:
        super().__init__(language)
        self._initialized = False

    @property
    def language(self) -> str:
        """Return the language code for this narrator instance."""
        return self._language

    def initialize(self, event_bus: EventBus) -> None:
        """Subscribe to narrated event types on *event_bus* (idempotent)."""
        if self._initialized:
            return
        self._initialized = True

        # Subscribe a handler for each narrated event type.
        for ev_type in sorted(_NARRATED_EVENTS):
            event_bus.subscribe(ev_type, self._bus_handler)

    def _bus_handler(self, event: EngineEvent) -> None:
        """Bus-side handler — discards return value; bus subscribers
        are fire-and-forget."""
        _ = self.handle_event(event, None)  # type: ignore[arg-type]

    def handle_event(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str | None:
        """Return narration text for key events, or ``None``."""
        if event.type == "action_output":
            text = event.payload.get("text", "")
            return str(text) if text else None

        if event.type == "entity_entered":
            name = event.payload.get("entity_name", "algo")
            return f"Entras en {name}."

        if event.type == "entity_examined":
            desc = event.payload.get("description", "No ves nada especial.")
            return str(desc)

        if event.type == "error_output":
            code = event.payload.get("error_code", "")
            if code:
                return f"({code})"
            return None

        return None
