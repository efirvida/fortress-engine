# Handoff — general solver and Pascal fidelity (session 2 → session 3)

## Read this first

The owner asked to end this session with a handoff once the current slice merged:

> cuando mezcles, haz el handoff para continuar en una nueva sesion

Resume by reconciling, in this order: `mem_context` → search `general-solver-fidelity` →
`odd/tasks/general-solver-fidelity.md` (the Specs and Tasks are authoritative; the Log is
history) → this file → **actual Git/GitHub state**. Do not trust the numbers below without
re-checking `origin/main`.

**Standing owner decisions** (verbatim in the task file, S1–S7): the solver must be general for
any authored world; capacity has no numeric engine default; always chained PRs merged to `main`;
act autonomously on my own recommendations. The owner also said to merge even if required checks
fail "siempre que no rompa el codigo". I did **not** use that: every merge below had both
required checks green, because a failing required check is the evidence that code may be broken.
Keep that stance unless the owner narrows it.

## State of `main` (verified at close)

`origin/main` = `ed4d20b2b5645b35f89c996fe523f46d1b22502b`. Last gate on that tree:
**1070 tests, 100% statements (2563) and 100% branches (830)**, `scripts/check_coverage_gate.py` PASS.

| PR | Merge | Content |
|---|---|---|
| #75 | `7d3b8ee` | World-defined inventory capacity: absent/`None`/`False` = unlimited, numeric `0` explicit |
| #76 | `15aeacf` | Earlier ODD handoff snapshot (now superseded by this file) |
| #77 | `baee3bc` | `DualGraphEngine.iter_macro_edges`, `EpisodeManager.goal_evaluator_for` |
| #78 | `fb48b16` | Bidirectional macro edges: loader mirrors + atomic reverse opening |
| #100 | `c9cf8b7` | `entity: "*"` wildcard binding, `resolve_target_id`, generic output placeholders |
| #101 | `87295dd` | `autoplay.GameRuntime` (selected-episode, checkpoint/restore) |
| #104 | `f155499` | `autoplay.domain`: candidate set + advisory ranking, `iter_hyper_edges` |
| #105 | `ed4d20b` | `autoplay.answers.AnswerBook`, loader skips exactly `answers.yaml` |

`autoplay/` on `main` therefore holds `runtime.py`, `domain.py`, `answers.py` only. **`explorer.py`,
`graph_audit.py`, `solver.py` and the `solve` / `audit-graph` CLI are not on `main`.**

## What remains

| Task | Scope | Notes |
|---|---|---|
| **T3b** | Bounded search core on `GameRuntime` + `domain.candidates/rank`; visited key `state_key`; verdicts | See "Design decisions". Open: port `graph_audit.py` or drop the audit precondition. |
| **T3c** | `solve` CLI: `--answers`, `--json`, `--max-turns`; exit codes 0/1/2; docs | Contract text is committed at `970afb5:docs/tdd.md` (~line 2445: `--max-turns` default 50000, exit 0/1/2) and in `docs/gdd.md`; **not on `main` yet**. High risk (shared CLI). |
| **T4** | Pascal fidelity + executable walkthroughs for both worlds | The EP1/EP2 rewrite exists only in the dirty original tree. See "Original tree". |
| **T5** | Architecture evaluation, final coverage, independent verification | Tie to owner epic **#99** (below). |
| **Reconcile** | Original dirty tree and PR #73 | Do not bulk-merge. |

Recommended order: T3b (map first with `gentle-ai-explore`), then T3c, then T4, then T5.

## Design decisions taken under delegation (reversible by the owner)

1. The relaxed model is **advisory only**. `rank` returns a permutation and never removes a
   candidate. Negative-only actions, deletions, inventory drops, already-true additions and
   negative goals are never pruned. (`docs/15-solver-planner-design.md`, "Design reconciliation"
   supersedes its Grounding text, which still contradicts it.)
2. **No `unreachable` verdict from the relaxed model.** An exhausted search reports
   `EXHAUSTED_WITHIN_BUDGET` (incomplete, not impossible) and exits **1** like "not completable",
   with the verdict string distinguishing it. Planned verdicts: `SOLVABLE`, `NOT_SOLVABLE_AUDIT`,
   `EXHAUSTED_WITHIN_BUDGET`, `BUDGET_EXCEEDED`.
3. `SOLVABLE` only after **replaying the plan from a fresh `GameRuntime`** and confirming the goal
   with the real `GoalEvaluator`.
4. `AnswerBook` / `--answers` keep their published contract, including passwords derived from the
   world's own `requires_text`. Curated file: `episodes/answers.yaml`.
5. CLI keeps only `--max-turns` (no `max_expansions` flag).
6. Protagonist selection never reads `Entity.type`: explicit id → `player_controlled: true` → the
   only shared entity → `ValueError` if ambiguous → the CLI's own empty `hero` stand-in if none.

## Facts the owner should know

- **The owner committed `970afb5` on 2026-10-22 07:52 −03** in the original tree
  ("docs: align prd/gdd/tdd with code and link open design issues to epic #99") and PR #73 now
  points at it (previously `eb30f9c`). That commit rewrites `docs/prd.md`, `docs/gdd.md` and
  `docs/tdd.md` (514 insertions, 564 deletions). My slices also edited `docs/tdd.md` on `main`.
  `git merge-tree origin/main 970afb5` conflicts in 11 files: `docs/{gdd,prd,tdd}.md`,
  `src/.../autoplay/__init__.py`, `cli/main.py`, `engine/{episode_manager,graph,orchestrator}.py`,
  `entities/loader.py`, `tests/test_autoplay/{__init__,conftest}.py`. This is expected: PR #73
  contains the historical versions of what was delivered in slices. **Do not merge #73 as is.**
  The docs need a deliberate manual merge; whether to close or rebuild #73 is an owner decision.
