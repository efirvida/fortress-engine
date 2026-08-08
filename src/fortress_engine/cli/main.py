"""CLI entry point for fortress-engine.

Provides the `fortress-engine` console script with three subcommands:
run, validate, and test. Bridges the engine core to the terminal.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.goal_evaluator import GoalEvaluator
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus
from fortress_engine.plugins.factory import create_narrator, create_parser
from fortress_engine.plugins.narrator_interface import NarratorInterface


# ---------------------------------------------------------------------------
# EngineBundle — fully wired engine components
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineBundle:
    """Fully wired engine components for a single world."""

    orchestrator: TurnOrchestrator
    state: WorldState
    event_bus: EventBus
    narrator: NarratorInterface
    episodes: list[Any]  # Episode dataclass (avoid circular import)
    episode_manager: EpisodeManager
    world_config: dict[str, Any]


# ---------------------------------------------------------------------------
# Engine builder
# ---------------------------------------------------------------------------


def _copy_hyper_edges_to_all_rooms(graph, state, episodes, path):
    """Copy hyper edges from start_anchor to all other rooms.

    EpisodeManager.start_episode() registers all hyper edges under the
    episode's start_anchor only.  Since the engine resolves hyper edges
    by anchor, edges defined at the start room would be unreachable from
    any other room.  This copies every registered hyper edge to every
    room in the episode so actions (take, give, kill, break, etc.) work
    regardless of where the protagonist currently is.

    This mirrors the _OrchFixture pattern from test_walkthrough.py but
    generalizes it from "escape edges" to ALL edges.
    """
    import yaml

    start_anchor = state.get_entity("hero").spatial_anchor
    if not start_anchor:
        return

    # Collect ALL hyper edges registered under start_anchor.
    all_edges: list = []
    for verb in [
        "tomar", "coger", "dejar", "soltar",
        "abrir", "matar", "asesinar", "destrozar",
        "romper", "forzar", "preguntar", "interrogar",
        "dar", "regalar", "ver", "leer", "mirar", "observar",
        "inventario", "abandonar", "terminar",
        "huir", "escapar", "ir", "atravesar", "cruzar", "pasar",
        "responder", "diciendo", "ejecutar", "salvar", "cargar",
        "pesar",
    ]:
        try:
            edges = graph.get_hyper_edges_for_verb(start_anchor, verb)
            if edges:
                all_edges.extend(edges)
        except Exception:
            continue

    if not all_edges:
        return

    # Copy every edge to every room in every episode.
    for ep in episodes:
        ep_num = ep.id.split("-")[-1]
        rooms_path = path / f"episode-{ep_num}" / "rooms"
        if not rooms_path.is_dir():
            continue

        for room_file in rooms_path.glob("*.yaml"):
            with open(room_file) as f:
                room_data = yaml.safe_load(f)
            if not room_data:
                continue
            room_id = room_data.get("entity_id")
            if room_id and room_id != start_anchor:
                for edge in all_edges:
                    graph.add_hyper_edge(room_id, edge)


def _build_engine(
    world_path: str,
    parser_name: str = "classic",
    narrator_name: str = "template",
) -> EngineBundle:
    """Build a fully wired engine for the given world.

    Raises SystemExit(1) on world/config/plugin/episode errors.
    """
    path = Path(world_path)

    # Validate world.yaml exists
    if not (path / "world.yaml").is_file():
        print(f"Error: world.yaml not found at {path / 'world.yaml'}", file=sys.stderr)
        raise SystemExit(1)

    try:
        loader = EntityLoader(str(path))

        # Validate world integrity
        problems = loader.validate_world()
        if problems:
            for problem in problems:
                print(f"World validation error: {problem}", file=sys.stderr)
            raise SystemExit(1)

        # Load world config and vocabulary
        world_config = loader.load_world_config()
        vocabulary = loader.load_vocabulary()
        episodes = loader.load_episodes()

        # Create event bus
        bus = EventBus()

        # Create plugins using world language
        language = world_config.get("language", "es")
        parser = create_parser(
            __import__("fortress_engine.plugins.factory", fromlist=["PluginConfig"]).PluginConfig(
                name=parser_name
            ),
            language,
        )
        narrator = create_narrator(
            __import__("fortress_engine.plugins.factory", fromlist=["PluginConfig"]).PluginConfig(
                name=narrator_name
            ),
            language,
        )
        narrator.initialize(bus)

        # Create protagonist entity at runtime
        state = WorldState(
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

        # Start episode
        ep_mgr = EpisodeManager(episodes, str(path), bus)
        graph = ep_mgr.start_episode("episode-01", state)

        # Copy escape edges from start_anchor to all other rooms.
        # This mirrors the _OrchFixture pattern from test_walkthrough.py.
        _copy_hyper_edges_to_all_rooms(graph, state, episodes, path)

        # Build goal evaluator
        episode = episodes[0]
        goal_eval = GoalEvaluator(episode.goal)

        # Build orchestrator
        orch = TurnOrchestrator(
            state=state,
            graph=graph,
            event_bus=bus,
            parser=parser,
            narrator=narrator,
            goal_evaluator=goal_eval,
            episode_manager=ep_mgr,
        )

        return EngineBundle(
            orchestrator=orch,
            state=state,
            event_bus=bus,
            narrator=narrator,
            episodes=episodes,
            episode_manager=ep_mgr,
            world_config=world_config,
        )

    except SystemExit:
        raise
    except Exception as e:
        print(f"Error building engine: {e}", file=sys.stderr)
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------------


def _install_narrator_stdout_handler(bundle: EngineBundle) -> None:
    """Subscribe wildcard handler that prints narrator output to stdout."""
    def handler(event):
        text = bundle.narrator.handle_event(event, bundle.state)
        if text is not None:
            print(text)
    bundle.event_bus.subscribe("*", handler)


def main() -> None:
    """Entry point for the fortress-engine console script."""
    parser = argparse.ArgumentParser(
        prog="fortress-engine",
        description="Fortress Engine — Interactive Fiction Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Run an interactive session")
    run_parser.add_argument("world_path", help="Path to the world directory")
    run_parser.add_argument("--save", metavar="SLOT", help="Save game to slot (deferred)")
    run_parser.add_argument("--parser", default="classic", help="Parser plugin name")
    run_parser.add_argument("--narrator", default="template", help="Narrator plugin name")

    # validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate world integrity")
    validate_parser.add_argument("world_path", help="Path to the world directory")
    validate_parser.add_argument("--verbose", action="store_true", help="Verbose output")

    # test subcommand
    test_parser = subparsers.add_parser("test", help="Run walkthrough test")
    test_parser.add_argument("world_path", help="Path to the world directory")
    test_parser.add_argument(
        "--walkthrough", required=True, help="Path to walkthrough file"
    )
    test_parser.add_argument("--episode", default="episode-01", help="Episode to test")
    test_parser.add_argument("--parser", default="classic", help="Parser plugin name")
    test_parser.add_argument("--narrator", default="template", help="Narrator plugin name")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help(sys.stderr)
        raise SystemExit(2)

    # Dispatch to subcommand handlers
    if args.command == "run":
        cmd_run(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "test":
        cmd_test(args)
    else:  # pragma: no cover — argparse ensures only known subcommands reach here
        parser.print_help(sys.stderr)
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# Subcommand handlers (stubs — implemented in Phase 3/4)
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    """Handle the run subcommand.

    Builds the engine, then loops on input("> ") until EOF, Ctrl+C, or quit.
    """
    try:
        bundle = _build_engine(
            args.world_path,
            parser_name=args.parser,
            narrator_name=args.narrator,
        )
    except SystemExit:
        raise

    # Install narrator output handler
    _install_narrator_stdout_handler(bundle)

    # Save acknowledgment
    if args.save:
        print(f"Saving to slot '{args.save}'... (persistence deferred)")

    # Input loop
    try:
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n¡Adiós!")
                break

            # Skip empty lines
            if not line.strip():
                continue

            # Check for quit
            if line.strip().lower() in ("quit", "exit"):
                break

            # Execute turn
            bundle.orchestrator.execute_turn(line)

            # Check if player is dead
            try:
                hero = bundle.state.get_entity("hero")
                if hero.components.get("is_dead", False):
                    break
            except KeyError:
                pass
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    raise SystemExit(0)


def cmd_validate(args: argparse.Namespace) -> None:
    """Handle the validate subcommand.

    Validates world integrity and prints results.
    """
    path = Path(args.world_path)

    # Check if world.yaml exists
    if not (path / "world.yaml").is_file():
        print(f"Error: world.yaml not found at {path / 'world.yaml'}", file=sys.stderr)
        raise SystemExit(1)

    try:
        loader = EntityLoader(str(path))
        problems = loader.validate_world()

        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            raise SystemExit(1)

        print("World validation passed.")
        raise SystemExit(0)

    except SystemExit:
        raise
    except Exception as e:
        print(f"Error validating world: {e}", file=sys.stderr)
        raise SystemExit(1) from e


def cmd_test(args: argparse.Namespace) -> None:
    """Handle the test subcommand.

    Runs a walkthrough file and evaluates if the goal is achieved.
    """
    try:
        bundle = _build_engine(
            args.world_path,
            parser_name=args.parser,
            narrator_name=args.narrator,
        )
    except SystemExit:
        raise

    # Install narrator output handler
    _install_narrator_stdout_handler(bundle)

    # Check if episode exists
    episode_id = args.episode
    episode_exists = any(ep.id == episode_id for ep in bundle.episodes)
    if not episode_exists:
        print(f"Error: Episode '{episode_id}' not found", file=sys.stderr)
        raise SystemExit(1)

    # If different episode, switch to it
    if bundle.state.current_episode_id != episode_id:
        bundle.episode_manager.start_episode(episode_id, bundle.state)

    # Read walkthrough file
    walkthrough_path = Path(args.walkthrough)
    if not walkthrough_path.is_file():
        print(f"Error: Walkthrough file not found at {walkthrough_path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        with open(walkthrough_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading walkthrough: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    # Execute each command
    for line in lines:
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        bundle.orchestrator.execute_turn(line)

    # Evaluate goal
    from fortress_engine.engine.goal_evaluator import GoalEvaluator

    episode = next(ep for ep in bundle.episodes if ep.id == episode_id)
    goal_eval = GoalEvaluator(episode.goal)
    goal_met = goal_eval.check(bundle.state)

    if goal_met:
        print("PASS")
        raise SystemExit(0)
    else:
        print("FAIL")
        raise SystemExit(1)
