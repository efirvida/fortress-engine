"""Acceptance walkthrough tests — Slice G final acceptance.

Prove the engine-core epic acceptance criteria:
- Load a minimal world from ``worlds/_test_minimal/``.
- Execute turn cycles with canonical event sequences.
- Walk through a multi-turn sequence: pick up an item, move, trigger the goal.
- No game_over on the happy path.
- Exactly one ``turn_ended`` per turn.
- ``player_controlled_entities`` is always a list (multi-protagonist invariant).
"""

from pathlib import Path

import pytest

from fortress_engine.entities.entity import Entity
from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.goal_evaluator import GoalEvaluator
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_ATTEMPTED,
    ACTION_OUTPUT,
    ACTION_RESOLVED,
    ENTITY_ENTERED,
    ENTITY_TELEPORTED,
    ENTITY_TRANSFERRED,
    EPISODE_COMPLETED,
    ERROR_OUTPUT,
    FLAG_SET,
    GAME_COMPLETED,
    GAME_OVER,
    INPUT_RECEIVED,
    TURN_ENDED,
    TURN_STARTED,
    EngineEvent,
)
from fortress_engine.plugins.narrator_interface import MinimalNarrator
from fortress_engine.plugins.parser_interface import MinimalParser


# ====================================================================
# Path to the on-disk minimal acceptance world
# ====================================================================

_WORLD_PATH = (
    Path(__file__).resolve().parent.parent.parent / "worlds" / "_test_minimal"
)


# ====================================================================
# Fixture — builds a fully wired TurnOrchestrator
# ====================================================================


class _OrchFixture:
    """Holds all components for a TurnOrchestrator with real plugins."""

    def __init__(self):
        self.bus = EventBus()
        self.parser = MinimalParser()
        self.narrator = MinimalNarrator()
        self.narrator.initialize(self.bus)

        loader = EntityLoader(str(_WORLD_PATH))

        # World integrity validated at fixture build time.
        problems = loader.validate_world()
        assert problems == [], f"World validation problems: {problems}"

        episodes = loader.load_episodes()
        assert len(episodes) >= 1

        self.state = WorldState(
            entities={
                "hero": Entity(
                    "hero", "player", "Hero", {"max_weight": 20}, None
                ),
            },
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="",
            turn_number=0,
        )

        self.ep_mgr = EpisodeManager(episodes, str(_WORLD_PATH), self.bus)
        self.graph = self.ep_mgr.start_episode("episode-01", self.state)
        assert self.state.current_episode_id == "episode-01"
        assert self.state.turn_number == 0

        # Episode manager registers all hyper edges under the start_anchor
        # ("cell").  The escape edge must also be reachable from "hall"
        # (the protagonist's anchor after movement).  Copy it.
        escape_edges = self.graph.get_hyper_edges_for_verb("cell", "huir")
        if escape_edges:
            self.graph.add_hyper_edge("hall", escape_edges[0])

        episode = episodes[0]
        self.goal_eval = GoalEvaluator(episode.goal)

        self.orch = TurnOrchestrator(
            state=self.state,
            graph=self.graph,
            event_bus=self.bus,
            parser=self.parser,
            narrator=self.narrator,
            goal_evaluator=self.goal_eval,
            episode_manager=self.ep_mgr,
        )

        # Wildcard subscriber — capture every event.
        self.events: list[EngineEvent] = []
        self.bus.subscribe("*", lambda e: self.events.append(e))

    def turn(self, command: str) -> list[EngineEvent]:
        """Execute one turn and return events emitted during THIS turn only."""
        before = len(self.events)
        self.orch.execute_turn(command)
        return self.events[before:]


# ====================================================================
# Tests
# ====================================================================


def test_walkthrough_world_validation():
    """The minimal acceptance world passes ``validate_world`` with zero problems."""
    loader = EntityLoader(str(_WORLD_PATH))
    problems = loader.validate_world()
    assert problems == []


def test_walkthrough_world_episodes_loaded():
    """The world has at least one episode that is loadable."""
    loader = EntityLoader(str(_WORLD_PATH))
    episodes = loader.load_episodes()
    assert len(episodes) >= 1
    assert episodes[0].id == "episode-01"
    assert episodes[0].start_anchor is not None


def test_walkthrough_pick_up_item():
    """``coger rusty_key`` transfers the item to the protagonist inventory
    and emits the canonical event sequence."""
    fx = _OrchFixture()
    turn_events = fx.turn("coger rusty_key")

    types = [e.type for e in turn_events]
    expected = [
        TURN_STARTED,
        INPUT_RECEIVED,
        ACTION_ATTEMPTED,
        ENTITY_TRANSFERRED,
        ACTION_OUTPUT,
        ACTION_RESOLVED,
        TURN_ENDED,
    ]
    assert types == expected, f"Expected canonical sequence, got {types}"

    # State mutation: key is in hero's inventory.
    inv = [e.entity_id for e in fx.state.get_player_inventory("hero")]
    assert "rusty_key" in inv, f"Expected key in inventory, got {inv}"

    # Exactly one turn_ended.
    turn_ended_count = sum(1 for e in turn_events if e.type == TURN_ENDED)
    assert turn_ended_count == 1

    # action_output carries the expected text.
    outputs = [e for e in turn_events if e.type == ACTION_OUTPUT]
    assert len(outputs) == 1
    assert "recoges" in outputs[0].payload["text"] or "llave" in outputs[0].payload["text"]

    # Narrator produces text for action_output.
    narration = fx.narrator.handle_event(outputs[0], fx.state)
    assert narration is not None
    assert isinstance(narration, str)
    assert len(narration) > 0


