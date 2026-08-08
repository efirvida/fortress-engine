"""RED tests for orchestrator save/load integration — P3.2.

These tests describe the required behavior BEFORE the orchestrator
save/load implementation exists. They import symbols that will exist
only after P3.3+P3.4 are complete.
"""

from __future__ import annotations

import pytest

from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ERROR_OUTPUT,
    GAME_LOADED,
    GAME_SAVED,
    SAVE_REPLAY_STARTED,
    SAVE_REPLAY_ENDED,
    TURN_ENDED,
    EngineEvent,
)


# ---------------------------------------------------------------------------
# Fake repository and save_system for controlled testing
# ---------------------------------------------------------------------------


class _FakeRepository:
    """In-memory fake that records calls and returns controlled data."""

    def __init__(self):
        self.snapshots: dict[str, tuple[WorldState, int]] = {}
        self.events: list[EngineEvent] = []
        self._append_calls: list[EngineEvent] = []
        self._snapshot_calls: list[tuple] = []

    def append_event(self, event: EngineEvent) -> None:
        self._append_calls.append(event)
        self.events.append(event)

    def get_event_log(self, since_turn: int = 0) -> list[EngineEvent]:
        return [e for e in self.events if e.turn_number > since_turn]

    def get_latest_turn(self) -> int:
        if not self.events:
            return 0
        return max(e.turn_number for e in self.events)

    def save_snapshot(self, state: WorldState, turn: int, save_slot: str) -> None:
        self._snapshot_calls.append((state, turn, save_slot))
        self.snapshots[save_slot] = (state, turn)

    def load_latest_snapshot(self, save_slot: str) -> tuple[WorldState, int] | None:
        return self.snapshots.get(save_slot)


class _FakeSaveSystem:
    """Fake save_system that records calls and returns controlled replay."""

    def __init__(self, replay_result: WorldState | None = None):
        self._replay_calls: list[tuple] = []
        self._replay_result = replay_result

    def replay_state(
        self, state: WorldState, save_slot: str, graph=None
    ) -> WorldState:
        self._replay_calls.append((state, save_slot, graph))
        if self._replay_result is not None:
            # Mutate in place — the real save_system does the same.
            state.entities = self._replay_result.entities
            state.flag_book = self._replay_result.flag_book
            state.player_controlled_entities = list(
                self._replay_result.player_controlled_entities
            )
            state.active_protagonist_id = (
                self._replay_result.active_protagonist_id
            )
            state.current_episode_id = (
                self._replay_result.current_episode_id
            )
            state.turn_number = self._replay_result.turn_number
        return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    turn: int = 0,
    protagonist_id: str = "hero",
    episode_id: str = "ep-01",
) -> WorldState:
    return WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {}, "room_a"),
            "room_a": Entity("room_a", "room", "Room A", {}, None),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id=protagonist_id,
        current_episode_id=episode_id,
        turn_number=turn,
    )


def _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                        repository=None, save_system=None):
    """Build a TurnOrchestrator with optional persistence deps."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator
    from fortress_engine.plugins.parser_interface import ParserInterface
    from fortress_engine.plugins.narrator_interface import NarratorInterface

    class _StubParser(ParserInterface):
        def parse(self, raw_text, ws):
            from fortress_engine.entities.entity import ParsedCommand
            return ParsedCommand(subject="hero", verb="mirar", target=None)

    class _StubNarrator(NarratorInterface):
        def initialize(self, eb): pass
        def handle_event(self, e, ws): return None

    return TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=_StubParser(),
        narrator=_StubNarrator(),
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=repository,
        save_system=save_system,
    )


# ---------------------------------------------------------------------------
# P3.2 — Orchestrator save/load command handling
# ---------------------------------------------------------------------------


class TestGuardarCommand:
    """Spec: GUARDAR dispatches save, emits game_saved, turn unchanged."""

    def test_guardar_default_slots_game_saved(self, tmp_path):
        """GUARDAR (no number) emits game_saved with slot_1."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        turn_before = state.turn_number
        orch.execute_turn("GUARDAR")

        # game_saved emitted.
        saved = [e for e in received if e.type == GAME_SAVED]
        assert len(saved) == 1
        assert saved[0].payload.get("save_slot") == "slot_1"

        # Turn unchanged.
        assert state.turn_number == turn_before

        # No error.
        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 0

    def test_guardar_with_number_saves_correct_slot(self, tmp_path):
        """GUARDAR 2 emits game_saved with slot_2."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("GUARDAR 2")

        saved = [e for e in received if e.type == GAME_SAVED]
        assert len(saved) == 1
        assert saved[0].payload.get("save_slot") == "slot_2"

    def test_guardar_3_saves_slot_3(self, tmp_path):
        """GUARDAR 3 emits game_saved with slot_3."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("GUARDAR 3")

        saved = [e for e in received if e.type == GAME_SAVED]
        assert len(saved) == 1
        assert saved[0].payload.get("save_slot") == "slot_3"


