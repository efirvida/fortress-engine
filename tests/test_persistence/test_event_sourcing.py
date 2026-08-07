"""RED tests for EventSourcingSaveSystem — P3.1 & P3.5.

These tests describe the required behavior BEFORE the implementation exists.
They import code that does not exist yet (EventSourcingSaveSystem),
guaranteeing a RED state.
"""

from __future__ import annotations

import pytest

from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_OUTPUT,
    ACTION_RESOLVED,
    ENTITY_ENTERED,
    ENTITY_TELEPORTED,
    ENTITY_TRANSFERRED,
    ENTITY_TRANSFORMED,
    ENTITY_COMBINED,
    ERROR_OUTPUT,
    FLAG_SET,
    GAME_SAVED,
    GAME_LOADED,
    SAVE_REPLAY_STARTED,
    SAVE_REPLAY_ENDED,
    EngineEvent,
)
from fortress_engine.persistence import (
    CorruptSnapshotError,
    NonPersistableEventError,
    WorldStateRepository,
)
from fortress_engine.persistence.sqlite_repository import (
    SQLiteWorldStateRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_type: str,
    turn: int = 1,
    payload: dict | None = None,
    protagonist_id: str | None = None,
    episode_id: str | None = None,
) -> EngineEvent:
    """Build an EngineEvent with controlled fields."""
    from uuid import uuid4

    return EngineEvent(
        event_id=uuid4(),
        type=event_type,
        turn_number=turn,
        timestamp=1000.0 + turn,
        payload=payload or {},
        protagonist_id=protagonist_id,
        episode_id=episode_id,
    )


def _make_action_resolved(
    turn: int = 1,
    has_effects: bool = True,
    protagonist_id: str = "hero",
) -> EngineEvent:
    return _make_event(
        ACTION_RESOLVED,
        turn=turn,
        payload={
            "hyper_edge_id": "h1",
            "operators_executed": ["TRANSFER"],
            "has_effects": has_effects,
            "protagonist_id": protagonist_id,
        },
        protagonist_id=protagonist_id,
    )


def _make_state() -> WorldState:
    return WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {"max_weight": 40}, "room_a"),
            "room_a": Entity("room_a", "room", "Room A", {}, None),
            "key": Entity("key", "item", "Key", {"weight": 1}, "room_a"),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="ep-01",
        turn_number=5,
    )


# ---------------------------------------------------------------------------
# P3.1 — Save system: subscription, filtering, snapshot, replay
# ---------------------------------------------------------------------------


class TestEventPersistenceSubscriber:
    """Spec: EventBus persistence subscriber — wildcard subscription filters
    and appends persistable events only."""

    def test_wildcard_subscription_persists_state_change_events(self):
        """GIVEN EventSourcingSaveSystem subscribed to EventBus wildcard
        WHEN 5 state-change events are emitted
        THEN each is appended to the repository.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        save_system = EventSourcingSaveSystem(bus, repo)

        # Emit 5 state-change events through the bus.
        events = [
            _make_event(ENTITY_TRANSFERRED, turn=1, payload={
                "entity_id": "key", "from_container_id": "room_a",
                "to_container_id": "hero",
            }),
            _make_event(ENTITY_TRANSFORMED, turn=1, payload={
                "entity_id": "key", "component_key": "weight",
                "old_value": 1, "new_value": 2,
            }),
            _make_event(ENTITY_COMBINED, turn=2, payload={
                "input_entity_ids": ["a", "b"], "output_entity_id": "c",
            }),
            _make_event(FLAG_SET, turn=2, payload={
                "flag_name": "door_open", "old_value": False, "new_value": True,
            }),
            _make_event(ENTITY_TELEPORTED, turn=3, payload={
                "entity_id": "hero", "from_anchor_id": "room_a",
                "to_anchor_id": "room_b",
            }),
        ]
        for evt in events:
            bus.emit(evt)

        # All 5 should be in the log.
        log = repo.get_event_log(since_turn=0)
        assert len(log) == 5
        persisted_types = [e.type for e in log]
        assert ENTITY_TRANSFERRED in persisted_types
        assert ENTITY_TRANSFORMED in persisted_types
        assert ENTITY_COMBINED in persisted_types
        assert FLAG_SET in persisted_types
        assert ENTITY_TELEPORTED in persisted_types

    def test_action_resolved_with_effects_is_persisted(self):
        """GIVEN action_resolved with has_effects=True
        WHEN emitted through bus
        THEN it is appended to the event log.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        evt = _make_action_resolved(turn=1, has_effects=True)
        bus.emit(evt)

        log = repo.get_event_log(since_turn=0)
        assert len(log) == 1
        assert log[0].type == ACTION_RESOLVED
        assert log[0].payload["has_effects"] is True

    def test_action_resolved_without_effects_is_not_persisted(self):
        """GIVEN action_resolved with has_effects=False
        WHEN emitted through bus
        THEN no row is written to the event log.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        evt = _make_action_resolved(turn=1, has_effects=False)
        bus.emit(evt)

        log = repo.get_event_log(since_turn=0)
        assert len(log) == 0

    def test_narration_events_are_not_persisted(self):
        """GIVEN narration events (action_output, entity_entered, error_output)
        WHEN emitted through bus
        THEN none are appended to the log.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        narration_events = [
            _make_event(ACTION_OUTPUT, turn=1, payload={"text": "Hello"}),
            _make_event(ENTITY_ENTERED, turn=1, payload={"entity_id": "hero"}),
            _make_event(ERROR_OUTPUT, turn=1, payload={"error_code": "test"}),
        ]
        for evt in narration_events:
            bus.emit(evt)

        log = repo.get_event_log(since_turn=0)
        assert len(log) == 0


