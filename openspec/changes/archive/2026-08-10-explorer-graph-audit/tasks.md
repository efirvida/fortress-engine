# Tasks: Explorer Graph Audit (Stage A)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,300–1,500 (additions + deletions) |
| 400-line budget risk | High |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Single PR requiring size:exception (user preference: single-pr) |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High
800-line budget risk: High

Traceability: dev-tool change — NOT part of the docs/tdd.md 36-task roadmap; maps to delta specs `autoplay-graph-audit` + `cli-entry-point`.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Fixtures + `graph_audit.py` + unit tests (1.1–2.3) | PR 1 (size:exception) | `pytest tests/test_autoplay/ -q` | N/A — pure loader dataclass/BFS math; no process boundary until CLI exists | Delete `autoplay/graph_audit.py` + `tests/test_autoplay/` |
| 2 | CLI `audit-graph` + tests (3.1–3.2) | PR 1 | `pytest tests/test_cli/test_audit_graph.py -q` | `fortress-engine audit-graph <fixture world>` asserting exit 0/1/2 | Revert `cli/main.py`; delete `test_audit_graph.py` |
| 3 | Integration + coverage gate (4.1, 5.1) | PR 1 | `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` | `fortress-engine audit-graph worlds/fortaleza --episode episode-01 --json` (smoke) | Delete integration test additions |

## Phase 1: Fixture Worlds (Foundation)

- [x] 1.1 Create `tests/test_autoplay/__init__.py` + `conftest.py`: `tmp_path` YAML builders `audit_happy`, `audit_broken`, `audit_disconnected`, `audit_limbo` (world.yaml, episodes/, rooms/, items/, npcs/, macros/) covering all 11 findings + both BFS branches; `audit_happy` uses non-Spanish identifiers, zero findings. Acceptance: every fixture loads via `EntityLoader` (smoke assert) and maps to documented findings.

## Phase 2: Core Module (TDD)

- [x] 2.1 RED — `tests/test_autoplay/test_graph_audit.py`: exact severity/location/message/data for all 11 findings; BFS branches (missing start → empty set + `start_anchor_missing`; gated path reachable; disconnected unreachable; self-loop once); passive predicates verbatim incl. `None`/`False` + `PassageRecord` field order; findings sort (ERROR→WARN→INFO, category, location); `unreachable == declared − reachable`; no runtime construction. Fails: module absent.
- [x] 2.2 GREEN — `src/fortress_engine/autoplay/graph_audit.py`: dataclasses `Finding`/`PassageRecord`/`AuditReport` + `GraphAudit.run(loader, episode)` — one BFS over `load_macro_edges` from `start_anchor` ignoring `open` + all predicates; 11 scans (4 ERROR / 6 WARN / 1 INFO); passive gate serialization; deterministic ordering. Acceptance: 2.1 green; loader data only.
- [x] 2.3 Export `GraphAudit`, `Finding`, `PassageRecord`, `AuditReport` in `src/fortress_engine/autoplay/__init__.py`; import smoke in 2.1.

## Phase 3: CLI Wiring (TDD)

- [x] 3.1 RED — `tests/test_cli/test_audit_graph.py` mirroring `test_validate.py`: exit 0 (no ERROR) / 1 (ERROR findings) / 2 (missing or malformed world, unknown `--episode`, usage); default first episode vs explicit; `--json` deterministic; INFO hidden without `--include-info`; human output grouped by severity.
- [x] 3.2 GREEN — `cli/main.py`: `audit-graph` subparser (`world_path`, `--episode`, `--json`, `--include-info`) + `cmd_audit_graph` (world.yaml check, load episodes, default first, errors → stderr/exit 2, grouped human output, deterministic JSON, exit 0/1 by ERROR presence); `run`/`validate`/`test` untouched. Acceptance: 3.1 green + full branch coverage of the new handler.

## Phase 4: Integration

- [x] 4.1 `tests/test_integration/test_graph_audit.py`: audit `worlds/_test_minimal` → zero findings; audit `worlds/fortaleza` episode-01 + episode-02 → typed report, no crash, set arithmetic holds, no pinned findings.

## Phase 5: Coverage Verification

- [x] 5.1 Whole-project `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` > 99% AND targeted `pytest tests/test_autoplay/ tests/test_cli/test_audit_graph.py --cov=src/fortress_engine/autoplay --cov-branch --cov-report=term-missing -q` ≥ 99% (pyproject `omit` excludes `autoplay/*`). FLAG the `pyproject.toml` omit consideration (keep vs narrow to `explorer.py`) without changing it unless this task proves it needed; commit tests with code (AGENTS.md hard gate).

**5.1 results**: whole-project TOTAL = 2194 stmts / 0 missed / 684 branches / 0 missed → **100% statements, 100% branches** (1016 passed). Targeted run cannot measure `autoplay/*` with the pyproject `omit` (no-data-collected); ran with a temporary `--cov-config` (no omit, `/tmp/opencode/autoplay-cov.ini`) + `--cov=fortress_engine.autoplay.graph_audit` → **100% statements, 100% branches** (218 stmts / 106 branches). **FLAG**: pyproject `omit = ["src/fortress_engine/autoplay/*"]` is now too broad — it hides `graph_audit.py` from the whole-project gate; consider narrowing to `explorer.py` (pre-existing dev tool with deliberate defensive branches). Kept unchanged per task; revisit at archive/verify.
