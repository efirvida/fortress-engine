# General solver and world fidelity recovery

Recover development continuity without overwriting the existing world rewrite.
The solver remains world-agnostic; Pascal is the fidelity reference for world data only.

## Specs

S1. "este repositorio antes usaba openspec ahora usamos odd, pero en algun momento perdimos el hilo del desarrollo. necesito retomalrlo, solo recuerdo que estava validando que el engine pudiera recorrer los mundos implementados, y que los mundos implementados fueran fieles al codigo originalk de  pascal que se encuentra en  @docs/original-source/ vamos a continuar. Tambien quiero que evalues la arquitectura para posibles mejoras"
S2. "si quiero que lo hagas todo en automatico, solo una cosa, el solver es un solver general que debe servir para cualquier mundo, no para estos mundos en especifico, por lo que debe ser capaz de navegar el grafo, resolver puzles, inventarios etc, para cualquier mundo que se implemente, tal como lo especificamos en su definicion."
S3. "continua"
S4. "la capacidad maxima no puede tener un default de 40,  en todo caso None|False, para infinito o algo por el estilo"
S5. "haz siempre PR encadenados, y mezclalos a main"
S6. "cuando hagas los commits y mezcles cierra la sesion con un handoff, y vamos a continuar en otra q ya esta tiene el cotexto lleno"

## Tasks

- T0 [done] (S4) Remove numeric capacity defaults; absent/None/False unlimited, numeric zero preserved; route: parent + independent verifier; evidence: 1182 tests passed, verifier PASS; commit: 1082d660ff4fb3d9da608177942ab212a833915a for main engine/CLI slice, merged PR75; explorer/runtime updates remain local until their dependencies land.
- T1 [done] (S1-S3) Reconcile design, history, current diff and runtime proof; route: parent + bounded read-only challenge; evidence: chained-episode RED/GREEN and verifier PASS; commit: not yet committed.
- Tdelivery [done] (S1-S4) Deliver isolated capacity slice as first PR in auto-chain/stacked-to-main strategy; commit: 1082d660ff4fb3d9da608177942ab212a833915a; PR75 merged as 7d3b8eee542f1fc9d8921727ecdf0b071544af30, 912 tests and 100%/100% local coverage, native review approved/acknowledged and CI3.11/3.12 PASS. Runtime/history/world follow-ups explicitly deferred to next session.
- T2 [pending] (S2-S3) Implement generic action domain and advisory heuristic without suppressing negative-effect actions; route: parent (writer unavailable); commit: pending.
- T3 [pending] (S2-S3) Integrate bounded search, retain AnswerBook/--answers, replay successful plans and distinguish exhausted search from impossibility; route: parent; commit: pending.
- T4 [pending] (S1-S3) Validate both worlds against Pascal and executable walkthroughs, separating world defects from solver limits; route: parent; commit: pending.
- T5 [pending] (S1-S3) Finish architecture evaluation, coverage and required independent verification/review; route: parent + applicable verifier; commit: pending.

## Log

L1. Original request verbatim: este repositorio antes usaba openspec ahora usamos odd, pero en algun momento perdimos el hilo del desarrollo. necesito retomalrlo, solo recuerdo que estava validando que el engine pudiera recorrer los mundos implementados, y que los mundos implementados fueran fieles al codigo originalk de  pascal que se encuentra en  @docs/original-source/ vamos a continuar. Tambien quiero que evalues la arquitectura para posibles mejoras

L2. User constraint verbatim: si quiero que lo hagas todo en automatico, solo una cosa, el solver es un solver general que debe servir para cualquier mundo, no para estos mundos en especifico, por lo que debe ser capaz de navegar el grafo, resolver puzles, inventarios etc, para cualquier mundo que se implemente, tal como lo especificamos en su definicion.

L3. Resume request verbatim: continua

L4. Reconciliation: branch already contains roughly 309 uncommitted entries, mostly world rewrite. Preserve pre-existing changes. Runtime and tests were added by worker mvinhz03-1-5ly6; domain writer mvinobxe-2-xxb2 failed with no domain.py artifact. Do not claim its implementation exists. Previous suite: 1161 passed (worker evidence); parent verification still needed. Earlier claim that zero probe_count proved inactive probing was incorrect: solver.py hardcodes probe_count=0. Historical memory also records later EP-1 fidelity corrections, so docs/14-fidelity-audit.md is historical evidence, not current truth.

L5. Read-only challenge mvipqa4j-3-ch4r: relaxed additions cannot safely be the exclusive candidate generator; preserve negative-effect actions and real engine validation. Checkpoints fail across automatic episode transition. Preserve published AnswerBook/--answers contracts. Scope remains selected-episode solving; retain real goal evaluator as authority. No theoretical guarantee of arbitrary-world completeness under finite budgets.

L7. User correction verbatim: la capacidad maxima no puede tener un default de 40,  en todo caso None|False, para infinito o algo por el estilo

