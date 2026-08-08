# Design: epic-4-cli

## Technical Approach

Single `src/fortress_engine/cli/main.py` (~300 lines) implementing the `fortress-engine` console script with three argparse subcommands (`run`, `validate`, `test`). A shared `_build_engine(world_path, parser_name, narrator_name)` helper returns an `EngineBundle` dataclass containing all wired components. Wiring mirrors the proven `_OrchFixture` pattern from `tests/test_integration/test_walkthrough.py:58-122`: load world config → read language → create plugins via `PluginFactory` → `EventBus` → `WorldState` with runtime-created protagonist → `EpisodeManager.start_episode()` → `GoalEvaluator` → `TurnOrchestrator`.

**Critical narrator output handling**: The existing narrators (`MinimalNarrator`, `TemplateNarrator`) subscribe their `_bus_handler` which calls `handle_event(event, None)` and discards the return value. The CLI **MUST** install its own wildcard subscriber `event_bus.subscribe("*", handler)` that calls `narrator.handle_event(event, live_world_state)` and prints non-`None` results to stdout. This is the only way narrator output reaches the terminal.

## Architecture Decisions

### Decision: EngineBundle dataclass for shared wiring

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Return tuple of 7 components | Fragile ordering, no self-documentation | ❌ |
| Return `dict` | No type safety, keys typo-prone | ❌ |
| `@dataclass EngineBundle` | Explicit fields, type hints, IDE support | ✅ |

**Rationale**: The `_build_engine()` helper is called by all three subcommands. A dataclass provides clear contracts, prevents positional errors, and documents the wiring result.

### Decision: Protagonist entity created at runtime (not loaded from YAML)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Load protagonist from `shared/player.yaml` | Couples world authoring to engine; player entity may not exist | ❌ |
| Create `Entity("hero", "player", "Hero", {"max_weight": 20}, None)` in `_build_engine()` | Matches `_OrchFixture`; engine-agnostic; world only provides `protagonist_id` via config | ✅ |

**Rationale**: The engine is entity-agnostic (architecture constant). The world config may specify `protagonist_id` (default `"hero"`). The CLI creates the entity at runtime with sensible defaults, same as `_OrchFixture`.

### Decision: Wildcard event bus subscription for narrator output

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Modify narrators to print directly | Breaks plugin contract; narrators are reusable libraries | ❌ |
| Subscribe to specific event types (`action_output`, `entity_entered`, …) | Must mirror `_NARRATED_EVENTS`; fragile if narrator adds types | ❌ |
| `event_bus.subscribe("*", handler)` calling `narrator.handle_event(event, state)` | Captures ALL narratable events; single subscription; uses live `WorldState` | ✅ |

**Rationale**: Spec requirement #6 (CRITICAL). The narrator's internal `_bus_handler` discards output. Only a wildcard subscription with live `WorldState` captures narration for stdout.

### Decision: Exit code contract enforced at argparse + subcommand level

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Let exceptions bubble (exit 1 for all) | Cannot distinguish argparse (2) from world errors (1) | ❌ |
| `sys.exit(code)` in each error path | Explicit, testable, matches spec | ✅ |

**Rationale**: Spec requirement #7. Argparse errors → exit 2 (stderr). World/validation/plugin/episode errors → exit 1 (stderr). Success → exit 0.

## Data Flow

### `run` command

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  User Input │────▶│  Parser      │────▶│  TurnOrchestrator│
│  (stdin)    │     │  (plugin)    │     │  execute_turn() │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                    ┌──────────────┐              │
                    │  EventBus    │◀─────────────┘
                    │  (sync)      │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  Narrator   │  │  CLI Wild-  │  │  State      │
   │  _bus_hdlr  │  │  card Sub   │  │  Mutations  │
   │ (discards)  │  │ (prints to  │  │             │
   └─────────────┘  │  stdout)    │  └─────────────┘
                    └─────────────┘
```

### `validate` command

```text
EntityLoader(world_path) → validate_world() → problems list
         │                                        │
         ▼                                        ▼
    (loads                                  Empty → "World validation passed."
     world.yaml)                             Non-empty → each problem to stderr
