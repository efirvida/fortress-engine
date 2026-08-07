"""Fortress Engine persistence layer.

Public API — the only symbols callers outside ``persistence/`` should need:
  - ``WorldStateRepository`` — ABC that defines the storage seam
  - ``RepositoryError`` and its typed subclasses
  - ``Base``, ``EventLog``, ``SaveSnapshot`` — ORM models for concrete backends
"""

from fortress_engine.persistence.models import Base, EventLog, SaveSnapshot
from fortress_engine.persistence.repository import (
    CorruptEventError,
    CorruptSnapshotError,
    InvalidSlotError,
    NonPersistableEventError,
    RepositoryError,
    WorldStateRepository,
)

__all__ = [
    "Base",
    "EventLog",
    "SaveSnapshot",
    "WorldStateRepository",
    "RepositoryError",
    "NonPersistableEventError",
    "CorruptEventError",
    "CorruptSnapshotError",
    "InvalidSlotError",
]
