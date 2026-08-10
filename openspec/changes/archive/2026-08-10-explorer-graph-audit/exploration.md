# Exploration: Static Graph Audit for Fortress Worlds (`explorer-graph-audit`)

## Context

The current `src/fortress_engine/autoplay/explorer.py` is a blind brute-force
explorer (plays the game reading narrator text) plus a `MapComparator` that
diffs discovered topology vs the YAML-declared map. With the fortaleza world
it does NOT traverse everything, and nobody can tell whether the fault is in
the world graph, the world design, or the explorer itself.

This change (Stage A) builds a **static, deterministic graph-analysis tool**
that detects orphaned/inaccessible entities from the YAML data alone — no
turns, no parser, no narrator. Stage B (out of scope) will rework the blind
explorer into a design/completability checker that runs ONLY after the static
graph is proven complete.

## Current State

### World graph data model

- **Loader** (`src/fortress_engine/entities/loader.py`): `EntityLoader(world_path)` loads
  rooms/items/npcs (`load_rooms/load_items/load_npcs` → `list[Entity]` from
  `episode-XX/{rooms,items,npcs}/*.yaml`), macro edges
  (`load_macro_edges` → `list[MacroEdge]`, **already expands bidirectional edges
  into `_reverse` copies**), hyper edges (`load_hyper_edges`, recursive),
  episodes (`load_episodes` → `list[Episode]` with `start_anchor`, `goal`,
  `carry_over`), shared entities, vocabulary. `load_episode_data` aggregates
  them into one dict.
- **Runtime dataclasses** (`entities/entity.py`, `engine/graph.py`): `Entity`
  (`entity_id, type, name, components, spatial_anchor`), `Episode`
  (`id, start_anchor, goal: GoalConditions, carry_over`), `MacroEdge`
  (`from_anchor, to_anchor, direction, passage_name, requires_text,
  requires_item, forbids_item, requires_flag, forbids_flag, death_message,
  open`). YAML defaults: `open: true`; `spatial_anchor: null` (limbo is legal
  per PRD 4.3 — "destroyed").
- **Graph** (`engine/graph.py`): `DualGraphEngine.build_macro_graph(anchors,
  edges)` just indexes edges under `from_anchor`; `validate_macro_edge` shows
  gate semantics: text gate only applies when `requires_text is not None and
  not edge.open`; item/flag gates are inventory/flag checks. **Quirk:
  `open: false` without `requires_text` is NOT blocked by the engine** — the
  text-gate branch is skipped, so the edge is passable. A static audit can
  flag this data-intent mismatch.
- **Existing integrity checks**: `validate_world()` already covers
  start_anchor existence, dangling `spatial_anchor` (cross-episode union of
  ALL entity ids — loose: an ep-2 item anchored to an ep-1-only room passes),
  and duplicate `(verb, target, priority)` hyper edges. It does NOT do
  reachability, macro-edge endpoint checks, gate-reference checks, or goal
  reference checks.

### Blind explorer / MapComparator (`autoplay/explorer.py`)

- `BlindExplorer` builds the FULL runtime (plugins, EventBus, WorldState,
  EpisodeManager, TurnOrchestrator), reads narrator text, tokenizes, and
  brute-forces verbs × tokens with snapshot/restore. It is heavy, heuristic,
  and depends on narrator-text quality (`found_npcs` is never populated by
  `_probe_actions` — dead field today).
- `MapComparator.compare(discovery)` diffs declared rooms/passages/items/npcs
  vs discovered ones. Its "declared" side is exactly the static data — that
  part is reusable conceptually; its "discovered" side depends on the blind
  explorer.

### Live probe of the fortaleza world (read-only, current tree)

Episode 1: 50 rooms, 60 items, 24 NPCs, 142 edges (124 declared). No dangling
endpoints/anchors; start_anchor OK. But **one macro edge has
`requires_item: "nada"`** — a nonexistent item (rewrite artifact).
Episode 2: 55 rooms, 67 items, 23 NPCs, 120 edges. **Edges
`me_antesala_comedor`, `me_huespedes_pasillo`, `me_limites_piramide` require
`arco`/`grabado` which do NOT exist in ep-2** (only `arco_inmortal`,
`grabado_pintor` exist — likely a rename leftover; they exist in ep-1, but
ep-2 `carry_over.inventory: []` means nothing carries). `bajos_de_las_cataratas`
has no incoming passage and is not the start anchor. `maza` (ep-2) is in
limbo (`spatial_anchor: null`) at load. The prior walkthrough exploration
(Aug 8) also recorded orphans `laberinto_salida`, `sala_de_lobos` (ep-1) —
since connected in the rewrite — confirming the world is a **moving target**,
exactly the case the audit tool is for.

