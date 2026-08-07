"""RED tests for SQLiteWorldStateRepository — P2.1 & P2.2.

These tests describe the required behavior BEFORE the implementation exists.
They MUST all fail on import or execution until ``SQLiteWorldStateRepository``
is created.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile

import pytest

from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity
from fortress_engine.events.event_types import (
    ACTION_OUTPUT,
    ACTION_RESOLVED,
    ENTITY_COMBINED,
    ENTITY_ENTERED,
    ENTITY_TELEPORTED,
    ENTITY_TRANSFERRED,
    ENTITY_TRANSFORMED,
    ERROR_OUTPUT,
    FLAG_SET,
    EngineEvent,
)
from fortress_engine.persistence import (
    CorruptSnapshotError,
    NonPersistableEventError,
)
from fortress_engine.persistence.sqlite_repository import (
    SQLiteWorldStateRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_world_state(entities: dict | None = None, turn: int = 0) -> WorldState:
    """Build a minimal WorldState for testing."""
    return WorldState(
        entities=entities or {},
        turn_number=turn,
    )


def _make_entity(
    eid: str = "e1", name: str = "test-entity", etype: str = "item"
) -> Entity:
    """Build a minimal Entity."""
    return Entity(
        entity_id=eid,
        type=etype,
        name=name,
        components={},
        spatial_anchor=None,
    )


def _make_event(
    event_type: str,
    turn: int = 1,
    payload: dict | None = None,
    event_id: str | None = None,
) -> EngineEvent:
    """Build an EngineEvent with controlled fields."""
    from uuid import UUID, uuid4

    return EngineEvent(
        event_id=UUID(event_id) if event_id else uuid4(),
        type=event_type,
        turn_number=turn,
        timestamp=1000.0 + turn,
        payload=payload or {},
        protagonist_id=None,
        episode_id=None,
    )


# ---------------------------------------------------------------------------
# P2.1 — Storage round-trip, snapshot integrity, slot independence
# ---------------------------------------------------------------------------


class TestFileRoundTrip:
    """Spec: file round-trip — two repositories on the same db_path."""

    def test_round_trip_events_and_snapshot(self):
        """GIVEN a file-based repo that saves an event and snapshot
        WHEN a new repo opens the same path
        THEN both are queryable with equivalent values.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            state = _make_world_state(
                entities={"e1": _make_entity("e1", "sword")}, turn=7
            )
            event = _make_event(
                ENTITY_TRANSFERRED, turn=7, payload={"entity": "e1"}
            )

            # Write with first repo.
            repo1 = SQLiteWorldStateRepository(db_path)
            repo1.append_event(event)
            repo1.save_snapshot(state, turn=7, save_slot="slot_1")

            # Read with second repo — same file.
            repo2 = SQLiteWorldStateRepository(db_path)
            loaded_state, loaded_turn = repo2.load_latest_snapshot("slot_1")

            assert loaded_turn == 7
            assert loaded_state.turn_number == 7
            assert "e1" in loaded_state.entities
            assert loaded_state.entities["e1"].name == "sword"

            events = repo2.get_event_log()
            assert len(events) == 1
            assert events[0].type == ENTITY_TRANSFERRED
            assert events[0].turn_number == 7
        finally:
            import os

            os.unlink(db_path)


class TestMissingSnapshot:
    """Spec: missing snapshot returns None."""

    def test_no_snapshot_returns_none(self):
        """GIVEN a valid repository with no snapshot for slot_1
        WHEN load_latest_snapshot("slot_1") is called
        THEN it returns None.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        assert repo.load_latest_snapshot("slot_1") is None


class TestCorruptedSnapshot:
    """Spec: corrupted snapshot JSON → CorruptSnapshotError."""

    def test_corrupted_json_raises_typed_error(self):
        """GIVEN a snapshot row with invalid JSON
        WHEN it is loaded
        THEN CorruptSnapshotError is raised.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            # First, create the schema and save a valid snapshot.
            repo1 = SQLiteWorldStateRepository(db_path)
            state = _make_world_state(
                entities={"e1": _make_entity("e1")}, turn=3
            )
            repo1.save_snapshot(state, turn=3, save_slot="slot_1")

            # Delete the repo reference so the engine can be rebuilt.
            del repo1

            # Corrupt the snapshot JSON directly in the SQLite file.
            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE save_snapshots SET world_state_json = ?",
                ("NOT_VALID_JSON{{{",),
            )
            conn.commit()
            conn.close()

            # Now open a new repo on the same file.
            repo2 = SQLiteWorldStateRepository(db_path)
            with pytest.raises(CorruptSnapshotError) as exc_info:
                repo2.load_latest_snapshot("slot_1")

            assert exc_info.value.save_slot == "slot_1"
            assert "json" in exc_info.value.cause.lower()
        finally:
            import os

            os.unlink(db_path)


