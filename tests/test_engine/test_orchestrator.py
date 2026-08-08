"""Tests for TurnOrchestrator — RED phase (E1.3, L2).

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

from fortress_engine.entities.loader import Vocabulary
from fortress_engine.plugins.parser_interface import ParserInterface
from fortress_engine.plugins.narrator_interface import NarratorInterface


# ===================================================================
# Minimal stubs (Slice E1 — real implementations in E2)
# ===================================================================


class _StubParser(ParserInterface):
    """Parser that returns a pre-configured command."""
    def __init__(self, command: ParsedCommand, language: str = "es"):
        super().__init__(language)
        self.command = command

    @property
    def language(self) -> str:
        return self._language

    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        return self.command


class _StubNarrator(NarratorInterface):
    """Narrator that records events instead of producing text."""
    def __init__(self, language: str = "es"):
        super().__init__(language)
        self.events: list[EngineEvent] = []

    @property
    def language(self) -> str:
        return self._language

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
    """When no clique matches, error_output is emitted with code+data (no message)."""
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

    # error_output emitted with code+data, no message
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    payload = error_events[0].payload
    assert payload["error_code"] == "no_action"
    assert "data" in payload
    assert payload["data"]["verb"] == "volar"
    assert "message" not in payload

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
    """ABRIR on a closed requires_text door without the text → error_output with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "blocked"
    assert "data" in payload
    assert payload["data"]["passage_name"] == "puerta principal"
    assert "message" not in payload

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
    """IR on a closed requires_text edge without the text → error_output with code+data.

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
    payload = error_events[0].payload
    assert payload["error_code"] == "blocked"
    assert "data" in payload
    assert "message" not in payload

    assert state.get_entity("hero").spatial_anchor == "room_a"
    assert not any(e.type == ENTITY_TELEPORTED for e in received)
    assert graph.get_macro_edge_by_passage_name("room_a", "puerta principal").open is False


# ===================================================================
# Movement fails (danger without item)
# ===================================================================


def test_execute_turn_danger_macro_edge_fails(tmp_path):
    """Movement through a requires_item gate without the item → game_over.

    L4: death-vs-block is now via is_fatal (MacroGateResult), not string
    equality.  GAME_OVER reason is "player_death" (stable code); the
    world-authored death_message flows in gate.data.
    """
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

    # Fatal gate → is_fatal=True → GAME_OVER with reason="player_death"
    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    assert game_over_events[0].payload["reason"] == "player_death"

    # No error_output on death
    assert not any(e.type == ERROR_OUTPUT for e in received)


def test_execute_turn_lethal_gate_emits_game_over_player_death(tmp_path):
    """A lethal gate (is_fatal=True) emits GAME_OVER reason="player_death"
    regardless of gate_code, and never emits error_output."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator
    from fortress_engine.engine.graph import MacroGateResult

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Monkey-patch validate_macro_edge to simulate a lethal gate for ANY
    # movement so we don't need to set up an actual edge.
    original = graph.validate_macro_edge
    graph.validate_macro_edge = lambda edge, st, tx=None: MacroGateResult(
        is_valid=False, is_fatal=True, gate_code="requires_item",
        data={"passage_name": "north", "required_item": "amulet",
              "death_message": "The bridge collapses!"},
    )

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )

    orch.execute_turn("ir north")

    # Restore for cleanliness (pytest does not require it but good practice).
    graph.validate_macro_edge = original

    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    assert game_over_events[0].payload["reason"] == "player_death"
    # W-1 fix: the world-authored death_message flows through gate.data so
    # a narrator can render it (engine never constructs the string itself).
    assert game_over_events[0].payload["death_message"] == "The bridge collapses!"

    assert not any(e.type == ERROR_OUTPUT for e in received)


