# Handoff — general solver and Pascal fidelity

## Read this first

The user explicitly requested stopping after verified commits/merges and continuing
in a new session because the conversation context is full:

> cuando hagas los commits y mezcles cierra la sesion con un handoff, y vamos a continuar en otra q ya esta tiene el cotexto lleno

Do not resume the planner in this session. Next session must reconcile memory,
`odd/tasks/general-solver-fidelity.md`, this handoff, and actual Git state.

## User decisions

- Solver is generic for any authored world: graph navigation, puzzles, inventory.
  No Fortaleza identifiers, Pascal puzzle solutions or world-specific verbs in logic.
- `max_weight` absent / `None` / boolean `False` means unlimited. Numeric `0`
  is an explicit zero limit. No numeric engine default (neither 40 nor 20).
  Fortaleza's own authored `max_weight: 40` remains correct and unchanged.
- Always use chained PRs; verified slices land on `main` in order.
- Publishing, opening PRs and merging verified slices to main are explicitly authorized.
- Creation of `status:approved` and applying it to issues #41 and #46 explicitly
  authorized and completed (job-4, exit 0).
- General merge authorization does not grant native review consent. This session
  separately obtained review consent for the capacity candidate only.

## Delivered slice / proof

- Branch: `fix/world-defined-capacity`.
- Worktree: `.worktrees/world-defined-capacity` (registered, same clone).
  After merging capacity, reused on `docs/solver-recovery-handoff` based on merged
  main to version this handoff and the task document. Capacity branch retained.
- Base: `941811d` (remote main at preparation).
- Commit: `1082d660ff4fb3d9da608177942ab212a833915a`.
- PR: https://github.com/efirvida/fortress-engine/pull/75
- Scope: eight paths, 105 additions + 19 deletions = 124 authored diff lines.
  `entities/components.py` helper, TRANSFER capacity checks, CLI fallback,
  operator/CLI tests and PRD/GDD/TDD semantics. No worlds, explorer or runtime.
- Isolated full suite: `PYTHONPATH=src pytest --cov=src/fortress_engine
  --cov-branch --cov-report=term-missing --cov-report=json -q -p no:cacheprovider`:
  **912 passed, 321 warnings**, 100% statements and branches, exit 0.
- `python scripts/check_coverage_gate.py`: PASS.
- Native review: `review-27fe37eefa019576`, 3 lenses risk/readability/reliability,
  approved; exact acknowledgement completed and authority burned. No correction.
- Remote CI: Python3.11 and3.12 both SUCCESS, Actions run `39693172256`.
- PR75 MERGED at `2026-10-21T23:25:32Z`; main merge commit
  `7d3b8eee542f1fc9d8921727ecdf0b071544af30`. Parent fetched main and confirmed
  that it contains commit `1082d66`. No CI bypass or admin merge used.
- PR body source: `odd/prs/world-defined-capacity.md`.

## Original development tree — preserve it

- Original cwd: `/home/efirvida/Desktop/dev/games/fortaleza`.
- Branch: `feat/issue-41-walkthrough-l1`, HEAD `5a6ab97`.
- Roughly 322 dirty entries before handoff/worktree artifacts. Most predate this
  session: a substantial EP-1 Pascal-fidelity rewrite, engine narration changes,
  updated walkthrough tests. Do not reset, clean, stash away or overwrite them.
- Main was much older than the feature branch: 12 feature commits ahead of its
  merge base, 328 files / 12799 additions / 520 deletions against main before PR75.
- Existing PR #73 has remote head `eb30f9c`, older than local feature HEAD.
  It is not proof of the local tree and was not updated/merged in this session.
- Do not rebase the original dirty branch automatically. Reconcile history and
  extract reviewable slices with explicit bases; no bulk merge of the whole tree.
- Main lacks `EpisodeManager.goal_evaluator_for` and other runtime dependencies.
  This is why new runtime was not added to PR75.
- Capacity changes remain duplicated in the dirty original tree. They were
  extracted independently, not removed from the original branch. After updating
  to merged main, reconcile duplicates rather than re-deliver the same fix.

