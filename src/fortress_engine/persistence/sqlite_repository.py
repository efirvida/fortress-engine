"""SQLiteWorldStateRepository — concrete WorldStateRepository backed by SQLite.

TDD §4.10 — implements all ABC methods using SQLAlchemy with append-only
event log and per-slot snapshot cache.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from fortress_engine.persistence.models import Base, EventLog, SaveSnapshot
from fortress_engine.persistence.repository import (
    CorruptSnapshotError,
    NonPersistableEventError,
    WorldStateRepository,
)

if TYPE_CHECKING:
    from fortress_engine.engine.state import WorldState
    from fortress_engine.events.event_types import EngineEvent

# ---------------------------------------------------------------------------
# Persistable event type set (design §Persistence filter)
# ---------------------------------------------------------------------------

# State-change events are always persistable.
_STATE_CHANGE_TYPES: frozenset[str] = frozenset(
    {
        "entity_transferred",
        "entity_transformed",
        "entity_combined",
        "flag_set",
        "entity_teleported",
    }
)

# action_resolved is only persistable when has_effects is True — checked
# inline in append_event.


def _is_persistable(event: EngineEvent) -> bool:
    """Return True if *event* should be recorded in the event log.

    Rules (design §Persistence filter):
      - State-change types → always persistable.
      - ``action_resolved`` → persistable only when
        ``payload["has_effects"]`` is truthy.
      - Everything else → NOT persistable.
    """
    etype: str = event.type

    if etype in _STATE_CHANGE_TYPES:
        return True

    if etype == "action_resolved":
        return bool(event.payload.get("has_effects"))

    return False


# ---------------------------------------------------------------------------
# SQLiteWorldStateRepository
# ---------------------------------------------------------------------------


class SQLiteWorldStateRepository(WorldStateRepository):
    """SQLite-backed persistence adapter.

    Parameters:
        db_path: File path (e.g. ``"saves/slot_1/fortaleza.db"``) or
                 ``":memory:"`` for an in-memory database.
    """

    def __init__(self, db_path: str) -> None:
        engine_url = (
            "sqlite://"
            if db_path == ":memory:"
            else f"sqlite:///{db_path}"
        )
        self._engine = create_engine(engine_url)
        Base.metadata.create_all(self._engine)
        # Session factory — callers create their own session per operation.
        self._Session = lambda: Session(self._engine)

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def append_event(self, event: EngineEvent) -> None:
        """Append *event* to the event log if it is persistable.

        Raises:
            NonPersistableEventError: If *event* is not persistable.
        """
        if not _is_persistable(event):
            raise NonPersistableEventError(
                f"{event.type}: event is not persistable"
            )

        import json as _json

        payload_json = _json.dumps(event.payload)

        row = EventLog(
            event_id=str(event.event_id),
            event_type=event.type,
            turn_number=event.turn_number,
            timestamp=event.timestamp,
            payload=payload_json,
            protagonist_id=event.protagonist_id,
            episode_id=event.episode_id,
        )

        with self._Session() as session:
            session.add(row)
            session.commit()

    def get_event_log(self, since_turn: int = 0) -> list[EngineEvent]:
        """Return events with ``turn_number > since_turn``,
        ordered by turn then insertion id.
        """
        from fortress_engine.events.event_types import event_from_dict

        import json as _json

        with self._Session() as session:
            stmt = (
                select(EventLog)
                .where(EventLog.turn_number > since_turn)
                .order_by(EventLog.turn_number, EventLog.id)
            )
            rows = session.scalars(stmt).all()

        results: list[EngineEvent] = []
        for row in rows:
            payload = _json.loads(row.payload)
            data = {
                "event_id": row.event_id,
                "type": row.event_type,
                "turn_number": row.turn_number,
                "timestamp": row.timestamp,
                "payload": payload,
                "protagonist_id": row.protagonist_id,
                "episode_id": row.episode_id,
            }
            results.append(event_from_dict(data))
        return results

    def get_latest_turn(self) -> int:
        """Return ``MAX(turn_number)`` or ``0`` if the log is empty."""
        with self._Session() as session:
            result = session.scalar(
                select(func.max(EventLog.turn_number))
            )
        return result if result is not None else 0

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def save_snapshot(
        self, state: WorldState, turn: int, save_slot: str
    ) -> None:
        """Upsert a snapshot for ``(save_slot, turn)``.

        Replaces an existing snapshot at the same (slot, turn) or inserts
        a new row.
        """
        import json as _json

        world_json = _json.dumps(state.to_dict())

        with self._Session() as session:
            existing = (
                session.query(SaveSnapshot)
                .filter(
                    SaveSnapshot.save_slot == save_slot,
                    SaveSnapshot.turn_number == turn,
                )
                .first()
            )

            if existing is not None:
                existing.world_state_json = world_json
                existing.save_slot = save_slot
            else:
                row = SaveSnapshot(
                    save_slot=save_slot,
                    turn_number=turn,
                    world_state_json=world_json,
                )
                session.add(row)

            session.commit()

    def load_latest_snapshot(
        self, save_slot: str
    ) -> tuple[WorldState, int] | None:
        """Return the newest ``(WorldState, turn)`` for *save_slot*, or
        ``None`` if the slot has never been saved.

        Raises:
            CorruptSnapshotError: When ``world_state_json`` cannot be
                deserialized as a valid ``WorldState``.
        """
        from fortress_engine.engine.state import WorldState as WS

        import json as _json

        with self._Session() as session:
            row = (
                session.query(SaveSnapshot)
                .filter(SaveSnapshot.save_slot == save_slot)
                .order_by(SaveSnapshot.turn_number.desc())
                .first()
            )

        if row is None:
            return None

        try:
            data = _json.loads(row.world_state_json)
        except (_json.JSONDecodeError, TypeError) as exc:
            raise CorruptSnapshotError(
                save_slot,
                f"Invalid JSON in snapshot: {exc}",
            ) from exc

        try:
            state = WS.from_dict(data)
        except (ValueError, TypeError, KeyError) as exc:
            raise CorruptSnapshotError(
                save_slot,
                f"Cannot deserialize WorldState: {exc}",
            ) from exc

        return state, row.turn_number