def test_execute_turn_nonfatal_gate_emits_blocked_error(tmp_path):
    """A non-fatal gate (is_fatal=False) emits error_output with
    error_code="blocked" and gate data."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator
    from fortress_engine.engine.graph import MacroGateResult

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    original = graph.validate_macro_edge
    graph.validate_macro_edge = lambda edge, st, tx=None: MacroGateResult(
        is_valid=False, is_fatal=False, gate_code="requires_flag",
        data={"passage_name": "north", "required_flag": "key_found"},
    )

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )

    orch.execute_turn("ir north")

    graph.validate_macro_edge = original

    # error_output emitted with blocked code + gate data
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    payload = error_events[0].payload
    assert payload["error_code"] == "blocked"
    assert "data" in payload
    assert payload["data"]["gate_code"] == "requires_flag"
    assert payload["data"]["passage_name"] == "north"
    assert payload["data"]["required_flag"] == "key_found"
    assert "message" not in payload

    # No GAME_OVER
    assert not any(e.type == GAME_OVER for e in received)

    # turn_ended still emitted
    assert any(e.type == TURN_ENDED for e in received)


# ===================================================================
# Operator fails
# ===================================================================


def test_execute_turn_operator_fails_emits_error(tmp_path):
    """When an operator fails, error_output is emitted with code+data (no message)."""
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

    # error_output emitted with code+data, no message
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 1
    payload = error_events[0].payload
    assert payload["error_code"] == "operator_failed"
    assert "data" in payload
    assert "message" not in payload

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
    """GUARDAR without a repository emits error_output with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "no_repository"
    assert "data" in payload
    assert "message" not in payload


def test_execute_turn_cargar_without_repository_emits_error(tmp_path):
    """CARGAR without a repository emits error_output with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "no_repository"
    assert "data" in payload
    assert "message" not in payload


# ===================================================================
# System commands: bare GUARDAR / CARGAR (no slot)
# ===================================================================


def test_execute_turn_guardar_bare_without_repository(tmp_path):
    """GUARDAR (without slot number) emits error_output with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "no_repository"
    assert "message" not in payload


def test_execute_turn_cargar_bare_without_repository(tmp_path):
    """CARGAR (without slot number) emits error_output with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "no_repository"
    assert "message" not in payload


# ===================================================================
# CAMBIAR A — invalid name / same protagonist
# ===================================================================


def test_execute_turn_cambiar_a_invalid_name(tmp_path):
    """CAMBIAR A <nonexistent> emits error_output with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "invalid_protagonist"
    assert "data" in payload
    assert "message" not in payload


# ===================================================================
# Movement — conditional edge blocked (no death)
# ===================================================================


def test_execute_turn_conditional_edge_blocked(tmp_path):
    """requires_flag macro edge that is blocked emits error_output with code+data."""
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

    # Should emit error_output (blocked, not death) with code+data
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) >= 1
    payload = error_events[0].payload
    assert payload["error_code"] == "blocked"
    assert "data" in payload
    assert "message" not in payload
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
    """CAMBIAR A with a player_controlled ID not in entities dict → error with code+data."""
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
    payload = error_events[0].payload
    assert payload["error_code"] == "invalid_protagonist"
    assert "data" in payload
    assert "message" not in payload


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
    """GUARDAR with repository and save_system emits game_saved."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    repo = _MockRepository()
    # A minimal save_system stub that satisfies the type check.
    class _StubSaveSystem:
        pass
    save_sys = _StubSaveSystem()

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=repo,
        save_system=save_sys,
    )

    orch.execute_turn("GUARDAR 1")

    # No error when both repository and save_system are present.
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 0

    # game_saved emitted.
    saved_events = [e for e in received if e.type == "game_saved"]
    assert len(saved_events) == 1
    assert saved_events[0].payload["save_slot"] == "slot_1"


def test_execute_turn_cargar_with_repository(tmp_path):
    """CARGAR with repository, save_system, and a snapshot emits game_loaded."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    # A mock repo that has a snapshot so the slot "exists".
    class _MockRepoWithSnapshot:
        def load_latest_snapshot(self, save_slot):
            return (WorldState(turn_number=3), 3)
        def get_event_log(self, since_turn=0):
            return []

    repo = _MockRepoWithSnapshot()

    class _StubSaveSystem:
        def replay_state(self, st, slot, graph=None):
            return st

    save_sys = _StubSaveSystem()

    orch = TurnOrchestrator(
        state=state,
        graph=graph,
        event_bus=bus,
        parser=parser,
        narrator=narrator,
        goal_evaluator=goal_eval,
        episode_manager=ep_mgr,
        repository=repo,
        save_system=save_sys,
    )

    orch.execute_turn("CARGAR 1")

    # No error when both are present and snapshot exists.
    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(error_events) == 0

    # game_loaded emitted.
    loaded_events = [e for e in received if e.type == "game_loaded"]
    assert len(loaded_events) == 1
    assert loaded_events[0].payload["save_slot"] == "slot_1"


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


