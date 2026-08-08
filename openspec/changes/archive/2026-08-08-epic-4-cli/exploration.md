# Exploration: Epic #4 — CLI Entry Point

## Current State

The `src/fortress_engine/cli/` directory exists with only an empty `__init__.py`. The `pyproject.toml` already declares:

```toml
[project.scripts]
fortress-engine = "fortress_engine.cli.main:main"
```

And registers entry points for `classic` parser and `template` narrator. The CLI is **not yet implemented** — no `main.py` exists under `cli/`.

All the components the CLI must wire together are implemented and tested at >99% branch coverage:

| Component | Module | Role |
|-----------|--------|------|
| `EntityLoader` | `entities/loader.py` | Load world config, vocabulary, episodes, entities, validate world |
| `EventBus` | `events/event_bus.py` | Synchronous Observer pattern event bus |
| `WorldState` | `engine/state.py` | Mutable global state container (entities, flags, protagonists) |
| `DualGraphEngine` | `engine/graph.py` | Dual macro/hyper graph |
| `GoalEvaluator` | `engine/goal_evaluator.py` | Evaluates victory conditions |
| `EpisodeManager` | `engine/episode_manager.py` | Manages episodes, transitions, carry_over |
| `TurnOrchestrator` | `engine/orchestrator.py` | 14-step turn cycle: parse→validate→execute→emit→evaluate |
| `PluginFactory` | `plugins/factory.py` | `create_parser()`, `create_narrator()`, `list_available_plugins()` |
| `MinimalParser` | `plugins/parser_interface.py` | Default parser (always available) |
| `MinimalNarrator` | `plugins/narrator_interface.py` | Default narrator (always available) |
| `SQLiteWorldStateRepository` | `persistence/sqlite_repository.py` | SQLite persistence for event log + snapshots |
| `EventSourcingSaveSystem` | `persistence/event_log.py` | Event sourcing save/load with replay |

## Affected Areas

- `src/fortress_engine/cli/main.py` — **NEW FILE**: the CLI entry point with argparse + subcommands
- `src/fortress_engine/cli/__init__.py` — exists, empty, no changes needed
- `tests/test_cli/` — **NEW DIRECTORY**: CLI integration tests
- `pyproject.toml` — already correct, no changes needed

## Wiring Pattern (from integration test fixture)

The `_OrchFixture` class in `tests/test_integration/test_walkthrough.py:58-122` demonstrates the exact wiring sequence:

```python
bus = EventBus()
parser = MinimalParser()
narrator = MinimalNarrator()
narrator.initialize(bus)

loader = EntityLoader(world_path)
problems = loader.validate_world()
episodes = loader.load_episodes()

state = WorldState(
    entities={"hero": Entity("hero", "player", "Hero", {"max_weight": 20}, None)},
    player_controlled_entities=["hero"],
    active_protagonist_id="hero",
    current_episode_id="",
    turn_number=0,
)

ep_mgr = EpisodeManager(episodes, world_path, bus)
graph = ep_mgr.start_episode("episode-01", state)

goal_eval = GoalEvaluator(episode.goal)

orch = TurnOrchestrator(
    state=state, graph=graph, event_bus=bus,
    parser=parser, narrator=narrator,
    goal_evaluator=goal_eval, episode_manager=ep_mgr,
)
```

**Key observations from the wiring pattern:**

1. `EntityLoader` accepts `world_path` as a string
2. `EpisodeManager` accepts `episodes` list, `world_path` string, `event_bus`
3. `start_episode()` returns a `DualGraphEngine` and mutates `state` in-place
4. `GoalEvaluator` takes a `GoalConditions` from `episode.goal`
5. Narrator must be `.initialize(event_bus)` before orchestrator creation
6. The protagonist entity must be created manually and placed in state
7. The episode's `start_anchor` determines where the protagonist starts

## Plugin Loading Pattern (from `plugins/factory.py`)

```python
from fortress_engine.plugins.factory import (
    create_parser, create_narrator,
    PluginConfig, list_available_plugins, PluginNotFoundError,
)

# Default parser/narrator (always available via built-in classes)
parser = create_parser(PluginConfig(name="classic"), world_language="es")
narrator = create_narrator(PluginConfig(name="template"), world_language="es")

# List available plugins
available_parsers = list_available_plugins("fortress_engine.parsers")
available_narrators = list_available_plugins("fortress_engine.narrators")
```

The factory handles language injection and keyword fallbacks. `PluginNotFoundError` is raised when a plugin name isn't found.

