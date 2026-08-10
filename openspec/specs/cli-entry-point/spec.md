# CLI Entry Point Specification

## Purpose

The `fortress-engine` console script — an argparse CLI with `run`, `validate`, `test` subcommands bridging the engine core to the terminal. Closes epic #4 sub-issues #28, #26, #27.

## Requirements

### Requirement: Console script registration and argparse subcommands

`pyproject.toml` MUST register `fortress-engine = "fortress_engine.cli.main:main"`.
`main()` MUST build an argparse parser with subparsers `run`, `validate`,
`test`, and `audit-graph`. Missing/unknown subcommands MUST exit 2 (stderr).

| Subcommand | Arg | Flags |
|---|---|---|
| `run` | `world_path` (dir) | `--save SLOT`, `--parser`, `--narrator` |
| `validate` | `world_path` (dir) | `--verbose` |
| `test` | `world_path` (dir) | `--walkthrough FILE` (req), `--episode`, `--parser`, `--narrator` |
| `audit-graph` | `world_path` (dir) | `--episode ID`, `--json`, `--include-info` |

#### Scenario: Missing subcommand exits 2
- GIVEN no subcommand on the command line
- WHEN `main()` parses args
- THEN argparse writes an error to stderr and exits 2

#### Scenario: Audit subcommand is registered
- GIVEN `audit-graph WORLD --episode ep-2`
- WHEN `main()` parses args
- THEN it dispatches the selected world and episode to the audit handler

### Requirement: EngineBundle and _build_engine() helper

`_build_engine(world_path, parser_name="classic", narrator_name="template")` MUST return an `EngineBundle` with `orchestrator`, `state`, `event_bus`, `narrator`, `episodes`, `episode_manager`, `world_config`. World language MUST be read from `world_config` BEFORE plugin creation. `player_controlled_entities` MUST be a list. Wiring mirrors `_OrchFixture`: validate path+`world.yaml` → config/vocab/episodes → `EventBus()` → `create_parser`/`create_narrator` → `narrator.initialize(bus)` → `WorldState` → `EpisodeManager.start_episode()` → `GoalEvaluator` → `TurnOrchestrator`.

#### Scenario: Minimal world builds successfully
- GIVEN `worlds/_test_minimal/`
- WHEN `_build_engine()` is called
- THEN `bundle.state.current_episode_id == "episode-01"`, `type(bundle.state.player_controlled_entities) is list`

#### Scenario: Missing world.yaml exits 1
- GIVEN a directory without `world.yaml`
- WHEN `_build_engine()` is called
- THEN error to stderr, exit 1

### Requirement: Run command

`run` MUST call `_build_engine()`, then loop on `input("> ")` until `EOFError`, `KeyboardInterrupt`, or a quit command. Each non-empty line MUST be passed to `orchestrator.execute_turn(line)`. If `player_dead` is set, the loop MUST break. `--save SLOT` prints an acknowledgment (persistence deferred). Exit 0 on success.

#### Scenario: EOF exits 0
- GIVEN an active input loop
- WHEN `input()` raises `EOFError`
- THEN loop breaks, exit code 0

#### Scenario: Ctrl+C exits 0
- GIVEN an active input loop
- WHEN `KeyboardInterrupt` is raised
- THEN a farewell is printed to stdout, exit code 0

### Requirement: Validate command

`validate` MUST create an `EntityLoader`, call `validate_world()`, print `"World validation passed."` on success (stdout, exit 0), else print each problem to stderr (exit 1).

#### Scenario: Valid world passes
- GIVEN `_test_minimal`
- WHEN `validate` runs
- THEN `"World validation passed."` to stdout, exit 0

#### Scenario: Broken world fails
- GIVEN a world with dangling `spatial_anchor`
- WHEN `validate` runs
- THEN problem to stderr, exit 1

### Requirement: Test command walkthrough execution

`test` MUST call `_build_engine()`, optionally switch episode via `--episode`, read the walkthrough (one command per line, `#` = comments skipped), execute each via `execute_turn()`, then evaluate via `GoalEvaluator.check(state)`. Exit 0 "PASS", 1 "FAIL". Missing episode exits 1.

#### Scenario: Walkthrough achieves goal
- GIVEN `_test_minimal` and a walkthrough with `ir norte` then `huir hall`
- WHEN `test` runs
- THEN `GoalEvaluator.check(state)` returns True, "PASS" to stdout, exit 0

#### Scenario: Walkthrough misses goal
- GIVEN a walkthrough that never sets the `escaped` flag
- WHEN `test` runs
- THEN "FAIL" to stdout, exit 1

### Requirement: Narrator output via wildcard subscription (CRITICAL)

The narrator's `_bus_handler` calls `handle_event(event, None)` and discards the result — the narrator does NOT print to stdout. The CLI MUST subscribe a wildcard handler via `event_bus.subscribe("*", handler)` that calls `narrator.handle_event(event, world_state)` with the LIVE `WorldState` (NOT `None`) and prints non-`None` results to stdout. This is the ONLY way to capture narrator output.

#### Scenario: Narrative events print to stdout
- GIVEN an `action_output` event emitted into the bus
- WHEN the CLI's wildcard handler fires
- THEN `narrator.handle_event` returns a string printed to stdout

#### Scenario: Non-narrative events produce no output
- GIVEN an `entity_transferred` event emitted
- WHEN the wildcard handler fires
- THEN `narrator.handle_event` returns `None`, nothing printed

### Requirement: Exit code contract

`run`, `validate`, and `test` retain their existing exit contract. For
`audit-graph`, exit 0 SHALL mean no ERROR findings, exit 1 SHALL mean one or
more ERROR findings, and exit 2 SHALL mean usage, missing-world, malformed-world,
or unknown-episode errors.

#### Scenario: Existing command contract remains stable
- GIVEN a valid invocation of `run`, `validate`, or `test`
- WHEN the command completes
- THEN its pre-existing success or failure exit behavior is unchanged

#### Scenario: Audit severity controls success
- GIVEN a valid world with no ERROR findings, or one with an ERROR finding
- WHEN `audit-graph` runs
- THEN it exits 0 in the first case and 1 in the second

### Requirement: Audit graph output

`audit-graph <world_path> [--episode ID] [--json] [--include-info]` MUST invoke
the static `GraphAudit`; the first loaded episode is the default. Human output
MUST be grouped by severity, and INFO findings MUST be omitted unless
`--include-info` is supplied. `--json` MUST emit deterministic machine-readable
`AuditReport` data containing the single `reachable_rooms` set,
`unreachable_rooms`, passive per-passage gate data, and findings, with the same
filtering rule.

#### Scenario: JSON and human modes are CI-safe
- GIVEN a synthetic world with WARN and INFO findings
- WHEN the command runs once with `--json` and once with `--include-info`
- THEN JSON parses as an audit report, human output is grouped, and INFO appears only when requested

#### Scenario: World errors use usage status
- GIVEN a missing or malformed world, or an unknown `--episode`
- WHEN `audit-graph` runs
- THEN it writes the error to stderr and exits 2
