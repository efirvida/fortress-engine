"""Integration tests — real MinimalParser + MinimalNarrator with TurnOrchestrator.

Proves the plugin wiring works end-to-end: parse Spanish input → resolve clique
→ execute operators → narrator produces text from events.
"""

from fortress_engine.entities.entity import Entity
from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.goal_evaluator import GoalEvaluator
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_OUTPUT,
    ENTITY_ENTERED,
    ERROR_OUTPUT,
    EngineEvent,
)
from fortress_engine.plugins.parser_interface import MinimalParser
from fortress_engine.plugins.narrator_interface import MinimalNarrator


# ===================================================================
# Helpers — minimal world on disk
# ===================================================================


def _make_minimal_world(tmp_path):
    """Create a minimal 2-room world with items, actions, and macro edges.

    Same layout style as tests/test_integration/test_engine_integration.py.
    """
    import os

    base = tmp_path / "plugin_world"

    def _w(p, c):
        path = base / p
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(c)

    _w("world.yaml", "world_id: plugin_world\nname: PluginTest\n")
    _w(
        "episodes/episode-01.yaml",
        """\
id: episode-01
name: "Test Episode"
order: 1
description: "intro"
requires: []
start_anchor: room_a
goal:
  conditions:
    - type: flag_is_set
      params:
        flag: won
  output: "Victory!"
  side_effects: []
carry_over:
  inventory: []
  flags: []
""",
    )
    _w(
        "shared/player.yaml",
        """\
entity_id: hero
type: player
name: Hero
components:
  max_weight: 40
spatial_anchor: null
""",
    )
    _w(
        "episode-01/rooms/room_a.yaml",
        """\
entity_id: room_a
type: room
name: "Room A"
components:
  visited: false
""",
    )
    _w(
        "episode-01/rooms/room_b.yaml",
        """\
entity_id: room_b
type: room
name: "Room B"
components:
  visited: false
""",
    )
    _w(
        "episode-01/items/key.yaml",
        """\
entity_id: rusty_key
type: item
name: "Rusty Key"
components:
  weight: 1
spatial_anchor: room_a
""",
    )
    _w(
        "episode-01/macros/door.yaml",
        """\
- macro_edge_id: door_north
  from_anchor: room_a
  to_anchor: room_b
  direction: bidirectional
  passage_name: norte
  passage_description: "A wooden door."
""",
    )
    _w(
        "episode-01/actions/pick_up.yaml",
        """\
- hyper_edge_id: pick_key
  name: "Pick key"
  priority: 10
  clique:
    subject: player
    verb: coger
    target: rusty_key
  operators:
    - type: TRANSFER
      entity: rusty_key
      from_container: room_a
      to_container: hero
  output: "Tomas la llave."
""",
    )

    return base


# ===================================================================
# Orchestrator fixture
# ===================================================================


class _OrchFixture:
    """Holds all components for a TurnOrchestrator with real plugins."""

    def __init__(self, tmp_path):
        base = _make_minimal_world(tmp_path)
        loader = EntityLoader(str(base))
        episodes = loader.load_episodes()

        self.bus = EventBus()
        self.parser = MinimalParser()
        self.narrator = MinimalNarrator()
        self.narrator.initialize(self.bus)

        self.state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None),
            },
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="",
            turn_number=0,
        )

        self.ep_mgr = EpisodeManager(episodes, str(base), self.bus)
        self.graph = self.ep_mgr.start_episode("episode-01", self.state)
        assert self.state.current_episode_id == "episode-01"

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

        # Collect events through the bus
        self.received: list[EngineEvent] = []
        self.bus.subscribe("*", lambda e: self.received.append(e))


# ===================================================================
# Tests
# ===================================================================


