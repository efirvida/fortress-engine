# Tasks: epic-4-cli — fortress-engine CLI entry point

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

> Threat matrix N/A per design (no routing, shell, subprocess, VCS). No threat-matrix RED-test tasks.

## Phase 1: Foundation — EngineBundle and _build_engine()

- [x] 1.1 Create `src/fortress_engine/cli/main.py` with imports: orchestrator, state, event_bus, narrator_interface, episode_manager, goal_evaluator, loader, factory, dataclass
- [x] 1.2 Define `EngineBundle` `@dataclass(frozen=True)` with 7 fields: orchestrator, state, event_bus, narrator, episodes, episode_manager, world_config
- [x] 1.3 Implement `_build_engine(world_path, parser_name="classic", narrator_name="template")` — validate path + world.yaml → EntityLoader → config/vocab/episodes → EventBus → create_parser/create_narrator → narrator.initialize(bus) → WorldState(hero, player_controlled_entities=["hero"]) → EpisodeManager.start_episode → GoalEvaluator → TurnOrchestrator
- [x] 1.4 RED: `test_build_engine_minimal_world` — assert current_episode_id == "episode-01" and isinstance(player_controlled_entities, list)
- [x] 1.5 RED: `test_build_engine_missing_world_yaml` — SystemExit(1) + stderr

## Phase 2: CLI Structure — argparse, main(), exit codes

- [x] 2.1 Implement `main()` — argparse subparsers `run`/`validate`/`test`; `run`: world_path + --save/--parser/--narrator; `validate`: world_path + --verbose; `test`: world_path + --walkthrough (req) + --episode/--parser/--narrator
- [x] 2.2 RED: `test_missing_subcommand_exits_2` — main() no subcommand; SystemExit(2) + argparse error stderr
- [x] 2.3 Create `tests/test_cli/__init__.py` (empty) + `tests/test_cli/test_main.py` — argparse + exit-code unit tests

## Phase 3: Run and Validate Handlers

- [x] 3.1 Implement `run` handler — loop on input("> "), break on EOFError/KeyboardInterrupt/quit; execute_turn per non-empty line; check player_dead; farewell on Ctrl+C; exit 0
- [x] 3.2 RED: `test_run_eof_exits_0` — mock input() → EOFError; exit 0
- [x] 3.3 RED: `test_run_ctrl_c_exits_0` — mock input() → KeyboardInterrupt; farewell stdout + exit 0
- [x] 3.4 Implement `--save SLOT` acknowledgment — print "Saving to slot '{slot}'... (persistence deferred)" to stdout; no persistence calls
- [x] 3.5 RED: `test_save_acknowledged_only` — stdout message, no save-system side-effects
- [x] 3.6 Implement `validate` handler — EntityLoader.validate_world(); "World validation passed." + exit 0; problems to stderr + exit 1
- [x] 3.7 RED: `test_validate_valid_world` — "World validation passed." + exit 0
- [x] 3.8 RED: `test_validate_broken_world` — problem to stderr + exit 1
- [x] 3.9 Create `tests/test_cli/test_run.py` + `tests/test_cli/test_validate.py`

## Phase 4: Test Command and Narrator Output

- [x] 4.1 Implement `test` handler — _build_engine(); optional --episode; read walkthrough (# lines skipped); execute_turn per command; GoalEvaluator.check(); PASS/FAIL + exit 0/1; missing episode → exit 1
- [x] 4.2 RED: `test_walkthrough_achieves_goal` — `ir norte` + `huir hall`; GoalEvaluator True + "PASS" + exit 0
- [x] 4.3 RED: `test_walkthrough_misses_goal` — never sets `escaped` flag; "FAIL" + exit 1
- [x] 4.4 RED: `test_test_cmd_missing_episode` — missing episode_id; exit 1
- [x] 4.5 Implement `_install_narrator_stdout_handler(bundle)` — subscribe("*") calling narrator.handle_event(event, bundle.state); print non-None to stdout; install before execute_turn loop
- [x] 4.6 RED: `test_narrator_action_output_prints` — emit action_output; assert string to stdout
- [x] 4.7 RED: `test_narrator_entity_transferred_no_output` — emit entity_transferred; assert stdout empty
- [x] 4.8 Create `tests/test_cli/test_test_cmd.py` — walkthrough PASS/FAIL, episode switch, goal eval

## Phase 5: Coverage Gate

- [x] 5.1 Run `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q`
- [x] 5.2 Assert >99% branch coverage on `src/fortress_engine/cli/main.py`; add missing tests if uncovered lines remain