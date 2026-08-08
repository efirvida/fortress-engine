# Exploration: fortaleza-walkthrough-acceptance

## Executive Summary

The walkthrough `docs/09-walkthrough.md` (364 extractable commands: 129 Part I + 235 Part II) is **not executable verbatim** against the current world: movement targets need snake_case passage names (`puerta_negra`), text-gated doors need the `ir <pasaje> diciendo <contraseña>` form (verb `abrir` is not a movement verb), 5 macro edges carry **literal unresolved password placeholders** (`password_key[2]`, `key[3]`, `key[14]`, `key[15]`, `key[42]`) — decodable from the original source as "Abrete Sesamo", "Ariete", "Nombus Rostomelaris", "Luz", "Agua" — and **bidirectional macro edges register only one direction** (return trips all fail). The existing `_PART1_COMMANDS` test passes **vacuously**: the hero never leaves the exterior; every command errors. Part II is additionally unwinnable as world stands (`he_romper_muralla` requires `marmidosa`, obtainable only later; no `maza` item exists in episode-02). The engine itself is robust to invalid input (controlled `error_output`, no crashes, GAME_OVER only via `player_dead` flag / fatal gates / quit), so the robustness battery the user wants is feasible. Multi-episode goal evaluation has an engine gap: the `GoalEvaluator` is never swapped on episode transition, so episode-02 can never complete.

## Current State

### The walkthrough doc (`docs/09-walkthrough.md`, 1170 lines)

