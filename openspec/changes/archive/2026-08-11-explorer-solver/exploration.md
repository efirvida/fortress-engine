# Exploration: explorer-solver (Stage B — Completability Solver)

**Change**: `explorer-solver` — prove the world is COMPLETABLE, not just traversable.
**Stage**: B of the autoplay redesign (Stage A = static graph audit, archived).
**Mode**: hybrid (filesystem + Engram `sdd/explorer-solver/explore`).

---

## Current State

### The blind explorer (WIP, `src/fortress_engine/autoplay/explorer.py`, 982 lines)

The committed+WIP `BlindExplorer` is the predecessor Stage B replaces:

- `_learn_passwords()` (line 187) reads **`requires_text` from every macro edge** of the
  episode into a global password set, then brute-forces it against text-closed passages
  with `"{movement_verb} {token} diciendo {password}"`. **`requires_text` IS the
  answer-side** (e.g. `"Abrete Sesamo"`, `"Seis"`, `"cdfghjklmnopqruvwxyz"`); the
  `question:` macro field is the riddle prose (narration only, never evaluated).
  The orchestrator's assumption that this gives "the question-side, not the answer" is
  **factually wrong** — verified in `me_enigma_dorada.yaml` (`question` = prose,
  `requires_text` = answer) and in `graph.py:validate_macro_edge` (correct spoken text
  sets `edge.open = True`).
- `_probe_actions()`/`_probe_one()` (336/435): differential probing — snapshot →
  execute → compare `(inventory, flags)` signature → KEEP only actions with positive
  observable progress, restore otherwise; `game_over` always restored. Instrument
  window capped at `MAX_PROBE_ITEMS = 6`. `probed_cmds` memo per room.
- `_movement_pass()` (639): brute-forces movement verbs over narrator tokens; real
  gates detected via `ERROR_OUTPUT error_code "blocked"` (gate_code from
  `MacroGateResult`); inline password brute-force; `room_snap` restore for one-way
  sinks.
- `explore()` (761): BFS queue over discovered rooms, `blocked_rooms` re-queued when
  the global progress signature changes, `MAX_REVISITS = 8`, hard guard 20k turns.
- `_take_if_present`/`_drop_for` (308/268): verb-agnostic item acquisition with
  weight management (lightest-first victim).

**Failure mode the user saw**: the explorer's search is *topology*-shaped, not
*goal*-shaped. It stops when the room queue is empty — "all rooms visited" ≠ "episode
goal reached". It never checks `GoalEvaluator.check(state)`; it has no key-retrieval
backtracking (a blocked passage's required item is only re-encountered passively via
revisits); passwords are tried only *after* bumping into a closed gate in that room;
and there is no diagnosis when it stops stuck (no unsatisfiable-gate report).

### Stage A seam (`src/fortress_engine/autoplay/graph_audit.py`, committed)

`AuditReport{episode, declared_rooms, reachable_rooms, unreachable_rooms, passages,
findings}` with `PassageRecord` carrying **passive** gate data (requires_item,
forbids_item, requires_flag, forbids_flag, requires_text, open, direction). Zero
ERROR findings = static graph complete. **Stage B consumes this as its starting
knowledge**: which passages are text-gated (and their exact `passage_name`), which
need items/flags, which rooms are statically unreachable → gates requiring entities
placed there are provably unsatisfiable.

### Engine mechanics the solver drives (all read, verified)

- `TurnOrchestrator.execute_turn` (orchestrator.py:175): 14-step cycle; movement
  resolved via `get_macro_edge_by_passage_name`; `validate_macro_edge(edge, state,
  text)` — text arrives from the parser's speech extraction (`diciendo`/`respondiendo`
  markers, standalone `decir`/`responder` verbs). Gate fail → `ERROR_OUTPUT`
  `blocked` + gate_code; fatal (`death_message`) → `GAME_OVER`. Goal check
  (`_evaluate_goal`) runs **after micro actions only, not after movement** — the
  solver must check the goal itself after crossings too (catches
  `entity_in_room`-style goals).
