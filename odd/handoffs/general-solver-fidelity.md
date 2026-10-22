# Handoff — general solver and Pascal fidelity (session 2 → session 3)

## Read this first

Resume by reconciling, in this order: `mem_context` → search `general-solver-fidelity` →
`odd/tasks/general-solver-fidelity.md` (Specs and Tasks are authoritative; the Log is history) →
this file → **actual Git/GitHub state**. Do not trust the numbers below without re-checking
`origin/main`.

Requests that shape this handoff (verbatim in the task file, S1–S8):

> cuando mezcles, haz el handoff para continuar en una nueva sesion

> jice unos cambios en el prd dgg y tdd de lo cual salieron varios isses, revisalos en caso de que haya que modificar el plan a seguir y rectifica el handoff

Standing owner decisions: the solver must be general for any authored world; capacity has no numeric
engine default; always chained PRs merged to `main`; act autonomously on my own recommendations. The
owner also said to merge even if required checks fail "siempre que no rompa el codigo". I did **not**
use that: every merge had both required checks green, because a failing required check is the
evidence that code may be broken. Keep that stance unless the owner narrows it.

## State of `main` (verified at close)

Code at `ed4d20b2b5645b35f89c996fe523f46d1b22502b`; `origin/main` = `2673b95` (docs-only on top).
Last gate: **1070 tests, 100% statements (2563) and 100% branches (830)**, `check_coverage_gate.py` PASS.

| PR | Merge | Content |
|---|---|---|
| #75 | `7d3b8ee` | World-defined inventory capacity: absent/`None`/`False` = unlimited, numeric `0` explicit |
| #76 | `15aeacf` | Earlier ODD handoff snapshot (superseded) |
| #77 | `baee3bc` | `DualGraphEngine.iter_macro_edges`, `EpisodeManager.goal_evaluator_for` |
| #78 | `fb48b16` | Bidirectional macro edges: loader mirrors + opening one side opens its mirror |
| #100 | `c9cf8b7` | `entity: "*"` wildcard binding, `resolve_target_id`, generic output placeholders |
| #101 | `87295dd` | `autoplay.GameRuntime` (selected-episode, checkpoint/restore) |
| #104 | `f155499` | `autoplay.domain`: candidate set + advisory ranking, `iter_hyper_edges` |
| #105 | `ed4d20b` | `autoplay.answers.AnswerBook`; loader skips exactly `answers.yaml` |
| #106 | `2673b95` | Session-2 handoff |

`autoplay/` on `main` holds `runtime.py`, `domain.py`, `answers.py` only. **`explorer.py`,
`graph_audit.py`, `solver.py` and the `audit-graph` / `solve` CLI are not on `main`.**

## Review of the owner's docs commit and issues (done in session 2, after #106)

