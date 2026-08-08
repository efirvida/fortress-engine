"""Tests for SQLAlchemy ORM models: EventLog, SaveSnapshot, indexes, and constraints.

TDD §5.1-5.2 — persistence-models spec.
"""

from datetime import datetime

import pytest

# ---------------------------------------------------------------------------
# P1.2 RED — the production module does NOT exist yet
# ---------------------------------------------------------------------------
from fortress_engine.persistence.models import Base, EventLog, SaveSnapshot


class TestBase:
    """Base must be a DeclarativeBase subclass."""

    def test_base_is_declarative_base(self):
        """Base must inherit from SQLAlchemy DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)


class TestEventLogSchema:
    """EventLog ORM model matches TDD §5.1 exactly."""

    def test_tablename(self):
        assert EventLog.__tablename__ == "event_log"

    def test_columns_exist(self):
        """All columns from TDD §5.1 must be present."""
        cols = {c.name for c in EventLog.__table__.columns}
        expected = {
            "id",
            "event_id",
            "event_type",
            "turn_number",
            "timestamp",
            "payload",
            "protagonist_id",
            "episode_id",
            "save_slot",
            "created_at",
        }
        assert cols == expected, f"Mismatch: {cols ^ expected}"

    def test_id_column(self):
        col = EventLog.__table__.columns["id"]
        assert col.primary_key is True
        assert col.autoincrement is True
        assert isinstance(col.type, __import__("sqlalchemy").Integer)

    def test_event_id_column(self):
        col = EventLog.__table__.columns["event_id"]
        assert col.nullable is False
        assert col.unique is True
        assert isinstance(col.type, __import__("sqlalchemy").String)
        assert col.type.length == 36

    def test_event_type_column(self):
        col = EventLog.__table__.columns["event_type"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").String)
        assert col.type.length == 50

    def test_turn_number_column(self):
        col = EventLog.__table__.columns["turn_number"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").Integer)

    def test_timestamp_column(self):
        col = EventLog.__table__.columns["timestamp"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").Float)

    def test_payload_column(self):
        col = EventLog.__table__.columns["payload"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").Text)

    def test_protagonist_id_column(self):
        col = EventLog.__table__.columns["protagonist_id"]
        assert col.nullable is True
        assert isinstance(col.type, __import__("sqlalchemy").String)
        assert col.type.length == 100

    def test_episode_id_column(self):
        col = EventLog.__table__.columns["episode_id"]
        assert col.nullable is True
        assert isinstance(col.type, __import__("sqlalchemy").String)
        assert col.type.length == 50

    def test_save_slot_column(self):
        col = EventLog.__table__.columns["save_slot"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").String)
        assert col.type.length == 20
        assert col.default.arg == "auto"

    def test_created_at_column(self):
        col = EventLog.__table__.columns["created_at"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").DateTime)
        assert col.default is not None


class TestSaveSnapshotSchema:
    """SaveSnapshot ORM model matches TDD §5.1 exactly."""

    def test_tablename(self):
        assert SaveSnapshot.__tablename__ == "save_snapshots"

    def test_columns_exist(self):
        cols = {c.name for c in SaveSnapshot.__table__.columns}
        expected = {"id", "save_slot", "turn_number", "world_state_json", "created_at"}
        assert cols == expected, f"Mismatch: {cols ^ expected}"

    def test_id_column(self):
        col = SaveSnapshot.__table__.columns["id"]
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_save_slot_column(self):
        col = SaveSnapshot.__table__.columns["save_slot"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").String)
        assert col.type.length == 20

    def test_turn_number_column(self):
        col = SaveSnapshot.__table__.columns["turn_number"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").Integer)

    def test_world_state_json_column(self):
        col = SaveSnapshot.__table__.columns["world_state_json"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").Text)

    def test_created_at_column(self):
        col = SaveSnapshot.__table__.columns["created_at"]
        assert col.nullable is False
        assert isinstance(col.type, __import__("sqlalchemy").DateTime)
        assert col.default is not None


class TestEventLogIndexes:
    """TDD §5.2 — three indexes on EventLog."""

    def test_idx_event_log_turn_exists(self):
        indexes = {i.name for i in EventLog.__table__.indexes}
        assert "idx_event_log_turn" in indexes, f"Found: {indexes}"

    def test_idx_event_log_type_exists(self):
        indexes = {i.name for i in EventLog.__table__.indexes}
        assert "idx_event_log_type" in indexes, f"Found: {indexes}"

    def test_idx_event_log_slot_exists(self):
        indexes = {i.name for i in EventLog.__table__.indexes}
        assert "idx_event_log_slot" in indexes, f"Found: {indexes}"

    def test_total_index_count_event_log(self):
        """EventLog must have exactly 3 declarative indexes (plus implicit PK)."""
        # The table-level indexes set from Index() constructs, not counting
        # PK which is auto-generated.
        indexes = [
            i for i in EventLog.__table__.indexes
            if i.name.startswith("idx_event_log")
        ]
        assert len(indexes) == 3, f"Expected 3, got {len(indexes)}: {[i.name for i in indexes]}"


class TestSaveSnapshotIndexesAndConstraints:
    """TDD §5.2 — one index + unique constraint on SaveSnapshot."""

    def test_idx_snapshot_slot_turn_exists(self):
        indexes = {i.name for i in SaveSnapshot.__table__.indexes}
        assert "idx_snapshot_slot_turn" in indexes, f"Found: {indexes}"

    def test_unique_sk_turn_constraint_exists(self):
        """(save_slot, turn_number) must have a unique constraint."""
        constraints = SaveSnapshot.__table__.constraints
        unique_constraints = [
            c
            for c in constraints
            if hasattr(c, "columns") and len(c.columns) == 2
        ]
        names = {str(uc) for uc in unique_constraints}
        # The UniqueConstraint must cover save_slot and turn_number
        found = any(
            {"save_slot", "turn_number"}.issubset(
                {col.name for col in uc.columns}
            )
            for uc in unique_constraints
        )
        assert found, (
            f"No unique constraint on (save_slot, turn_number); "
            f"constraints: {unique_constraints}"
        )

    def test_unique_sk_turn_prevent_duplicate(self):
        """Inserting duplicate (save_slot, turn_number) must fail."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        snapshot_a = SaveSnapshot(
            save_slot="slot_1",
            turn_number=12,
            world_state_json='{"entities": {}}',
            created_at=datetime.utcnow(),
        )
        snapshot_b = SaveSnapshot(
            save_slot="slot_1",
            turn_number=12,
            world_state_json='{"entities": {"changed": "yes"}}',
            created_at=datetime.utcnow(),
        )

        with Session(engine) as session:
            session.add(snapshot_a)
            session.commit()

            session.add(snapshot_b)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()
