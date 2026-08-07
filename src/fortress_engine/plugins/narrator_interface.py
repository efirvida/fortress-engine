"""Narrator interface ABC — contract for narrator plugins.

Follows plugin-contracts spec and tdd.md §4.14.
The MinimalNarrator implementation arrives in Slice E2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.events.event_bus import EventBus
    from fortress_engine.events.event_types import EngineEvent
    from fortress_engine.engine.state import WorldState


class NarratorInterface(ABC):
    """Abstract narrator that produces output from engine events."""

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
