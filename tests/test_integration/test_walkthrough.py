"""Acceptance walkthrough tests — Slice G final acceptance.

Prove the engine-core epic acceptance criteria:
- Load a minimal world from ``worlds/_test_minimal/``.
- Execute turn cycles with canonical event sequences.
- Walk through a multi-turn sequence: pick up an item, move, trigger the goal.
- No game_over on the happy path.
- Exactly one ``turn_ended`` per turn.
- ``player_controlled_entities`` is always a list (multi-protagonist invariant).
"""

from dataclasses import dataclass
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
# Fortaleza acceptance walkthrough fixture
# ====================================================================


_FORTALEZA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "worlds" / "fortaleza"
)


class _FortalezaFixture:
    """Fixture for Fortaleza world — uses real plugins and full engine wiring.

    The protagonist is loaded from ``shared/player.yaml`` (max_weight 40) and
    the world's ``Vocabulary`` is injected into the classic parser via
    ``PluginConfig.options`` so the parser understands the world's canonical
    verbs and movement verbs (not the parser defaults).
    """

    def __init__(self, episode_id: str = "episode-01"):
        from fortress_engine.plugins.factory import (
            PluginConfig,
            create_parser,
            create_narrator,
        )

        self.bus = EventBus()
        self.loader = EntityLoader(str(_FORTALEZA_PATH))

        problems = self.loader.validate_world()
        assert problems == [], f"World validation problems: {problems}"

        self.episodes = self.loader.load_episodes()
        assert len(self.episodes) == 2

        world_config = self.loader.load_world_config()
        self.vocabulary = self.loader.load_vocabulary()
        language = world_config.get("language", "es")

        # The classic parser accepts the world vocabulary via options.
        parser_cfg = PluginConfig(
            name="classic", options={"vocabulary": self.vocabulary}
        )
        narrator_cfg = PluginConfig(name="template")
        self.parser = create_parser(parser_cfg, language)
        self.narrator = create_narrator(narrator_cfg, language)
        self.narrator.initialize(self.bus)

        # Protagonist from the world definition (max_weight 40), not hardcoded.
        shared = self.loader.load_shared_entities(episode_id)
        player_entities = [e for e in shared if e.type == "player"]
        assert len(player_entities) == 1, (
            f"Expected exactly one player entity, got {len(player_entities)}"
        )
        player = player_entities[0]

        self.state = WorldState(
            entities={"hero": player},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="",
            turn_number=0,
        )

        # Subscribe to events BEFORE start_episode (episode_started emitted there)
        self.events: list[EngineEvent] = []
        self.bus.subscribe("*", lambda e: self.events.append(e))

        self.ep_mgr = EpisodeManager(
            self.episodes, str(_FORTALEZA_PATH), self.bus
        )
        self.graph = self.ep_mgr.start_episode(episode_id, self.state)
        # Distribute hyper edges to all anchors (engine-agnostic)
        self.ep_mgr.distribute_hyper_edges_to_anchors(
            self.graph, self.state, episode_id
        )

        self.episode_id = episode_id
        self.goal_eval = GoalEvaluator(self.episodes[0].goal)

        self.orch = TurnOrchestrator(
            state=self.state,
            graph=self.graph,
            event_bus=self.bus,
            parser=self.parser,
            narrator=self.narrator,
            goal_evaluator=self.goal_eval,
            episode_manager=self.ep_mgr,
            vocabulary=self.vocabulary,
        )

    def turn(self, command: str) -> list[EngineEvent]:
        """Execute one turn and return events for THIS turn."""
        before = len(self.events)
        self.orch.execute_turn(command)
        return self.events[before:]

    def all_event_types(self) -> list[str]:
        return [e.type for e in self.events]

    def hero_anchor(self) -> str | None:
        """Current spatial anchor of the protagonist."""
        return self.state.get_entity("hero").spatial_anchor

    def inventory_ids(self) -> list[str]:
        """Entity IDs in the protagonist's inventory."""
        return [e.entity_id for e in self.state.get_player_inventory("hero")]

    def last_error(self, turn_events: list[EngineEvent]) -> str | None:
        """First ``error_code`` from an error_output in *turn_events*."""
        for e in turn_events:
            if e.type == ERROR_OUTPUT:
                return e.payload.get("error_code")
        return None