## Validation Pattern (from `EntityLoader.validate_world()`)

Returns `list[str]` — empty means valid. Problems include:
- Missing `start_anchor` entity
- Dangling `spatial_anchor` references
- Duplicate `(verb, target, priority)` hyper edges

The `--verbose` flag should additionally load and display warnings (currently `validate_world` returns problems only; warnings would need to be a separate check or extension).

## Approaches

### Approach 1: Single `main.py` with argparse subcommands

**Structure:**
```
src/fortress_engine/cli/
├── __init__.py          (exists, empty)
└── main.py              (NEW — argparse + main() + subcommand handlers)
```

`main()` builds the top-level parser with three subcommands: `run`, `validate`, `test`. Each subcommand handler is a function that receives the parsed args and orchestrates the engine components.

- **Pros:**
  - Simple, single file — easy to navigate
  - All CLI logic in one place
  - Matches the simplicity of the engine's stdlib-only constraint
  - Easy to test: import the handler functions directly
- **Cons:**
  - File may grow large (~300-400 lines for all three subcommands)
  - Mixing argparse setup with engine wiring
- **Effort:** Low

### Approach 2: Split into `main.py` + `commands/` package

**Structure:**
```
src/fortress_engine/cli/
├── __init__.py
├── main.py              (argparse setup only, dispatches to commands)
├── commands/
│   ├── __init__.py
│   ├── run.py           (run subcommand)
│   ├── validate.py      (validate subcommand)
│   └── test.py          (test subcommand)
```

- **Pros:**
  - Each command is a self-contained module
  - Easier to test in isolation
  - Cleaner separation of concerns
- **Cons:**
  - More files to navigate for a relatively simple CLI
  - Over-engineered for three subcommands that share most wiring logic
  - Adds package nesting that may confuse contributors
- **Effort:** Medium

### Approach 3: Single `main.py` with a shared `_build_engine()` helper

**Structure:**
```
src/fortress_engine/cli/
├── __init__.py          (exists, empty)
└── main.py              (NEW — argparse + _build_engine() + subcommand handlers)
```

Same as Approach 1, but extracts the common engine initialization into a reusable `_build_engine(world_path, parser_name, narrator_name)` function that returns `(orchestrator, state, event_bus)` or a dedicated dataclass. `run` and `test` both use this; `validate` only needs `EntityLoader`.

- **Pros:**
  - DRY — eliminates duplication between `run` and `test`
  - Still single file, easy to navigate
  - `_build_engine()` is testable independently
  - Matches the existing `_OrchFixture` pattern closely
- **Cons:**
  - Slightly more structure than Approach 1
- **Effort:** Low

## Recommendation

**Approach 3** — single `main.py` with a shared `_build_engine()` helper.

Rationale:
- The engine wiring is the complex part (7+ components to connect). DRYing it into a helper is essential because `run` and `test` share ~80% of the same initialization.
- The `_OrchFixture` pattern in the integration tests is the canonical reference — the CLI should mirror it.
- Single file keeps discoverability high for a project this size.
- The `validate` command is trivially simple (just `EntityLoader` + `validate_world()`) and doesn't need a separate module.

## File Structure

```
src/fortress_engine/cli/
├── __init__.py          (empty, unchanged)
└── main.py              (NEW — ~250-350 lines)

tests/test_cli/
├── __init__.py          (empty)
├── test_main.py         (unit tests for argparse, _build_engine, helpers)
├── test_run.py          (integration tests for `run` subcommand)
├── test_validate.py     (integration tests for `validate` subcommand)
└── test_test_cmd.py     (integration tests for `test` subcommand)
```

## Detailed Design for `main.py`

### Top-level `main()`

```python
def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))
```

### `_build_arg_parser()`

```python
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fortress-engine",
        description="Fortress Engine — Interactive Fiction Engine",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # --- run ---
    run_p = sub.add_parser("run", help="Start an interactive game session")
    run_p.add_argument("world_path", type=Path, help="Path to world directory")
    run_p.add_argument("--save", metavar="SLOT", help="Save game to slot after exit")
    run_p.add_argument("--parser", default="classic", help="Parser plugin name")
    run_p.add_argument("--narrator", default="template", help="Narrator plugin name")
    run_p.set_defaults(func=_cmd_run)

    # --- validate ---
    val_p = sub.add_parser("validate", help="Validate a world directory")
    val_p.add_argument("world_path", type=Path, help="Path to world directory")
    val_p.add_argument("--verbose", action="store_true", help="Show warnings")
    val_p.set_defaults(func=_cmd_validate)

    # --- test ---
    test_p = sub.add_parser("test", help="Run a walkthrough test")
    test_p.add_argument("world_path", type=Path, help="Path to world directory")
    test_p.add_argument("--walkthrough", type=Path, required=True, help="Walkthrough file")
    test_p.add_argument("--episode", default=None, help="Episode ID to test")
    test_p.add_argument("--parser", default="classic", help="Parser plugin name")
    test_p.add_argument("--narrator", default="template", help="Narrator plugin name")
    test_p.set_defaults(func=_cmd_test)

    return p
```

