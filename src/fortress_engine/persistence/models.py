"""SQLAlchemy ORM models for the event log and snapshot cache.

TDD §5.1-5.2 — ``EventLog`` is the authoritative event-sourcing source of
truth; ``SaveSnapshot`` is a per-slot performance cache.

.. note::

   The event log is **append-only** by contract.  Concrete repositories
   must not expose update/delete methods, and this module does not define
   any ``UPDATE`` / ``DELETE`` helper functions.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all persistence models."""


class EventLog(Base):
    """Immutable event log — the authoritative source of truth for all
    state-changing events.

    TDD §5.1.
    """

    __tablename__ = "event_log"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    event_id: str = Column(String(36), nullable=False, unique=True)
    event_type: str = Column(String(50), nullable=False)
    turn_number: int = Column(Integer, nullable=False)
    timestamp: float = Column(Float, nullable=False)
    payload: str = Column(Text, nullable=False)
    protagonist_id: str | None = Column(String(100), nullable=True)
    episode_id: str | None = Column(String(50), nullable=True)
    save_slot: str = Column(String(20), nullable=False, default="auto")
    created_at: datetime = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # TDD §5.2 indexes
    __table_args__ = (
        Index("idx_event_log_turn", "turn_number"),
        Index("idx_event_log_type", "event_type"),
        Index("idx_event_log_slot", "save_slot"),
    )


class SaveSnapshot(Base):
    """Per-slot performance cache of full WorldState JSON.

    TDD §5.1-5.2.
    """

    __tablename__ = "save_snapshots"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    save_slot: str = Column(String(20), nullable=False)
    turn_number: int = Column(Integer, nullable=False)
    world_state_json: str = Column(Text, nullable=False)
    created_at: datetime = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("save_slot", "turn_number"),
        Index("idx_snapshot_slot_turn", "save_slot", "turn_number"),
    )
