# Proposal: epic-4-cli

## Intent

The engine core is fully implemented at >99% branch coverage, but it is unreachable from a terminal — `src/fortress_engine/cli/` contains only an empty `__init__.py` while `pyproject.toml` already declares the `fortress-engine` console script pointing at `fortress_engine.cli.main:main`. This change implements that entry point so users can run interactive sessions, validate worlds, and execute walkthrough tests. Closes epic #4 sub-issues #28, #26, #27.

## Scope

### In Scope
- `src/fortress_engine/cli/main.py` (NEW, ~250-350 lines): argparse entry + `main()`, 3 subcommands, plugin loading via `importlib.metadata.entry_points` (through `PluginFactory`), world path validation (#28)
- `run` command (#26): full 10-step engine wiring, interactive stdin/stdout loop, exit 0 normal / 1 error
- `validate` command (#27): `EntityLoader.validate_world()`, problems to stderr, exit 1 on failure
- `test` command (#27): walkthrough execution + goal evaluation, force-loads episodes (skip prerequisites), exit 0 PASS / 1 FAIL
- `tests/test_cli/` (NEW): unit + integration tests; coverage hard gate >99% branches

### Out of Scope
- Real save/restore wiring — `--save` prints an acknowledgment only (EventSourcingSaveSystem integration deferred)
- New parser/narrator plugins beyond `classic`/`template`
- TUI/REPL features beyond the plain stdin loop

## Capabilities

### New Capabilities
- `cli-entry-point`: `fortress-engine` console entry, argparse subcommands `run`/`validate`/`test`, engine wiring helper (`EngineBundle` + `_build_engine()`), exit-code contract

### Modified Capabilities
None — pure glue over existing capabilities (`world-loading`, `turn-orchestrator`, `plugin-factory`, `parser-classic-v1`, `narrator-template-v1`); no existing requirement changes.

## Approach

Single `main.py` with shared `_build_engine()` helper returning an `EngineBundle` dataclass (exploration Approach 3). Wiring mirrors the proven `_OrchFixture` pattern (`tests/test_integration/test_walkthrough.py:58-122`): world language read from `load_world_config()` BEFORE parser/narrator creation; protagonist entity created at runtime; narrator output to stdout via event bus; errors to stderr; argparse errors exit 2, world/validation errors exit 1.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/fortress_engine/cli/main.py` | New | CLI entry, argparse, 3 subcommand handlers, `_build_engine()` |
| `src/fortress_engine/cli/__init__.py` | Unchanged | Exists, empty |
| `tests/test_cli/` | New | `test_main.py`, `test_run.py`, `test_validate.py`, `test_test_cmd.py` |
| `pyproject.toml` | Unchanged | Entry points already correct |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Narrator stdout coupling (output mixed with stderr errors) | Med | Route narrator via event bus to stdout only; errors exclusively to stderr; assert stream separation in tests |
| Protagonist creation defaults diverge from world config | Med | `world_config` `protagonist_id` with `"player"` fallback, matching `_OrchFixture` pattern |
| `test` episode force-load bypasses prerequisites | Low | Explicit force-load in test command only; `run` keeps normal episode flow |
| Coverage gate on I/O-heavy code | Med | Mock `input()`/stdout for `run`; subprocess end-to-end test; `_build_engine()` tested against minimal world |

## Rollback Plan

Single feature: revert the commit deleting `src/fortress_engine/cli/main.py` + `tests/test_cli/`. `pyproject.toml` and engine core untouched — no schema, persistence, or data migration involved.

## Dependencies

- Stdlib `argparse` only (no new deps)
- Existing components: `EntityLoader`, `EventBus`, `WorldState`, `EpisodeManager`, `TurnOrchestrator`, `PluginFactory`, `GoalEvaluator`
- `pyproject.toml` `[project.scripts]` entry already present

## Success Criteria

- [ ] `fortress-engine --help` and all 3 subcommands render correctly; unknown command exits 2
- [ ] `run` on the minimal test world accepts input, narrates via event bus, `salir`/EOF exits 0; bad world path exits 1
- [ ] `validate` on a valid world prints "World validation passed." exit 0; on a broken world lists problems to stderr exit 1
- [ ] `test` with a walkthrough file reports PASS/FAIL via `GoalEvaluator`; missing episode exits 1
- [ ] `pytest --cov-branch` total > 99% including `tests/test_cli/`
- [ ] #28, #26, #27 closed
