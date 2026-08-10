# Delta for CLI Entry Point

Traceability: dev-tool, not in the 36-task roadmap.

## MODIFIED Requirements

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

(Previously: only `run`, `validate`, and `test` were registered.)

#### Scenario: Missing subcommand exits 2
- GIVEN no subcommand on the command line
- WHEN `main()` parses args
- THEN argparse writes an error to stderr and exits 2

#### Scenario: Audit subcommand is registered
- GIVEN `audit-graph WORLD --episode ep-2`
- WHEN `main()` parses args
- THEN it dispatches the selected world and episode to the audit handler

### Requirement: Exit code contract

`run`, `validate`, and `test` retain their existing exit contract. For
`audit-graph`, exit 0 SHALL mean no ERROR findings, exit 1 SHALL mean one or
more ERROR findings, and exit 2 SHALL mean usage, missing-world, malformed-world,
or unknown-episode errors.

(Previously: world/validation/plugin/episode errors uniformly exited 1.)

#### Scenario: Existing command contract remains stable
- GIVEN a valid invocation of `run`, `validate`, or `test`
- WHEN the command completes
- THEN its pre-existing success or failure exit behavior is unchanged

#### Scenario: Audit severity controls success
- GIVEN a valid world with no ERROR findings, or one with an ERROR finding
- WHEN `audit-graph` runs
- THEN it exits 0 in the first case and 1 in the second

## ADDED Requirements

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
