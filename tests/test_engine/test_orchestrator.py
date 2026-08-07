"""Tests for TurnOrchestrator — RED phase (E1.3).

TurnOrchestrator coordinates one active-protagonist turn: parse → validate →
execute operators → emit events → evaluate goals → transition/end.

All tests follow Strict TDD: RED first (this file), then GREEN in orchestrator.py.

Parser and narrator stubs are defined inline — Slice E2 adds real implementations.
"""

from fortress_engine.entities.entity import (
    CarryOver,
    Entity,
    Episode,
    GoalCondition,
    GoalConditions,
    ParsedCommand,
)
from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge, MacroEdge
from fortress_engine.engine.goal_evaluator import GoalEvaluator
from fortress_engine.engine.state import WorldState
from fortress_engine.engine.operators import (
    TransferOp,
    FlagOp,
    TeleportOp,
)
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_ATTEMPTED,
    ACTION_OUTPUT,
    ACTION_RESOLVED,
    ENTITY_ENTERED,
    ENTITY_TELEPORTED,
    ENTITY_TRANSFERRED,
    EPISODE_COMPLETED,
    EPISODE_STARTED,
    EPISODE_TRANSITION,
    ERROR_OUTPUT,
    FLAG_SET,
    GAME_OVER,
    INPUT_RECEIVED,
    PROTAGONISTS_LISTED,
    PROTAGONIST_SWITCHED,
    TURN_STARTED,
    TURN_ENDED,
    EngineEvent,
)

from fortress_engine.plugins.parser_interface import ParserInterface
from fortress_engine.plugins.narrator_interface import NarratorInterface


# ===================================================================
# Minimal stubs (Slice E1 — real implementations in E2)
# ===================================================================


class _StubParser(ParserInterface):
    """Parser that returns a pre-configured command."""
    def __init__(self, command: ParsedCommand):
        self.command = command

    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        return self.command


class _StubNarrator(NarratorInterface):
    """Narrator that records events instead of producing text."""
    def __init__(self):
        self.events: list[EngineEvent] = []

    def initialize(self, event_bus: EventBus) -> None:
        event_bus.subscribe("*", lambda e: self.events.append(e))

    def handle_event(self, event: EngineEvent, world_state: WorldState) -> str | None:
        return None


# ===================================================================
# Fixtures
# ===================================================================


