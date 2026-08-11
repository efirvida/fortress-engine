# Delta for CLI Entry Point

Traceability: `solve` is a developer-tool delta intentionally outside the 36-task `docs/tdd.md` roadmap.

## MODIFIED Requirements

### Requirement: Console script registration and argparse subcommands

`pyproject.toml` MUST register `fortress-engine = "fortress_engine.cli.main:main"`. `main()` MUST build subparsers `run`, `validate`, `test`, `audit-graph`, and `solve`. Missing/unknown subcommands MUST exit 2 (stderr).

| Subcommand | Arg | Flags |
|---|---|---|
| `run` | `world_path` (dir) | `--save SLOT`, `--parser`, `--narrator` |
| `validate` | `world_path` (dir) | `--verbose` |
| `test` | `world_path` (dir) | `--walkthrough FILE` (req), `--episode`, `--parser`, `--narrator` |
| `audit-graph` | `world_path` (dir) | `--episode ID`, `--json`, `--include-info` |
| `solve` | `world_path` (dir) | `--episode ID`, `--answers PATH`, `--json`, `--max-turns N` |

(Previously: the registered subcommands ended at `audit-graph`.)

#### Scenario: Missing subcommand exits 2
- GIVEN no subcommand on the command line
- WHEN `main()` parses args
- THEN argparse writes an error to stderr and exits 2

#### Scenario: Audit subcommand is registered
- GIVEN `audit-graph WORLD --episode ep-2`
- WHEN `main()` parses args
- THEN it dispatches the selected world and episode to the audit handler

#### Scenario: Solve subcommand is registered
- GIVEN `solve WORLD --episode ep-2 --answers answers.yaml --json`
- WHEN `main()` parses args
- THEN it dispatches all solver options to the solve handler

### Requirement: Exit code contract

`run`, `validate`, and `test` MUST retain their existing exit contract. For `audit-graph`, exit 0 SHALL mean no `ERROR` findings, exit 1 SHALL mean one or more `ERROR` findings, and exit 2 SHALL mean usage, missing-world, malformed-world, or unknown-episode errors. `solve` SHALL use 0 for completable, 1 for diagnosed not-completable, and 2 for usage/load/unknown-episode errors.

(Previously: the contract did not define `solve`.)

#### Scenario: Existing command contract remains stable
- GIVEN a valid invocation of `run`, `validate`, or `test`
- WHEN the command completes
- THEN its pre-existing success or failure exit behavior is unchanged

#### Scenario: Audit severity controls success
- GIVEN a valid world with no `ERROR` findings, or one with an `ERROR` finding
- WHEN `audit-graph` runs
- THEN it exits 0 in the first case and 1 in the second

#### Scenario: Solve severity controls success
- GIVEN a completable world, an unsolvable world, or an invalid invocation
- WHEN `solve` runs
- THEN it exits 0, 1, or 2 respectively

## ADDED Requirements

### Requirement: Solve command output

`solve WORLD [--episode ID] [--answers PATH] [--json] [--max-turns N]` MUST default to the first loaded episode and a `50_000` turn guard. Human output MUST group verdict and diagnoses; JSON MUST be deterministic and include the `SolveVerdict` fields and nested `GateDiagnosis` values.

#### Scenario: JSON and human modes are CI-safe
- GIVEN a synthetic completable or diagnosed world
- WHEN `solve` runs with and without `--json`
- THEN JSON parses deterministically, while human output groups the verdict and diagnosis

#### Scenario: Load and episode errors use status 2
- GIVEN a missing/malformed world or unknown episode
- WHEN `solve` runs
- THEN it writes an error to stderr and exits 2