# ===================================================================
# L2: Vocabulary-driven orchestrator — new RED tests
# ===================================================================


def test_orchestrator_accepts_vocabulary_parameter(tmp_path):
    """Constructor accepts vocabulary: Vocabulary|None=None."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    # No vocabulary → constructor works (back-compat)
    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )
    assert orch is not None

    # English vocabulary → constructor works
    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go", "open"],
        system_commands={
            "save": ["save"], "load": ["load"], "quit": ["quit"],
            "wait": ["wait"], "group": ["group"], "switch": ["switch to"],
        },
    )
    orch_en = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )
    assert orch_en is not None


def test_movement_uses_vocabulary_verbs(tmp_path):
    """Orchestrator resolves movement from vocabulary.movement_verbs (English 'go')."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="go", target="north")
    )

    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go", "open"],
        system_commands={},
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    orch.execute_turn("go north")

    # Movement succeeded: hero teleported to room_b
    assert state.get_entity("hero").spatial_anchor == "room_b"
    assert any(e.type == ENTITY_TELEPORTED for e in received)
    assert any(e.type == ENTITY_ENTERED for e in received)


def test_system_commands_from_vocabulary_english(tmp_path):
    """English system commands from vocabulary dispatch correctly (save→stash, quit→quit)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go"],
        system_commands={
            "save": ["save"],
            "load": ["load"],
            "quit": ["quit"],
            "wait": ["wait"],
            "group": ["group"],
            "switch": ["switch to"],
        },
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    orch.execute_turn("quit")

    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    assert game_over_events[0].payload["reason"] == "player_quit"


def test_switch_prefix_uses_vocabulary_surface(tmp_path):
    """switch prefix strips the vocabulary surface (e.g. 'switch to' instead of 'cambiar a')."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a switchable companion
    state.entities["ana"] = Entity("ana", "player", "Ana", {}, "room_a")
    state.player_controlled_entities = ["hero", "ana"]

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go"],
        system_commands={
            "save": ["save"], "load": ["load"],
            "quit": ["quit"], "wait": ["wait"],
            "group": ["group"], "switch": ["switch to"],
        },
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    orch.execute_turn("switch to ana")

    switched = [e for e in received if e.type == PROTAGONIST_SWITCHED]
    assert len(switched) == 1
    assert switched[0].payload["from_protagonist_id"] == "hero"
    assert switched[0].payload["to_protagonist_id"] == "ana"


def test_default_movement_verbs_fallback(tmp_path):
    """When vocabulary is None, DEFAULT_MOVEMENT_VERBS={'ir','abrir'} applies."""
    from fortress_engine.engine.orchestrator import (
        TurnOrchestrator,
        DEFAULT_MOVEMENT_VERBS,
    )

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(
        ParsedCommand(subject="hero", verb="ir", target="north")
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=None,
    )

    orch.execute_turn("ir north")

    # Movement succeeded: hero teleported to room_b
    assert state.get_entity("hero").spatial_anchor == "room_b"
    # DEFAULT_MOVEMENT_VERBS is {'ir', 'abrir'}
    assert "ir" in DEFAULT_MOVEMENT_VERBS
    assert "abrir" in DEFAULT_MOVEMENT_VERBS


