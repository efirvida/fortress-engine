# Tasks: Explorer Solver (Stage B)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,800–2,400 |
| 400-line budget risk | High |
| 800-line budget risk | High |
| Chained PRs recommended | No |
| Suggested split | Single PR with size:exception (fallback: 3 chained PRs) |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High
800-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | pyproject omit + fixtures + KB + dataclasses | PR 1 (if chaining) | `pytest tests/test_autoplay -q` | N/A — no solver yet; worlds proven via GraphAudit zero-ERROR | revert omit in pyproject.toml, drop conftest builders, remove AnswerBook |
| 2 | Solver walk/backtrack/diagnosis + unit tests | PR 2 | `pytest tests/test_autoplay/test_solver.py -q` | `fortress-engine solve <tmp fixture world> --json` | delete solver.py + test_solver.py + __init__ exports |
| 3 | CLI + integration + coverage gate | PR 3 | `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` | `fortress-engine solve worlds/fortaleza --json` (unpinned smoke) | revert main.py solve branch, drop CLI/integration tests |

## Phase 1: Foundation

- [x] 1.1 Narrow coverage omit in `pyproject.toml` from `src/fortress_engine/autoplay/*` to `src/fortress_engine/autoplay/explorer.py` (update the comment too). Acceptance: whole-project `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` stays >99% branch; explorer.py remains excluded.

- [x] 1.2 Extend `tests/test_autoplay/conftest.py` (reuse Stage A builders' exact YAML partitions): `solver_happy` (item+text+flag gates, exact walkthrough), `solver_kb` (answer ONLY in `episodes/answers.yaml`), `solver_retrieve` (key item in far room), `solver_unsolvable` (item_unreachable + flag_never_set). Acceptance: each world passes `GraphAudit` with zero ERRORs so the solver runs.

## Phase 2: Solver core (TDD — failing tests first, code+test in same commit)

- [x] 2.1 `AnswerBook` + KB loader in `src/fortress_engine/autoplay/solver.py`: derive selected-episode macro-edge `requires_text`; merge `episodes/answers.yaml` (per-episode `passwords`/`riddle_answers`) or `--answers` override; normalize/dedup/sort; movement verbs + speech markers only from world vocabulary. Resolve the `answers.yaml` glob collision with `EntityLoader.load_episodes()` without changing gameplay semantics (documented skip or equivalent) + regression test. Export from `autoplay/__init__.py`. Acceptance: curated-only answer opens a passage; `--answers` replaces default file; tests red→green. *(Chunk 1: AnswerBook + loader skip + 7 explorer seams done; "curated-only answer opens a passage" integration lands in 2.3/2.5.)*

- [x] 2.2 `SolveVerdict`/`GateDiagnosis` dataclasses (spec fields, 5 literal reasons) + audit precondition in `solver.py`: `GraphAudit.run()` first; any ERROR → `completable=false` + `static_errors`, runtime never constructed. Export from `autoplay/__init__.py`. Acceptance: audit-ERROR world returns typed verdict without building BlindExplorer. *(Sub-chunk 2a done: dataclasses + audit precondition; BFS walk lands in 2.3.)*

- [x] 2.3 Incremental BFS walk: compose `BlindExplorer`; queue audit `reachable_rooms`; per room take (`_take_if_present`) → differential probe (`_probe_actions`) → movement pass with sorted KB answers; commit hook runs `GoalEvaluator.check` after EVERY committed change incl. crossings and stops before post-goal commands; snapshot/restore ONLY via explorer central path (incl. `orch._state` rebinding); ledger holds committed commands only; bounded revisits (`MAX_REVISITS=8`) on progress-signature change. Acceptance: `solver_happy` walkthrough is the deterministic committed order; restored probes/failed answers absent.

- [x] 2.4 Key-retrieval backtracking + fixed-point diagnosis + guards: navigate→take→return→retry, bounded (`MAX_RETRIEVALS_PER_GATE=8`), snapshot-safe with ledger-segment truncation; diagnose via audit `PassageRecord` cross-ref — `answer_not_in_kb` (exact msg `DATA gap: answer for '<passage>' is absent from the knowledge base`), `item_missing_from_world`, `item_unreachable`, `item_never_acquired`, `flag_never_set`; `--max-turns` guard (default 50_000) counting restored probes; deterministic diagnosis/JSON sort. Acceptance: `solver_retrieve` returns with key and retries; `solver_unsolvable` yields exactly `item_unreachable` + `flag_never_set`; low-turn world terminates deterministically.

- [x] 2.5 Unit test matrix `tests/test_autoplay/test_solver.py`: verdict fields, audit precondition, KB merge/dedup/sort, BFS branches, retrieval, EACH diagnosis reason (exact messages), committed-vs-restored ledger, max-turns termination, determinism (repeat runs, JSON key order), non-Spanish vocabulary. Acceptance: strict exact-value assertions, all failure branches covered, suite green.

## Phase 3: CLI + Integration

- [x] 3.1 `solve` subcommand in `src/fortress_engine/cli/main.py`: argparse registration + dispatch + `cmd_solve` (`--episode`, `--answers`, `--json`, `--max-turns`, default first episode/50_000); human output groups verdict + numbered walkthrough + diagnoses; deterministic JSON via `SolveVerdict.to_dict()`; exit 0 completable / 1 diagnosed / 2 usage-load-unknown-episode. Acceptance: mirrors `cmd_audit_graph` contract.

- [x] 3.2 CLI tests `tests/test_cli/test_solve.py` mirroring `test_audit_graph.py`/`test_validate.py`: all three exits, JSON parses deterministically, human grouping, malformed world/unknown episode → stderr + exit 2. Acceptance: subprocess-level coverage of the full exit contract.

- [x] 3.3 Integration tests: minimal-world end-to-end solve (loader→audit→solver→verdict); fortaleza smoke `solve worlds/fortaleza` asserting no-crash + structure only (no pinned verdicts — world mid-rewrite); add optional `worlds/fortaleza/episodes/answers.yaml` ONLY if cheap and safe (never modifies existing gameplay data). Acceptance: smoke green; integration glue covered.

- [x] 3.4 Coverage verification: whole-project gate >99% branch WITH narrowed omit (solver measured); targeted solver coverage via temp cov-config (no omit) + dotted `--cov=fortress_engine.autoplay.solver` (file-path form collects nothing). Acceptance: both commands >99% branch; commands recorded in PR description.