def test_walkthrough_movement():
    """``ir norte`` moves the protagonist through the open macro edge
    and emits the canonical movement event sequence."""
    fx = _OrchFixture()
    turn_events = fx.turn("ir norte")

    types = [e.type for e in turn_events]
    expected = [
        TURN_STARTED,
        INPUT_RECEIVED,
        ACTION_ATTEMPTED,
        ENTITY_TELEPORTED,
        ENTITY_ENTERED,
        ACTION_RESOLVED,
        TURN_ENDED,
    ]
    assert types == expected, f"Expected movement sequence, got {types}"

    # State: protagonist moved to hall.
    assert fx.state.get_entity("hero").spatial_anchor == "hall"

    # Exactly one turn_ended.
    turn_ended_count = sum(1 for e in turn_events if e.type == TURN_ENDED)
    assert turn_ended_count == 1

    # entity_entered carries protagonist info.
    entered = [e for e in turn_events if e.type == ENTITY_ENTERED]
    assert len(entered) == 1
    assert entered[0].payload["entity_id"] == "hero"
    assert entered[0].payload["to_anchor_id"] == "hall"

    # Narrator produces text for entity_entered.
    narration = fx.narrator.handle_event(entered[0], fx.state)
    assert narration is not None
    assert isinstance(narration, str)
    assert len(narration) > 0


def test_walkthrough_goal_achievement():
    """After moving to ``hall``, ``huir`` sets the escape flag and triggers
    goal evaluation → ``episode_completed`` → ``game_completed``."""
    fx = _OrchFixture()

    # First, move to hall.
    fx.turn("ir norte")
    assert fx.state.get_entity("hero").spatial_anchor == "hall"

    # Then, escape (sets flag → goal triggers).
    turn_events = fx.turn("huir hall")

    types = [e.type for e in turn_events]
    # Canonical sequence for a micro action that triggers the goal:
    # turn_started → input_received → action_attempted → flag_set →
    # action_output → action_resolved → episode_completed → game_completed →
    # turn_ended
    assert TURN_STARTED in types
    assert INPUT_RECEIVED in types
    assert ACTION_ATTEMPTED in types
    assert FLAG_SET in types
    assert ACTION_OUTPUT in types
    assert ACTION_RESOLVED in types
    assert EPISODE_COMPLETED in types, f"Expected episode_completed, got {types}"
    assert GAME_COMPLETED in types, f"Expected game_completed, got {types}"
    assert TURN_ENDED in types

    # Verify the flag was actually set.
    assert fx.state.get_flag("escaped") is True

    # Exactly one turn_ended.
    turn_ended_count = sum(1 for e in turn_events if e.type == TURN_ENDED)
    assert turn_ended_count == 1


def test_walkthrough_full_sequence():
    """The complete walkthrough (3 turns) never emits game_over
    and every turn has exactly one turn_ended."""
    fx = _OrchFixture()

    # Turn 1: pick up the key.
    fx.turn("coger rusty_key")

    # Turn 2: move north to hall.
    fx.turn("ir norte")

    # Turn 3: escape — triggers goal → game_completed.
    fx.turn("huir hall")

    # No game_over anywhere in the happy path.
    all_types = [e.type for e in fx.events]
    assert GAME_OVER not in all_types, f"Unexpected GAME_OVER in {all_types}"

    # Every turn ended the game.
    assert EPISODE_COMPLETED in all_types
    assert GAME_COMPLETED in all_types

    # Turn count confirmed: 3 turn_started, 3 turn_ended.
    assert sum(1 for e in fx.events if e.type == TURN_STARTED) == 3
    assert sum(1 for e in fx.events if e.type == TURN_ENDED) == 3

    # Final state: turn_number advanced across 3 turns.
    assert fx.state.turn_number == 3


def test_walkthrough_player_controlled_is_list():
    """``player_controlled_entities`` is always a list (multi-protagonist
    invariant — architecture constant #2)."""
    fx = _OrchFixture()
    assert isinstance(fx.state.player_controlled_entities, list)
    assert fx.state.player_controlled_entities == ["hero"]
    # active_protagonist_id must be one of them.
    assert fx.state.active_protagonist_id in fx.state.player_controlled_entities


def test_walkthrough_no_game_over_on_happy_path():
    """A simple take-and-move sequence never produces game_over."""
    fx = _OrchFixture()
    fx.turn("coger rusty_key")
    fx.turn("ir norte")

    all_types = [e.type for e in fx.events]
    assert GAME_OVER not in all_types


def test_walkthrough_unknown_command_produces_error_output():
    """An unknown command ``xyzzy`` goes through the error_output path
    without crashing."""
    fx = _OrchFixture()
    turn_events = fx.turn("xyzzy")

    types = [e.type for e in turn_events]
    assert TURN_STARTED in types
    assert INPUT_RECEIVED in types
    assert ERROR_OUTPUT in types
    assert TURN_ENDED in types

    # No state change events.
    for forbidden in (ENTITY_TRANSFERRED, ENTITY_TELEPORTED, FLAG_SET):
        assert forbidden not in types

    # Exactly one turn_ended.
    assert sum(1 for e in turn_events if e.type == TURN_ENDED) == 1
