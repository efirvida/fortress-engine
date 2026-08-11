# Proposal: Completability Solver (Stage B)

## Intent

Stage A proves structural graph reachability; Stage B must prove the episode is **completable** by actually resolving item, flag, password, and puzzle gates. The dev-tool walks the runtime incrementally, using culturally supplied answers rather than inferring riddles from narrator prose.

## Scope

### In Scope

- New `src/fortress_engine/autoplay/solver.py`: dataclasses for `SolveVerdict` and `GateDiagnosis`, KB loading, audit-guided resolver, snapshot/restore, and committed-command evidence.
- `fortress-engine solve <world_path> [--episode ID] [--answers PATH] [--json] [--max-turns N]`, mirroring `audit-graph`, with exit 0 completable, 1 diagnosed not-completable, 2 usage/load failure.
- Optional `worlds/fortaleza/episodes/answers.yaml`, strict fixture/CLI/integration tests, and narrowing `pyproject.toml` coverage omit to `autoplay/explorer.py`.

### Out of Scope

Engine changes (spoken riddles cannot currently be modeled because cliques have no text predicate), world-data fixes, Stage A audit changes, and narrator-text quality checks.

## Capabilities

### New Capabilities

- `autoplay-solver`: prove completability with walkthrough or gate diagnosis.

### Modified Capabilities

- `cli-entry-point`: add the `solve` command and its exit/output contract.

## Approach

Use the audit-guided incremental resolver (Approach B) with Approach C diagnosis. First run `GraphAudit`; ERRORs yield not-completable evidence. Build runtime once, assemble knowledge, then BFS the audit frontier: **take → probe verb/target/instrument combinations → movement with KB brute force → goal check after every committed change**. Reuse BlindExplorer’s snapshot/restore machinery; log only committed commands. On an item gate, bounded backtracking performs **navigate → take → return → retry**. At fixed point, diagnose each gate as `answer_not_in_kb`, `item_unreachable`, `item_missing_from_world`, `item_never_acquired`, or `flag_never_set`, cross-referenced with `AuditReport` to separate world defects from solver limits.

## Knowledge Base and Architecture

Derive every macro-edge `requires_text` (the answer itself, e.g. `Abrete Sesamo`), then merge optional per-episode (selected by `--episode`) `passwords` and `riddle_answers` plain strings from `episodes/answers.yaml` or `--answers PATH`. The solver accepts any language, preserving the cultural/player-knowledge boundary. Runtime code remains dataclass-based, world-agnostic, and reuses the loader and orchestrator without modifying the engine.

## Testing, Risks, and Rollback

Strict TDD uses `solver_happy`, `solver_kb`, `solver_retrieve`, and `solver_unsolvable` `tmp_path` worlds; asserts exact walkthroughs, KB loading, retrieval, diagnoses, CLI JSON/exit codes, and an unpinned Fortaleza smoke. Coverage MUST exceed 99% branch; omit narrowing to `autoplay/explorer.py` is mandatory. Risks are search explosion (differential probing, `MAX_PROBE_ITEMS`, `--max-turns`), cultural KB gaps (explicit diagnosis), moving world data (unpinned smoke), private `restore()` coupling (central path), and the coverage gate (measure solver branches). Rollback deletes the additive solver/tests/CLI branch, reverts the coverage omit, and removes `answers.yaml` if added.

## Dependencies and Success Criteria

Depends on the committed `GraphAudit`, existing loader/orchestrator, and no new runtime dependency. Success means a completable fixture returns a deterministic committed walkthrough and exit 0; unsolvable fixtures identify the correct gate reason and exit 1; malformed inputs exit 2; and the whole project passes the strict >99% branch gate.