def _make_world(tmp_path):
    """Create a minimal world with 2 rooms, 1 item, and episode metadata.

    Same layout as the integration test fixture.
    """
    import os

    base = tmp_path / "test_world"

    def _w(p, c):
        path = base / p
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(c)

    _w("world.yaml", "world_id: test_world\nname: Test\n")
    _w(
        "episodes/episode-01.yaml",
        """\
id: episode-01
name: "Part One"
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
  passage_name: north
  passage_description: "A wooden door."
""",
    )
    _w(
        "episode-01/macros/danger_door.yaml",
        """\
- macro_edge_id: danger_pass
  from_anchor: room_b
  to_anchor: room_a
  direction: bidirectional
  passage_name: back
  passage_description: "A dangerous path."
  requires_item: amulet
  death_message: "You died on the path."
  open: true
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
    _w(
        "episode-01/actions/pick_up_fails.yaml",
        """\
- hyper_edge_id: pick_heavy
  name: "Try heavy"
  priority: 5
  clique:
    subject: player
    verb: coger
    target: rusty_key
  operators:
    - type: TRANSFER
      entity: non_existent
      from_container: room_a
      to_container: hero
  output: "Should not show."
""",
    )
    _w(
        "episode-01/actions/set_flag.yaml",
        """\
- hyper_edge_id: set_won
  name: "Win the game"
  priority: 10
  clique:
    subject: player
    verb: gritar
  operators:
    - type: FLAG
      flag: won
      value: true
  output: "Gritaste victoria."
""",
    )
    _w(
        "episode-01/actions/kill_player.yaml",
        """\
- hyper_edge_id: self_destruct
  name: "Self destruct"
  priority: 10
  clique:
    subject: player
    verb: explotar
  operators:
    - type: FLAG
      flag: player_dead
      value: true
  output: "Boom!"
""",
    )

    return base


def _setup_orchestrator(tmp_path):
    """Build a full orchestrator with an episode-01 world loaded."""
    from fortress_engine.engine.episode_manager import EpisodeManager
    from fortress_engine.entities.loader import EntityLoader

    base = _make_world(tmp_path)
    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()

    bus = EventBus()
    ep_mgr = EpisodeManager(episodes, str(base), bus)

    state = WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="",
        turn_number=0,
    )

    graph = ep_mgr.start_episode("episode-01", state)

    # Goal evaluator for episode-01
    episode = episodes[0]
    goal_eval = GoalEvaluator(episode.goal)

    return state, graph, bus, ep_mgr, goal_eval


# ===================================================================
# Constructor
# ===================================================================


def test_constructor_stores_dependencies(tmp_path):
    """TurnOrchestrator accepts all required dependencies."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )
    assert orch is not None


# ===================================================================
# execute_turn — successful micro action
# ===================================================================


def test_execute_turn_successful_action_event_order(tmp_path):
    """A successful 'coger rusty_key' produces the canonical event sequence."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="coger", target="rusty_key")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("coger llave")

    # Canonical event order per spec:
    # turn_started, input_received, action_attempted,
    # [entity_transferred], action_output, action_resolved, turn_ended
    event_types = [e.type for e in received]
    assert TURN_STARTED in event_types
    assert INPUT_RECEIVED in event_types
    assert ACTION_ATTEMPTED in event_types
    assert ENTITY_TRANSFERRED in event_types
    assert ACTION_OUTPUT in event_types
    assert ACTION_RESOLVED in event_types
    assert TURN_ENDED in event_types

    # Verify indices order
    idx_turn_started = event_types.index(TURN_STARTED)
    idx_input_recv = event_types.index(INPUT_RECEIVED)
    idx_attempted = event_types.index(ACTION_ATTEMPTED)
    idx_transferred = event_types.index(ENTITY_TRANSFERRED)
    idx_output = event_types.index(ACTION_OUTPUT)
    idx_resolved = event_types.index(ACTION_RESOLVED)
    idx_turn_ended = event_types.index(TURN_ENDED)

    assert idx_turn_started < idx_input_recv < idx_attempted
    assert idx_attempted < idx_transferred < idx_output < idx_resolved
    assert idx_resolved < idx_turn_ended

    # State mutated: rusty_key in hero's inventory
    inv = [e.entity_id for e in state.get_player_inventory("hero")]
    assert "rusty_key" in inv

    # turn_number incremented
    assert state.turn_number == 1


# ===================================================================
# execute_turn — no clique → error_output
# ===================================================================


def test_execute_turn_no_clique_emits_error(tmp_path):
    """When no clique matches, error_output is emitted and state is unchanged."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    # A verb that has no hyper edges: "volar"
    parser = _StubParser(ParsedCommand(subject="hero", verb="volar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("volar")

    # error_output emitted
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1

    # No action events
    assert not any(e.type == ACTION_ATTEMPTED for e in received)

    # turn_ended still emitted
    assert any(e.type == TURN_ENDED for e in received)


# ===================================================================
# System command: TERMINAR
# ===================================================================


def test_execute_turn_system_terminar(tmp_path):
    """TERMINAR emits game_over with reason player_quit."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("TERMINAR")

    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    assert game_over_events[0].payload["reason"] == "player_quit"


# ===================================================================
# System command: CAMBIAR A
# ===================================================================


def test_execute_turn_system_cambiar_a(tmp_path):
    """CAMBIAR A <name> switches active_protagonist_id and emits protagonist_switched."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a second player-controlled entity
    state.entities["sidekick"] = Entity("sidekick", "player", "Sidekick", {}, "room_a")
    state.player_controlled_entities = ["hero", "sidekick"]

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("CAMBIAR A Sidekick")

    # protagonist_switched emitted
    switched = [e for e in received if e.type == PROTAGONIST_SWITCHED]
    assert len(switched) == 1
    assert switched[0].payload["from_protagonist_id"] == "hero"
    assert switched[0].payload["to_protagonist_id"] == "sidekick"

    # active_protagonist_id updated
    assert state.active_protagonist_id == "sidekick"

    # player_controlled_entities still a list, unchanged structure
    assert state.player_controlled_entities == ["hero", "sidekick"]


# ===================================================================
# System command: ESPERAR
# ===================================================================


def test_execute_turn_system_esperar(tmp_path):
    """ESPERAR is a no-op (passes the turn)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ESPERAR")

    # turn_started and turn_ended still emitted (the turn happened)
    assert any(e.type == TURN_STARTED for e in received)
    assert any(e.type == TURN_ENDED for e in received)

    # No action events
    assert not any(e.type == ACTION_ATTEMPTED for e in received)


# ===================================================================
# System command: GRUPO
# ===================================================================


def test_execute_turn_system_grupo(tmp_path):
    """GRUPO emits protagonists_listed."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("GRUPO")

    grupo_events = [e for e in received if e.type == PROTAGONISTS_LISTED]
    assert len(grupo_events) == 1


# ===================================================================
# Movement via macro edge
# ===================================================================


def test_execute_turn_movement_emits_single_turn_ended(tmp_path):
    """Movement via macro edge must emit exactly ONE turn_ended per turn.

    Regression: _handle_movement already calls _post_action_checks, and
    execute_turn called it again → duplicate turn_ended (and duplicate
    game_over when player_dead).
    """
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir north")

    turn_ended_count = sum(1 for e in received if e.type == TURN_ENDED)
    assert turn_ended_count == 1, (
        f"Expected exactly one turn_ended per movement, got {turn_ended_count}"
    )


def test_execute_turn_movement_macro_edge(tmp_path):
    """Movement via macro edge emits entity_teleported + entity_entered."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    # Parse "ir north" — the orchestrator should detect this as movement
    # and find the macro edge with passage_name="north"
    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir north")

    # Verify movement events in order
    event_types = [e.type for e in received]

    assert ENTITY_TELEPORTED in event_types
    assert ENTITY_ENTERED in event_types

    idx_teleported = event_types.index(ENTITY_TELEPORTED)
    idx_entered = event_types.index(ENTITY_ENTERED)

    # entity_teleported comes before entity_entered
    assert idx_teleported < idx_entered

    # Player's spatial_anchor changed
    assert state.get_entity("hero").spatial_anchor == "room_b"


# ===================================================================
# Movement — requires_text macro edges (text gate)
# ===================================================================


def _add_text_door(graph, passage_name="puerta principal"):
    """Register a closed requires_text edge from room_a in *graph*."""
    graph.add_macro_edge(
        MacroEdge(
            macro_edge_id="pass_principal",
            from_anchor="room_a",
            to_anchor="room_b",
            direction="bidirectional",
            passage_name=passage_name,
            passage_description="A locked main door.",
            requires_text="treinta y nueve",
            open=False,
        )
    )


def test_movement_abrir_text_door_blocked(tmp_path):
    """ABRIR on a closed requires_text door without the text → error_output."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    _add_text_door(graph)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="abrir", target="puerta principal")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("abrir puerta principal")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    assert error_events[0].payload["error_code"] == "blocked"
    assert "cerrada" in error_events[0].payload["message"]

    # No teleport — the hero stays in room_a and the door stays closed.
    assert state.get_entity("hero").spatial_anchor == "room_a"
    assert not any(e.type == ENTITY_TELEPORTED for e in received)
    assert graph.get_macro_edge_by_passage_name("room_a", "puerta principal").open is False


def test_movement_abrir_text_correct_opens_and_moves(tmp_path):
    """ABRIR ... DICIENDO <correct text> → opens the door and teleports."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    _add_text_door(graph)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(
            subject="hero",
            verb="abrir",
            target="puerta principal",
            text="treinta y nueve",
        )
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("abrir puerta principal diciendo treinta y nueve")

    # Door opened and hero moved to room_b.
    assert graph.get_macro_edge_by_passage_name("room_a", "puerta principal").open is True
    assert state.get_entity("hero").spatial_anchor == "room_b"
    assert any(e.type == ENTITY_TELEPORTED for e in received)

    # No error was emitted.
    assert not any(e.type == ERROR_OUTPUT for e in received)


def test_movement_ir_open_door_still_works(tmp_path):
    """Regression: IR through an open edge still moves the hero."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir north")

    assert state.get_entity("hero").spatial_anchor == "room_b"
    assert any(e.type == ENTITY_TELEPORTED for e in received)


def test_movement_ir_closed_text_door_blocked(tmp_path):
    """IR on a closed requires_text edge without the text → error_output.

    The orchestrator passes text=None for IR commands, so the door must
    not open and the hero must not move.
    """
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    _add_text_door(graph)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="puerta principal")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir puerta principal")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    assert error_events[0].payload["error_code"] == "blocked"

    assert state.get_entity("hero").spatial_anchor == "room_a"
    assert not any(e.type == ENTITY_TELEPORTED for e in received)
    assert graph.get_macro_edge_by_passage_name("room_a", "puerta principal").open is False


# ===================================================================
# Movement fails (danger without item)
# ===================================================================


def test_execute_turn_danger_macro_edge_fails(tmp_path):
    """Movement through a requires_item gate without the item → game_over."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Move hero to room_b first so we can try the fatal edge back
    from fortress_engine.engine.operators import execute_teleport

    execute_teleport(state, TeleportOp(entity="hero", to_anchor="room_b"))

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="back")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir back")

    # Fatal gate requires amulet, hero doesn't have it → game_over
    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    assert "You died on the path." in game_over_events[0].payload.get("reason", "")


# ===================================================================
# Operator fails
# ===================================================================


def test_execute_turn_operator_fails_emits_error(tmp_path):
    """When an operator fails, error_output is emitted and the sequence stops."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    # Target the low-priority edge that references a nonexistent entity
    parser = _StubParser(
        ParsedCommand(subject="hero", verb="coger", target="rusty_key")
    )

    # Remove the high-priority edge so the failing one is selected
    hyper_edges = graph.get_hyper_edges_for_verb("room_a", "coger")
    if len(hyper_edges) > 1 and hyper_edges[1].priority < hyper_edges[0].priority:
        graph._hyper_edges["room_a"]["coger"] = [hyper_edges[1]]  # only the failing one

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("coger llave")

    # error_output emitted (operator failure)
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1

    # No state-change events (the failing TRANSFER didn't emit)
    assert not any(e.type == ENTITY_TRANSFERRED for e in received)


# ===================================================================
# Goal completion → episode transition
# ===================================================================


def test_execute_turn_goal_completion_episode_transition(tmp_path):
    """When goal is met and next episode exists, orchestrator transitions."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Pre-set the goal flag so "gritar" triggers completion
    # Actually, the goal is flag "won"=true, and "gritar" sets it.

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="gritar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    # The goal is just flag "won"=true. The "gritar" action sets it.
    # But there's no next episode in the fixture (only episode-01).
    # So this tests that goal evaluation happens and game_completed
    # fires when no next episode exists.
    orch.execute_turn("gritar")

    # The "won" flag should be set
    assert state.get_flag("won") is True

    # Since no next episode exists, game_completed should fire
    from fortress_engine.events.event_types import GAME_COMPLETED

    completed = [e for e in received if e.type == GAME_COMPLETED]
    assert len(completed) == 1


# ===================================================================
# player_dead check
# ===================================================================


def test_execute_turn_player_dead_emits_game_over(tmp_path):
    """When player_dead flag is set, game_over is emitted."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="explotar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("explotar")

    # player_dead flag set
    assert state.get_flag("player_dead") is True

    # game_over emitted
    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    # The reason should indicate death
    assert game_over_events[0].payload["reason"] == "player_death"


# ===================================================================
# Multi-protagonist invariant
# ===================================================================


def test_player_controlled_entities_remains_a_list(tmp_path):
    """player_controlled_entities is always a list, never a singleton."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add second protagonist
    state.entities["sidekick"] = Entity("sidekick", "player", "Sidekick", {}, "room_a")
    state.player_controlled_entities = ["hero", "sidekick"]

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="coger", target="rusty_key")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("coger llave")

    # player_controlled_entities must remain a list with both entries
    assert isinstance(state.player_controlled_entities, list)
    assert len(state.player_controlled_entities) == 2
    assert "hero" in state.player_controlled_entities
    assert "sidekick" in state.player_controlled_entities


# ===================================================================
# turn_number increments
# ===================================================================


def test_execute_turn_increments_turn_number(tmp_path):
    """Each turn increments turn_number by 1."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    assert state.turn_number == 0

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("mirar")
    assert state.turn_number == 1

    orch.execute_turn("mirar")
    assert state.turn_number == 2

    orch.execute_turn("mirar")
    assert state.turn_number == 3


# ===================================================================
# System command: GUARDAR/CARGAR (graceful without repository)
# ===================================================================


def test_execute_turn_guardar_without_repository_emits_error(tmp_path):
    """GUARDAR without a repository emits error_output gracefully."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=None,  # no persistence layer
    )

    orch.execute_turn("GUARDAR 1")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) >= 1


def test_execute_turn_cargar_without_repository_emits_error(tmp_path):
    """CARGAR without a repository emits error_output gracefully."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=None,
    )

    orch.execute_turn("CARGAR 1")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) >= 1