- `MacroEdge`/`validate_macro_edge` (graph.py:495): text gate evaluated **only when
  `requires_text is not None and not edge.open`**; correct text flips `edge.open` and
  propagates to the bidirectional reverse. Then item gates, then flag gates. Gates are
  uniform predicates — perfect for a solver that reads `MacroGateResult.gate_code`.
- `WorldState.to_dict/from_dict` — snapshot/restore already proven; note `restore()`
  rebinds `orch._state` (private-attribute coupling the solver must reuse carefully).
- `GoalEvaluator.check(state)`: 6 atomic condition types + recursive and/or.
  Episode-01 goal = 5 flags (`centro_*_dead` ×4 + `troll_muerto`).
- `EpisodeManager`: `start_episode`, `distribute_hyper_edges_to_anchors`,
  `goal_evaluator_for`, `transition_to_next` (ep-1→ep-2 with carry_over).
- Loader API: `load_world_config`, `load_vocabulary`, `load_episodes`,
  `load_shared_entities`, `load_rooms/items/npcs`, `load_macro_edges` (bidirectional
  expansion), `load_hyper_edges`, `load_episode_data`.

### Where answers live today

- `worlds/fortaleza/world.yaml`: NO answers section (world_id, name, language,
  description, parser, narrator only).
- `episodes/episode-01.yaml`: NO answers section (id, name, order, requires,
  start_anchor, goal, carry_over).
- The **only** answer data today: `requires_text` on individual macro edges (13
  distinct answers across ep-1/ep-2: Abrete Sesamo, Nombus Rostomelaris, Luz, Agua,
  Seis/treinta y nueve, cdfghjklmnopqruvwxyz, Aura, Aura Srka, MIAU, Omicuos Ihanti,
  Grifo, Yo, crunch — cataloged in `openspec/changes/fortaleza-walkthrough-complete/
  explore.md`).
- Vocabulary has `speech_verbs: ["decir", "responder"]` and parser support for
  standalone speech commands (`responder X` → `verb=responder, target=None,
  text="X"`), but **no world hyper edge consumes speech** (ep-2 `he_responder_ep2` is
  a no-op fallback; cliques have no text predicate, so hyper-edge riddles cannot match
  spoken text today). **All current riddle gates are macro-edge text gates.**

---

## Affected Areas