## Implemented locally but NOT delivered to main

- `src/fortress_engine/autoplay/runtime.py`, `tests/test_autoplay/test_runtime.py`,
  `tests/test_autoplay/test_capacity.py` (new original-tree files).
- `DualGraphEngine.iter_macro_edges()` + test in original tree.
- Runtime uses authored protagonist ID, compact state diff checkpoints and
  in-place restoration. Parent fixed episode manager wiring to include only the
  selected episode so goal completion cannot unload graph/change entity set.
- Runtime/explorer fallback numeric capacity removed locally too.
- Original-tree focused capacity/runtime/operators/CLI tests: 116 passed.
- Original-tree full suite after correcting stale explorer expectation:
  **1182 passed, 318 warnings**, 65.69s, exit 0; 2876 statements / 14 missed,
  964 branches / 8 incomplete. Both percentages >99%, not 100%.
- Independent verifier `mvipxpot-4-qbo4`: PASS capacity + selected-episode runtime;
  199 focused tests, 36 capacity probes, five rejection checks, two restore/replay
  probes, ten finite-behavior differentials. Planner/fidelity not verified.
- Verifier retained `/tmp/fortaleza-verify-6kwvYa`; no permission granted to parent
  for deleting that external directory. Do not depend on its persistence.

## Pending work and architecture findings

1. Reconcile remaining committed history and PR73 before choosing next slice base.
2. `domain.py` does NOT exist. Worker task `mvinobxe-2-xxb2` failed without artifact.
   The planner is not implemented. Do not report it complete or automatically retry
   the failed writer.
3. `docs/15-solver-planner-design.md` is a DRAFT. Read its reconciliation section.
   Initial draft had unsafe assumptions, caught by a bounded read-only challenge:
   - Relaxed positive facts must only guide ordering, not be the exclusive action
     generator. Keep negative-only actions, needed deletions and inventory drops.
   - Negative goals and already-true additions cannot be used to prune solutions.
   - Finite budgets cannot prove arbitrary-world impossibility.
   - Keep `AnswerBook` and `--answers`; removing them violates published contracts.
   - Partial operator effects require care: orchestrator stops on failure without
     rolling back previous successful operators.
4. Replay a found plan through real engine commands before claiming completion.
5. Validate world fidelity against actual Pascal, not stale audit tables.
   `docs/original-source/` is read-only reference; source uses CP850/encoded text.
6. Last original-tree observations (not fresh after any future edits):
   - EP1 static audit no ERROR, one `me_lobos_lobos` self-loop warning.
   - EP2 static audit reports isolated `bajos_de_las_cataratas`.
   - Old solver EP1 fails after 33998 attempts / 382 kept commands; candelabro
     never acquired. This is not proof the world is impossible.
   - `probe_count=0` is HARDCODED in old solver: it does not prove probing never ran.
7. Old `docs/14-fidelity-audit.md` is historical; memory records later EP1 corrections.
   Prior claim that all EP1 fidelity is unimplemented was stale.
8. Architecture: large TurnOrchestrator mixes system commands, rendering and turns;
   explorer hardcodes hero, uses private state rebinding, overlaps solver, and is
   omitted from coverage. Evaluate improvements against runnable contracts, do not
   perform a broad redesign without bounded tests.

## Resume protocol

1. `mem_context`, then project/feature scoped search `general-solver-fidelity` and
   `delivery/capacity-slice`, then full observations and task file.
2. Verify Git HEADs and PR75 merged state/merge commit; do not use stale origin/main.
3. Preserve original worktree; reuse or create registered same-clone slice worktrees.
4. Select next smallest coherent dependency slice toward generic solver; keep tests
   and docs with behavior. Each slice must independently exceed 99% statement AND
   branch coverage and pass required CI on Python 3.11 and 3.12 before merge.
5. Risk item 3 applies to shared transfer/contracts. Independent verification and
   native review follow actual candidate risk; prior approval is capacity-only.
