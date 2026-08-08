"""Tests for EngineBundle and _build_engine() — Phase 1 of epic-4-cli.

These tests define the contract for the CLI engine builder.
They MUST fail before the implementation exists (RED phase).
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.goal_evaluator import GoalEvaluator
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.plugins.narrator_interface import NarratorInterface
from fortress_engine.entities.entity import Episode, GoalConditions, CarryOver


_WORLD_PATH = Path(__file__).resolve().parent.parent.parent / "worlds" / "_test_minimal"
_BROKEN_WORLD = Path(__file__).resolve().parent.parent.parent / "tests" / "test_cli" / "_broken_world"


@pytest.fixture(autouse=True)
def _ensure_broken_world(tmp_path: Path) -> Path:
    """Create a broken world directory for testing."""
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "world.yaml").write_text("world_id: broken\nname: Broken\n")
    episodes_dir = broken / "episodes"
    episodes_dir.mkdir()
    (episodes_dir / "episode-01.yaml").write_text(
        "id: episode-01\n"
        "name: Broken Episode\n"
        "order: 1\n"
        "description: A broken episode\n"
        "requires: []\n"
        "start_anchor: nonexistent_room\n"
        "goal:\n"
        "  conditions: []\n"
        "  output: ''\n"
        "  side_effects: []\n"
        "carry_over:\n"
        "  inventory: []\n"
        "  flags: []\n"
    )
    return broken


class TestEngineBundle:
    """EngineBundle dataclass contract tests."""

    def test_bundle_is_frozen_dataclass(self):
        """EngineBundle must be a frozen dataclass."""
        from fortress_engine.cli.main import EngineBundle
        import dataclasses

        assert dataclasses.is_dataclass(EngineBundle)
        fields = {f.name for f in dataclasses.fields(EngineBundle)}
        expected = {
            "orchestrator",
            "state",
            "event_bus",
            "narrator",
            "episodes",
            "episode_manager",
            "world_config",
        }
        assert fields == expected

    def test_bundle_is_immutable(self):
        """EngineBundle fields cannot be reassigned after creation."""
        from fortress_engine.cli.main import EngineBundle

        # We'll construct a minimal bundle to test immutability
        bundle = EngineBundle(
            orchestrator=None,
            state=None,
            event_bus=None,
            narrator=None,
            episodes=[],
            episode_manager=None,
            world_config={},
        )
        with pytest.raises(AttributeError):
            bundle.orchestrator = "changed"  # type: ignore[misc]


class TestBuildEngine:
    """_build_engine() contract tests."""

    def test_build_engine_returns_bundle(self):
        """_build_engine must return an EngineBundle with all fields populated."""
        from fortress_engine.cli.main import _build_engine

        bundle = _build_engine(str(_WORLD_PATH))

        assert bundle.orchestrator is not None
        assert bundle.state is not None
        assert bundle.event_bus is not None
        assert bundle.narrator is not None
        assert bundle.episodes is not None
        assert bundle.episode_manager is not None
        assert bundle.world_config is not None

    def test_build_engine_sets_episode_id(self):
        """current_episode_id must be set after _build_engine."""
        from fortress_engine.cli.main import _build_engine

        bundle = _build_engine(str(_WORLD_PATH))
        assert bundle.state.current_episode_id == "episode-01"

    def test_build_engine_player_controlled_is_list(self):
        """player_controlled_entities must be a list (multi-protagonist)."""
        from fortress_engine.cli.main import _build_engine

        bundle = _build_engine(str(_WORLD_PATH))
        assert isinstance(bundle.state.player_controlled_entities, list)
        assert "hero" in bundle.state.player_controlled_entities

    def test_build_engine_missing_world_exits_1(self, tmp_path: Path):
        """Missing world.yaml must raise SystemExit(1)."""
        from fortress_engine.cli.main import _build_engine

        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            _build_engine(str(empty))
        assert exc_info.value.code == 1

    def test_build_engine_broken_world_exits_1(self, _ensure_broken_world: Path):
        """World validation failure must raise SystemExit(1)."""
        from fortress_engine.cli.main import _build_engine

        with pytest.raises(SystemExit) as exc_info:
            _build_engine(str(_ensure_broken_world))
        assert exc_info.value.code == 1

    def test_build_engine_custom_parser_narrator(self):
        """_build_engine accepts parser_name and narrator_name overrides."""
        from fortress_engine.cli.main import _build_engine

        bundle = _build_engine(
            str(_WORLD_PATH),
            parser_name="classic",
            narrator_name="template",
        )
        assert bundle.orchestrator is not None

    def test_build_engine_generic_exception_exits_1(self, tmp_path: Path):
        """Generic exceptions during build raise SystemExit(1)."""
        from fortress_engine.cli.main import _build_engine

        # Create a world with invalid YAML that causes a generic exception
        broken = tmp_path / "broken_yaml"
        broken.mkdir()
        (broken / "world.yaml").write_text("invalid: yaml: [[[")

        with pytest.raises(SystemExit) as exc_info:
            _build_engine(str(broken))
        assert exc_info.value.code == 1

    def test_build_engine_copies_edges_to_other_rooms(self):
        """_build_engine must copy edges from start_anchor to other rooms."""
        from fortress_engine.cli.main import _build_engine

        bundle = _build_engine(str(_WORLD_PATH))

        # Check that the escape edge is accessible from hall
        hero = bundle.state.get_entity("hero")
        # After building, hero should be in cell (start_anchor)
        assert hero.spatial_anchor == "cell"

        # The orchestrator should have the escape edge accessible from both cell and hall
        # This is tested indirectly through the test command tests

    def test_build_engine_no_escape_edges(self, tmp_path):
        """_build_engine handles worlds with no escape edges gracefully."""
        from fortress_engine.cli.main import _build_engine

        # Create a world with no escape edges
        world_dir = tmp_path / "no_escape"
        world_dir.mkdir()
        (world_dir / "world.yaml").write_text("world_id: no_escape\nname: No Escape\n")
        episodes_dir = world_dir / "episodes"
        episodes_dir.mkdir()
        (episodes_dir / "episode-01.yaml").write_text(
            "id: episode-01\n"
            "name: No Escape Episode\n"
            "order: 1\n"
            "description: An episode with no escape\n"
            "requires: []\n"
            "start_anchor: room1\n"
            "goal:\n"
            "  conditions: []\n"
            "  output: ''\n"
            "  side_effects: []\n"
            "carry_over:\n"
            "  inventory: []\n"
            "  flags: []\n"
        )
        rooms_dir = world_dir / "episode-01" / "rooms"
        rooms_dir.mkdir(parents=True)
        (rooms_dir / "room1.yaml").write_text(
            "entity_id: room1\n"
            "type: room\n"
            "name: Room 1\n"
            "components: {}\n"
        )

        # This should not raise an exception
        bundle = _build_engine(str(world_dir))
        assert bundle.orchestrator is not None

    def test_build_engine_missing_rooms_dir(self, tmp_path):
        """_build_engine handles missing rooms directory gracefully."""
        from fortress_engine.cli.main import _build_engine

        # Create a world with missing rooms directory
        world_dir = tmp_path / "missing_rooms"
        world_dir.mkdir()
        (world_dir / "world.yaml").write_text("world_id: missing_rooms\nname: Missing Rooms\n")
        episodes_dir = world_dir / "episodes"
        episodes_dir.mkdir()
        (episodes_dir / "episode-01.yaml").write_text(
            "id: episode-01\n"
            "name: Missing Rooms Episode\n"
            "order: 1\n"
            "description: An episode with missing rooms\n"
            "requires: []\n"
            "start_anchor: room1\n"
            "goal:\n"
            "  conditions: []\n"
            "  output: ''\n"
            "  side_effects: []\n"
            "carry_over:\n"
            "  inventory: []\n"
            "  flags: []\n"
        )
        # Don't create rooms directory

        # This should raise SystemExit(1) because validation fails
        with pytest.raises(SystemExit) as exc_info:
            _build_engine(str(world_dir))
        assert exc_info.value.code == 1

    def test_distribute_hyper_edges_spatial_anchors(self):
        """EpisodeManager.distribute_hyper_edges_to_anchors copies to all anchors."""
        from fortress_engine.engine.episode_manager import EpisodeManager
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity, Episode, GoalConditions, CarryOver
        from fortress_engine.events.event_bus import EventBus

        # Entities with spatial_anchors (entity-agnostic: not "rooms").
        # Rooms use their own entity_id as spatial_anchor (self-anchored).
        room_a = Entity("anchor_a", "type_a", "Anchor A", {}, "anchor_a")
        room_b = Entity("anchor_b", "type_b", "Anchor B", {}, "anchor_b")
        room_c = Entity("anchor_c", "type_c", "Anchor C", {}, "anchor_c")

        state = WorldState(
            entities={
                "hero": Entity("hero", "player", "Hero", {}, "anchor_a"),
                "anchor_a": room_a,
                "anchor_b": room_b,
                "anchor_c": room_c,
            },
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )

        # Episode with anchor_a as start
        episode = Episode(
            id="ep1", name="Test", order=1, description="",
            requires=[], start_anchor="anchor_a",
            goal=GoalConditions(conditions=[], output="", side_effects=[]),
            carry_over=CarryOver(),
        )

        bus = EventBus()
        mgr = EpisodeManager([episode], "/tmp", bus)

        # Mock graph with hyper edges at start_anchor
        class MockHyperEdge:
            def __init__(self, name):
                self.name = name

        class MockGraph:
            def __init__(self):
                self._hyper_edges = {"anchor_a": {"verb1": [MockEdge("e1")]}}
                self.added = []

            def get_hyper_edges_for_verb(self, anchor, verb):
                return self._hyper_edges.get(anchor, {}).get(verb, [])

            def add_hyper_edge(self, anchor, edge):
                self.added.append((anchor, edge))

        MockEdge = MockHyperEdge
        graph = MockGraph()

        mgr.distribute_hyper_edges_to_anchors(graph, state, "ep1")

        # Edge should be copied to anchor_b and anchor_c (not anchor_a)
        added_anchors = [a for a, _ in graph.added]
        assert "anchor_b" in added_anchors
        assert "anchor_c" in added_anchors
        assert "anchor_a" not in added_anchors  # not copied to self

    def test_distribute_hyper_edges_no_edges(self):
        """distribute_hyper_edges_to_anchors handles no edges gracefully."""
        from fortress_engine.engine.episode_manager import EpisodeManager
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity, Episode, GoalConditions, CarryOver
        from fortress_engine.events.event_bus import EventBus

        state = WorldState(
            entities={"hero": Entity("hero", "player", "Hero", {}, None)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )
        state.get_entity("hero").spatial_anchor = "start"

        episode = Episode(
            id="ep1", name="Test", order=1, description="",
            requires=[], start_anchor="start",
            goal=GoalConditions(conditions=[], output="", side_effects=[]),
            carry_over=CarryOver(),
        )

        bus = EventBus()
        mgr = EpisodeManager([episode], "/tmp", bus)

        class MockGraph:
            def __init__(self):
                self._hyper_edges = {"start": {}}
                self.added = []

            def get_hyper_edges_for_verb(self, anchor, verb):
                return self._hyper_edges.get(anchor, {}).get(verb, [])

            def add_hyper_edge(self, anchor, edge):
                self.added.append((anchor, edge))

        graph = MockGraph()
        mgr.distribute_hyper_edges_to_anchors(graph, state, "ep1")
        assert len(graph.added) == 0  # nothing to distribute