## Affected Areas

- `src/fortress_engine/autoplay/graph_audit.py` — **NEW module**: the static audit engine.
- `src/fortress_engine/autoplay/__init__.py` — export the audit API.
- `src/fortress_engine/cli/main.py` — new `audit-graph` subcommand + `cmd_audit_graph`.
- `tests/test_engine/test_graph_audit.py` — unit tests with synthetic fixture worlds.
- `tests/test_cli/test_audit_graph.py` — CLI contract tests (mirror `test_validate.py`).
- `tests/test_integration/` — minimal-world audit must pass clean; fortaleza audit must run without crashing (no pinned findings — world mid-rewrite).
- `worlds/fortaleza/**` — **target only, NOT modified** (mid-rewrite on branch `feat/issue-41-walkthrough-l1`).
- Reuse without modification: `entities/loader.py` (`EntityLoader` calls),
  `engine/graph.py` (`MacroEdge`, `Clique` dataclasses), `entities/entity.py`
  (`Entity`, `Episode`), `autoplay/explorer.py` (`MapComparator` data shapes).

## Approaches

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **A. Pure-static module** (`autoplay/graph_audit.py`): `EntityLoader` only; BFS over `load_macro_edges` from `start_anchor`; no engine runtime, no WorldState, no plugins | Deterministic; fast; no narrator/parser coupling; trivial to test (>99% gate friendly — pure dataclass math); works for ANY world; reuses loader's bidirectional expansion | Duplicates a little indexing logic from `DualGraphEngine` (10 lines); gate satisfiability is only partially decidable statically | Low-Med |
| **B. Reuse engine runtime**: build WorldState/EpisodeManager + `DualGraphEngine`, traverse `graph._macro_edges`, evaluate gates via `validate_macro_edge` | Uses the engine's own graph and gate evaluation verbatim; gate semantics can't drift | Requires EventBus + plugins + WorldState wiring (`_build_engine`-style); mutates edge `open` state; slower; harder to test (mocks, runtime setup) for marginal gain — reachability is pure edge-list math | Med-High |

### Recommendation

**Approach A**, with one concession to B: reuse `DualGraphEngine.build_macro_graph`
+ `get_edges_from_anchor` as the traversal index (pure indexing, no
WorldState/plugins) — or simply index `load_macro_edges` output in a local
dict (KISS; ~10 lines). Gate evaluation stays static:
- Edge with no item/flag predicates → **unconditional** (text gates count as
  passable — passwords live in the world data; `open:false` without
  `requires_text` is passable per engine semantics, flagged INFO).
