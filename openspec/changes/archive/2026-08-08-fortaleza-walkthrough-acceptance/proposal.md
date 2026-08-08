# Proposal: Fortaleza Walkthrough Acceptance

## Intent

Issue #41 needs an end-to-end acceptance test for the real Fortaleza YAML world. The current test is vacuous: unresolved names/passwords keep the hero outside. This change proves both episodes and safe failures.

## Scope

### In Scope

- Curated data for Part I (129) and Part II (235): snake_case YAML passages, speech forms, decoded passwords, corrected 17/18 order, and compressed labyrinth routes. The walkthrough supplies order, not parsing.
- Fix world/fixture data: repair five placeholder sites (four text values plus `key[3]` → Ariete for `he_romper_pared_solaria`, no text gate), add `abrir`, inject world vocabulary, re-anchor `antorcha_3`, and use player weight 40. Preserve `crunch`/center weapons; document divergences.
- Original Part II model: Hacha breaks `arbol_de_marfil`; TRANSFER creates Maza (37), `he_romper_muralla` uses it, and `muralla` moves to `otra_orilla_del_rio_negro`; `me_orilla2_jardines` requires `muralla_rota`. Marmidosa remains for Esfera, Carcelero, and Hechicero; Muralla 3 is a decoy.
- Per-anchor robustness tests cover invalid verbs/objects, bad passwords, and wrong weapons: exact `error_output`, no `GAME_OVER`, unchanged state, one `turn_ended`, and recovery. Test designed deaths only at fatal gates.
- Implement bidirectional expansion and open a follow-up issue whose tests close after this suite. Propose goal-evaluator swapping; implementation waits for design approval.

### Out of Scope

Verbatim parsing, original bugs/lore, episodes 3+, and unrelated CLI work.

## Capabilities

### New Capabilities
- `fortaleza-walkthrough-acceptance`: complete walkthrough and robustness contract.

### Modified Capabilities
- `dual-graph`: bidirectional edges MUST work in both directions.
- `goal-evaluator`: transition MUST evaluate the next episode’s goal (design-gated).

## Approach

Stacked-to-main slices: **L1** Part I; **L2** world/parser corrections; **L3** robustness; **L4** bidirectional engine plus issue; **L5** Part II and approved goal transition. Each slice stays green with state/event assertions.

## Affected Areas

`tests/test_integration/test_walkthrough.py`; `worlds/fortaleza/`; graph and episode-transition engine code; this change’s specs/design/tasks and follow-up issue.

## Risks

- 364 commands may exceed the 400-line review budget: retain five chained slices.
- Graph/episode fixes have broad blast radius: isolate tests and gate evaluator changes on design approval.
- Doc/YAML drift can recreate vacuous passes: require movement, inventory, goals, transition, and event counts.

## Rollback Plan

Revert chained slices in reverse order; revert world data independently. Do not modify original-source docs.

## Dependencies

Walkthrough, both explorations, Pascal evidence, GDD/TDD edge semantics, and current YAML.

## Success Criteria

- [ ] Both curated episodes reach `goal == True`, transition correctly, and avoid `GAME_OVER` canonically.
- [ ] Every turn emits exactly one `turn_ended`; movement and inventory progress are asserted.
- [ ] Robustness failures are controlled, state-preserving, and recoverable.
- [ ] Bidirectional follow-up issue closes; goal-swap approval precedes implementation.

## Open Questions

Empty — product decisions are resolved; only the goal-evaluator mechanism remains a design approval gate.