# --------------------------------------------------------------------
# Curated Part I command rows (Slice L1)
# --------------------------------------------------------------------
# Each row references a real macro edge / hyper edge that MUST exist in the
# world (data-integrity guard against vacuous passes). The canonical path in
# L1 uses only commands that resolve against the CURRENT world data; rows that
# depend on the L2 world corrections (password tokens, `abrir`, ariete, etc.)
# are listed under _PART1_PENDING_L2 and become executable in later slices.


@dataclass(frozen=True)
class _CuratedCommand:
    """One curated walkthrough command.

    Attributes:
        episode: episode id the command belongs to.
        anchor_before: anchor the protagonist must occupy before this command.
        verb: parser verb surface (e.g. "tomar", "ir").
        target: entity id or snake_case passage name.
        instrument: optional instrument entity id.
        spoken_text: optional text for ``diciendo`` gates.
        yaml_ref: macro_edge_id or hyper_edge_id that must exist in the world.
        expected_anchor: anchor expected after a movement command.
        expected_inventory: entity IDs expected in the inventory after the turn.
    """

    episode: str
    anchor_before: str
    verb: str
    target: str
    instrument: str | None = None
    spoken_text: str | None = None
    yaml_ref: str = ""
    expected_anchor: str | None = None
    expected_inventory: tuple[str, ...] = ()


# Canonical Part I path executable with the CURRENT world data (no L2 yet):
# exterior -> patio_interior -> biblioteca -> jardin, picking the two exterior
# items. The full 129-command script is completed in later slices (L2 world
# corrections unlock password-gated passages).
_PART1_CANONICAL: tuple[_CuratedCommand, ...] = (
    _CuratedCommand(
        "episode-01",
        "el_exterior_de_la_fortaleza",
        "tomar",
        "maza",
        yaml_ref="he_tomar_maza",
        expected_inventory=("maza",),
    ),
    _CuratedCommand(
        "episode-01",
        "el_exterior_de_la_fortaleza",
        "tomar",
        "pastel_cerezas",
        yaml_ref="he_tomar_pastel_cerezas",
        expected_inventory=("maza", "pastel_cerezas"),
    ),
    _CuratedCommand(
        "episode-01",
        "el_exterior_de_la_fortaleza",
        "ir",
        "tunel",
        yaml_ref="me_exterior_patio",
        expected_anchor="patio_interior",
    ),
    _CuratedCommand(
        "episode-01",
        "patio_interior",
        "ir",
        "puerta_verde",
        yaml_ref="me_patio_biblioteca",
        expected_anchor="biblioteca",
    ),
    _CuratedCommand(
        "episode-01",
        "biblioteca",
        "ir",
        "libro",
        yaml_ref="me_biblioteca_jardin",
        expected_anchor="jardin",
    ),
)

# Commands from the walkthrough that require the L2 world corrections to be
# executable (password tokens still block their passages in the current data).
# They are documented here and become part of the canonical script once L2
# applies (see tasks L2-T1..L2-T4 in openspec/changes/.../tasks.md).
_PART1_PENDING_L2: tuple[str, ...] = (
    "puerta_principal (requires_text password_key[2] -> Abrete Sesamo)",
    "puerta_secreta (requires_text key[3] -> ariete instrument fix)",
    "puerta_cristal (requires_text key[42] -> Agua)",
    "puerta_triangular (requires_text crunch)",
    "puerta_hierro / puerta_dorada / puerta_prohibida (L2 text gates)",
    "escalera sala_de_juegos (requires_text)",
    "abrir <X> diciendo <Y> (abrir missing from movement_verbs)",
    "antorcha_3 re-anchor to sala_del_minotauro",
    "ariete item + he_romper_pared_solaria instrument swap",
    "goal flatten type:and -> atomic conditions (episode goals)",
)


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


# ====================================================================
# Fortaleza acceptance walkthrough — Part I (Slice L1)
# ====================================================================


def test_fortaleza_fixture_player_from_world():
    """The protagonist comes from shared/player.yaml (max_weight 40),
    not a hardcoded 20."""
    fx = _FortalezaFixture()
    hero = fx.state.get_entity("hero")
    assert hero.components["max_weight"] == 40
    assert fx.state.current_episode_id == "episode-01"
    assert fx.hero_anchor() == "el_exterior_de_la_fortaleza"


