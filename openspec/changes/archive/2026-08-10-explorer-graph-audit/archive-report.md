# Archive Report — explorer-graph-audit

**Change**: explorer-graph-audit (Stage A: Static Explorer Graph Audit)
**Archived**: 2026-08-10 → `openspec/changes/archive/2026-08-10-explorer-graph-audit/`
**Mode**: hybrid (filesystem + Engram `sdd/explorer-graph-audit/archive-report`)
**Cycle status**: COMPLETE — planned, implemented, verified, archived

## Change Summary

Stage A is a deterministic, world-agnostic YAML-only audit that diagnoses graph
disconnection before puzzle analysis, without ever playing the world. It adds:

- `src/fortress_engine/autoplay/graph_audit.py`: `GraphAudit.run()` — one
  structural BFS over loader macro edges from `start_anchor` (gates passive),
  11 typed findings (4 ERROR / 6 WARN / 1 INFO), `Finding`/`PassageRecord`/
  `AuditReport` dataclasses with JSON-safe deterministic serialization.
- `audit-graph` CLI subcommand (`--episode`, `--json`, `--include-info`) with
  exit contract 0 (no ERROR) / 1 (ERROR findings) / 2 (usage/load/episode errors).
- 57 tests (31 unit + 18 CLI + 8 integration) plus 4 YAML fixture builders.

Traceability: dev-tool change — NOT part of the docs/tdd.md 36-task roadmap;
maps to delta specs `autoplay-graph-audit` + `cli-entry-point`.

## Final State (at close — per final-state authority)

Highest-authority facts are the orchestrator's final-state facts (post-verify
independent re-run) and the persisted tasks artifact; intermediate snapshots
(`apply-progress` obs #2099, `verify-report` obs #2101) describe their own
moments and are only cited where they remain the best evidence.

| Fact | Value | Source |
|---|---|---|
| Tasks | 8/8 `[x]` in `tasks.md` (archived copy) | tasks artifact (gate passed) |
| Requirements | 8/8 COMPLIANT | final-state facts; verify-report #2101 |
| Scenarios | 13/13 COMPLIANT | final-state facts; verify-report #2101 |
| CRITICAL findings | 0 | verify-report #2101 (`critical_findings: 0`) |
| Whole-project coverage (post-verify re-run) | 100% stmts / 100% branches (2194 stmts / 684 branches, 1016 passed) | orchestrator final-state facts |
| Targeted `graph_audit.py` coverage | 100% / 100% (218 stmts / 106 branches, 57 passed) | orchestrator final-state facts |
| CLI smoke (post-verify re-run) | `episode-01` exit 0; `episode-02` exit 1 (world mid-rewrite, no crash); missing world exit 2; unknown episode exit 2; JSON deterministic | orchestrator final-state facts |

Note: at verification time (`verify-report` #2101) the same coverage numbers
(100%/100%, 1016 passed) were measured; the post-verify independent re-run
confirmed them, so no number drift occurred.

Spec authority: the CORRECTED spec (Engram obs #2095, revisions 4) is
authoritative — it defines 11 findings (4 ERROR / 6 WARN / 1 INFO), not the
proposal's earlier 16-category contract. Verified implementation matches the
corrected spec.

## Merged Deltas

| Domain | Action | Details |
|--------|--------|---------|
| `autoplay-graph-audit` | Created | Main spec did not exist → delta copied mechanically as full spec to `openspec/specs/autoplay-graph-audit/spec.md` (byte-identical, empty `diff -r`). 5 requirements, 6 scenarios. |
| `cli-entry-point` | Updated | Main spec existed (from archived `2026-08-08-epic-4-cli`). Merged: 2 MODIFIED requirements replaced in full (`Console script registration and argparse subcommands` — adds `audit-graph` row + scenario; `Exit code contract` — adds audit-graph 0/1/2 semantics + 2 scenarios) and 1 ADDED requirement appended (`Audit graph output`, 2 scenarios). All other requirements (EngineBundle, Run, Validate, Test, Narrator wildcard) preserved untouched. |

Destructive-delta assessment (config rule "Warn before merging destructive
deltas"): **non-destructive** — no REMOVED requirements, no large-section
removal; both MODIFIED blocks carried their complete updated content including
unchanged scenarios. No warning required. The delta's `(Previously: ...)`
changelog annotations were dropped from the main spec (main specs carry current
contract, not diff history; the archive is the history).

## Traceability — Engram observations read

| Observation | Topic | Role |
|---|---|---|
| #1946 | `sdd-init/fortress-engine` | Project baseline (stack, conventions, strict_tdd) |
| #2094 | `sdd/explorer-graph-audit/proposal` | Intent, scope, approach |
| #2095 | `sdd/explorer-graph-audit/spec` | CORRECTED authoritative spec (revisions 4) |
| #2096 | `sdd/explorer-graph-audit/design` | Technical design |
| #2098 | `sdd/explorer-graph-audit/tasks` | 8/8 tasks complete |
| #2099 | `sdd/explorer-graph-audit/apply-progress` | Apply evidence (intermediate snapshot) |
| #2101 | `sdd/explorer-graph-audit/verify-report` | Verify evidence (verdict pass, 0 CRITICAL) |

This report persisted as Engram topic `sdd/explorer-graph-audit/archive-report`.

## Follow-ups (recorded, NOT executed — archive touches no code)

1. **WARNING — `pyproject.toml` omit too broad**: `[tool.coverage.run] omit =
   ["src/fortress_engine/autoplay/*"]` hides the fully-covered `graph_audit.py`
   from the whole-project coverage gate; the >99% gate can pass while the new
   module is unmeasured. Recommendation (deferred by task 5.1, re-raised by
   apply and verify): narrow the omit to `src/fortress_engine/autoplay/explorer.py`
   (pre-existing dev tool with deliberate defensive branches) in a follow-up so
   the audit module stays under the whole-project gate. Targeted coverage
   (218 stmts / 106 branches, 100%/100%) proves the module is fully covered
   today.
2. **SUGGESTION — AGENTS.md**: the whole-project gate run takes ~290s and the
   targeted autoplay command requires the `--cov-config` + dotted-module quirk
   (file-path `--cov=` collects no data under the omit). Consider adding the
   targeted command to AGENTS.md Quick commands.
3. **Scope note**: working tree carries unrelated uncommitted WIP on branch
   `feat/issue-41-walkthrough-l1` (worlds/fortaleza rewrite, explorer.py,
   walkthrough tests). This archive touched ONLY openspec artifacts; no code was
   staged or committed.

## state.yaml reconciliation

`phase_state.tasks` was `pending` in state.yaml while the authoritative tasks
artifact shows 8/8 `[x]` and `apply: done`. Reconciled to `done` (mechanical
state sync, evidence: tasks.md all checkboxes + verify 8/8), and
`phase_state.archive` set to `done` before the archive move (snapshot readback
confirms the archived copy carries it).

## Rollback Note

Rollback of this change is additive-only: delete `autoplay/graph_audit.py` +
`tests/test_autoplay/` + `tests/test_cli/test_audit_graph.py` +
`tests/test_integration/test_graph_audit.py`, revert the `audit-graph` addition
in `cli/main.py` and the exports in `autoplay/__init__.py`, and remove the two
synced main specs (or re-merge the delta reversals). No migration, no
world-data rollback needed. Archived artifacts are the audit trail — do not
modify them.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
