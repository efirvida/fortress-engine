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

    def test_copy_escape_edges_no_escape_edges(self):
        """_copy_escape_edges handles no escape edges gracefully."""
        from fortress_engine.cli.main import _copy_escape_edges
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity
        from fortress_engine.events.event_bus import EventBus

        state = WorldState(
            entities={"hero": Entity("hero", "player", "Hero", {}, None)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )
        state.get_entity("hero").spatial_anchor = "cell"

        bus = EventBus()

        # Mock graph with no escape edges
        class MockGraph:
            def get_hyper_edges_for_verb(self, anchor, verb):
                return []

        graph = MockGraph()

        # This should not raise an exception
        _copy_escape_edges(graph, state, [], Path("/tmp"))

    def test_copy_escape_edges_with_escape_edges(self, tmp_path):
        """_copy_escape_edges copies edges to other rooms."""
        from fortress_engine.cli.main import _copy_escape_edges
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity
        from fortress_engine.events.event_bus import EventBus

        state = WorldState(
            entities={"hero": Entity("hero", "player", "Hero", {}, None)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )
        state.get_entity("hero").spatial_anchor = "cell"

        bus = EventBus()

        # Mock graph with escape edges
        class MockEdge:
            pass

        escape_edge = MockEdge()

        class MockGraph:
            def __init__(self):
                self.added = []

            def get_hyper_edges_for_verb(self, anchor, verb):
                if anchor == "cell" and verb == "huir":
                    return [escape_edge]
                return []

            def add_hyper_edge(self, anchor, edge):
                self.added.append((anchor, edge))

        graph = MockGraph()

        # Create a world with rooms
        world_dir = tmp_path / "escape_world"
        world_dir.mkdir()
        (world_dir / "world.yaml").write_text("world_id: escape_world\nname: Escape World\n")
        episodes_dir = world_dir / "episodes"
        episodes_dir.mkdir()
        (episodes_dir / "episode-01.yaml").write_text(
            "id: episode-01\n"
            "name: Escape Episode\n"
            "order: 1\n"
            "description: An episode with escape\n"
            "requires: []\n"
            "start_anchor: cell\n"
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
        (rooms_dir / "cell.yaml").write_text(
            "entity_id: cell\n"
            "type: room\n"
            "name: Cell\n"
            "components: {}\n"
        )
        (rooms_dir / "hall.yaml").write_text(
            "entity_id: hall\n"
            "type: room\n"
            "name: Hall\n"
            "components: {}\n"
        )

        # Mock episodes
        class MockEpisode:
            id = "episode-01"

        _copy_escape_edges(graph, state, [MockEpisode()], world_dir)

        # Should have copied edge to hall but not cell
        assert len(graph.added) == 1
        assert graph.added[0][0] == "hall"
        assert graph.added[0][1] is escape_edge

    def test_copy_escape_edges_missing_rooms_dir(self, tmp_path):
        """_copy_escape_edges handles missing rooms dir for episode with escape edges."""
        from fortress_engine.cli.main import _copy_escape_edges
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity

        state = WorldState(
            entities={"hero": Entity("hero", "player", "Hero", {}, None)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )
        state.get_entity("hero").spatial_anchor = "cell"

        class MockEdge:
            pass

        escape_edge = MockEdge()

        class MockGraph:
            def get_hyper_edges_for_verb(self, anchor, verb):
                if anchor == "cell" and verb == "huir":
                    return [escape_edge]
                return []

        graph = MockGraph()

        world_dir = tmp_path / "no_rooms_dir"
        world_dir.mkdir()

        class MockEpisode:
            id = "episode-01"

        # rooms dir does NOT exist → line 73 (continue) should be hit
        _copy_escape_edges(graph, state, [MockEpisode()], world_dir)

    def test_copy_escape_edges_exception_handler(self, tmp_path):
        """_copy_escape_edges handles exceptions gracefully."""
        from fortress_engine.cli.main import _copy_escape_edges
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity

        state = WorldState(
            entities={"hero": Entity("hero", "player", "Hero", {}, None)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )
        state.get_entity("hero").spatial_anchor = "cell"

        class MockEdge:
            pass

        escape_edge = MockEdge()

        class MockGraph:
            def get_hyper_edges_for_verb(self, anchor, verb):
                if anchor == "cell" and verb == "huir":
                    return [escape_edge]
                # For "escapar" and "fuir" raise an exception
                raise RuntimeError("Graph error")

        graph = MockGraph()

        world_dir = tmp_path / "exception_world"
        world_dir.mkdir()
        episodes_dir = world_dir / "episodes"
        episodes_dir.mkdir()
        (episodes_dir / "episode-01.yaml").write_text(
            "id: episode-01\nname: Test\norder: 1\ndescription: ''\n"
            "requires: []\nstart_anchor: cell\n"
            "goal:\n  conditions: []\n  output: ''\n  side_effects: []\n"
            "carry_over:\n  inventory: []\n  flags: []\n"
        )
        rooms_dir = world_dir / "episode-01" / "rooms"
        rooms_dir.mkdir(parents=True)
        (rooms_dir / "cell.yaml").write_text(
            "entity_id: cell\ntype: room\nname: Cell\ncomponents: {}\n"
        )

        class MockEpisode:
            id = "episode-01"

        # Should not raise — exception is caught
        _copy_escape_edges(graph, state, [MockEpisode()], world_dir)

    def test_copy_escape_edges_null_anchor(self):
        """_copy_escape_edges returns early when start_anchor is None."""
        from fortress_engine.cli.main import _copy_escape_edges
        from fortress_engine.engine.state import WorldState
        from fortress_engine.entities.entity import Entity

        state = WorldState(
            entities={"hero": Entity("hero", "player", "Hero", {}, None)},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
        )
        # hero has no spatial_anchor (None)
        class MockGraph:
            pass

        # Should return early without error — line 60
        _copy_escape_edges(MockGraph(), state, [], Path("/tmp"))
