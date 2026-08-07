"""WorldStateRepository ABC and typed error hierarchy.

TDD §4.9 — the single persistence seam between the engine and storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.events.event_types import EngineEvent
    from fortress_engine.engine.state import WorldState


# ---------------------------------------------------------------------------
# Typed error hierarchy
# ---------------------------------------------------------------------------

class RepositoryError(Exception):
    """Base exception for all repository-level errors."""


class NonPersistableEventError(RepositoryError):
    """Raised when an event cannot be persisted because its type is not in the
    persistable set (e.g. narration events).
    """


class CorruptEventError(RepositoryError):
    """Raised when a persisted event is unreadable or malformed.

    Attributes:
        cause: A short machine-readable tag for the corruption kind.
        event_id: The ``event_id`` of the affected event.
    """

    def __init__(self, event_id: str, cause: str) -> None:
        self.event_id = event_id
        self.cause = cause
        super().__init__(f"{event_id}: {cause}")


class CorruptSnapshotError(RepositoryError):
    """Raised when a saved snapshot cannot be deserialized.

    Attributes:
        save_slot: The slot whose snapshot is corrupted.
        cause: A short description of the deserialisation failure.
    """

    def __init__(self, save_slot: str, cause: str) -> None:
        self.save_slot = save_slot
        self.cause = cause
        super().__init__(f"{save_slot}: {cause}")


class InvalidSlotError(RepositoryError):
    """Raised when a save-slot identifier is not valid (e.g. out of range)."""

    def __init__(self, slot: str) -> None:
        self.slot = slot
        super().__init__(slot)


# ---------------------------------------------------------------------------
# WorldStateRepository ABC
# ---------------------------------------------------------------------------

class WorldStateRepository(ABC):
    """Abstract persistence interface for the engine (PRD §10, GDD §2.6).

    The event log is append-only — there are no ``update_event``,
    ``delete_event``, or ``clear_log`` methods.  This contract is enforced by
    the tests and must not be violated by any concrete implementation.
    """

    @abstractmethod
    def append_event(self, event: EngineEvent) -> None:
        """Append a state-changing event to the immutable event log."""
        ...

    @abstractmethod
    def get_event_log(self, since_turn: int = 0) -> list[EngineEvent]:
        """Return events whose turn is strictly greater than *since_turn*.

        Ordered by turn, then insertion order.
        ``since_turn=0`` returns every event.
        """
        ...

    @abstractmethod
    def get_latest_turn(self) -> int:
        """Return the highest turn number in the log, or ``0`` if empty."""
        ...

    @abstractmethod
    def save_snapshot(
        self, state: WorldState, turn: int, save_slot: str
    ) -> None:
        """Store a full-state snapshot as a performance cache."""
        ...

    @abstractmethod
    def load_latest_snapshot(
        self, save_slot: str
    ) -> tuple[WorldState, int] | None:
        """Return the most recent ``(state, turn)`` or ``None`` if the slot
        has never been saved.
        """
        ...