class TestIndependentSlots:
    """Spec: slots are independent — no cross-talk."""

    def test_slots_track_different_states(self):
        """GIVEN different states saved to slot_1 and slot_2
        WHEN each slot is loaded
        THEN each returns its own state and turn.
        """
        repo = SQLiteWorldStateRepository(":memory:")

        state1 = _make_world_state(
            entities={"e1": _make_entity("e1", "first")}, turn=5
        )
        state2 = _make_world_state(
            entities={"e2": _make_entity("e2", "second")}, turn=8
        )

        repo.save_snapshot(state1, turn=5, save_slot="slot_1")
        repo.save_snapshot(state2, turn=8, save_slot="slot_2")

        loaded1, t1 = repo.load_latest_snapshot("slot_1")
        loaded2, t2 = repo.load_latest_snapshot("slot_2")

        assert t1 == 5
        assert t2 == 8
        assert "e1" in loaded1.entities
        assert "e2" in loaded2.entities
        # Verify no cross-talk — slot_1 has only e1, slot_2 has only e2.
        assert "e2" not in loaded1.entities
        assert "e1" not in loaded2.entities


# ---------------------------------------------------------------------------
# P2.2 — Persistable filter, query order, latest turn
# ---------------------------------------------------------------------------


class TestPersistableFilterRejection:
    """Spec: narration events and unknown types are rejected."""

    @pytest.mark.parametrize(
        "event_type",
        [
            ACTION_OUTPUT,
            ENTITY_ENTERED,
            ERROR_OUTPUT,
        ],
    )
    def test_narration_rejected(self, event_type):
        """GIVEN a narration event type
        WHEN append_event is called
        THEN NonPersistableEventError is raised and no row is stored.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        event = _make_event(event_type, turn=1)

        with pytest.raises(NonPersistableEventError) as exc_info:
            repo.append_event(event)

        assert exc_info.value.args[0].startswith(event_type[:20])

        # Verify no row was stored.
        assert repo.get_event_log() == []
        assert repo.get_latest_turn() == 0

    def test_unknown_event_type_rejected(self):
        """GIVEN an event type outside the persistable set
        WHEN append_event is called
        THEN NonPersistableEventError is raised.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        event = _make_event("nonexistent_event_type", turn=1)

        with pytest.raises(NonPersistableEventError) as exc_info:
            repo.append_event(event)

        assert "nonexistent_event_type" in str(exc_info.value)

    @pytest.mark.parametrize(
        "event_type",
        [
            ENTITY_TRANSFERRED,
            ENTITY_TRANSFORMED,
            ENTITY_COMBINED,
            FLAG_SET,
            ENTITY_TELEPORTED,
        ],
    )
    def test_state_change_events_accepted(self, event_type):
        """GIVEN a state-change event type
        WHEN append_event is called
        THEN it is accepted and persisted.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        event = _make_event(event_type, turn=1, payload={"entity": "e1"})

        repo.append_event(event)  # Must NOT raise.

        assert len(repo.get_event_log()) == 1

    def test_action_resolved_with_effects_accepted(self):
        """GIVEN an action_resolved event with has_effects=True
        WHEN appended
        THEN it is persisted.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        event = _make_event(
            ACTION_RESOLVED,
            turn=2,
            payload={"has_effects": True, "ops_executed": 2},
        )
        repo.append_event(event)
        assert len(repo.get_event_log()) == 1

    def test_action_resolved_without_effects_rejected(self):
        """GIVEN an action_resolved with has_effects=False
        WHEN appended
        THEN it is rejected.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        event = _make_event(
            ACTION_RESOLVED,
            turn=2,
            payload={"has_effects": False, "ops_executed": 0},
        )
        with pytest.raises(NonPersistableEventError):
            repo.append_event(event)


class TestEventLogQuery:
    """Spec: get_event_log ordering and tail query."""

    def test_events_ordered_by_turn_then_id(self):
        """GIVEN events at turns 1, 2, 2, 3
        WHEN get_event_log() is called
        THEN they are ordered by turn_number, then insertion order (id).
        """
        repo = SQLiteWorldStateRepository(":memory:")

        e1 = _make_event(ENTITY_TRANSFERRED, turn=1, payload={"n": 1})
        e2a = _make_event(ENTITY_TRANSFERRED, turn=2, payload={"n": 2})
        e2b = _make_event(FLAG_SET, turn=2, payload={"n": 3})
        e3 = _make_event(ENTITY_TELEPORTED, turn=3, payload={"n": 4})

        repo.append_event(e1)
        repo.append_event(e2a)
        repo.append_event(e2b)
        repo.append_event(e3)

        events = repo.get_event_log()
        assert len(events) == 4

        turns = [e.turn_number for e in events]
        assert turns == [1, 2, 2, 3]

        # At turn 2: e2a (inserted first) should precede e2b.
        assert events[1].type == ENTITY_TRANSFERRED
        assert events[2].type == FLAG_SET

    def test_since_turn_strictly_greater(self):
        """GIVEN events through turn 9
        WHEN get_event_log(5) is called
        THEN only turns 6-9 are returned.
        """
        repo = SQLiteWorldStateRepository(":memory:")

        for t in range(1, 10):
            repo.append_event(
                _make_event(ENTITY_TRANSFERRED, turn=t, payload={"t": t})
            )

        events = repo.get_event_log(since_turn=5)
        assert len(events) == 4
        turns = {e.turn_number for e in events}
        assert turns == {6, 7, 8, 9}

    def test_since_turn_zero_returns_all(self):
        """GIVEN any events
        WHEN get_event_log(0) is called
        THEN all events are returned.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        for t in range(1, 4):
            repo.append_event(
                _make_event(ENTITY_TRANSFERRED, turn=t, payload={"t": t})
            )

        assert len(repo.get_event_log(since_turn=0)) == 3


