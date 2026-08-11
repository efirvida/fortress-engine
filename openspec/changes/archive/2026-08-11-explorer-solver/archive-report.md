# Archive Report — explorer-solver (Stage B)

**Status: ARCHIVED** | 2026-08-11 | Hybrid store

## Summary

The `explorer-solver` change implemented Stage B of the autoplay redesign — a completability solver that proves an episode can be completed by walking the runtime incrementally with a knowledge base of answers, returning either walkthrough evidence (exit 0) or gate-level diagnosis (exit 1).

## Merged Domains

| Domain | Action | Description |
|--------|--------|-------------|
| `autoplay-solver` | **CREATE** | New domain: typed verdicts, audit precondition, answer knowledge base, incremental BFS walk, key-retrieval backtracking, fixed-point diagnosis, world-agnostic bounds. 7 requirements, all ADDED. |
| `cli-entry-point` | **MODIFY + ADD** | Added `solve` subcommand to registration table and exit contract (MODIFIED). Added "Solve command output" requirement with JSON/human modes and error handling (ADDED). |

## Implementation

- **10/10 tasks done**, all 10 spec requirements PASS
- **7 explorer hooks**: additive, default-off; `commit_hook`, `solved`, `_commit`, `turn_counter`, `gate_code`, `_movement_pass(passwords)`, `_speech_marker()`, sorted iteration in `_probe_actions`/`_navigate_to`
- **answers.yaml loader skip**: filename-exact `if path.name == "answers.yaml": continue` in `load_episodes()` + 2 regression tests
- **pyproject omit**: narrowed from `autoplay/*` to `autoplay/explorer.py`

## Files Changed

| File | Change |
|------|--------|
| `src/fortress_engine/autoplay/solver.py` | NEW — `GateDiagnosis`, `SolveVerdict`, `AnswerBook`, `GateObserver`, `Solver` (466 lines) |
| `src/fortress_engine/autoplay/explorer.py` | ADDITIVE — 7 default-off hooks |
| `src/fortress_engine/autoplay/__init__.py` | MODIFIED — solver exports |
| `src/fortress_engine/entities/loader.py` | MODIFIED — `answers.yaml` skip in `load_episodes()` |
| `src/fortress_engine/cli/main.py` | MODIFIED — `solve` subcommand + `cmd_solve` |
| `pyproject.toml` | MODIFIED — narrowed coverage omit |
| `worlds/fortaleza/episodes/answers.yaml` | NEW — optional curated KB |
| `tests/test_autoplay/conftest.py` | MODIFIED — `solver_happy`, `solver_kb`, `solver_retrieve`, `solver_unsolvable` fixtures |
| `tests/test_autoplay/test_solver.py` | NEW — 117 solver tests |
| `tests/test_autoplay/test_answer_book.py` | NEW — AnswerBook tests |
| `tests/test_cli/test_solve.py` | NEW — CLI exit contract tests |
| `tests/test_entities/test_loader.py` | MODIFIED — `answers.yaml` skip regression tests |

## Coverage

| Metric | Value |
|--------|-------|
| Total tests | 1135 |
| Statement coverage | 99.56% (2728/2740) |
| Branch coverage | 99.25% (927/934) |
| Gate | >99% branch ✓ |
| Omitted | `src/fortress_engine/autoplay/explorer.py` |

## CLI Exit Contract Verified

| Case | Exit |
|------|------|
| Completable | 0 |
| Diagnosed not-completable | 1 |
| Usage/load/unknown-episode | 2 |
| Fortaleza ep-01 | 1 (unpinned, per design) |
| Fortaleza ep-02 | 1 (static_errors, per design) |

## Deferred / Out of Scope

- Engine changes (spoken hyper-edge riddles — cliques have no text predicate)
- World-data fixes
- Stage A audit changes
- Narrator-text quality checks
- Pinned Fortaleza verdicts (world is mid-rewrite)