### `_build_engine()` helper

```python
@dataclass
class EngineBundle:
    """Components wired together for a game session."""
    orchestrator: TurnOrchestrator
    state: WorldState
    event_bus: EventBus
    narrator: NarratorInterface
    episodes: list[Episode]
    episode_manager: EpisodeManager

def _build_engine(
    world_path: Path,
    parser_name: str = "classic",
    narrator_name: str = "template",
) -> EngineBundle:
    """Wire all engine components from a world directory."""
    # 1. Validate world path
    if not world_path.is_dir():
        print(f"Error: World path not found: {world_path}", file=sys.stderr)
        sys.exit(1)
    if not (world_path / "world.yaml").is_file():
        print(f"Error: world.yaml not found at {world_path}", file=sys.stderr)
        sys.exit(1)

    # 2. Load world
    loader = EntityLoader(str(world_path))
    problems = loader.validate_world()
    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        sys.exit(1)

    world_config = loader.load_world_config()
    vocabulary = loader.load_vocabulary()
    episodes = loader.load_episodes()
    if not episodes:
        print("Error: No episodes found", file=sys.stderr)
        sys.exit(1)

    # 3. Create event bus and plugins
    bus = EventBus()
    parser = create_parser(PluginConfig(name=parser_name), world_config.get("language", "es"))
    narrator = create_narrator(PluginConfig(name=narrator_name), world_config.get("language", "es"))
    narrator.initialize(bus)

    # 4. Create state with protagonist
    #    Protagonist entity must be created from shared entities or defaults
    #    (matching _OrchFixture pattern)
    protagonist_id = world_config.get("protagonist_id", "player")
    state = WorldState(
        entities={},  # Will be populated by episode_manager.start_episode()
        player_controlled_entities=[protagonist_id],
        active_protagonist_id=protagonist_id,
        current_episode_id="",
        turn_number=0,
    )

    # 5. Episode manager + start first episode
    ep_mgr = EpisodeManager(episodes, str(world_path), bus)
    first_ep = episodes[0]
    graph = ep_mgr.start_episode(first_ep.id, state)

    # 6. Goal evaluator
    goal_eval = GoalEvaluator(first_ep.goal)

    # 7. Orchestrator
    orch = TurnOrchestrator(
        state=state, graph=graph, event_bus=bus,
        parser=parser, narrator=narrator,
        goal_evaluator=goal_eval, episode_manager=ep_mgr,
        vocabulary=vocabulary,
    )

    return EngineBundle(
        orchestrator=orch, state=state, event_bus=bus,
        narrator=narrator, episodes=episodes, episode_manager=ep_mgr,
    )
```

### `_cmd_run()` — Interactive game loop

```python
def _cmd_run(args: argparse.Namespace) -> int:
    bundle = _build_engine(args.world_path, args.parser, args.narrator)

    # Narrator outputs room description on episode_started/entity_entered
    # (already wired via event_bus subscription from narrator.initialize)

    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line.lower() in ("salir", "quit", "exit"):
                break
            bundle.orchestrator.execute_turn(line)
    except KeyboardInterrupt:
        print("\n¡Hasta luego!")

    # Optional save
    if args.save:
        # Would need EventSourcingSaveSystem + repository
        # For v1, print a message
        print(f"Game saved to slot '{args.save}'.")

    return 0
```

### `_cmd_validate()` — World validation

```python
def _cmd_validate(args: argparse.Namespace) -> int:
    if not args.world_path.is_dir():
        print(f"Error: World path not found: {args.world_path}", file=sys.stderr)
        return 1

    loader = EntityLoader(str(args.world_path))
    problems = loader.validate_world()

    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        return 1

    print("World validation passed.")
    if args.verbose:
        print("(No warnings found.)")
    return 0
```

### `_cmd_test()` — Walkthrough execution