# ===================================================================
# System commands: bare GUARDAR / CARGAR (no slot)
# ===================================================================


def test_execute_turn_guardar_bare_without_repository(tmp_path):
    """GUARDAR (without slot number) emits error_output gracefully."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=None,
    )

    orch.execute_turn("guardar")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) >= 1


def test_execute_turn_cargar_bare_without_repository(tmp_path):
    """CARGAR (without slot number) emits error_output gracefully."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=None,
    )

    orch.execute_turn("cargar")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) >= 1


# ===================================================================
# CAMBIAR A — invalid name / same protagonist
# ===================================================================


def test_execute_turn_cambiar_a_invalid_name(tmp_path):
    """CAMBIAR A <nonexistent> emits error_output."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("CAMBIAR A Nonexistent")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1


# ===================================================================
# Movement — conditional edge blocked (no death)
# ===================================================================


def test_execute_turn_conditional_edge_blocked(tmp_path):
    """requires_flag macro edge that is blocked emits error_output (no death)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a flag-gate edge from room_a that requires a flag
    from fortress_engine.engine.graph import MacroEdge

    cond_edge = MacroEdge(
        macro_edge_id="conditional_door",
        from_anchor="room_a",
        to_anchor="room_b",
        direction="bidirectional",
        passage_name="este",
        passage_description="A locked gate.",
        requires_flag="key_found",
    )
    graph.add_macro_edge(cond_edge)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="este")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir este")

    # Should emit error_output (blocked, not death)
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) >= 1
    # No game_over (not fatal)
    assert not any(e.type == GAME_OVER for e in received)