def test_default_system_commands_fallback(tmp_path):
    """When vocabulary has no system_commands, DEFAULT_SYSTEM_COMMANDS covers Spanish."""
    from fortress_engine.engine.orchestrator import (
        TurnOrchestrator,
        DEFAULT_SYSTEM_COMMANDS,
    )

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go"],
        system_commands={},  # fall back to defaults
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    orch.execute_turn("terminar")

    game_over_events = [e for e in received if e.type == GAME_OVER]
    assert len(game_over_events) == 1
    assert game_over_events[0].payload["reason"] == "player_quit"
    # DEFAULT_SYSTEM_COMMANDS covers all 6 canonical kinds
    for kind in ("save", "load", "quit", "wait", "group", "switch"):
        assert kind in DEFAULT_SYSTEM_COMMANDS


def test_default_system_commands_is_dict_of_lists(tmp_path):
    """DEFAULT_SYSTEM_COMMANDS is a dict mapping canonical kind → list of surface words."""
    from fortress_engine.engine.orchestrator import DEFAULT_SYSTEM_COMMANDS

    assert isinstance(DEFAULT_SYSTEM_COMMANDS, dict)
    for surfaces in DEFAULT_SYSTEM_COMMANDS.values():
        assert isinstance(surfaces, list)
        assert len(surfaces) > 0


def test_default_movement_verbs_is_frozenset(tmp_path):
    """DEFAULT_MOVEMENT_VERBS is a frozenset containing 'ir' and 'abrir'."""
    from fortress_engine.engine.orchestrator import DEFAULT_MOVEMENT_VERBS

    assert isinstance(DEFAULT_MOVEMENT_VERBS, frozenset)
    assert DEFAULT_MOVEMENT_VERBS == frozenset({"ir", "abrir"})


def test_parse_save_slot_strips_vocabulary_surface(tmp_path):
    """_parse_save_slot strips vocabulary surface words using the surfaces parameter."""
    from fortress_engine.engine.orchestrator import _parse_save_slot

    # With default (no surfaces arg) — uses hardcoded Spanish/English defaults
    assert _parse_save_slot("guardar 2") == "slot_2"

    # With custom surfaces (English only)
    assert _parse_save_slot("save 3", surfaces={"save", "load"}) == "slot_3"
    assert _parse_save_slot("load 2", surfaces={"save", "load"}) == "slot_2"
    assert _parse_save_slot("save", surfaces={"save", "load"}) == "slot_1"
    assert _parse_save_slot("guardar 1", surfaces={"save", "load"}) == "slot_1"  # unrecognized → slot_1
    assert _parse_save_slot("save 99", surfaces={"save", "load"}) is None  # out of range

    # Non-numeric suffix with custom surfaces
    assert _parse_save_slot("save xyz", surfaces={"save", "load"}) == "slot_1"


def test_episode_completed_constant_import(tmp_path):
    """The orchestrator imports EPISODE_COMPLETED constant (not bare string)."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator
    from fortress_engine.events.event_types import EPISODE_COMPLETED

    # Verify the constant is importable and is the string "episode_completed"
    assert EPISODE_COMPLETED == "episode_completed"

    # Verify the orchestrator uses the constant internally (not bare string)
    import inspect
    source = inspect.getsource(TurnOrchestrator._evaluate_goal)
    assert "EPISODE_COMPLETED" in source
    assert '"episode_completed"' not in source


def test_grupo_location_is_none_not_limbo(tmp_path):
    """GRUPO emits location as spatial_anchor (may be None), never 'limbo' literal."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    # Add a protagonist with no spatial_anchor (None)
    state.entities["nomad"] = Entity("nomad", "player", "Nomad", {}, None)
    state.player_controlled_entities = ["hero", "nomad"]

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )

    orch.execute_turn("GRUPO")

    grupo_events = [e for e in received if e.type == PROTAGONISTS_LISTED]
    assert len(grupo_events) == 1
    prots = grupo_events[0].payload["protagonists"]
    nomad = next(p for p in prots if p["name"] == "Nomad")
    # location is None, NOT "limbo"
    assert nomad["location"] is None


