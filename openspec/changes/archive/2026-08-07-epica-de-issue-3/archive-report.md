# Archive Report — epica de issue #3

**Status**: CLOSED
**Archived**: 2026-08-07
**Branch**: feat/epica-de-issue-3-n1..n5 (stacked-to-main)
**Issue**: #3 (parent epic) via #21, #23, #24, #25

## Executive Summary

Plugins layer (Parser Interface + Classic Parser V1, Narrator Interface + Template Narrator V1, plugin factory with entry-point discovery, WorldYAML language/parser/narrator extensions, per-world vocabulary loader) fully implemented and verified. All 20 tasks (N1.1–N5.5) complete, 696 tests pass with 100% statement and branch coverage, 10/10 requirements satisfied, 17/17 scenarios compliant. The change is archived per ordinary SDD policy.

## Final State (Authority: orchestrator launch prompt + verified artifacts)

| Metric | Value |
|--------|-------|
| Tests passing | 696 (0 failed, 0 skipped) |
| Branch coverage | 100% (1725 stmts, 0 misses, 526 branches, 0 partials) |
| Uncovered items | 0 — hard gate (>99%) PASSED |
| Tasks completed | 20/20 (N1.1–N5.5) |
| Slices delivered | N1 (ABC language), N2 (factory), N3 (WorldYAML+vocabulary), N4 (ClassicParser), N5 (TemplateNarrator+integration) |
| PRs merged | #58, #59, #60, #61, #62 (stacked-to-main, merge order 58→62) |
| Verify verdict | PASS WITH WARNINGS — no CRITICAL issues |

## Architecture Decision Record (user decision, this epic)

- **Plugin factory + language in world.yaml**: `world.yaml` declares `language: "es"` + `parser`/`narrator` plugin declarations; `create_parser`/`create_narrator` resolve entry points (arch constant #7 — factory is the ONLY entry-point caller) and inject `language` into the plugin instance.
- **Multi-language seam**: a new language = new entry point + world declares its language; engine unchanged. `ParserInterface`/`NarratorInterface` expose `language` (default `"es"`).
- **Verb inventory**: original Fortaleza 37-verb constants with synonym groups + `EXAMINAR` (docs/07-vocabulary.md authoritative). `esperar` explicitly excluded (user decision).
- **Stopwords**: V2 expanded 9-word set `{el, la, los, las, un, una, al, del, por}` — documented deviation from TDD §4.15 V1, consistent with MinimalParser.
- **Language validation**: warn-level at load time; strict mode deferred to v1.1.

## Warning Record (non-archival, for future slices)

1. **`item_examined` vs `entity_examined` naming drift (RESOLVED)**: verify flagged that spec/design named the 9th narrator event `item_examined` while engine taxonomy (`ENTITY_EXAMINED`) and implementation use `entity_examined`. Fixed at archive: spec, design, proposal now use `entity_examined` (0 occurrences of `item_examined` remain in change artifacts).
2. **Hardcoded Spanish user-facing strings in the ENGINE** (graph.py, operators.py, orchestrator.py) and engine language-coupling (movement verbs `"ir"`/`"abrir"`, system commands `guardar/cargar/terminar/esperar/grupo`): engine emits `error_code` + message today; the message text should move to narrator templates and verb/system recognition should move out of the engine. **New SDD change `engine-language-agnostic` planned and approved by user for next iteration.**
3. **`episode_completed` literal vs constant**: orchestrator emits the string literal `"episode_completed"` instead of the `EPISODE_COMPLETED` constant (minor, folded into the engine-language-agnostic change).
4. **Dead ternaries** in orchestrator save/load no-repository branches (both branches identical) — folded into the engine-language-agnostic change.
5. **CLI entry point dangling**: `pyproject.toml` declares `fortress-engine = fortress_engine.cli.main:main` but `cli/main.py` does not exist yet (CLI owned by a later epic).

## Specs synced to openspec/specs/

- `openspec/specs/parser-classic-v1/spec.md` (new)
- `openspec/specs/narrator-template-v1/spec.md` (new)
- `openspec/specs/plugin-factory/spec.md` (new)
- `openspec/specs/world-yaml-extensions/spec.md` (new)
- `openspec/specs/plugin-contracts/spec.md` (modified — language property, corrected `initialize`/`handle_event` narrator contract)