def test_fortaleza_fixture_world_vocabulary_wired():
    """The classic parser receives the world vocabulary, so movement verbs
    include ``ir`` and the parser understands canonical world verbs."""
    fx = _FortalezaFixture()
    assert "ir" in fx.vocabulary.movement_verbs
    # Parse a world movement command without crashing.
    parsed = fx.parser.parse("ir tunel", fx.state)
    assert parsed is not None
    assert parsed.verb == "ir"
    assert parsed.target == "tunel"


def test_fortaleza_part1_rows_reference_real_yaml():
    """Every curated row references a macro edge / hyper edge that exists
    in the world — a data-integrity guard against vacuous passes."""
    fx = _FortalezaFixture()
    macro_ids = {
        e.macro_edge_id for e in fx.loader.load_macro_edges("episode-01")
    }
    hyper_ids = {
        e.hyper_edge_id for e in fx.loader.load_hyper_edges("episode-01")
    }
    for row in _PART1_CANONICAL:
        assert row.episode == "episode-01"
        assert row.yaml_ref in macro_ids or row.yaml_ref in hyper_ids, (
            f"{row.verb} {row.target}: yaml_ref {row.yaml_ref!r} not found"
        )
        # The starting anchor must exist as a room.
        rooms = {
            r.entity_id for r in fx.loader.load_rooms("episode-01")
        }
        assert row.anchor_before in rooms, (
            f"anchor_before {row.anchor_before!r} not a room in episode-01"
        )


def test_fortaleza_part1_canonical_progress():
    """Executing the curated Part I canonical path produces REAL progress:
    the hero leaves the exterior, moves through expected anchors, picks up
    the two exterior items, never emits game_over, and every turn emits
    exactly one turn_ended."""
    fx = _FortalezaFixture()

    for row in _PART1_CANONICAL:
        assert fx.hero_anchor() == row.anchor_before, (
            f"anchor precondition failed before {row.verb} {row.target}: "
            f"expected {row.anchor_before!r}, got {fx.hero_anchor()!r}"
        )
        turn_events = fx.turn(
            _command_surface(row)
        )
        error = fx.last_error(turn_events)
        assert error is None, (
            f"{row.verb} {row.target} errored with {error!r} at "
            f"{fx.hero_anchor()}"
        )
        # Exactly one turn_ended per turn.
        assert sum(1 for e in turn_events if e.type == TURN_ENDED) == 1
        # No game_over on the canonical path.
        assert GAME_OVER not in [e.type for e in turn_events]
        if row.expected_anchor is not None:
            assert fx.hero_anchor() == row.expected_anchor, (
                f"{row.verb} {row.target}: expected anchor "
                f"{row.expected_anchor!r}, got {fx.hero_anchor()!r}"
            )
        if row.expected_inventory:
            assert fx.inventory_ids() == list(row.expected_inventory), (
                f"{row.verb} {row.target}: expected inventory "
                f"{list(row.expected_inventory)}, got {fx.inventory_ids()}"
            )

    # The hero genuinely left the exterior (anti-vacuous gate).
    assert fx.hero_anchor() != "el_exterior_de_la_fortaleza"
    assert fx.hero_anchor() == "jardin"
    assert "maza" in fx.inventory_ids()
    assert "pastel_cerezas" in fx.inventory_ids()

    # Global invariants across the whole run.
    all_types = fx.all_event_types()
    assert GAME_OVER not in all_types
    assert sum(1 for e in fx.events if e.type == TURN_STARTED) == len(
        _PART1_CANONICAL
    )
    assert sum(1 for e in fx.events if e.type == TURN_ENDED) == len(
        _PART1_CANONICAL
    )
    assert fx.state.turn_number == len(_PART1_CANONICAL)

    # Goal evaluator must run without crashing on this state.
    result = fx.goal_eval.check(fx.state)
    assert isinstance(result, bool)


def _command_surface(row: _CuratedCommand) -> str:
    """Build the user-facing command string for a curated row."""
    parts = [row.verb, row.target]
    if row.instrument:
        parts.extend(["con", row.instrument])
    if row.spoken_text:
        parts.extend(["diciendo", row.spoken_text])
    return " ".join(parts)


def test_fortaleza_part1_pending_l2_documented():
    """The walkthrough commands that still require L2 world corrections are
    explicitly listed so no canonical assertion silently ignores them."""
    assert len(_PART1_PENDING_L2) >= 10
    assert any("puerta_principal" in p for p in _PART1_PENDING_L2)