- Two parts in code fences; commands are plain `verbo objeto [con instrumento]` / `ir <pasaje> [diciendo/respondiendo <texto>]` lines — extractable by regex (````\n(.*?)``` `` fences, filter non-command lines).
- **364 commands** (129 Part I, 235 Part II). Verb distribution: `ir` 112, `tomar` 79, `mirar` 68, `interrogar` 27, `dar` 25, `matar` 14, `romper` 13, `abrir` 11, `dejar` 11, `ver` 4.
- **Not directly parseable**: placeholders `[contraseña]` (paso 5, 15, 16, 28), `[contraseña del ciclope]`, `[objeto]` (paso 33 "romper pared solitaria con [objeto]"), `[viajar a R1]` / `[tomar bote en R11]` / `[ir a R12]` (pasos 66–73). Alternate routes in prose ("o más directo", "O volver por donde viniste"), optional steps ("OPCIONAL" paso 4).
- **Doc-internal order bug**: paso 17 "dar pocion para crecer a homunculo" runs BEFORE paso 18 where the pocion is obtained (R8).
- **Lore notes not modeled in the world**: pañuelo-in-cocina death at Goal() (nota 6), hija sin aguja = muerte instantánea (nota 7), 7 antorchas (paso 38).

### The world (`worlds/fortaleza/`)

- 2 episodes; episode-01 goal: 4 `centro_*_dead` flags + `troll_muerto` (`episodes/episode-01.yaml:8-26`); episode-02 goal: 7 `entity_in_room` + `monstruo_muerto` + `hija_muerta` (`episodes/episode-02.yaml`); carry_over both empty (clears all flags+inventory on transition).
- `shared/vocabulary.yaml`: canonical verbs `ver`, `preguntar`, `responder`…; `movement_verbs: [ir, atravesar, cruzar, pasar]` — **`abrir` excluded**.
- 45 macro edges per episode, snake_case `passage_name` (`puerta_negra`, `arteria_principal`), gates: `requires_text`, `requires_item`, `forbids_item`, `requires_flag`, `death_message` (fatal → GAME_OVER), `open`.
- Items/NPCs named close to the walkthrough (maza, pastel de cerezas, trébol…), resolution via partial-match "Equals" algorithm in `_resolve_phrase` (`classic_parser.py:303-361`).
- Episode-01 antorchas: only `antorcha` + `antorcha_3` (no antorcha 1/2/4/5/6/7). Episode-02 has NO `maza` item.

### The current test (`tests/test_integration/test_walkthrough.py`, 493 lines, uncommitted)

- `_FortalezaFixture` (lines 134-207): real `EntityLoader`, `create_parser`/`create_narrator` (classic/template), `distribute_hyper_edges_to_anchors`, TurnOrchestrator with vocabulary — good base.
- `_PART1_COMMANDS` (lines 417-464): 46 hardcoded doc-style commands (spaces, no passwords).
- 3 Fortaleza tests (lines 467-493) assert only: loads, `GAME_OVER not in events`, `goal_eval.check()` returns bool.
- **Verified vacuous**: executing `_PART1_COMMANDS` leaves the hero in `el_exterior_de_la_fortaleza` for all 46 commands — every movement/take fails with `error_output no_action` (only `tomar maza` + `tomar pastel de cerezas` succeed). No assertion checks movement, inventory, or goal==True.
- Fixture hardcodes hero `max_weight: 20` (line 166) — world `shared/player.yaml` says 40; with 20 the TRANSFER operator (weight gate at `operators.py:139-161`) rejects the maza (39).

### Engine behavior (verified by execution)

- `TurnOrchestrator.execute_turn` (`orchestrator.py:174`): unknown verb/target → `error_output no_action` (step 7); parser exceptions isolated → `parser_error`; blocked movement → `error_output blocked` (fatal only when `death_message`); operator failure → `operator_failed`; exactly one `turn_ended` on every path. GAME_OVER only from `player_dead` flag (steps 13/`_post_action_checks`), fatal macro gate, or quit.
- Movement resolution: `_resolve_movement` (`orchestrator.py:477`) requires `parsed.verb in movement_verbs` and **exact** `get_macro_edge_by_passage_name(anchor, parsed.target)` (`graph.py:264-274`). Parser returns raw phrase (`"puerta negra"`) when no entity matches; passage names are `"puerta_negra"` → mismatch → no_action.
- Text gates open via `ir <pasaje> diciendo <texto>` — `_handle_movement` passes `parsed.text` to `validate_macro_edge` (`graph.py:464-502`), which normalizes both sides (diacritics/case) and sets `edge.open = True` on match.
- `GoalEvaluator.check` (`goal_evaluator.py:30`): recursive and/or tree; `_evaluate_goal` (`orchestrator.py:423`) emits `episode_completed` + `transition_to_next`; the **evaluator instance is never swapped** — after transition it still checks episode-01 conditions against a cleared flag book → **episode-02 can never complete** (engine gap).
- `EntityLoader.validate_world` (`loader.py:561-636`): start_anchor existence, dangling `spatial_anchor`, duplicate (verb,target,priority). Does NOT check macro from/to anchors, hyper-edge entity references, goal condition entity refs, or passage-name conventions.

## Findings

### 1. Walkthrough format & parseability

- Commands are extractable (fences, 364 total) but the doc mixes: placeholders (`[contraseña]`, `[objeto]`, `[viajar a R1]`), alternates, an internal order bug (dar pocion before tomarla), and lore notes that don't match world behavior (pañuelo, hija, 7 antorchas).
- Verdict: a verbatim doc parser is NOT viable; a curated command script with the doc as source-of-truth is required (plus a small placeholder-resolution table).

### 2. Command ↔ YAML mismatches (concrete)

| # | Issue | Evidence |
|---|-------|----------|
| 1 | **Passage targets need snake_case**: walkthrough `ir puerta negra` vs passage `puerta_negra`; exact match in `get_macro_edge_by_passage_name` | `graph.py:264-274`; verified: `ir puerta_principal` → no_action, `ir puerta_principal` (underscore) → moves |
| 2 | **`abrir` not a movement verb** (world vocabulary `movement_verbs` lacks it) → all 11 `abrir X diciendo Y` fail; doors only open via `ir X diciendo Y` | `vocabulary.yaml:35`, `orchestrator.py:153-157`; verified |
| 3 | **Literal password placeholders in 5 macro edges**: `me_exterior_salon` (password_key[2]), `me_exterior_arana` (key[3]), `me_bailarina_enigma` (key[42]), `me_biblioteca_pasillo` (password_key[14]), `me_pasillo_laboratorio` (password_key[15]) — door opens only saying the literal token | verified: `ir puerta_principal diciendo password_key[2]` moves |
| 4 | **Decoded passwords exist** (FORT1.PAS key array, `DecodeLine` = byte−20): key[2]="Abrete Sesamo", key[3]="Ariete", key[14]="Nombus Rostomelaris", key[15]="Luz", key[42]="Agua" | `docs/original-source/FORT1.PAS:47-95` |
| 5 | **Bidirectional edges register one direction only**: 45 files → 45 edges; `direction` stored but never expanded; all return trips fail (`ir traquea` back, `ir puerta_azul` back…) | `loader.py:310-326`, `graph.py:245-254`; verified (hero stuck in `centro_de_los_pulmones`) |
| 6 | **Parser vocabulary wiring gap**: `create_parser` (`factory.py:117`) injects only language+options; world `vocabulary.yaml` goes only to the orchestrator → parser uses `DEFAULT_SPANISH_VOCABULARY` whose canonical verbs differ (`examinar` vs `ver`, `interrogar` vs `preguntar`) → all 4 `ver X` commands fail (parsed verb `examinar` ≠ edge verb `ver`); `interrogar` always hits the generic edge `he_interrogar_npc` (`he_otros.yaml:39-47`, verb "interrogar") and the 2 specific `preguntar` edges never fire | `classic_parser.py:28-54`; verified |
| 7 | **Part II deadlock**: `he_romper_muralla` requires instrument `marmidosa` (obtained at Cueva de Cristal, deep in the lake area) while the walkthrough breaks muralla 1 with `maza`; **no maza item exists in episode-02** (grep: zero hits); the árbol de marfil edge (`he_romper_arbol_de_marfil`) creates no item | `he_romper_ep2.yaml:22-58` |
| 8 | **Antorchas**: only `antorcha` + `antorcha_3` exist; `tomar antorcha 1/2/4/5/6/7` → no_action (harmless for the goal: cerebro needs `antorcha`, columna needs `antorcha_3`) | `items/antorcha*.yaml` |
| 9 | Walkthrough `matar troll` (no instrument) works despite clique `instrument: maza` — concrete clique instruments only check inventory presence, parsed instrument is ignored | `graph.py:425-434` |
| 10 | Generic fallback edges use **non-canonical verbs** (`asesinar`, `destrozar`, `forzar`, `coger`, `regalar`, `leer`, `observar`, `soltar`, `terminar`) → dead code; parser canonicalizes input, so fallbacks never fire | verb counts across `actions/*.yaml` |
| 11 | Fixture/CLI hero hardcodes `max_weight: 20` vs world player `40`; both also ignore the world player entity | `test_walkthrough.py:166`, `cli/main.py:103`, `shared/player.yaml` |
| 12 | Death notes (pañuelo en cocina al evaluar Goal; hija sin aguja = muerte) are **not modeled** in the world; only `me_pasillo_cocina` requires_item panuelo + death_message (death entering the kitchen, not leaving the pañuelo) | `me_pasillo_cocina.yaml:8-9`, `he_matar_ep2.yaml:31-43` |

### 3. Current test state

- Exists: `_FortalezaFixture`, 3 vacuous tests (loads / no game_over / goal evaluable), hardcoded `_PART1_COMMANDS` (doc-style, spaces).
- Missing: doc-parsing or curated sequence, any movement/inventory assertion, Part II, episode transition, `goal == True` assert, invalid-input robustness, exact `turn_ended` counts.

### 4. Engine behavior on invalid input (robustness base)

- All failure paths are controlled: `no_action` (no edge/clique), `blocked` (non-fatal gate), `operator_failed` (e.g. weight), `parser_error`. No exceptions escape; one `turn_ended` per turn. GAME_OVER only via `player_dead` flag, fatal gate (`death_message`), or quit.
- Death mechanics: `player_dead` FLAG set by `he_abandonar` edges (`he_otros.yaml:20-24`) or fatal macro gates (`me_*` with `death_message`).

### 5. Robustness gaps (user's extra requirement)

- The engine already survives invalid commands; what's missing is TEST COVERAGE: per-anchor battery of (a) unknown verb (`xyzzy`), (b) valid verb + object not in room (`tomar espada` in exterior), (c) valid verb + nonexistent object, (d) wrong password on a gated door, (e) wrong weapon on a guard — assert: `error_output` emitted, no `game_over`, state unchanged (snapshot compare), subsequent canonical commands still work.
- "Unprojected story paths": the fatal gates ARE projected paths (designed deaths) — the test should assert known deaths happen exactly where designed and NOT on the canonical path; and that no state corruption (partial operator application) occurs after failures.
- Known world-level robustness defects the battery will expose: bidirectional gap (soft-lock in cocina/orilla), Part II muralla deadlock.

## Affected Areas

- `tests/test_integration/test_walkthrough.py` — main deliverable (rewrite of `_FortalezaFixture` + new tests).
- `worlds/fortaleza/episode-01/macros/me_exterior_salon.yaml`, `me_exterior_arana.yaml`, `me_bailarina_enigma.yaml`, `me_biblioteca_pasillo.yaml`, `me_pasillo_laboratorio.yaml` — placeholder passwords → decoded values (YAML fix, allowed in situ).
- `worlds/fortaleza/shared/vocabulary.yaml` — add `abrir` to `movement_verbs` (YAML fix, allowed in situ).
- `worlds/fortaleza/episode-02/` — muralla/maza model (arbol → maza transfer; `he_romper_muralla` instrument) — YAML fix, needs user confirmation on intent.
- `worlds/fortaleza/episode-01/macros/` (45 files) or engine — bidirectional expansion decision (engine-level → propose).
- `src/fortress_engine/plugins/factory.py` / fixture wiring — parser must receive the world vocabulary (wiring fix).
- `src/fortress_engine/engine/orchestrator.py` + `episode_manager.py` — goal evaluator swap on transition (engine gap → propose).

## Approaches

1. **Curated canonical script + robustness battery (recommended)**
   - A corrected command list derived from the walkthrough (snake_case passages, `ir X diciendo Y`, decoded passwords, resolved placeholders, fixed order) executed through the fixture; assert goal==True at end of Part I, transition to episode-02, Part II completion, no game_over, exactly one turn_ended per turn.
   - Plus the per-anchor invalid-command battery described above.
   - World-data fixes in situ (passwords, movement vocabulary, wiring, player weight). Engine-level fixes (bidirectional, goal swap) proposed, not applied.
   - Pros: honest acceptance signal; satisfies user's robustness requirement; bounded scope; vacuous-pass eliminated.
   - Cons: the command list is curated, not auto-parsed from the doc (doc has placeholders/alternates/order bugs making verbatim parsing impossible); the "7 antorchas" and Part II muralla decisions need user input.
   - Effort: High (world fixes + test + decisions).

2. **Fix world data first, then parse the doc verbatim**
   - Repair all YAML gaps (passwords, bidirectional twin files, maza/muralla, antorchas 1-7, movement verbs, parser wiring), then write a doc extractor (fences + placeholder resolution table) and execute all 364 commands.
   - Pros: maximal fidelity to the issue text ("extract ALL commands").
   - Cons: 45 macro files × 2 directions churn; doc alternates/order bugs still need a resolution table; still requires the engine goal-swap fix; largest diff (review guard risk).
   - Effort: Very High.

3. **Engine normalization + world fixes**
   - Add space↔underscore normalization in `get_macro_edge_by_passage_name`, `abrir` in default movement verbs, bidirectional expansion in `build_macro_graph`, goal-evaluator swap in `_evaluate_goal`/`transition_to_next`.
   - Pros: fixes root causes; walkthrough-style commands work as documented.
   - Cons: touches engine hot path (violates "don't modify engine without proposing"); needs user approval; bigger blast radius (72 `execute_turn` callers).
   - Effort: High (engine) + High (world/test).

## Recommendation

Approach 1, with this sequencing:
1. **Propose (sdd-propose)**: frame the change as "acceptance test + world-data corrections", explicitly flagging the two engine-level gaps (bidirectional macro edges; goal-evaluator swap on transition) and the Part II muralla/maza intent question for user decision.
2. In the change: fix YAML in situ (5 passwords, `abrir` in movement_verbs, parser-vocabulary wiring, hero max_weight 40 / world player entity), then rewrite the fixture + curated script + robustness battery.
3. Engine gaps: only implement after the user picks a direction (bidirectional: twin YAML files vs engine expansion; goal: evaluator swap vs orchestrator reads current episode goal).

## Risks

- **Scope creep**: 364-command walkthrough + world repairs could exceed the 400-line PR budget → chain the change (test skeleton → world data fixes → robustness battery).
- **Part II muralla/marmidosa deadlock** may be an intentional redesign of the original game — needs user confirmation before "fixing" it to match the walkthrough.
- **Vacuous-pass regression**: current tests pass without moving; new tests MUST assert state progress (anchor changes, inventory, goal==True), not just absence of game_over.
- **Doc↔world drift**: the walkthrough documents the ORIGINAL game; the YAML world deliberately diverges in places (marmidosa, antorchas) — the curated script must be the contract, and the doc should eventually be annotated.
- **Engine fixes** (bidirectional, goal swap) are architecture-adjacent: must be proposed and approved before touching engine code.
- **Password decoding** ("Abrete Sesamo" etc.) derives from the original Pascal source (byte−20 cipher) — acceptable as world-data ground truth, but note it in the proposal.

## Ready for Proposal

Yes — with the user decision on: (a) Part II muralla/maza intent, (b) bidirectional edges (world twin files vs engine expansion), (c) goal-evaluator swap (engine change), (d) delivery strategy for a potentially >400-line change.