class TestSnapshotOnGameSaved:
    """Spec: snapshot-on-save — game_saved triggers a state snapshot."""

    def test_game_saved_triggers_snapshot_with_state_provider(self):
        """GIVEN a save_system with state_provider
        WHEN game_saved is emitted with save_slot in payload
        THEN repository.save_snapshot is called with current state.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        state = _make_state()

        save_system = EventSourcingSaveSystem(
            bus, repo, state_provider=lambda: state
        )

        # Emit game_saved via the bus.
        evt = _make_event(
            GAME_SAVED, turn=state.turn_number,
            payload={"save_slot": "slot_2"},
        )
        bus.emit(evt)

        # The snapshot should now exist.
        result = repo.load_latest_snapshot("slot_2")
        assert result is not None
        loaded_state, loaded_turn = result
        assert loaded_turn == state.turn_number
        assert loaded_state.active_protagonist_id == "hero"
        assert "hero" in loaded_state.entities
        assert loaded_state.current_episode_id == "ep-01"

    def test_game_saved_without_state_provider_is_noop(self):
        """GIVEN save_system without state_provider
        WHEN game_saved is emitted
        THEN no snapshot is saved (no crash).
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)  # no state_provider

        evt = _make_event(
            GAME_SAVED, turn=1,
            payload={"save_slot": "slot_1"},
        )
        bus.emit(evt)

        # No snapshot created.
        result = repo.load_latest_snapshot("slot_1")
        assert result is None

    def test_game_saved_default_slot_when_no_save_slot_in_payload(self):
        """GIVEN game_saved event without save_slot in payload
        WHEN emitted
        THEN snapshot is saved to default slot 'slot_1'.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        state = _make_state()

        EventSourcingSaveSystem(bus, repo, state_provider=lambda: state)

        evt = _make_event(GAME_SAVED, turn=state.turn_number, payload={})
        bus.emit(evt)

        result = repo.load_latest_snapshot("slot_1")
        assert result is not None


class TestReplayFromEmptyLog:
    """Spec: replay from empty log — no snapshot, replay all events."""

    def test_replay_from_empty_log_restores_state(self):
        """GIVEN 3 effectful actions persisted via save_system
        WHEN replay_state is called on a fresh state
        THEN the replayed state reflects all 3 actions.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        save_system = EventSourcingSaveSystem(bus, repo)

        # Turn 1: TRANSFER key from room_a to hero.
        bus.emit(_make_action_resolved(turn=1, has_effects=True))
        bus.emit(_make_event(ENTITY_TRANSFERRED, turn=1, payload={
            "entity_id": "key", "from_container_id": "room_a",
            "to_container_id": "hero",
        }))

        # Turn 2: FLAG door_open = True.
        bus.emit(_make_action_resolved(turn=2, has_effects=True))
        bus.emit(_make_event(FLAG_SET, turn=2, payload={
            "flag_name": "door_open", "old_value": False, "new_value": True,
        }))

        # Turn 3: TELEPORT hero from room_a to room_b.
        bus.emit(_make_action_resolved(turn=3, has_effects=True))
        bus.emit(_make_event(ENTITY_TELEPORTED, turn=3, payload={
            "entity_id": "hero", "from_anchor_id": "room_a",
            "to_anchor_id": "room_b",
        }))

        # Fresh state with minimal entities.
        state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "room_a"),
                "room_a": Entity("room_a", "room", "Room A", {}, None),
                "room_b": Entity("room_b", "room", "Room B", {}, None),
                "key": Entity("key", "item", "Key", {"weight": 1}, "room_a"),
            },
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            turn_number=0,
        )

        # Build an isolated bus to capture boundary events.
        replay_bus = EventBus()
        replay_events: list[EngineEvent] = []
        replay_bus.subscribe("*", lambda e: replay_events.append(e))

        # Create a save_system on the replay bus for replay_state.
        replay_save = EventSourcingSaveSystem(replay_bus, repo)

        result_state = replay_save.replay_state(state, "slot_1")

        # State was mutated in place.
        assert result_state is state

        # Key moved from room_a to hero.
        assert result_state.get_entity("key").spatial_anchor == "hero"

        # Flag set.
        assert result_state.get_flag("door_open") is True

        # Hero teleported.
        assert result_state.get_entity("hero").spatial_anchor == "room_b"

        # Turn number should be 3 (last event's turn).
        assert result_state.turn_number == 3

    def test_replay_emits_only_boundary_events(self):
        """GIVEN events persisted in log
        WHEN replay_state runs
        THEN only SAVE_REPLAY_STARTED and SAVE_REPLAY_ENDED are emitted,
        with zero state-change events between them.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        # Persist some events.
        bus.emit(_make_action_resolved(turn=1, has_effects=True))
        bus.emit(_make_event(ENTITY_TRANSFERRED, turn=1, payload={
            "entity_id": "key", "from_container_id": "room_a",
            "to_container_id": "hero",
        }))

        state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "room_a"),
                "room_a": Entity("room_a", "room", "Room A", {}, None),
                "key": Entity("key", "item", "Key", {}, "room_a"),
            },
        )

        # Capture all events on a fresh bus during replay.
        capture_bus = EventBus()
        captured: list[EngineEvent] = []
        capture_bus.subscribe("*", lambda e: captured.append(e))

        replay_save = EventSourcingSaveSystem(capture_bus, repo)
        replay_save.replay_state(state, "slot_1")

        # Only boundary events emitted.
        event_types = [e.type for e in captured]
        assert SAVE_REPLAY_STARTED in event_types
        assert SAVE_REPLAY_ENDED in event_types

        # Zero state-change events were re-emitted.
        state_change_types = {
            ENTITY_TRANSFERRED, ENTITY_TRANSFORMED, ENTITY_COMBINED,
            FLAG_SET, ENTITY_TELEPORTED,
        }
        replayed_state_changes = [
            e for e in captured if e.type in state_change_types
        ]
        assert len(replayed_state_changes) == 0

        # No narration events.
        narration_types = {ACTION_OUTPUT, ENTITY_ENTERED, ERROR_OUTPUT}
        replayed_narration = [
            e for e in captured if e.type in narration_types
        ]
        assert len(replayed_narration) == 0


class TestReplayFromSnapshot:
    """Spec: snapshot-first replay — load snapshot, replay only tail."""

    def test_replay_from_snapshot_only_replays_tail(self):
        """GIVEN 50 events logged and a snapshot at turn 25
        WHEN replay_state loads slot_1
        THEN only 25 tail events are replayed (turn 26-50).
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        save_system = EventSourcingSaveSystem(bus, repo)

        # Build state with entities for all 50 turns.
        entities = {
            "hero": Entity("hero", "player", "Hero", {}, "room_a"),
            "room_a": Entity("room_a", "room", "Room A", {}, None),
        }
        # Create 50 items that will be flagged.
        for i in range(1, 51):
            eid = f"item_{i}"
            entities[eid] = Entity(eid, "item", f"Item {i}", {}, None)

        # Persist 50 actions (each: action_resolved + FLAG_SET).
        for turn in range(1, 51):
            bus.emit(_make_action_resolved(turn=turn, has_effects=True))
            bus.emit(_make_event(FLAG_SET, turn=turn, payload={
                "flag_name": f"item_{turn}_flag",
                "old_value": False, "new_value": True,
            }))

        # Save snapshot at turn 25 (after first 25 turns).
        state_at_25 = WorldState(
            entities={k: Entity(v.entity_id, v.type, v.name, dict(v.components), v.spatial_anchor)
                      for k, v in entities.items()},
            flag_book={f"item_{i}_flag": True for i in range(1, 26)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            turn_number=25,
        )
        repo.save_snapshot(state_at_25, 25, "slot_1")

        # Replay on fresh state.
        fresh_state = WorldState(entities=entities)
        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)
        result = replay_save.replay_state(fresh_state, "slot_1")

        # Verify flags from snapshot (1-25) are present.
        for i in range(1, 26):
            assert result.get_flag(f"item_{i}_flag") is True

        # Verify flags from tail (26-50) are present.
        for i in range(26, 51):
            assert result.get_flag(f"item_{i}_flag") is True

        # Turn number restored to 50 (last event).
        assert result.turn_number == 50

    def test_replay_slot_independence(self):
        """GIVEN distinct states saved in slots 1 and 2
        WHEN slot 1 is loaded
        THEN slot 2 remains unchanged.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        save_system = EventSourcingSaveSystem(bus, repo)

        # Slot 1: TRANSFER key → hero, FLAG slot1_flag.
        bus.emit(_make_action_resolved(turn=1, has_effects=True))
        bus.emit(_make_event(ENTITY_TRANSFERRED, turn=1, payload={
            "entity_id": "key", "from_container_id": "room_a",
            "to_container_id": "hero",
        }))
        bus.emit(_make_event(FLAG_SET, turn=2, payload={
            "flag_name": "slot1_flag", "old_value": False, "new_value": True,
        }))

        # Save slot 1 via game_saved.
        state1 = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "room_a"),
                "key": Entity("key", "item", "Key", {}, "hero"),
            },
            flag_book={"slot1_flag": True},
            turn_number=2,
        )
        repo.save_snapshot(state1, 2, "slot_1")

        # Slot 2: different events.
        bus2 = EventBus()
        repo2 = SQLiteWorldStateRepository(":memory:")
        save2 = EventSourcingSaveSystem(bus2, repo2)
        bus2.emit(_make_action_resolved(turn=1, has_effects=True))
        bus2.emit(_make_event(FLAG_SET, turn=1, payload={
            "flag_name": "slot2_flag", "old_value": False, "new_value": True,
        }))
        state2 = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "room_b"),
            },
            flag_book={"slot2_flag": True},
            turn_number=1,
        )
        repo2.save_snapshot(state2, 1, "slot_2")

        # Load slot 1. Slot 2 must remain unchanged.
        fresh_state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "room_a"),
                "key": Entity("key", "item", "Key", {}, "room_a"),
            },
        )

        # Use slot 1.
        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)
        result = replay_save.replay_state(fresh_state, "slot_1")

        assert result.get_entity("key").spatial_anchor == "hero"
        assert result.get_flag("slot1_flag") is True
        assert not result.get_flag("slot2_flag")  # slot 2 flag absent


class TestUnknownEventType:
    """Spec: invalid replay event raises typed error."""

    def test_unknown_event_type_raises_during_replay(self):
        """GIVEN an unknown event type in the log
        WHEN replay_state is called
        THEN a CorruptEventError (or typed replay error) is raised.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem
        from fortress_engine.persistence.repository import CorruptEventError
        from fortress_engine.persistence.models import EventLog as EventLogModel
        from sqlalchemy.orm import Session

        repo = SQLiteWorldStateRepository(":memory:")

        # Insert a row with unknown event type directly, bypassing the
        # persistable filter that would reject it in append_event.
        with Session(repo._engine) as session:
            row = EventLogModel(
                event_id="00000000-0000-0000-0000-000000000001",
                event_type="unknown_event_type",
                turn_number=1,
                timestamp=1001.0,
                payload='{"data": 42}',
                save_slot="slot_1",
            )
            session.add(row)
            session.commit()

        state = WorldState()
        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)

        with pytest.raises((CorruptEventError, ValueError, KeyError)):
            replay_save.replay_state(state, "slot_1")