The owner committed `970afb5` ("docs: align prd/gdd/tdd with code and link open design issues to
epic #99") and opened issues #79–#99, #102, #103. I read the diffs and issue bodies and checked each
claim against `main`. **Findings below were verified; inferences are labelled.**

### Docs describe engine features that `main` does not have

Measured with `grep` over `main`'s `src/` (0 matches each) against the owner's docs:

| Documented in `970afb5` | On `main` | Needed by |
|---|---|---|
| `@anchor` in `from_container`/`to_container` (`tdd.md:281`, `gdd.md:495`) | **no** | The rewritten world uses it **91 times** (generic take/drop in EP1/EP2); `main`'s worlds use fixed room ids instead |
| Passage-name normalization in macro lookup (`tdd.md:592`) | **no** | Shipped passage names are already lowercase single tokens (0 with caps/spaces in EP1/EP2), so likely not needed by the shipped worlds — verify in T4 |
| CLI `audit-graph` and `solve` (`tdd.md:2439–2450`, `gdd.md:1467–1472`, `prd.md:604`: "el CLI **ya incluye**…") | **no** | The sentence is false on `main` until T3c lands |
| Wildcard `entity: "*"` binding (`tdd.md:182`) | **yes (#100)** | — |
| `{contents}` output placeholder | not on `main`; **not in the owner's docs either** (0 mentions), but the rewritten world uses it twice | Owner question D4 |

Consequence: **merging `970afb5`'s docs (PR #73) before these land would make `main`'s docs claim
features it lacks.** Land each feature with its documentation; merge the rest last.

### Issue-by-issue impact on delivered code and the plan

- **#79 passage open-state lives outside `WorldState`.** Proposes one flag per physical passage
  (`passage_open:<id>`), `MacroEdge` frozen, `_open_reverse_edges` removed. It **replaces the mechanism
  of #78** (same semantics: one open-state per physical door) and invalidates `GameRuntime`'s
  `Checkpoint.edges`. Because `Checkpoint.flags` already copies the whole flag book, the follow-up in
  `runtime.py` is small. Issue #74's note ("the return leg re-requires the text") describes the
  opposite of what #78 implements and of TDD §3.3; I did not edit the issue.
- **#80 operator sequences not atomic.** GDD says transactional, TDD says "no rollback", code does the
  latter. Not a correctness prerequisite for the search (`restore()` rebuilds from baseline + diff and
  replay runs from a fresh runtime), **but it changes the reachable state set**: do not freeze solver
  verdict fixtures against Fortaleza until it lands. Tests that pin "failed step still advances the
  turn / partial effects" (#100, #101 suites) will need updating then. *(Inference, not tested.)*
- **#94 affordances API** is meant to replace the explorer's brute-force probing. `domain.candidates`
  is the interim; keep candidate generation behind that single seam. **Do not port `explorer.py`**
  (superseded by `GameRuntime` + `domain`).
- **#46 validator** is to be built on the existing solver + `audit-graph`. The new TDD defines `solve`
  as "auditoría estática + búsqueda BFS a ciegas", so the audit is part of the contract. **This resolves
  the open question: port `graph_audit.py`.** It imports only `entities.entity` and `EntityLoader`, so
  it is portable on its own.
- **#98** (automated Pascal text-fidelity test) is the vehicle for T4.
- **#83** (global rule index) would replace `iter_hyper_edges`; **#84** (one condition language): the
  docs define composite goals only as `{"and": [...]}`; `domain.py`'s goal parser also accepts a
  `type: and` + `conditions` form that `GoalEvaluator` would reject (unknown type → false). No shipped
  world uses it. Remove or reconcile when #84 is decided.
- **#88 engine-reserved components.** The PRD still says an entity with `player_controlled: true` is a
  protagonist **and** marks it "Abierto … ver #88"; the GDD says the engine does not read it; the CLI
  picks the first shared entity with `type == "player"` and registers it as `hero`. `select_protagonist`
  (explicit id → `player_controlled: true` → sole shared entity → `ValueError`) is consistent with the
  PRD's stated direction but reads a component the GDD says the engine ignores. Open, not a defect.
- **No impact:** #81, #82, #103 (persistence), #85–#87, #89–#93, #95, #96, #97, #102 do not block the
  solver. #96: deterministic JSON only needs a stable sort order, not a seeded RNG.
- **`solve` semantics.** The docs say "BFS a ciegas"; the plan is a bounded, ranked search that never
  uses the solution. I judge them compatible ("a ciegas" = without a walkthrough); confirm with the
  owner (D6).

## What remains — revised plan

Recommended order: **T1e → T3b0 → T3b → T3c → T1f → T4 → docs merge → T5**.
If the owner prefers strict epic order, insert **#79** (and optionally #80) before T3b; the cost of not
doing so is the small `runtime.py` follow-up above.

| Task | Scope | Risk / notes |
|---|---|---|
| **T1e** (new) | `@anchor` resolution in `from_container`/`to_container` (TRANSFER), per `tdd.md:281`; tests; TDD | **High** (shared operator contract) → independent verifier. Prerequisite for delivering the rewritten world. Then check `domain.py`'s relaxed model treats `@anchor` as "protagonist's current anchor" (advisory only, so correctness is unaffected, ranking quality is). |
| **T3b0** (new) | Port `graph_audit.py` (module + tests, **no CLI**) | Medium. Verify it needs nothing else from the dirty tree. |
| **T3b** | Bounded search on `GameRuntime` + `domain`; visited key `state_key`; verdicts; replay from a fresh runtime | Map first with `gentle-ai-explore`. See "Design decisions". |
| **T3c** | **Both** CLIs `audit-graph` and `solve`: `--answers`, `--json`, `--max-turns` (default 50000), exit 0/1/2; docs from `970afb5` | **High** (shared CLI). Contract: `970afb5:docs/tdd.md:2439–2450`, `gdd.md:1467–1472`. |
| **T1f** (new) | Passage-name normalization (`tdd.md:592`) | Medium. Needed for the docs to be true; likely unneeded by shipped worlds. |
| **T4** | Pascal fidelity: deliver the EP1/EP2 rewrite as reviewable slices **after T1e** (and a `{contents}` decision), plus the #98 ratchet | The rewrite exists only in the dirty original tree. |
| **Docs merge** | Reconcile `970afb5`'s `prd/gdd/tdd` with the sections added on `main` (§4.18–4.20, accessor and bidirectional text) | Manual merge; do it last so docs never claim missing features. |
| **T5** | Architecture review, final coverage, independent verification; tie to epic #99 | — |
| **Reconcile** | Original dirty tree and PR #73 | Do not bulk-merge. |

## Design decisions taken under delegation (reversible by the owner)

1. The relaxed model is **advisory only**: `rank` returns a permutation and never removes a candidate.
   Negative-only actions, deletions, inventory drops, already-true additions and negative goals are never
   pruned. (`docs/15-solver-planner-design.md`, "Design reconciliation", supersedes its Grounding text.)
2. **No `unreachable` verdict from the relaxed model.** Exhaustion reports `EXHAUSTED_WITHIN_BUDGET`
   (incomplete, not impossible) and exits **1**. Planned verdicts: `SOLVABLE`, `NOT_SOLVABLE_AUDIT`,
   `EXHAUSTED_WITHIN_BUDGET`, `BUDGET_EXCEEDED` (names are mine; the docs define none).
3. `SOLVABLE` only after **replaying the plan from a fresh `GameRuntime`** and confirming the goal with
   the real `GoalEvaluator`.
4. `AnswerBook` / `--answers` keep their published contract, including passwords derived from the
   world's own `requires_text`. Curated file: `episodes/answers.yaml`.
5. CLI keeps only `--max-turns` (no `max_expansions` flag).
6. Protagonist selection never reads `Entity.type` (see #88 above).
7. The audit precondition is **kept** (docs define `solve` as audit + search); explorer is not ported.

## Owner decisions needed (not assistant decisions)

- **D1** Protagonist rule: is `player_controlled` a reserved component (PRD) or ignored (GDD)? Before T3c.
- **D2** Run #79 (and #80) before T3b, or after? Default if unanswered: after.
- **D3** Approve the verdict names and the `--json` schema.
- **D4** Is `{contents}` (Pascal "Usted ve: …" listing) an engine feature or a world convention? It is
  used by the rewritten world and documented nowhere.
- **D5** Close or rebuild PR #73 once the slices land.
- **D6** Confirm "BFS a ciegas" wording is compatible with ranked bounded search.

## Facts the owner should know

- **PR #73's head is `970afb5`.** `git merge-tree origin/main 970afb5` conflicts in 11 files:
  `docs/{gdd,prd,tdd}.md`, `src/.../autoplay/__init__.py`, `cli/main.py`,
  `engine/{episode_manager,graph,orchestrator}.py`, `entities/loader.py`,
  `tests/test_autoplay/{__init__,conftest}.py`. Expected: #73 holds the historical versions of what was
  delivered in slices. **Do not merge #73 as is.**
- Epic **#99** is the owner's own review; its Phase 0 lists #79, #80, #82, #81, #103 as "do first".

## Original development tree — preserve it

`/home/efirvida/Desktop/dev/games/fortaleza`, branch `feat/issue-41-walkthrough-l1`, HEAD `970afb5`,
about **320 porcelain entries** (the EP1 rewrite of `worlds/fortaleza/episode-01`, engine narration
changes, updated walkthrough tests, historical `explorer.py`/`solver.py`/`graph_audit.py` and tests).
Never reset, clean, stash or overwrite. It still duplicates code now on `main`; reconcile by
extraction, never re-delivery. `odd/evidence/` (about 6 MB, including `docs-review/` diffs and issue
bodies) and `odd/prs/` there are **local scratch**, not versioned.

Registered delivery worktree: `.worktrees/world-defined-capacity` (same clone). Create a fresh branch
from the then-current `origin/main` for each slice.

## Known limitations and unverified items (do not claim otherwise)

- No claim of arbitrary-world completeness, and **none of the Pascal-fidelity work is verified**.
- `domain.rank` recomputes the relaxed closure per candidate and **has never run against Fortaleza**.
- `GameRuntime` and `domain` are exercised only on small synthetic fixtures and `_test_minimal`.
- `domain`: a world without `vocabulary.yaml`/`movement_verbs` records every move as unrenderable;
  passages not spoken as one lowercase token cannot be rendered; same-normalized-name entities collide in
  the classic parser; `@anchor` is not modelled (see T1e).
- `AnswerBook` quirks kept from the original and pinned by tests: invalid curated YAML raises, a missing
  world raises `FileNotFoundError`, an empty macros file raises `TypeError`, `answers.yml` is not exempt,
  the filename guard is case-sensitive.
- Old audit results (EP1: one `me_lobos_lobos` self-loop warning; EP2: isolated `bajos_de_las_cataratas`)
  predate the rewrite. The old solver failing EP1 (candelabro never acquired) is **not** proof the world
  is impossible; the old `probe_count=0` was hardcoded.
- Native review was never started for the later slices: assessments were `reviewDue:false`; #78 and
  #105 used the independent-verifier plan instead.

## Environment and process lessons

- **`/tmp` is a user-quota tmpfs (~9.3 GB, nearly full).** A verifier once died with `errno -122` after
  copying all of `site-packages` there. Never copy dependencies or venvs; use the installed `pytest` with
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<src> -p no:cacheprovider`, not conda `python -m pytest`. The
  real CLI is `/usr/bin/python3 -c 'from fortress_engine.cli.main import main; main()'` (no `__main__`
  guard; do not use `-I`, it ignores `PYTHONPATH`).
- `rm -rf` is blocked for subagents: use fresh scratch names. Move generated scratch to
  `odd/evidence/<slice>` and never stage it.
- **`gh pr checks --watch` right after `gh pr create` can report "no checks reported"** and stop an `&&`
  chain without merging (it happened once). Poll until the rollup has two entries, then watch, then merge
  with `--match-head-commit`.
- Workers overshoot size stop rules because they count lines only at the end. Say "report before writing
  past N lines"; cohesive units can exceed 400 lines — declare it in the PR instead of trimming tests/docs.
- Review contract-level rules yourself (e.g. `Entity.type` stays opaque): a worker that skipped
  `gdd.md`/`tdd.md` still passed its own gate, and that review caught a real defect in `GameRuntime`.
- Verify before accepting a subagent's recommendation: its claim that #80 blocks the search did not hold
  up against how `restore()` works.
- Independent verifiers pay off only for named high-risk items (shared loader/graph/turn/CLI contracts);
  mutation checks on guards were the most useful probes.

## Resume protocol

1. `mem_context`; `mem_search` `general-solver-fidelity`; read the task file and this handoff.
2. `git fetch origin main`; confirm `origin/main` ⊇ `2673b95`; `gh pr list --state open`; re-check PR
   #73's head and mergeability; re-read the owner's open issues for changes.
3. Re-run the full gate on a fresh worktree of `origin/main` before relying on any number here.
4. Preserve the original tree. New branch per slice from current `origin/main`.
5. Each slice: tests in the same commit, gate > 99% on statements **and** branches, both required CI
   checks (3.11 and 3.12) green before merge, a Risk line in the PR, independent verifier when a shared
   contract changes.