L8. Capacity RED: 19 failed, 58 passed (tests/test_autoplay/test_capacity.py plus test_operators.py). Runtime chained-completion RED: 1 failed. Focused GREEN after fixes: 116 passed in 1.78s (capacity/runtime/operators/CLI builder). Capacity centralized in inventory_capacity; fallback protagonist has empty components; authored Fortaleza max_weight:40 unchanged. Runtime isolates selected episode, retaining real operator/turn behavior. Full coverage and differential still pending. Risk item 3: shared transfer helper and CLI/runtime defaults affect existing commands, independently verify.

L6. Workload forecast: planner/search plus fixtures likely exceeds 400 authored diff lines; preserve coherent work units. No publishing authorized. Commit boundaries depend on green whole-project coverage and candidate assessment. Existing dirty work must not be swept into new commits.

L9. Final capacity/runtime proof: parent full branch coverage command exited 0, 1182 passed/318 warnings in 65.69s; TOTAL 2876 statements/14 missed, 964 branches/8 incomplete. Existing uncovered solver/CLI/orchestrator paths remain; no claim of full coverage. Finite-capacity CLI differential with max_weight:7 matched exact exit/stdout/stderr for run, validate, test, audit-graph and solve. Raw HEAD difference in movement narration predated this unit; baseline overlay preserved existing episode_manager/orchestrator/state changes to isolate capacity unit.

L10. Independent verifier mvipxpot-4-qbo4 PASS for S4/T0 and selected-episode runtime subset S2-S3/T1: 199 focused tests, 36 capacity-interface probes, 5 rejection-state checks, 2 restore/replay probes and 10 finite-behavior differentials. First full run failed on a stale expected default40; parent corrected it and reran green. Scratch /tmp/fortaleza-verify-6kwvYa belongs to verifier; no parent cleanup without permission outside project.

L11. Assessment escalated item3 shared transfer/default contract; native assessment unassessable pending untracked declaration. INSPECT created no lineage and stopped at intended-untracked selection over accumulated dirty work. No START, receipt, review approval or publishing occurred. Review must use isolated work-unit candidate, not unrelated dirty-world accumulation.

L12. Oversized delivery question initially cancelled. Superseded by L13; no permission was inferred from cancellation.

L13. User delivery instruction verbatim: haz siempre PR encadenados, y mezclalos a main

L15. Fresh remote evidence: origin/main941811d, merge-base f5683b0, local HEAD5a6ab97 includes 12 unpublished-to-main commits and 328 files/12799 additions/520 deletions vs main. Existing PR73 remote head eb30f9c (older than local HEAD), CI3.11/3.12 success for that exact old head, strict main protection requires those two checks. No existing PR merged or updated. Do not count old-head checks as proof of current dirty tree. Required issue-first approval missing: issue41 OPEN with phase:mvp/epic:validation/type:task, no status:approved; no status:approved label in repo inventory. Await exact human approval before introducing approval label; preserve original dirty worktree. New PRs need scoped bases, not entire328-file feature accumulation.

L16. User approved exact issue-label operation: si, estas autorizado. job4 created status:approved and applied it to issues41/46, exit0.

L17. User explicit stop after delivery verbatim: cuando hagas los commits y mezcles cierra la sesion con un handoff, y vamos a continuar en otra q ya esta tiene el cotexto lleno

L18. Isolated capacity worktree .worktrees/world-defined-capacity registered from main941811d; no original dirty files staged. Runtime not delivered: main lacks goal_evaluator_for and other historical dependencies. Commit1082d660ff4fb3d9da608177942ab212a833915a, 8paths105adds19dels. PR75 refs46, type:task. Local full suite912passed321warnings,2053stmts0miss620branches0miss, gate100%/100%. Native lineage review-27fe37eefa019576 approved after explicit candidate consent; exact ack burned authority. Required GitHub3.11/3.12 checks PASS, run39693172256. Merge requested by job8 with exact expected head, without bypass.

L19. Follow-ups T2-T5 remain pending under user explicit stop L17; no arbitrary-world completeness or Pascal-fidelity completion claimed. Handoff odd/handoffs/general-solver-fidelity.md identifies exact local/remote history and remaining artifacts.

L20. PR75 confirmed MERGED2026-10-21T23:25:32Z; merge7d3b8eee542f1fc9d8921727ecdf0b071544af30 fetched and contains1082d66. Handoff/task documentation is next chain slice on docs/solver-recovery-handoff based on merged main. No runtime or dirty world changes in either delivery slice.

L14. Decision: auto-chain/stacked-to-main. Explicit publishing, PR creation and merge authorized for this repository under applicable checks; main verified as default via target metadata github.com/efirvida/fortress-engine. Existing open PR73 targets main from current branch and local origin/main appears 15 commits behind HEAD; refreshing target evidence before choosing clean slice bases. Preserve original dirty worktree. Repo CI requires tests/coverage on Python3.11 and3.12; no PR template or status:approved label found in initial inventory. Do not invent approval labels or merge unverified existing PR.