# ===================================================================
# Multi-episode transition success (covers graph replacement path)
# ===================================================================


def test_execute_turn_goal_transitions_to_next_episode(tmp_path):
    """When goal is met and next episode exists, transition succeeds and
    graph is replaced (covers the new_graph assignment branch)."""
    import os

    base = tmp_path / "multi_world"

    def _w(p, c):
        path = base / p
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(c)

    _w("world.yaml", "world_id: multi\nname: Multi\n")
    _w(
        "episodes/episode-01.yaml",
        """\
id: episode-01
name: "One"
order: 1
description: ""
requires: []
start_anchor: room_a
goal:
  conditions:
    - type: flag_is_set
      params:
        flag: done1
  output: "Ep1 done!"
  side_effects: []
carry_over:
  inventory: []
  flags: []
""",
    )
    _w(
        "episodes/episode-02.yaml",
        """\
id: episode-02
name: "Two"
order: 2
description: ""
requires: [episode-01]
start_anchor: room_b
goal:
  conditions:
    - type: flag_is_set
      params:
        flag: done2
  output: "Ep2 done!"
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
        "episode-01/actions/win.yaml",
        """\
- hyper_edge_id: trigger_win
  name: "Win"
  priority: 10
  clique:
    subject: player
    verb: gritar
  operators:
    - type: FLAG
      flag: done1
      value: true
  output: "Done."
""",
    )
    _w(
        "episode-02/rooms/room_b.yaml",
        """\
entity_id: room_b
type: room
name: "Room B"
components:
  visited: false
""",
    )

    from fortress_engine.entities.loader import EntityLoader
    from fortress_engine.engine.episode_manager import EpisodeManager
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    loader = EntityLoader(str(base))
    episodes = loader.load_episodes()
    assert len(episodes) == 2

    bus = EventBus()
    ep_mgr = EpisodeManager(episodes, str(base), bus)

    state = WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {"max_weight": 40}, None),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="",
        turn_number=0,
    )

    graph = ep_mgr.start_episode("episode-01", state)
    goal_eval = GoalEvaluator(episodes[0].goal)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="gritar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("gritar")

    # Goal completed → episode_transition + episode_started emitted
    assert any(e.type == EPISODE_COMPLETED for e in received)
    assert any(e.type == EPISODE_TRANSITION for e in received)
    assert any(e.type == EPISODE_STARTED for e in received)

    # Graph was replaced (orchestrator now references new graph)
    assert orch._graph is not graph

    # turn_number: start_episode resets to 0, then execute_turn
    # increments to 1 (the complete turn cycle).
    assert state.turn_number == 1


# ===================================================================
# Edge cases for branch coverage
# ===================================================================


def test_execute_turn_hyper_edge_without_output(tmp_path):
    """HyperEdge without output text still resolves (covers output=None branch)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator
    from fortress_engine.engine.graph import HyperEdge, Clique

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a hyper edge with no output
    silent_edge = HyperEdge(
        hyper_edge_id="silent_action",
        name="Silent",
        priority=10,
        clique=Clique(subject="player", verb="silbar"),
        operators=[],
        output=None,  # No output
    )
    graph.add_hyper_edge("room_a", silent_edge)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="silbar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("silbar")

    # No action_output emitted
    assert not any(e.type == ACTION_OUTPUT for e in received)
    # action_attempted and action_resolved still emitted
    assert any(e.type == ACTION_ATTEMPTED for e in received)
    assert any(e.type == ACTION_RESOLVED for e in received)


def test_execute_turn_cambiar_a_entity_not_in_state(tmp_path):
    """CAMBIAR A with a player_controlled ID not in entities dict."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a ghost ID to player_controlled_entities (not in entities dict)
    state.player_controlled_entities.append("ghost")

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("CAMBIAR A Ghost")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1


def test_execute_turn_grupo_with_ghost_entities(tmp_path):
    """GRUPO handles player_controlled entities not in entities dict."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a ghost and a valid sidekick
    state.player_controlled_entities.append("ghost")
    state.entities["sidekick"] = Entity("sidekick", "player", "Sidekick", {}, "room_a")
    state.player_controlled_entities.append("sidekick")

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("GRUPO")

    grupo_events = [e for e in received if e.type == PROTAGONISTS_LISTED]
    assert len(grupo_events) == 1
    # Only valid entities are listed (hero + sidekick, not ghost)
    prots = grupo_events[0].payload["protagonists"]
    prot_ids = [p["id"] for p in prots]
    assert "hero" in prot_ids
    assert "sidekick" in prot_ids
    assert "ghost" not in prot_ids


# ===================================================================
# Repository present (GUARDAR/CARGAR without error)
# ===================================================================


class _MockRepository:
    """Minimal mock repository that does nothing."""


def test_execute_turn_guardar_with_repository(tmp_path):
    """GUARDAR with a repository present does NOT emit error."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    repo = _MockRepository()

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=repo,
    )

    orch.execute_turn("GUARDAR 1")

    # No error_output when repository is present
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 0


def test_execute_turn_cargar_with_repository(tmp_path):
    """CARGAR with a repository present does NOT emit error."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    repo = _MockRepository()

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=repo,
    )

    orch.execute_turn("CARGAR 1")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 0