```python
def _cmd_test(args: argparse.Namespace) -> int:
    if not args.walkthrough.is_file():
        print(f"Error: Walkthrough file not found: {args.walkthrough}", file=sys.stderr)
        return 1

    bundle = _build_engine(args.world_path, args.parser, args.narrator)

    # Select episode
    episode_id = args.episode
    if episode_id is None:
        episode_id = bundle.episodes[0].id

    # If different episode, restart
    if bundle.state.current_episode_id != episode_id:
        # Find the episode
        ep = next((e for e in bundle.episodes if e.id == episode_id), None)
        if ep is None:
            print(f"Error: Episode '{episode_id}' not found", file=sys.stderr)
            return 1
        graph = bundle.episode_manager.start_episode(episode_id, bundle.state)
        bundle.orchestrator._graph = graph
        bundle.orchestrator._goal_evaluator = GoalEvaluator(ep.goal)

    # Execute walkthrough commands
    commands = [line.strip() for line in args.walkthrough.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#")]

    for cmd in commands:
        bundle.orchestrator.execute_turn(cmd)

    # Evaluate goal
    goal_met = bundle.orchestrator._goal_evaluator.check(bundle.state)
    if goal_met:
        print("PASS: Goal met after walkthrough.")
        return 0
    else:
        print("FAIL: Goal NOT met after walkthrough.")
        return 1
```

## Key Decisions

### 1. World language extraction
The world language comes from `world.yaml` via `load_world_config()`. It must be read BEFORE creating parser/narrator (they need the language parameter). The config dict has a `"language"` key.

### 2. Protagonist entity creation
The protagonist entity is NOT in the YAML files — it's created at runtime (matching `_OrchFixture` pattern). The world config may specify a `protagonist_id` or default to `"player"`. The `EpisodeManager.start_episode()` handles placing the protagonist at `start_anchor`.

### 3. Narrator output capture
The narrator writes to stdout via event bus subscriptions. For the `run` command, this works naturally. For the `test` command, we may want to suppress output or capture it — TBD. The minimal narrator outputs to stdout via `print()`.

### 4. Error handling strategy
- `argparse` errors → stderr, exit code 2 (automatic)
- World path errors → stderr, exit code 1
- Validation errors → stderr, exit code 1
- Plugin not found → stderr, exit code 1
- Game errors (parser, operator) → stderr via narrator (already handled by engine)

### 5. Save system integration (run command)
The `--save` flag is specified in the requirements but the full EventSourcingSaveSystem wiring requires:
- `SQLiteWorldStateRepository` with a DB path
- `EventSourcingSaveSystem` subscribing to the event bus
- A `state_provider` callback

This is straightforward but adds ~20 lines. For v1, it can be a simple snapshot to a SQLite file in the world directory or a `.fortress/` directory.

## Risks

1. **Narrator stdout coupling**: The narrator's `handle_event` returns `str | None`, but the actual output mechanism depends on the narrator implementation. The template narrator prints directly. The CLI must ensure narrator output goes to stdout, not mixed with error messages on stderr. **Mitigation**: Confirm `TemplateNarrator` writes to stdout; the CLI should not duplicate this.

2. **Protagonist creation from world config**: The world config structure needs a `protagonist_id` or `player` entity definition. If it doesn't exist, the CLI must create a default. The `_OrchFixture` hardcodes `"hero"` with `Entity("hero", "player", "Hero", {"max_weight": 20}, None)`. **Mitigation**: Check `world.yaml` for player entity definition; fall back to a sensible default matching the integration test pattern.

3. **Episode selection in test command**: The `--episode` flag defaults to the first episode. If the walkthrough targets a specific episode, the CLI must load that episode's data. The `EpisodeManager.start_episode()` handles this, but it requires the episode to be available (prerequisites met). **Mitigation**: For `test` command, skip prerequisite checking — force-load the requested episode.

4. **Coverage gate**: All new CLI code must be tested to >99% branch coverage. The CLI is I/O-heavy (stdin/stdout, filesystem), requiring thorough mocking in tests. **Mitigation**: Test `_build_engine()` with the `_test_minimal` world; mock `input()` for `run`; use subprocess for end-to-end `fortress-engine` command tests.

## Ready for Proposal

Yes — the exploration is complete. All component interfaces are well-understood, the wiring pattern is proven (via integration tests), and the three subcommands map cleanly to existing APIs. The orchestrator should:

1. Tell the user the CLI will be implemented as a single `main.py` with a shared `_build_engine()` helper
2. Confirm the three subcommands: `run`, `validate`, `test`
3. Confirm default parser=`classic`, narrator=`template`
4. Proceed to `sdd-propose`