def test_full_turn_with_real_parser_and_narrator(tmp_path):
    """Execute 'coger llave' through TurnOrchestrator with real plugins.

    - MinimalParser parses Spanish text.
    - TurnOrchestrator resolves the clique and runs operators.
    - MinimalNarrator produces text from action_output events.
    """
    fx = _OrchFixture(tmp_path)

    # NOTE: The minimal parser does NOT resolve entity names → IDs.
    # It returns raw tokens as the target.  The cliques use entity_ids
    # as targets; therefore the raw input must use the entity_id of the
    # item (rusty_key), not its display name (Rusty Key / llave).
    fx.orch.execute_turn("coger rusty_key")

    # State mutated: rusty_key transferred to hero.
    inv = [e.entity_id for e in fx.state.get_player_inventory("hero")]
    assert "rusty_key" in inv

    # Orchestrator emitted canonical events.
    from fortress_engine.events.event_types import (
        TURN_STARTED,
        INPUT_RECEIVED,
        ACTION_ATTEMPTED,
        ENTITY_TRANSFERRED,
        ACTION_OUTPUT,
        ACTION_RESOLVED,
        TURN_ENDED,
    )

    event_types = [e.type for e in fx.received]
    for ev in (TURN_STARTED, INPUT_RECEIVED, ACTION_ATTEMPTED,
               ENTITY_TRANSFERRED, ACTION_OUTPUT, ACTION_RESOLVED, TURN_ENDED):
        assert ev in event_types, f"Expected {ev} in event sequence"

    # Narrator produces text for action_output.
    action_outputs = [e for e in fx.received if e.type == ACTION_OUTPUT]
    assert len(action_outputs) == 1
    narration = fx.narrator.handle_event(action_outputs[0], fx.state)
    assert narration is not None
    assert "Tomas la llave" in narration


def test_movement_with_real_parser_and_narrator(tmp_path):
    """Execute 'ir norte' — movement through macro edge with real parser."""
    fx = _OrchFixture(tmp_path)

    fx.orch.execute_turn("ir norte")

    # Player moved to room_b.
    assert fx.state.get_entity("hero").spatial_anchor == "room_b"

    # entity_entered narration event emitted.
    entered_events = [e for e in fx.received if e.type == ENTITY_ENTERED]
    assert len(entered_events) == 1

    narration = fx.narrator.handle_event(entered_events[0], fx.state)
    assert narration is not None
    assert isinstance(narration, str)
    assert len(narration) > 0


def test_unknown_command_with_real_parser(tmp_path):
    """Unknown command 'xyzzy' → error_output with code+data (no message)."""
    fx = _OrchFixture(tmp_path)

    fx.orch.execute_turn("xyzzy")

    # error_output emitted with code+data
    error_events = [e for e in fx.received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    payload = error_events[0].payload
    assert payload["error_code"] == "no_action"
    assert "data" in payload
    assert "message" not in payload


def test_examinar_with_real_parser(tmp_path):
    """'examinar rusty_key' parses to examinar verb — no matching clique
    (no he in the minimal world), so error_output fires with code+data."""
    fx = _OrchFixture(tmp_path)

    fx.orch.execute_turn("examinar rusty_key")

    # No examinar hyper edge → error_output
    error_events = [e for e in fx.received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    payload = error_events[0].payload
    assert payload["error_code"] == "no_action"
    assert "data" in payload
    assert "message" not in payload


def test_system_commands_bypass_parser(tmp_path):
    """System commands (ESPERAR, GRUPO) are intercepted before parser."""
    fx = _OrchFixture(tmp_path)

    fx.orch.execute_turn("ESPERAR")

    from fortress_engine.events.event_types import TURN_ENDED

    assert any(e.type == TURN_ENDED for e in fx.received)
    # No input_received because system command was intercepted
    from fortress_engine.events.event_types import INPUT_RECEIVED
    assert not any(e.type == INPUT_RECEIVED for e in fx.received)


def test_parser_subject_resolution_in_turn(tmp_path):
    """Parser resolves subject to active_protagonist_id during a real turn."""
    fx = _OrchFixture(tmp_path)

    # Add a second protagonist
    fx.state.entities["sidekick"] = Entity(
        "sidekick", "player", "Sidekick", {}, "room_a"
    )
    fx.state.player_controlled_entities.append("sidekick")
    fx.state.active_protagonist_id = "sidekick"

    # Now the parser should return subject="sidekick"
    parsed = fx.parser.parse("ir norte", fx.state)
    assert parsed.subject == "sidekick"


# ===================================================================
# N5.4: Factory-built ClassicParser + TemplateNarrator integration
# ===================================================================


class _FactoryOrchFixture:
    """Holds all components for a factory-built TurnOrchestrator."""

    def __init__(self, tmp_path):
        from fortress_engine.plugins.factory import (
            PluginConfig,
            create_parser,
            create_narrator,
        )

        base = _make_minimal_world(tmp_path)
        loader = EntityLoader(str(base))
        episodes = loader.load_episodes()

        self.bus = EventBus()
        self.parser = create_parser(PluginConfig("classic"), "es")
        self.narrator = create_narrator(PluginConfig("template"), "es")
        self.narrator.initialize(self.bus)

        self.state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None),
            },
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="",
            turn_number=0,
        )

        self.ep_mgr = EpisodeManager(episodes, str(base), self.bus)
        self.graph = self.ep_mgr.start_episode("episode-01", self.state)
        assert self.state.current_episode_id == "episode-01"

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

        # Collect events through the bus
        self.received: list[EngineEvent] = []
        self.bus.subscribe("*", lambda e: self.received.append(e))


