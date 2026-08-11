"""CLI entry point for fortress-engine.

Provides the `fortress-engine` console script with four subcommands:
run, validate, test, and audit-graph. Bridges the engine core to the
terminal.
"""

from __future__ import annotations

import argparse
import json
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
                name=parser_name,
                options={"vocabulary": vocabulary},
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

        # Protagonist from the world definition when present, else default.
        shared = loader.load_shared_entities("episode-01")
        player_entities = [e for e in shared if e.type == "player"]
        if player_entities:
            hero = player_entities[0]
        else:
            hero = Entity("hero", "player", "Hero", {"max_weight": 20}, None)

        # Create protagonist entity at runtime
        state = WorldState(
            entities={"hero": hero},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="",
            turn_number=0,
        )

        # Start episode.
        # EpisodeManager.distribute_hyper_edges_to_anchors() copies all
        # hyper edges from start_anchor to every spatial_anchor in the
        # episode, so actions work regardless of protagonist position.
        # The engine is entity-agnostic: no "rooms", no hardcoded verbs.
        ep_mgr = EpisodeManager(episodes, str(path), bus)
        graph = ep_mgr.start_episode("episode-01", state)
        ep_mgr.distribute_hyper_edges_to_anchors(graph, state, "episode-01")

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
            vocabulary=vocabulary,
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

    # audit-graph subcommand
    audit_parser = subparsers.add_parser(
        "audit-graph", help="Audit macro graph integrity"
    )
    audit_parser.add_argument("world_path", help="Path to the world directory")
    audit_parser.add_argument(
        "--episode", default=None, help="Episode to audit (default: first loaded)"
    )
    audit_parser.add_argument(
        "--json", action="store_true", help="Emit deterministic JSON report"
    )
    audit_parser.add_argument(
        "--include-info", action="store_true", help="Include INFO findings"
    )

    # solve subcommand
    solve_parser = subparsers.add_parser(
        "solve", help="Verify episode completability via blind exploration"
    )
    solve_parser.add_argument("world_path", help="Path to the world directory")
    solve_parser.add_argument(
        "--episode", default=None,
        help="Episode to solve (default: first loaded)",
    )
    solve_parser.add_argument(
        "--answers", default=None,
        help="Path to curated answers YAML override",
    )
    solve_parser.add_argument(
        "--json", action="store_true",
        help="Emit deterministic JSON verdict",
    )
    solve_parser.add_argument(
        "--max-turns", type=int, default=50_000,
        help="Maximum turn budget (default: 50000)",
    )

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
    elif args.command == "audit-graph":
        cmd_audit_graph(args)
    elif args.command == "solve":
        cmd_solve(args)
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


def cmd_audit_graph(args: argparse.Namespace) -> None:
    """Handle the audit-graph subcommand.

    Runs the static graph audit for the selected episode (first loaded by
    default) and prints a grouped human report or deterministic JSON.

    Exit codes: 0 = no ERROR findings, 1 = one or more ERROR findings,
    2 = usage / missing or malformed world / unknown episode.
    """
    from fortress_engine.autoplay.graph_audit import GraphAudit

    path = Path(args.world_path)

    # Check if world.yaml exists
    if not (path / "world.yaml").is_file():
        print(f"Error: world.yaml not found at {path / 'world.yaml'}", file=sys.stderr)
        raise SystemExit(2)

    try:
        loader = EntityLoader(str(path))
        # Validate world.yaml structure so malformed worlds exit 2.
        loader.load_world_config()
        episodes = loader.load_episodes()
        if not episodes:
            print("Error: no episodes found", file=sys.stderr)
            raise SystemExit(2)

        if args.episode is None:
            episode = episodes[0]
        else:
            matches = [ep for ep in episodes if ep.id == args.episode]
            if not matches:
                print(f"Error: Episode '{args.episode}' not found", file=sys.stderr)
                raise SystemExit(2)
            episode = matches[0]

        report = GraphAudit(loader, episode).run()
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error auditing world: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    findings = [
        f for f in report.findings if args.include_info or f.severity != "INFO"
    ]

    if args.json:
        payload = report.to_dict()
        payload["findings"] = [f.to_dict() for f in findings]
        print(json.dumps(payload, sort_keys=True))
    else:
        _print_audit_human(findings)

    raise SystemExit(1 if any(f.severity == "ERROR" for f in findings) else 0)


def cmd_solve(args: argparse.Namespace) -> None:
    """Handle the solve subcommand.

    Runs the static graph audit and BFS solver for the selected episode.
    Exit codes: 0 = completable, 1 = not completable (diagnosis),
    2 = usage / missing or malformed world / unknown episode.
    """
    from fortress_engine.autoplay.solver import AnswerBook, Solver

    path = Path(args.world_path)

    if not (path / "world.yaml").is_file():
        print(f"Error: world.yaml not found at {path / 'world.yaml'}", file=sys.stderr)
        raise SystemExit(2)

    try:
        loader = EntityLoader(str(path))
        loader.load_world_config()
        episodes = loader.load_episodes()
        if not episodes:
            print("Error: no episodes found", file=sys.stderr)
            raise SystemExit(2)

        if args.episode is None:
            episode = episodes[0]
        else:
            matches = [ep for ep in episodes if ep.id == args.episode]
            if not matches:
                print(
                    f"Error: Episode '{args.episode}' not found",
                    file=sys.stderr,
                )
                raise SystemExit(2)
            episode = matches[0]

        kb = AnswerBook(
            episode_id=episode.id,
            world_path=str(path),
            answers_path=args.answers,
        )

        solver = Solver(loader, episode)
        verdict = solver.solve(max_turns=args.max_turns)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error solving world: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    if args.json:
        print(json.dumps(verdict.to_dict(), sort_keys=True))
    else:
        _print_solve_human(verdict)

    raise SystemExit(0 if verdict.completable else 1)


def _print_solve_human(verdict) -> None:
    """Print human-readable solve result: verdict line, walkthrough, diagnosis."""
    if verdict.completable:
        print(f"Verdict: SOLVABLE ({verdict.total_turns} turns)")
    else:
        print(f"Verdict: NOT SOLVABLE ({verdict.total_turns} turns)")

    if verdict.static_errors:
        print("\nStatic Errors:")
        for finding in verdict.static_errors:
            print(f"  [{finding.category}] {finding.location} — {finding.message}")

    if verdict.walkthrough:
        print("\nWalkthrough:")
        for i, cmd in enumerate(verdict.walkthrough, 1):
            print(f"  {i:>2}. {cmd}")

    if verdict.stuck_rooms:
        print(f"\nStuck Rooms: {', '.join(verdict.stuck_rooms)}")

    if verdict.unsatisfiable_gates:
        print("\nUnsatisfiable Gates:")
        for gate in verdict.unsatisfiable_gates:
            print(
                f"  {gate.passage} | {gate.predicate}: {gate.required} "
                f"— {gate.reason}"
            )


def _print_audit_human(findings: list[Any]) -> None:
    """Print findings grouped by severity (INFO omitted when filtered)."""
    groups: dict[str, list[Any]] = {"ERROR": [], "WARN": [], "INFO": []}
    for finding in findings:
        groups[finding.severity].append(finding)

    printed_any = False
    for severity in ("ERROR", "WARN", "INFO"):
        items = groups[severity]
        if not items:
            continue
        printed_any = True
        print(f"{severity} ({len(items)})")
        for finding in items:
            print(f"  [{finding.category}] {finding.location} — {finding.message}")

    if not printed_any:
        print("No findings.")
