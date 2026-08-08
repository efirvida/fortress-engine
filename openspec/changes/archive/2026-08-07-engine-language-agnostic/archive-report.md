# Archive Report — engine-language-agnostic

**Status**: CLOSED
**Archived**: 2026-08-08
**Branch**: feat/engine-language-agnostic-l1..l5 (stacked-to-main, pending)
**Issue**: none (user requirement — engine must be agnostic to text commands in any language)

## Executive Summary

The engine is now language-agnostic: it emits flat `error_code` + `data` for every failure and never constructs user-facing text. Movement verbs and system commands come from the injected world `Vocabulary` (with in-code Spanish defaults). `MacroGateResult` replaced the `(bool, str)` gate return and eliminated the death-vs-block string-equality bug. `OperatorResult` carries `code` + `data` with `error_message` removed. The TemplateNarrator owns text via `DEFAULT_SPANISH_MESSAGES` + a contract-guard test. All 22 tasks (L1.1–L5.5) complete, 786 tests pass with 100% statement and branch coverage, 12/12 requirements, 26/26 scenarios.

## Final State (Authority: orchestrator launch prompt + verified artifacts)

| Metric | Value |
|--------|-------|
| Tests passing | 786 (0 failed, 0 skipped) |
| Branch coverage | 100% (1804 stmts, 0 misses, 558 branches, 0 partials) |
| Uncovered items | 0 — hard gate (>99%) PASSED |
| Tasks completed | 22/22 (L1.1–L5.5) |
| Slices delivered | L1 (vocabulary sections), L2 (orchestrator vocab-driven), L3 (operators code+data), L4 (MacroGateResult + death-vs-block), L5 (narrator messages dispatch) |
| Verify verdict | PASS WITH WARNINGS — W-1 RESOLVED, W-2 aligned at archive, no CRITICAL |

## Architecture Decisions (user-confirmed)

- **Engine emits codes + data; narrator owns text**: all `error_output` carries flat `error_code` + `data`; no `message` key in any engine emission.
- **Text in world vocabulary**: `Vocabulary` gains optional `messages`, `movement_verbs`, `system_commands` sections; absent → `DEFAULT_SPANISH_MESSAGES` / `DEFAULT_MOVEMENT_VERBS` / `DEFAULT_SYSTEM_COMMANDS` in-code defaults.
- **Movement + system commands from vocabulary**: orchestrator reads them from the injected `Vocabulary` (default Spanish set). `switch` is a PREFIX command (strip the vocabulary surface).
- **`MacroGateResult(is_valid, is_fatal, gate_code, data)`**: 5 flat gate codes; death-vs-block via `is_fatal` — string equality `death_msg == edge.death_message` eliminated (the prerequisite refactor).
- **`OperatorResult` code + data**: 14 unique flat failure codes; `error_message` REMOVED immediately (user decision); English dev diagnostics no longer leak to the player.
- **`system_message` code-only** (user decision): no `message`-payload back-compat.
- **Flat codes, no namespace** (user decision); **switch prefix special-case** (user decision).

## Warning Record (resolved + archival)

1. **W-1 (RESOLVED)**: verify flagged that fatal `GAME_OVER` dropped `gate.data["death_message"]`. Fixed: the GAME_OVER payload spreads `**gate.data`; test asserts `payload["death_message"]`. Full suite stays 786 / 100%.
2. **W-2 (RESOLVED at archive)**: umbrella `engine-language-agnostic/spec.md` listed legacy codes `flag_readonly`/`anchor_not_found`; aligned to the real catalogue (`teleport_entity_not_found`, `teleport_anchor_not_found`, etc.) — FLAG has no failure path.
3. **S1 (archival note)**: `MinimalNarrator` (narrator_interface.py) needed a 3-line change to read `error_code` instead of `message` — necessary fallout of the code contract, covered by tests.
4. **S3 (minor)**: orchestrator ACTION_ATTEMPTED clique still labels macro movement with `{"verb": "ir"}` — recognition is vocabulary-driven so no behavioral coupling; a `MOVEMENT_LABEL` constant could be a future polish.

## Specs synced to openspec/specs/

- `openspec/specs/engine-language-agnostic/spec.md` (new umbrella)
- `openspec/specs/dual-graph/spec.md` (modified — MacroGateResult)
- `openspec/specs/atomic-operators/spec.md` (modified — OperatorResult code)
- `openspec/specs/turn-orchestrator/spec.md` (modified — vocabulary-driven)
- `openspec/specs/world-yaml-extensions/spec.md` (modified — vocabulary sections)
- `openspec/specs/narrator-template-v1/spec.md` (modified — messages dispatch)

## Engineering Notes

- `importlib.metadata` still exactly one hit (`plugins/factory.py`) — arch constant #7 preserved.
- Contract guard: parametrized test `test_every_error_code_has_template` enumerates all engine codes — a new engine code without a narrator template fails the suite.
- Next epics on the roadmap: CLI entry point (`cli/main.py` dangling in pyproject.toml), Fortaleza world data.
