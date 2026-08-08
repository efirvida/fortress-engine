# Fortress Engine — Agent Instructions

## Project identity

**Python 3.11+** interactive fiction engine. `src/` layout (PEP 517), package name `fortress-engine`.

The engine-core foundation is implemented (entity model, event system, world state, 5 atomic operators, dual graph, goal evaluator, world loader, turn orchestrator, episode manager) with tests at >99% branch coverage. Implementation follows the docs; see the Testing hard gate below.

## Quick commands

```bash
pip install -e ".[dev]"          # dev install with pytest + Alembic
pytest                           # run all tests (tests/ mirroring src/)
pytest tests/test_engine/        # single package
pytest -k "test_operators"      # single test pattern
```

There is no CI, no lint/typecheck config, no codegen, and no database yet. Alembic is installed but not initialized (MVP uses `Base.metadata.create_all`).

## Testing hard gate (MANDATORY — whole project)

This gate applies to **every slice, phase, or continuation**, before asking the user to continue, before committing, and before opening a PR:

1. Run branch coverage: `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q`
2. **TOTAL coverage must be > 99%** (statements AND branches). Below that, STOP: write the missing tests first, re-run, then continue.
3. The only allowed uncovered item is provably unreachable dead code (e.g. a defensive `else` after an exhaustive dispatch), documented with a comment and justification. Anything else uncovered is a defect.
4. Tests must be **strict, not lax**: assert exact messages/values (no substring filters that pass when the validator is broken), cover failure branches (KeyError, rejected wildcards, absent predicates, dispatch fall-through), and count events where the contract says exactly one (e.g. one `turn_ended` per turn).
5. **Integration is part of coverage**: the glue between modules (loader → graph → state → operators → EventBus) must be tested together, not only each module in isolation.
6. Tests belong in the same commit as the code they verify. Never commit code without green tests + coverage above the gate.

## Docs are the spec

Implementation authority lives in three Spanish docs. Read them before writing code — they define the architecture, not just the intent:

| Doc | Role |
|-----|------|
| `docs/prd.md` | Product vision, feature scope (MoSCoW), stack, plugin system, episode/puzzle grammar |
| `docs/gdd.md` | Entity schemas, macro/micro graph design, operator pre/postconditions, turn cycle pseudocode |
| `docs/tdd.md` (2493 lines) | **Authoritative implementation spec.** Class signatures, method contracts, SQLAlchemy models, plugin interfaces, testing strategy, 36-task roadmap |

The TDD's class names are **suggestions** — you can rename them, but preserve the architecture, public interfaces, and separation of responsibilities.

The `docs/01-11/` directory contains complete analysis of the original Fortaleza game (88 rooms, 120+ items, 50 NPCs, 93 puzzles, 37 verbs, walkthrough). `docs/original-source/` preserves the Turbo Pascal source as reference — it's not part of this engine.

## Architecture constants

These are hard design constraints. Do NOT violate them:

1. **`@dataclass` for runtime, Pydantic only for YAML validation at load time.** Pydantic never touches the hot path.
2. **`player_controlled_entities` is always a list**, never a singleton. The engine supports multi-protagonist from day one.
3. **Engine is strictly single-threaded, synchronous** for v1.0.
4. **Events are synchronous Observer pattern** (`EventBus`). No async, no callbacks.
5. **Persistence is Event Sourcing**, not state snapshots. Only state-changing actions are logged; narration events are derivable from state. Snapshots are performance caches, never the source of truth.
6. **Five atomic operators** compose ALL world logic: `TRANSFER`, `TRANSFORM`, `COMBINE`, `FLAG`, `TELEPORT`. No world-specific logic enters the engine.
7. **Plugins are loaded via `importlib.metadata.entry_points`**, never hardcoded imports. Parser and narrator must be swappable.

## Code conventions

- **Code identifiers (classes, methods, variables) in English.** YAML world data and in-game text follow each world's declared language (`world.yaml → language`). The engine is **language-agnostic**: the Spanish Fortaleza world happens to be in Spanish, but world data must never be assumed to be in a specific language. The `language` field and the plugin factory (parser/narrator) inject the language from `world.yaml` (PRD §4.11).
- **No entity type inheritance.** Entity behavior comes from components + HyperEdges, not class hierarchy. The engine is **entity-agnostic**: `Entity.type` is an opaque string owned by the world creator (e.g. `"item"`, `"room"`, `"npc"`). The engine MUST NOT validate, enumerate, or branch on entity types. World-type names like `"room"`/`"item"`/`"npc"` never appear in engine contracts — the engine's spatial vocabulary is `spatial_anchor`/`anchor` (see `add_anchor`, `from_anchor`/`to_anchor`, `start_anchor`).
- `spatial_anchor == None` means "destroyed" or "in limbo" (see Limbo Room pattern, PRD 4.3).
- Special clique values: `subject == "player"` resolves to `active_protagonist_id` at runtime. `target == "*"` and `instrument == "*"` are wildcards matching any entity of the expected type in the current anchor or inventory.
- HyperEdges with the same `(verb, target)` pair get different priorities — higher priority evaluated first. This replaces `if/else` logic entirely.

## Dependencies

Core: `pyyaml>=6.0`, `pydantic>=2.0`, `sqlalchemy>=2.0`. Dev extras: `pytest>=8.0`, `pytest-cov>=5.0`, `alembic>=1.13`.

## What NOT to do

- Don't add `class`-based OOP where `@dataclass` suffices.
- Don't serialize Pydantic models into the event log — convert to plain dicts first.
- Don't log narrative events (`action_output`, `entity_entered`) to the event sourcing log. Only events with `has_effects: true`.
- Don't write game logic as conditionals. Every action must be a HyperEdge with a Clique.
- Don't edit `docs/original-source/` files — they're preserved as-is for reference.