```

### `test` command

```text
_build_engine() → (optional --episode switch) → read walkthrough lines
       │                                              │
       ▼                                              ▼
execute_turn(cmd) for each line              GoalEvaluator.check(state)
       │                                              │
       ▼                                              ▼
   (state mutations)                         PASS/FAIL → stdout, exit 0/1
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/fortress_engine/cli/main.py` | Create | CLI entry point: `main()`, argparse with 3 subparsers, `_build_engine()` helper, `EngineBundle` dataclass, subcommand handlers |
| `src/fortress_engine/cli/__init__.py` | Unchanged | Empty, exists |
| `tests/test_cli/test_main.py` | Create | Unit tests: argparse setup, exit codes, help text |
| `tests/test_cli/test_run.py` | Create | Integration tests: stdin loop, EOF/Ctrl+C, `--save` acknowledgment, narrator output capture |
| `tests/test_cli/test_validate.py` | Create | Unit + integration: valid world (exit 0), broken world (exit 1, stderr) |
| `tests/test_cli/test_test_cmd.py` | Create | Integration: walkthrough PASS/FAIL, episode switching, missing episode exit 1 |

## Interfaces / Contracts

### EngineBundle dataclass

```python
from dataclasses import dataclass
from typing import Any

from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.plugins.narrator_interface import NarratorInterface
from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.goal_evaluator import GoalEvaluator


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
```

### _build_engine() signature

```python
def _build_engine(
    world_path: str,
    parser_name: str = "classic",
    narrator_name: str = "template",
) -> EngineBundle:
    """
    Build a fully wired engine for the given world.
    
    Raises SystemExit(1) on world/config/plugin/episode errors.
    """
    ...
```

### CLI wildcard narrator handler

```python
def _install_narrator_stdout_handler(bundle: EngineBundle) -> None:
    """Subscribe wildcard handler that prints narrator output to stdout."""
    def handler(event):
        text = bundle.narrator.handle_event(event, bundle.state)
        if text is not None:
            print(text)
    bundle.event_bus.subscribe("*", handler)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Argparse structure, exit codes, help text | Mock `sys.argv`, capture stderr/stdout, assert `SystemExit` codes |
| Unit | `_build_engine()` returns valid `EngineBundle` | Call against `worlds/_test_minimal/`; assert bundle fields populated, `state.player_controlled_entities` is list |
| Unit | `validate` command logic | Mock `EntityLoader.validate_world()` return values; assert stdout/stderr + exit codes |
| Integration | `run` command stdin loop | Mock `input()` with side effects (commands → EOF); capture stdout; verify narrator output printed; assert exit 0 |
| Integration | `run` Ctrl+C handling | Mock `input()` raising `KeyboardInterrupt`; assert farewell printed, exit 0 |
| Integration | `test` command walkthrough | Use real `_test_minimal` world + walkthrough file; assert PASS/FAIL + exit codes |
| Integration | Narrator output capture (CRITICAL) | Emit `action_output`/`entity_entered` events into bus; verify CLI wildcard handler prints to stdout; verify narrator's internal `_bus_handler` does NOT print |

**Coverage gate**: All new tests in `tests/test_cli/` must contribute to >99% branch coverage. Mock `input()`/`print()` for `run`; subprocess end-to-end test for full CLI invocation.

## Threat Matrix

**N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.** The CLI reads stdin, writes stdout/stderr, and calls engine APIs. It does not execute shell commands, spawn subprocesses, interact with git, or classify executable files.

## Migration / Rollout

No migration required. New console script only; `pyproject.toml` entry point already declared. Single commit adds `main.py` + `tests/test_cli/`. Rollback = revert commit.

## Open Questions

- [ ] Should `_build_engine()` accept a `protagonist_id` override (from `--protagonist` flag) or always use world config default? Spec says world config `protagonist_id` with `"hero"` fallback — no CLI flag needed.
- [ ] Should `--save` acknowledgment include the slot name in the message? Spec says "acknowledged only" — print `Saving to slot '{slot}'... (persistence deferred)` to stdout.
- [ ] Do we need a `--language` CLI flag to override world config language? Spec says world language read from config BEFORE plugin creation — no override flag in scope.

---

**Size check**: ~750 words (under 800 budget).