# ===================================================================
# Priority fallback — loop back-edge (orchestrator.py 159->158)
# ===================================================================


def test_execute_turn_priority_fallback_back_edge(tmp_path):
    """When the highest-priority candidate's clique does not form, the
    orchestrator falls back to the next candidate (loop back-edge 159->158)
    and resolves the matching lower-priority edge."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Two hyper edges for the same verb in room_a: the priority-10 edge
    # requires flag "has_key" (not set → clique won't form); the priority-0
    # edge has no constraints (clique forms).
    high_edge = HyperEdge(
        hyper_edge_id="open_requires_key",
        name="Open requiring key",
        priority=10,
        clique=Clique(subject="player", verb="abrir", flag="has_key"),
        operators=[{"type": "FLAG", "flag": "high_ran", "value": True}],
        output="High priority fired.",
    )
    fallback_edge = HyperEdge(
        hyper_edge_id="open_fallback",
        name="Open fallback",
        priority=0,
        clique=Clique(subject="player", verb="abrir"),
        operators=[{"type": "FLAG", "flag": "low_ran", "value": True}],
        output="Fallback fired.",
    )
    graph.add_hyper_edge("room_a", high_edge)
    graph.add_hyper_edge("room_a", fallback_edge)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="abrir", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("abrir")

    # The selected edge is the priority-0 fallback (per docs/13-event-system.md
    # §2: action_resolved payload = {hyper_edge_id, operators_executed, has_effects,
    # protagonist_id}).
    resolved = [e for e in received if e.type == ACTION_RESOLVED]
    assert len(resolved) == 1
    assert resolved[0].payload["hyper_edge_id"] == "open_fallback"
    assert resolved[0].payload["operators_executed"] == ["FLAG"]
    assert resolved[0].payload["has_effects"] is True

    # The priority-10 edge was NOT executed.
    assert state.get_flag("high_ran") is False
    assert not any(
        e.type == ACTION_OUTPUT
        and e.payload.get("text") == "High priority fired."
        for e in received
    )

    # The fallback side effect ran and the turn ended.
    assert state.get_flag("low_ran") is True
    assert any(e.type == TURN_ENDED for e in received)


# ===================================================================
# System command dispatch — unknown kind ignored (orchestrator.py 607->exit)
# ===================================================================


def test_handle_system_command_unknown_kind_ignored(tmp_path):
    """An unrecognized system-command kind falls through the dispatcher
    without emitting events or crashing (covers the grupo guard's False
    branch, orchestrator.py 607->exit)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch._handle_system_command("GRUPO", "unknown_kind", "hero")

    # No events emitted and no state mutation — the dispatcher is a no-op
    # for unrecognized kinds.
    assert received == []
    assert state.turn_number == 0


# ===================================================================
# player_dead via _post_action_checks (orchestrator.py 640-648)
# ===================================================================


def test_execute_turn_movement_player_dead_post_action_checks(tmp_path):
    """When player_dead is set, the movement path's _post_action_checks
    emits game_over with reason player_death (covers orchestrator.py 640-648)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Mark the protagonist dead before moving.
    state.set_flag("player_dead", True)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
    )

    orch.execute_turn("ir north")

    # Movement succeeded (teleported) and the post-action check then
    # emitted game_over for the dead protagonist.
    assert state.get_entity("hero").spatial_anchor == "room_b"

    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) >= 1
    assert game_over_events[0].payload["reason"] == "player_death"

    assert any(e.type == TURN_ENDED for e in received)
    assert state.get_flag("player_dead") is True