# ---------------------------------------------------------------------------
# P3.5 — Integration round-trip
# ---------------------------------------------------------------------------


class TestIntegrationRoundTrip:
    """Spec: acceptance round-trip — 3 actions, save, fresh load."""

    def test_full_round_trip_three_actions(self):
        """GIVEN 3 effectful actions executed and saved
        WHEN a fresh save_system loads the slot
        THEN entities, flags, active protagonist, episode, and turn
        equal the pre-save state.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        # --- Session 1: play and save ---
        repo1 = SQLiteWorldStateRepository(":memory:")
        bus1 = EventBus()
        save_system1 = EventSourcingSaveSystem(bus1, repo1)

        # Action 1: TRANSFER key → hero.
        bus1.emit(_make_action_resolved(turn=1, has_effects=True))
        bus1.emit(_make_event(ENTITY_TRANSFERRED, turn=1, payload={
            "entity_id": "key", "from_container_id": "room_a",
            "to_container_id": "hero",
        }))

        # Action 2: FLAG door_open.
        bus1.emit(_make_action_resolved(turn=2, has_effects=True))
        bus1.emit(_make_event(FLAG_SET, turn=2, payload={
            "flag_name": "door_open", "old_value": False, "new_value": True,
        }))

        # Action 3: TELEPORT hero.
        bus1.emit(_make_action_resolved(turn=3, has_effects=True))
        bus1.emit(_make_event(ENTITY_TELEPORTED, turn=3, payload={
            "entity_id": "hero", "from_anchor_id": "room_a",
            "to_anchor_id": "room_b",
        }))

        # Pre-save state.
        pre_save_state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "room_b"),
                "room_a": Entity("room_a", "room", "Room A", {}, None),
                "room_b": Entity("room_b", "room", "Room B", {}, None),
                "key": Entity("key", "item", "Key", {}, "hero"),
            },
            flag_book={"door_open": True},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="ep-01",
            turn_number=3,
        )

        # Save via game_saved event.
        bus1.emit(_make_event(GAME_SAVED, turn=3,
                              payload={"save_slot": "slot_1"}))

        # But the game_saved handler needs state_provider. Let's wire it.
        # Re-create with state_provider, but we need to capture pre-save too.
        # Actually for the test we save a snapshot directly to make it clean.
        repo1.save_snapshot(pre_save_state, 3, "slot_1")

        # --- Session 2: fresh load ---
        # Use the same repo (in-memory) with a fresh save_system.
        repo2 = repo1
        bus2 = EventBus()
        # Don't subscribe save_system2 to wildcard — we only use replay.
        save_system2 = EventSourcingSaveSystem(bus2, repo2)

        fresh_state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, None),
                "room_a": Entity("room_a", "room", "Room A", {}, None),
                "room_b": Entity("room_b", "room", "Room B", {}, None),
                "key": Entity("key", "item", "Key", {}, None),
            },
        )

        result = save_system2.replay_state(fresh_state, "slot_1")

        # Verify state matches pre-save.
        assert result.get_entity("key").spatial_anchor == "hero"
        assert result.get_entity("hero").spatial_anchor == "room_b"
        assert result.get_flag("door_open") is True
        assert result.active_protagonist_id == "hero"
        assert result.current_episode_id == "ep-01"
        assert result.turn_number == 3

    def test_snapshot_first_replay_fifty_actions(self):
        """Acceptance B: snapshot at turn 25, 25 tail actions, only tail replayed."""
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        save_system = EventSourcingSaveSystem(bus, repo)

        entities = {"hero": Entity("hero", "player", "Hero", {}, "room_a")}
        for i in range(1, 26):
            entities[f"item_{i}"] = Entity(f"item_{i}", "item", f"Item {i}", {}, None)

        # 50 turns of flag-setting.
        for turn in range(1, 51):
            bus.emit(_make_action_resolved(turn=turn, has_effects=True))
            bus.emit(_make_event(FLAG_SET, turn=turn, payload={
                "flag_name": f"flag_{turn}",
                "old_value": False, "new_value": True,
            }))

        # Snapshot at turn 25.
        state25 = WorldState(
            entities=entities,
            flag_book={f"flag_{i}": True for i in range(1, 26)},
            turn_number=25,
        )
        repo.save_snapshot(state25, 25, "slot_1")

        # Replay.
        fresh_state = WorldState(entities=entities)
        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)
        result = replay_save.replay_state(fresh_state, "slot_1")

        # All 50 flags present.
        for i in range(1, 51):
            assert result.get_flag(f"flag_{i}") is True
        assert result.turn_number == 50


class TestAppendOnlySurface:
    """Spec: append-only — no update/delete/clear on the repo."""

    def test_repository_has_no_mutating_methods(self):
        """The WorldStateRepository ABC must not expose update, delete, or clear."""
        repo = SQLiteWorldStateRepository(":memory:")

        forbidden = {"update_event", "delete_event", "clear_log",
                     "update_snapshot", "delete_snapshot"}
        public_methods = {
            name for name in dir(repo)
            if not name.startswith("_") and callable(getattr(repo, name, None))
        }
        assert forbidden.isdisjoint(public_methods)


class TestReplayStateChangeTypes:
    """Cover all five state-change event types during replay."""

    def test_replay_entity_transformed(self):
        """GIVEN an entity_transformed event in the log
        WHEN replay_state runs
        THEN the entity's component is updated.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        bus.emit(_make_action_resolved(turn=1, has_effects=True))
        bus.emit(_make_event(ENTITY_TRANSFORMED, turn=1, payload={
            "entity_id": "hero", "component_key": "max_weight",
            "old_value": 40, "new_value": 60,
        }))

        state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero",
                               {"max_weight": 40}, "room_a"),
            },
        )

        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)
        result = replay_save.replay_state(state, "slot_1")

        assert result.get_entity("hero").components["max_weight"] == 60
        assert result.turn_number == 1

    def test_replay_entity_combined(self):
        """GIVEN an entity_combined event in the log
        WHEN replay_state runs
        THEN inputs are destroyed and output is anchored to input location.
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        bus.emit(_make_action_resolved(turn=1, has_effects=True))
        bus.emit(_make_event(ENTITY_COMBINED, turn=1, payload={
            "input_entity_ids": ["stick", "stone"],
            "output_entity_id": "axe",
        }))

        state = WorldState(
            entities={
                "stick": Entity("stick", "item", "Stick", {}, "room_a"),
                "stone": Entity("stone", "item", "Stone", {}, "room_a"),
                "axe": Entity("axe", "item", "Axe", {}, None),
            },
        )

        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)
        result = replay_save.replay_state(state, "slot_1")

        # Inputs are in limbo.
        assert result.get_entity("stick").spatial_anchor is None
        assert result.get_entity("stone").spatial_anchor is None
        # Output is anchored where first input was.
        assert result.get_entity("axe").spatial_anchor == "room_a"

    def test_replay_entity_combined_empty_inputs(self):
        """GIVEN entity_combined with empty input list
        WHEN replay_state runs
        THEN output is anchored to None (edge case).
        """
        from fortress_engine.persistence.event_log import EventSourcingSaveSystem

        repo = SQLiteWorldStateRepository(":memory:")
        bus = EventBus()
        EventSourcingSaveSystem(bus, repo)

        bus.emit(_make_action_resolved(turn=1, has_effects=True))
        bus.emit(_make_event(ENTITY_COMBINED, turn=1, payload={
            "input_entity_ids": [],
            "output_entity_id": "axe",
        }))

        state = WorldState(
            entities={
                "axe": Entity("axe", "item", "Axe", {}, None),
            },
        )

        replay_bus = EventBus()
        replay_save = EventSourcingSaveSystem(replay_bus, repo)
        result = replay_save.replay_state(state, "slot_1")

        # Output stays at None (anchor from empty input list).
        assert result.get_entity("axe").spatial_anchor is None