- Edge with `requires_item`/`forbids_item`/`requires_flag`/`forbids_flag` →
  **conditional** (statically undecidable — that is Stage B's job).
- Report three sets: `unconditionally_reachable`, `conditionally_reachable`,
  `unreachable = declared − (both)`, plus per-passage gate lists.

## Audit Categories (Stage A detection contract)

Severity `ERROR` (exit code 1):
1. `start_anchor_missing` — episode `start_anchor` is not a declared room.
2. `dangling_edge_endpoint` — macro edge `from_anchor`/`to_anchor` is not a declared room.
3. `dangling_spatial_anchor` — item/NPC anchored to a room that does not exist (per-episode; stricter than `validate_world`'s cross-episode union).
4. `isolated_room` — declared room with neither incoming nor outgoing edges and not the start anchor.
5. `gate_unknown_entity` — `requires_item`/`forbids_item` references an item that exists in NO episode or shared dir.

Severity `WARN`:
6. `orphan_room` — no incoming passage and not start anchor (may be intentional one-way entry; must have outgoing).
7. `unreachable_room` — declared but not reachable even via gated passages.
8. `gated_only_room` — reachable only through item/flag-gated passages (expected in puzzle games; report the gates so the author verifies).
9. `gate_item_other_episode` — gate item exists only in another episode; check `carry_over` (e.g. ep-2 `carry_over.inventory: []` makes the gate unsatisfiable).
10. `goal_unknown_entity` — goal condition `entity`/`room`/`flag` params reference unknown entities/rooms/flags.
11. `duplicate_passage` — same `(from, to, passage_name)` declared twice.
12. `self_loop_edge` — `from_anchor == to_anchor`.

Severity `INFO`:
13. `entity_limbo_at_load` — `spatial_anchor: null` at load (LEGAL per PRD 4.3; listed for awareness).
14. `closed_edge_without_text_gate` — `open: false` with no `requires_text` (engine treats it as passable — data intent mismatch).
15. `flag_never_set` — `requires_flag` with no hyper-edge operator setting it in any episode.
16. `text_gated_passage` — `requires_text` gate (reachable; the password is in the data).

Distinction kept explicit: `entity_limbo_at_load` (declared None — legal)
is NOT `dangling_spatial_anchor` (references a nonexistent room — error).

## CLI Integration Proposal

```text
fortress-engine audit-graph <world_path> [--episode EPISODE_ID] [--json] [--include-info]
```

- Follows existing conventions in `cli/main.py`: positional `world_path`,
  `--episode` (default: first episode loaded, mirroring the CLI's current
  episode-01-centric `_build_engine`), argparse subparser + `cmd_audit_graph(args)`
  handler, `SystemExit` codes like `validate`/`test`.
- Human output grouped by severity:
  `[ERROR] episode-01 room=celda_pequena: macro edge me_x has dangling to_anchor 'laberinto_salida'`
  WARN/INFO printed when present (INFO only with `--include-info`).
- Exit `0` when no ERROR findings; exit `1` when ERROR findings exist.
- `--json`: machine-readable `AuditReport` dump (CI-friendly).

## Seam for Stage B (blind design-checker)

- `GraphAudit.run(episode_id) -> AuditReport` exposing
  `declared_rooms`, `unconditionally_reachable`, `conditionally_reachable`,
  `unreachable_rooms()`, per-passage gate lists, and `findings`.
- Stage B contract: run the audit FIRST; zero ERROR findings is the
  precondition that the static graph is complete/connected. Stage B then
  brute-forces actions ONLY on `conditionally_reachable` rooms/passages and
  attributes any failure to design/satisfiability, not data structure.
- `MapComparator` remains for narrator-text quality (declared vs discovered
  surface tokens); its declared-side topology role is subsumed by the audit.

## Testing Strategy (strict TDD, >99% branch gate)

Fixture worlds via `tmp_path` + `write_text` (established pattern in
`test_autoplay_explorer.py`/`test_validate.py`); no giant fortaleza world in
unit tests:

1. `audit_happy` — 3 rooms, 2 edges, 1 item, 1 NPC, valid start → ZERO findings.
2. `audit_broken` — missing start_anchor, dangling edge endpoint, dangling
   spatial_anchor, isolated room, gate to unknown item → one fixture per ERROR category.
3. `audit_gated` — text-gated, item-gated, flag-gated, bidirectional edges,
   orphan room, gated-only room, flag never set, closed-edge-without-text,
   duplicate passage → conditional/unconditional set assertions + WARN/INFO categories.
4. `audit_limbo` — item with `spatial_anchor: null`, cross-episode gate item
   with `carry_over: []` → INFO + `gate_item_other_episode`.

Tests: BFS set math; every category fires on its fixture; happy world fires
nothing; CLI exit codes/`--json`/`--episode` (mirror `test_validate.py`);
integration: `_test_minimal` audits clean, fortaleza audits without crashing
(assert categories present, never exact finding sets — world is mid-rewrite).

## Risks

- **World mid-rewrite**: fortaleza findings are a moving target; integration
  tests MUST NOT pin exact findings (flakiness).
- **Gates statically undecidable**: item/flag satisfiability is Stage B; the
  audit only reports conditional reachability — users may misread
  `gated_only_room` as a defect.
- **Coverage gate**: new module + CLI subcommand must stay >99% branch —
  every severity/category branch needs a test.
- **`validate_world` overlap**: audit is stricter per-episode; proposal phase
  must decide whether `validate` delegates to the audit or stays unchanged.
- **`open:false`-without-text quirk** and `entity_limbo_at_load` are
  intentional/legal — flagging them INFO prevents false-alarm complaints.

## Ready for Proposal

Yes. The orchestrator should tell the user: Stage A is a new static
`graph_audit` module + `audit-graph` CLI subcommand, deterministic, world-agnostic,
with the category contract above; it already proves real defects in the
current fortaleza world (ep-2 gates to renamed items, `requires_item: nada`,
ep-2 orphan room). Stage B (brute-force design checker) only starts once the
audit reports zero ERRORs.