def test_error_output_no_message_in_save_load_paths(tmp_path):
    """The no_repository and invalid_slot error sites emit NO 'message' key."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        repository=None, save_system=None,
    )

    orch.execute_turn("guardar")

    error_events = [e for e in received if e.type == ERROR_OUTPUT]
    for evt in error_events:
        assert "message" not in evt.payload, (
            f"error_output must not carry message: {evt.payload}"
        )


def test_detect_system_command_empty_input(tmp_path):
    """_detect_system_command returns None for empty/whitespace input."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )

    assert orch._detect_system_command("") is None
    assert orch._detect_system_command("   ") is None


def test_system_commands_fills_missing_canonical_kinds(tmp_path):
    """_system_commands() fills missing canonical kinds from defaults."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    # Vocabulary with only "save" defined — missing "load", "quit", etc.
    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go"],
        system_commands={"save": ["stash"]},
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    cmds = orch._system_commands()
    # All canonical kinds present
    for kind in ("save", "load", "quit", "wait", "group", "switch"):
        assert kind in cmds
    # save uses the vocabulary surface
    assert "stash" in cmds["save"]
    # load filled from defaults
    assert "cargar" in cmds["load"]


def test_switch_without_name_detected(tmp_path):
    """Bare 'switch' command (no name) is detected as switch kind."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go"],
        system_commands={"switch": ["switch to"]},
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    # Exact prefix match (no name) is detected as switch
    assert orch._detect_system_command("switch to") == "switch"


def test_switch_with_empty_surfaces_fallback(tmp_path):
    """Switch with empty surfaces falls back to defaults."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    state.entities["ana"] = Entity("ana", "player", "Ana", {}, "room_a")
    state.player_controlled_entities = ["hero", "ana"]

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))
    narrator = _StubNarrator()

    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))

    vocab = Vocabulary(
        language="en", verbs={}, stopwords=[], prepositions={},
        speech_markers=[], speech_verbs=[],
        messages={}, movement_verbs=["go"],
        system_commands={"switch": []},
    )

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocab,
    )

    # Empty switch surfaces are filled from defaults → "cambiar a" works
    orch.execute_turn("cambiar a ana")
    switched = [e for e in received if e.type == PROTAGONIST_SWITCHED]
    assert len(switched) == 1


def test_switch_prefix_no_space_not_detected(tmp_path):
    """Switch surface prefix matches but next char not a space → no detection.

    Covers the 608→602 branch where switch prefix matches but
    lower[len(surface)] != " ".
    """
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _StubParser(ParsedCommand(subject="hero", verb="mirar", target=None))
    narrator = _StubNarrator()

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )

    # "cambiar a" surface, raw = "cambiar ana"
    # "cambiar ana".startswith("cambiar a") → True
    # lower[9] = "n" ≠ " " → falls through, not detected as switch
    result = orch._detect_system_command("cambiar ana")
    # The save surfaces also don't match as exact, so it returns None
    assert result is None


# ===================================================================
# C1: plugin error isolation — a throwing parser must not crash the engine
# ===================================================================


class _ThrowingParser(ParserInterface):
    """Parser that always raises — used to verify §9.3 isolation."""

    def __init__(self, language: str = "es"):
        super().__init__(language)

    @property
    def language(self) -> str:
        return self._language

    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        raise RuntimeError("parser exploded")


def test_parser_exception_is_isolated(tmp_path):
    """A throwing parser emits error_output parser_error, does not crash."""
    from fortress_engine.engine.orchestrator import TurnOrchestrator

    state, graph, bus, ep_mgr, goal_eval = _setup_orchestrator(tmp_path)
    parser = _ThrowingParser()
    narrator = _StubNarrator()

    received: list[EngineEvent] = []
    bus.subscribe("*", lambda e: received.append(e))

    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
    )

    # Must not raise.
    orch.execute_turn("mirar puerta")

    errors = [e for e in received if e.type == ERROR_OUTPUT]
    assert len(errors) == 1
    assert errors[0].payload["error_code"] == "parser_error"
    assert errors[0].payload["data"] == {}
    # The failed turn still emits turn_ended.
    assert any(e.type == TURN_ENDED for e in received)