- `src/fortress_engine/autoplay/solver.py` — NEW: completability solver + verdict +
  knowledge-base loader (the change's core).
- `src/fortress_engine/autoplay/explorer.py` — source of reusable machinery
  (snapshot/restore, `_probe_actions`, `_drop_for`, `_take_if_present`, runtime
  wiring); likely extract `_build_runtime` into a shared builder to avoid duplicating
  ~55 lines of plugin wiring (SRP — design-phase decision, solver may instead compose
  BlindExplorer instances; do NOT rewrite the explorer in this change).
- `src/fortress_engine/autoplay/__init__.py` — exports.
- `src/fortress_engine/cli/main.py` — new `solve` subcommand (mirror
  `cmd_audit_graph` 0/1/2 exit contract).
- `pyproject.toml` — narrow `[tool.coverage.run] omit` from `autoplay/*` to
  `autoplay/explorer.py` (recorded follow-up from the Stage A archive report) so the
  new module is measured by the >99% gate.
- `worlds/fortaleza/episodes/answers.yaml` — NEW optional knowledge-base data
  (Spanish, world data, engine-agnostic).
- Tests: `tests/test_autoplay/` (conftest builders + `test_solver.py`),
  `tests/test_cli/test_solve.py`, `tests/test_integration/test_solver.py`.
- Docs: `docs/tdd.md` roadmap (dev-tool change, like Stage A: maps to a new delta
  spec `autoplay-solver` + `cli-entry-point` update).

---

## Approaches

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| A | **Full state-space BFS/DFS** over (room, inventory, flags, edge_open) with snapshot/restore; goal check per state | Complete in theory; shortest walkthrough | Combinatorial explosion (inventory subsets × flags × 2^edges) on a 50-room world; state signature expensive to hash; hard to bound; needs hand-built successor generator duplicating the parser | High |
| B | **Audit-guided incremental resolver** (recommended): walk the graph step by step (user's own phrasing); per room: take → probe → move with KB brute-force; on blocked gate, RETRIEVE the required key (navigate back to where it was found, take, return); goal check after every committed change; fixed point → stuck diagnosis | Reuses proven machinery (snapshot/restore, differential probing, weight mgmt); bounded; matches "recorrer el arbol paso a paso intentando resolver los caminos"; the audit's passive gate data gives pre-knowledge of where gates are; natural stuck frontier for diagnosis | Heuristic ordering is not complete in theory (rare in practice for classic IF); needs new key-retrieval backtracking step | Medium |
| C | **Plan-then-execute**: compute required items/flags per gate from the audit, plan a sequence, then drive the engine | Cleanest diagnosis; fewest probes | Cannot know statically HOW flags get set (hyper-edge operator chains); brittle against the mid-rewrite world; audit is deliberately passive — planning on it would re-introduce semantics it was designed to avoid | Medium-High |

**Recommendation: B**, hybridized with C's diagnosis output — the resolver is
incremental (B), but its stuck-analysis cross-references the audit's static report
(C's insight) to separate world defects from solver limits. This is the Stage A→B
seam made explicit: *static passivity seeds the search; dynamic probing resolves it*.

### Solver algorithm (concrete shape for design phase)

1. **Precondition**: `GraphAudit.run()`; if ERROR findings → verdict
   `not completable` with the audit findings as the diagnosis (no play attempt).
2. **Runtime**: build once (reuse/extract `BlindExplorer._build_runtime` wiring),
   parse vocabulary, snapshot/restore machinery.
3. **Knowledge base**: default = every `requires_text` from the episode's macro edges
   (proven mechanism); PLUS optional `episodes/answers.yaml` (`passwords: [...]`,
   `riddle_answers: [...]` — plain strings, any language, world-agnostic); PLUS CLI
   `--answers PATH` override/extension. Answers are tried against text gates
   (`abrir/ir <passage> diciendo <answer>`) — and, as harmless no-ops when the world
   has no speech edges, against standalone speech verbs.
4. **Walk** (BFS over audit `reachable_rooms`, navigated via discovered crossings):
   take present items → `_probe_actions` (keep-on-progress) → movement pass with KB
   brute-force → **goal check after every committed change (incl. crossings)** →
   re-visit blocked rooms on progress-signature change (existing pattern, but gated
   by audit knowledge: only re-visit rooms with known unsatisfied gates).
5. **Key retrieval (NEW)**: when a passage in room R is blocked by `requires_item X`
   and X is not carried: navigate to the room where X was found (found_items map),
   `_take_if_present(X)`, navigate back, retry — bounded retries. This is the
   structural upgrade over today's passive re-queue.
6. **Fixed point → stuck**: no committed progress across a full pass. Build the
   diagnosis: for every still-blocked passage (from audit `PassageRecord` +
   observed gate_code): text → `answer_not_in_kb` (or answer-tried-and-failed); item
   → `item_unreachable` (X placed in an audit-unreachable room) |
   `item_missing_from_world` | `item_never_acquired`; flag → `flag_never_set`.
7. **Goal reached** → walkthrough evidence: ordered list of commands that produced
   committed progress / crossings / gate-opens (the solver keeps its own committed
   log — NOT the raw probe log, which contains restored attempts).

### Knowledge base design

- Location (recommended): optional `worlds/<world>/episodes/answers.yaml`, following
  the loader's per-episode directory pattern; `--answers PATH` CLI override for
  world-independent files. World-level `world.yaml` extension is a valid alternative
  but mixes concerns (world config vs solver data).
- Shape: `passwords: [str]` (passage text-gate answers) and `riddle_answers: [str]`
  (free-text answers for riddle gates; today identical mechanics, distinct intent —
  the split documents the cultural-knowledge rationale and future hyper-edge riddles).
- Integration with `--episode`: answers are per-episode (macro-edge derivation is
  already per-episode; the answers file sits in the episode dir).
- Critical property: the engine contract "YAML data in Spanish, engine-agnostic"
  holds — the file is plain strings the solver never interprets.

### Completability verdict design

```python
@dataclass
class SolveVerdict:
    completable: bool
    episode: str
    walkthrough: list[str]            # committed-command evidence
    total_turns: int
    probe_count: int
    stuck_rooms: list[str]            # frontier with no progress
    unsatisfiable_gates: list[GateDiagnosis]  # passage + predicate + required + reason
    static_errors: list[Finding]      # from audit precondition (empty when audit clean)
```
`GateDiagnosis.reason` ∈ {answer_not_in_kb, item_unreachable, item_missing_from_world,
item_never_acquired, flag_never_set} — the world-defect vs solver-limit split the user
asked for, cross-referenced against `AuditReport` (rooms, passages, findings).

### CLI

`fortress-engine solve <world_path> [--episode ID] [--answers PATH] [--json]
[--max-turns N]` — exit 0 completable (walkthrough printed/JSON), 1 not completable
(diagnosis), 2 usage/load/episode errors. Mirrors `audit-graph` conventions and its
`cli-entry-point` spec rows (delta update).

---

## Testing strategy (hard gate >99% branch)

Fixture worlds via the established `tmp_path` + YAML-string builders
(`tests/test_autoplay/conftest.py` pattern):

- `solver_happy`: rooms + one item gate + one password gate + one flag gate (hyper
  edge setting the flag); goal flag at the end → solver completes; assert the exact
  walkthrough commands, verdict `completable`, exit 0.
- `solver_kb`: a text gate whose answer exists ONLY in `answers.yaml` — proves the
  KB file is loaded and brute-forced (data-driven, not just macro-edge derivation).
- `solver_retrieve`: key item found in a far room; assert the solver navigates
  there, takes it, returns, and opens the gate (the NEW backtracking step).
- `solver_unsolvable`: item gate whose item sits in an audit-unreachable room →
  verdict `not completable`, diagnosis `item_unreachable`; plus a flag gate never
  settable → `flag_never_set`. Proves stuck diagnosis, exit 1.
- Coverage: narrow `pyproject.toml` omit to `autoplay/explorer.py`; targeted run
  with the temp cov-config + dotted-module quirk (proven in Stage A). The solver's
  defensive branches (crash catch, guard) MUST be tested, not omitted.
- Integration: `_test_minimal` solves; fortaleza ep-1/ep-2 smoke — **never pin
  verdicts on the live world** (mid-rewrite: 100+ untracked YAML files, maza/arco
  rename leftovers in ep-2, unsatisfiable ep-2 carry_over per Stage A exploration).
- CLI tests mirror `tests/test_cli/test_audit_graph.py` (exit contract, JSON
  determinism, unknown episode → 2).

---

## Risks

- **World mid-rewrite**: the fortaleza world has 100+ untracked/modified YAML files
  on `feat/issue-41-walkthrough-l1`; solver verdicts on it are moving targets.
  Integration tests must not pin verdicts; commit must stage only solver files.
- **Cultural riddles**: KB completeness is a DATA question. A missing answer yields
  `answer_not_in_kb` by design — the diagnosis wording must be explicit that this is
  a knowledge-base gap, not proof of solver failure.
- **Search explosion**: verb×target×instrument probing on a 50-room world runs into
  tens of thousands of turns; needs the existing differential probing +
  MAX_PROBE_ITEMS + `--max-turns` guard; whole-project coverage run (~290s) gets a
  new measured module.
- **Engine limitation (out of scope)**: cliques have no spoken-text predicate, so
  hyper-edge riddles (`decir/responder X` setting a flag) cannot be modeled today;
  Stage B covers macro-edge text gates only. Do NOT attempt an engine change inside
  this change.
- **`restore()` private coupling**: `orch._state` rebinding is fragile; the solver
  must centralize state rebinding (one restore path), not copy the pattern ad hoc.
- **Coverage gate**: pyproject omit narrowing is mandatory for this change; without
  it the gate can pass while the solver is unmeasured (the exact Stage A follow-up
  that is still open).

---

## Ready for Proposal

**Yes.** Approach B is well-scoped, the machinery to reuse is proven, the seam from
Stage A is explicit (`AuditReport.passages` + `unreachable_rooms` seed the search and
the diagnosis), and the fixture strategy maps 1:1 to the user's requirements
(brute force with collected objects, preloaded answers, completability verdict with
walkthrough evidence or diagnosis). Tell the user: the answers file is NEW world data
they must curate (culture), and hyper-edge spoken riddles are out of scope (engine
limitation).
