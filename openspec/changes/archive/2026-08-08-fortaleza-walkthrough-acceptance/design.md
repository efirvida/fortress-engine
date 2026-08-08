# Design: Fortaleza Walkthrough Acceptance

## 1. Context and objectives

The current fixture is vacuous: unresolved names/passwords leave the protagonist at the exterior. The acceptance test will prove 129 curated Part-I commands, 235 Part-II commands, progress, both goals, transition, safe failures, and one `turn_ended` per turn. The walkthrough supplies order, never parser input.

## 2. Architecture decisions (ADRs)

| Capability | Choice | Rejected | Evidence / rationale |
|---|---|---|---|
| Script/vocabulary | Curated YAML-ID rows inject `Vocabulary` through `PluginConfig.options`. | Verbatim parsing; engine space/underscore normalization. | Exact lookup is `orchestrator.py:477-489`; `factory.py:117-143` already forwards options. |
| Bidirectionality | `EntityLoader.load_macro_edges()` uses `dataclasses.replace` for a deduplicated reverse. | Twin YAML files; expansion in `graph.add_macro_edge()` (larger runtime blast radius). | TDD:198/GDD:261 specify `direction`; `loader.py:310-326` and `graph.py:201-254` ignore it. HyperEdges remain untouched. |
| Goal handoff | Add `EpisodeManager.goal_evaluator_for(id)` and rebind after transition. | Returning `(graph,evaluator)`; parser/factory ownership. | The gap is `orchestrator.py:423-471`; episode definitions already belong to `episode_manager.py:145-221`. **Approval gate: do not implement until the user approves this design.** |

## 3. Detailed design

**Curated data.** `test_walkthrough.py` stores immutable rows: `episode, anchor_before, verb, target, instrument, spoken_text, yaml_ref, expected`. Movement targets are exact snake_case `passage_name`; action values are entity IDs. Rows assert referenced edge, destination, events, inventory/flags, goal, or episode. Passwords are decoded; order 17/18 is corrected and the labyrinth uses YAML routes. No document extraction occurs.

**Concrete world corrections.**

| File | Change |
|---|---|
| `episode-01/macros/me_exterior_salon.yaml` | `requires_text: Abrete Sesamo`. |
| `episode-01/macros/me_biblioteca_pasillo.yaml` | `requires_text: Nombus Rostomelaris`. |
| `episode-01/macros/me_pasillo_laboratorio.yaml` | `requires_text: Luz`. |
| `episode-01/macros/me_bailarina_enigma.yaml` | `requires_text: Agua` (the intentional value behind original `key[42]/43/45`). |
| `episode-01/macros/me_exterior_arana.yaml` | Remove spurious `requires_text`; set `open: true`, retain `requires_item: antorcha` for the secret passage. `Ariete` is an instrument, not a text gate. |
| `shared/vocabulary.yaml`; fixture/`cli/main.py` | Add `abrir`; inject `Vocabulary`; use loaded player capacity 40, not hardcoded 20. |
| `episode-01/actions/he_romper.yaml`, `actions/he_tomar.yaml`, new `items/ariete.yaml` | `he_romper_pared_solaria` uses `ariete`; add the 30-weight Ariete in `sala_de_armas` and its transfer edge. |
| `episode-01/items/antorcha_3.yaml`, `actions/he_tomar.yaml` | Re-anchor to `sala_del_minotauro`; add its transfer edge for the take/return/break route. |
| `episode-02/actions/he_romper_ep2.yaml`, `actions/he_tomar_ep2.yaml`, new `items/maza.yaml` | Tree break transfers limbo Maza (37) to the garden; add take-Maza; muralla uses it, then transfers to `otra_orilla_del_rio_negro` and sets `muralla_rota`. |
| `episode-02/macros/me_orilla2_jardines.yaml` | Add `requires_flag: muralla_rota`; keep initial `muralla` in the garden. Preserve `marmidosa` for esfera/carcelero/hechicero. |
| `episodes/episode-01.yaml`, `episode-02.yaml` | Flatten `type: and` into supported top-level atomic conditions (implicit AND; `loader.py:238-253`, `goal_evaluator.py:30-45`). |

`docs/fortaleza-walkthrough-divergences.md` records Agua/key indexing, `crunch` vs `Rumpelstinskin`, center weapons, bone-vs-Maza mirror, bed, torch placement/count, and Muralla 3 decoy.

**Bidirectional logic.** `load_macro_edges()` returns declared edges plus reverse dataclass copies (swapped anchors, generated ID, predicates/outcomes/open copied); an existing reverse key is skipped. `unidirectional` remains single-sided. Graph construction and HyperEdge distribution stay unchanged. A test crosses/returns and verifies no reverse for unidirectional input.

**Goal evaluator.** Add `EpisodeManager.goal_evaluator_for(id) -> GoalEvaluator`. After `transition_to_next()` returns, `_evaluate_goal` assigns `_graph` and the evaluator for `state.current_episode_id`. The completion event uses episode 01 before transition; the next turn uses episode 02. Test final `game_completed` only after the Part-II ritual.

**Robustness matrix.** Each anchor has `(command, expected_code, exact_data, fatal, recovery_row)` for unknown verb, wrong-room/nonexistent object, wrong password (`blocked`/`text_closed`), and non-fatal wrong weapon. Snapshot entities, anchors, flags, and gate state; only `turn_number` may differ. Assert no `GAME_OVER`, one `TURN_ENDED`, then recovery. Fatal rows are isolated to documented `death_message` passages.

## 4. Sequence diagrams

```text
turn -> _evaluate_goal(ep1) -> episode_completed -> transition_to_next
     -> start_episode(ep2) -> state.current_episode_id=ep2
     -> bind goal_evaluator_for(ep2) -> next turn checks ep2 -> game_completed
```

```text
YAML A->B (bidirectional) -> loader: declared + reverse B->A
                         -> graph.build_macro_graph -> indexes A and B
                         -> movement A->B / B->A; unidirectional stays A only
```

## 5. Impact and blast radius

Primary files are loader, `episode_manager.py`, `orchestrator.py`, `test_walkthrough.py`, Fortaleza YAML, and divergence docs. `execute_turn` has roughly 72 CLI callers; graph, episode-manager, orchestrator/plugin, CLI-builder, and walkthrough tests can observe graph counts, verbs, capacity, and evaluator state. Factory/parser need contract tests, not redesign.

## 6. Implementation order

L1 fixture plus curated Part I; L2 YAML, vocabulary/parser wiring, capacity, and goal-shape corrections; L3 per-anchor robustness and divergence doc; L4 loader expansion, round-trip test, and follow-up issue; L5 Part II world/script. **Apply the goal-evaluator slice only after explicit approval of this design.**

## 7. Risks and mitigations

The 364-row fixture may exceed 400 review lines: retain chained L1–L5 slices. Dedupe reverse edges and assert predicate parity. Because `open` is copied, gated round-trip tests verify equivalent blocking/unlocking, not shared identity. Validate goal shape during load. Threat matrix: N/A—no routing, shell, subprocess, VCS, or executable boundary.