def test_factory_orchestrator_movement_with_template_narrator(tmp_path):
    """Build orchestrator via factory (ClassicParser + TemplateNarrator),
    execute 'ir norte', and verify entity_entered narration."""
    fx = _FactoryOrchFixture(tmp_path)

    fx.orch.execute_turn("ir norte")

    # Player moved to room_b
    assert fx.state.get_entity("hero").spatial_anchor == "room_b"

    # entity_entered emitted
    entered_events = [e for e in fx.received if e.type == ENTITY_ENTERED]
    assert len(entered_events) == 1

    # TemplateNarrator produces text for entity_entered
    narration = fx.narrator.handle_event(entered_events[0], fx.state)
    assert narration is not None
    assert isinstance(narration, str)
    assert len(narration) > 0


def test_factory_orchestrator_integration_turn_structure(tmp_path):
    """Full turn with factory-built orchestrator: movement → canonical event
    sequence fires and TemplateNarrator narration is non-None for key events."""
    fx = _FactoryOrchFixture(tmp_path)

    fx.orch.execute_turn("ir norte")

    from fortress_engine.events.event_types import (
        TURN_STARTED,
        INPUT_RECEIVED,
        ACTION_ATTEMPTED,
        ENTITY_TELEPORTED,
        ACTION_RESOLVED,
        TURN_ENDED,
    )

    event_types = [e.type for e in fx.received]
    for ev in (
        TURN_STARTED, INPUT_RECEIVED, ACTION_ATTEMPTED,
        ENTITY_ENTERED, ENTITY_TELEPORTED, ACTION_RESOLVED, TURN_ENDED,
    ):
        assert ev in event_types, f"Expected {ev} in event sequence"

    # TemplateNarrator handles entity_entered and returns non-None text
    entered_events = [e for e in fx.received if e.type == ENTITY_ENTERED]
    assert len(entered_events) == 1
    narration = fx.narrator.handle_event(entered_events[0], fx.state)
    assert narration is not None
    assert isinstance(narration, str)
    assert len(narration) > 0


def test_factory_orchestrator_unknown_command(tmp_path):
    """Unknown command with factory-built orchestrator → error_output
    and TemplateNarrator renders DEFAULT_SPANISH_MESSAGES text from error_code."""
    fx = _FactoryOrchFixture(tmp_path)

    fx.orch.execute_turn("xyzzy")

    error_events = [e for e in fx.received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1

    narration = fx.narrator.handle_event(error_events[0], fx.state)
    assert narration is not None
    assert isinstance(narration, str)

    # TemplateNarrator dispatches by error_code against DEFAULT_SPANISH_MESSAGES
    payload = error_events[0].payload
    assert payload["error_code"] == "no_action"
    assert "No entiendes cómo hacer" in narration
    assert "xyzzy" in narration