class TestLatestTurn:
    """Spec: get_latest_turn returns 0 for empty log."""

    def test_empty_log_returns_zero(self):
        """GIVEN a repository with no events
        WHEN get_latest_turn is called
        THEN it returns 0.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        assert repo.get_latest_turn() == 0

    def test_populated_log_returns_max(self):
        """GIVEN events at turns 1, 3, 5
        WHEN get_latest_turn is called
        THEN it returns 5.
        """
        repo = SQLiteWorldStateRepository(":memory:")
        for t in (1, 3, 5):
            repo.append_event(
                _make_event(ENTITY_TRANSFERRED, turn=t, payload={"t": t})
            )

        assert repo.get_latest_turn() == 5


class TestCorruptedSnapshotInvalidWorldState:
    """Spec: JSON is valid but WorldState.from_dict fails → CorruptSnapshotError."""

    def test_valid_json_but_invalid_state_raises_typed_error(self):
        """GIVEN a snapshot row with valid JSON that is not a valid WorldState
        WHEN it is loaded
        THEN CorruptSnapshotError is raised.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            repo1 = SQLiteWorldStateRepository(db_path)
            state = _make_world_state(
                entities={"e1": _make_entity("e1")}, turn=3
            )
            repo1.save_snapshot(state, turn=3, save_slot="slot_1")
            del repo1

            # Valid JSON, but missing required WorldState keys.
            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE save_snapshots SET world_state_json = ?",
                ('{"not_a_valid_worldstate": true}',),
            )
            conn.commit()
            conn.close()

            repo2 = SQLiteWorldStateRepository(db_path)
            with pytest.raises(CorruptSnapshotError) as exc_info:
                repo2.load_latest_snapshot("slot_1")

            assert exc_info.value.save_slot == "slot_1"
            assert "deserialize" in exc_info.value.cause.lower()
        finally:
            import os

            os.unlink(db_path)


class TestSnapshotUpsert:
    """Spec: same (save_slot, turn) upserts via merge."""

    def test_save_same_slot_turn_replaces(self):
        """GIVEN a snapshot for slot_1 at turn 12
        WHEN another snapshot for slot_1 at turn 12 is saved
        THEN the saved state reflects the latest value.
        """
        repo = SQLiteWorldStateRepository(":memory:")

        state_a = _make_world_state(
            entities={"ea": _make_entity("ea", "first-save")}, turn=12
        )
        state_b = _make_world_state(
            entities={"eb": _make_entity("eb", "second-save")}, turn=12
        )

        repo.save_snapshot(state_a, turn=12, save_slot="slot_1")
        repo.save_snapshot(state_b, turn=12, save_slot="slot_1")

        loaded, turn = repo.load_latest_snapshot("slot_1")
        assert turn == 12
        assert "eb" in loaded.entities  # latest value
        assert "ea" not in loaded.entities  # replacement, not merge