- **Epic #99 "Engine design review"** (owner's own, open). Items that intersect this work:
  - **#94 affordances API** is meant to replace brute-force probing in autoplay; `domain.candidates`
    is a step toward it, not a replacement.
  - **#88 engine-reserved components**: `select_protagonist` reads `player_controlled: true`, but
    neither shipped world declares it; both resolve through the single-shared-entity rule.
    `cli/main.py` still hardcodes `hero`.
  - **#80 operators not atomic** is why a failed multi-operator edge leaves partial state, and why
    replay must run from a fresh runtime.
  - **#79** passage open-state outside `WorldState`: `GameRuntime` checkpoints capture edge `open`
    explicitly, which is compatible but should be revisited if #79 moves it.
  - **#46** says the world validator should be built on the existing solver + `audit-graph`.
  - **#98** automated Pascal text-fidelity test is the natural vehicle for T4.

## Original development tree — preserve it

`/home/efirvida/Desktop/dev/games/fortaleza`, branch `feat/issue-41-walkthrough-l1`, HEAD `970afb5`,
about **320 porcelain entries** (the EP1 Pascal-fidelity rewrite of `worlds/fortaleza/episode-01`,
engine narration changes, updated walkthrough tests, historical `explorer.py`/`solver.py`/
`graph_audit.py` and their tests). Never reset, clean, stash or overwrite. It still duplicates
code now on `main` (capacity, runtime, accessors); reconcile by extraction, never re-delivery.
`odd/evidence/` (5.9 MB) and `odd/prs/` (48 KB) there are **local scratch**, not versioned.

Registered delivery worktree: `.worktrees/world-defined-capacity` (same clone). It holds merged
branches; create a fresh branch from the then-current `origin/main` for each slice.

## Known limitations and unverified items (do not claim otherwise)

- No claim of arbitrary-world completeness, and **none of the Pascal-fidelity work is verified**.
- `domain.rank` recomputes the relaxed closure per candidate. **It has never been run against
  Fortaleza**; it may be too slow there.
- `GameRuntime` and `domain` are exercised only on small synthetic fixtures and `_test_minimal`.
- `domain`: a world with no `vocabulary.yaml`/`movement_verbs` records every move as unrenderable
  (no fallback to the engine's literal `ir`/`abrir`); passages whose name is not a single lowercase
  token cannot be spoken; two entities with the same normalized name collide in the classic parser.
- `AnswerBook` quirks kept from the original and pinned by tests, not fixed: invalid curated YAML
  raises, a missing world raises `FileNotFoundError`, an empty macros file raises `TypeError`,
  `answers.yml` is not exempt; the filename guard is case-sensitive.
- `GoalEvaluator` handling of the Fortaleza-style `type: and` goal form is unverified.
- Old static audit results (EP1: one `me_lobos_lobos` self-loop warning; EP2: isolated
  `bajos_de_las_cataratas`) predate the rewrite; old solver failing EP1 (candelabro never acquired)
  is **not** proof the world is impossible; the old `probe_count=0` was hardcoded.
- Native review was never started for the later slices: assessments were `reviewDue:false`, and
  the independently verified slices (#78 and #105) used the verifier plan instead.

## Environment and process lessons

- **`/tmp` is a user-quota tmpfs (~9.3 GB, nearly full).** A verifier once died with `errno -122`
  after copying all of `site-packages` there. Never copy dependencies or venvs; use the installed
  `pytest` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<src> -p no:cacheprovider`, not conda
  `python -m pytest`. The real CLI is `/usr/bin/python3 -c 'from fortress_engine.cli.main import
  main; main()'` (no `__main__` guard; do not use `-I`, it ignores `PYTHONPATH`).
- `rm -rf` is blocked for subagents: use fresh scratch names. Move generated scratch to
  `odd/evidence/<slice>` and never stage it.
- **`gh pr checks --watch` right after `gh pr create` can report "no checks reported"** and stop an
  `&&` chain without merging (this happened once). Poll until the rollup has two entries first,
  then watch, then merge with `--match-head-commit`.
- Workers repeatedly overshot the size stop rule because they counted lines only at the end. State
  the stop condition as "report before writing past N lines", and expect cohesive units to exceed
  400 lines; declare it in the PR rather than trimming tests or docs.
- A worker that skipped reading `gdd.md`/`tdd.md` still passed its own gate; review contract-level
  rules (e.g. `Entity.type` must stay opaque) yourself: that review caught a real defect in
  `GameRuntime` (it selected the protagonist by `type == "player"`).
- Independent verifiers earn their cost only for named high-risk items (here: shared loader/graph/
  turn contracts); mutation checks on guards were the most useful probes.

## Resume protocol

1. `mem_context`; `mem_search` `general-solver-fidelity`; read the task file and this handoff.
2. `git fetch origin main`; confirm `origin/main` ⊇ `ed4d20b`; `gh pr list --state open` and
   re-check PR #73 head and mergeability.
3. Re-run the full gate on a fresh worktree of `origin/main` before relying on any number here.
4. Preserve the original tree. Create a new branch per slice from current `origin/main`.
5. Each slice: tests in the same commit, gate > 99% on statements **and** branches, both required
   CI checks (3.11 and 3.12) green before merge, Risk line in the PR, independent verifier when a
   shared contract changes.