class TestCargarCommand:
    """Spec: CARGAR loads snapshot+replay, emits game_loaded, turn restored."""

    def test_cargar_loads_and_emits_game_loaded(self, tmp_path):
        """CARGAR 1 with valid slot emits game_loaded."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        # Pre-populate a snapshot so the slot "exists".
        repo.save_snapshot(_make_state(turn=5), 5, "slot_1")

        restored = _make_state(turn=10)
        save_sys = _FakeSaveSystem(replay_result=restored)

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("CARGAR 1")

        # game_loaded emitted.
        loaded = [e for e in received if e.type == GAME_LOADED]
        assert len(loaded) == 1
        assert loaded[0].payload.get("save_slot") == "slot_1"

        # State was replaced with replay result.
        assert state.turn_number == 10

    def test_cargar_restores_turn_number(self, tmp_path):
        """CARGAR restores turn number from replay."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        repo.save_snapshot(_make_state(turn=5), 5, "slot_1")

        restored = _make_state(turn=42)
        save_sys = _FakeSaveSystem(replay_result=restored)

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("CARGAR 1")

        assert state.turn_number == 42

    def test_cargar_preserves_graph_reference(self, tmp_path):
        """CARGAR uses the current graph during replay."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        repo.save_snapshot(_make_state(turn=5), 5, "slot_1")

        save_sys = _FakeSaveSystem(replay_result=_make_state(turn=5))

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("CARGAR 1")

        # replay_state was called with the graph.
        assert len(save_sys._replay_calls) == 1
        _, slot, passed_graph = save_sys._replay_calls[0]
        assert slot == "slot_1"
        assert passed_graph is graph


class TestNoRepositoryError:
    """Spec: no repository/save_system → no_repository error, turn unchanged."""

    def test_guardar_without_repository_emits_error(self, tmp_path):
        """GUARDAR without repository emits no_repository error."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=None, save_system=None)

        turn_before = state.turn_number
        orch.execute_turn("GUARDAR 1")

        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 1
        assert errors[0].payload["error_code"] == "no_repository"

        # Turn unchanged.
        assert state.turn_number == turn_before

        # No game_saved.
        assert not any(e.type == GAME_SAVED for e in received)

    def test_cargar_without_repository_emits_error(self, tmp_path):
        """CARGAR without repository emits no_repository error."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=None, save_system=None)

        turn_before = state.turn_number
        orch.execute_turn("CARGAR 2")

        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 1
        assert errors[0].payload["error_code"] == "no_repository"

        assert state.turn_number == turn_before
        assert not any(e.type == GAME_LOADED for e in received)

    def test_orchestrator_usable_after_no_repository_error(self, tmp_path):
        """After a no_repository error, the orchestrator still runs normal turns."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=None, save_system=None)

        # Trigger no_repository — this emits error but doesn't crash.
        orch.execute_turn("GUARDAR")

        # Now run a normal turn — should succeed (the turn cycle runs).
        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        orch.execute_turn("gritar")

        # The turn completed (turn_ended is always emitted after a normal turn).
        assert any(e.type == TURN_ENDED for e in received)


class TestInvalidSlot:
    """Spec: invalid slot numbers → invalid_slot error."""

    def test_guardar_4_emits_invalid_slot(self, tmp_path):
        """GUARDAR 4 emits invalid_slot error."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        turn_before = state.turn_number
        orch.execute_turn("GUARDAR 4")

        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 1
        assert errors[0].payload["error_code"] == "invalid_slot"

        assert state.turn_number == turn_before
        assert not any(e.type == GAME_SAVED for e in received)

    def test_cargar_0_emits_invalid_slot(self, tmp_path):
        """CARGAR 0 emits invalid_slot error."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        turn_before = state.turn_number
        orch.execute_turn("CARGAR 0")

        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 1
        assert errors[0].payload["error_code"] == "invalid_slot"

        assert state.turn_number == turn_before
        assert not any(e.type == GAME_LOADED for e in received)

    def test_guardar_negative_emits_invalid_slot(self, tmp_path):
        """GUARDAR -1 emits invalid_slot error."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("GUARDAR -1")

        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 1
        assert errors[0].payload["error_code"] == "invalid_slot"


class TestMissingSlot:
    """Spec: missing slot → error_output(missing_slot), state unchanged."""

    def test_cargar_missing_slot_emits_error(self, tmp_path):
        """CARGAR 3 with no snapshot emits missing_slot error."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()  # Empty — no snapshots, no events.
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        turn_before = state.turn_number
        orch.execute_turn("CARGAR 3")

        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 1
        assert errors[0].payload["error_code"] == "missing_slot"

        # State and turn unchanged.
        assert state.turn_number == turn_before
        assert not any(e.type == GAME_LOADED for e in received)


class TestSaveCommandAliases:
    """Spec: 'save' and 'load' English aliases work the same."""

    def test_english_save_alias_works(self, tmp_path):
        """SAVE (English alias) works the same as GUARDAR."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("SAVE 2")

        saved = [e for e in received if e.type == GAME_SAVED]
        assert len(saved) == 1
        assert saved[0].payload.get("save_slot") == "slot_2"

    def test_english_load_alias_works(self, tmp_path):
        """LOAD (English alias) works the same as CARGAR."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        repo.save_snapshot(_make_state(turn=5), 5, "slot_1")

        save_sys = _FakeSaveSystem(replay_result=_make_state(turn=5))

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("LOAD 1")

        loaded = [e for e in received if e.type == GAME_LOADED]
        assert len(loaded) == 1
        assert loaded[0].payload.get("save_slot") == "slot_1"


class TestParseSaveSlotEdgeCases:
    """Coverage: _parse_save_slot edge cases and slots with events but no snapshot."""

    def test_guardar_non_numeric_suffix(self, tmp_path):
        """GUARDAR with non-numeric suffix (xyz) falls back to slot_1."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        repo = _FakeRepository()
        save_sys = _FakeSaveSystem()

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("GUARDAR xyz")

        saved = [e for e in received if e.type == GAME_SAVED]
        assert len(saved) == 1
        # Falls back to slot_1.
        assert saved[0].payload.get("save_slot") == "slot_1"

    def test_cargar_with_events_no_snapshot(self, tmp_path):
        """CARGAR a slot that has events but no snapshot should load successfully."""
        from tests.test_engine.test_orchestrator import _setup_orchestrator

        state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

        received: list[EngineEvent] = []
        bus.subscribe("*", lambda e: received.append(e))

        # Repository has events but NO snapshot for slot_1.
        repo = _FakeRepository()
        repo.events = [
            EngineEvent.create("action_resolved", 1, {"has_effects": True}),
        ]

        save_sys = _FakeSaveSystem(replay_result=_make_state(turn=1))

        orch = _build_orchestrator(state, graph, bus, goal_eval, ep_mgr,
                                   repository=repo, save_system=save_sys)

        orch.execute_turn("CARGAR 1")

        # Load succeeds (events exist, no missing_slot error).
        loaded = [e for e in received if e.type == GAME_LOADED]
        assert len(loaded) == 1
        errors = [e for e in received if e.type == ERROR_OUTPUT]
        assert len(errors) == 0
