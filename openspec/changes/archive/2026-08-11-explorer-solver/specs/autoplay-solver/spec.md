# Autoplay Solver Specification

## Purpose

Stage B SHALL prove an episode completable, returning walkthrough evidence or diagnosis. This tool is outside 36-task `docs/tdd.md` roadmap.

## Requirements

### Requirement: Typed solve verdicts

The solver SHALL expose dataclasses `SolveVerdict` (`completable`, `episode`, `walkthrough`, `total_turns`, `probe_count`, `stuck_rooms`, `unsatisfiable_gates`, `static_errors`) and `GateDiagnosis` (`passage`, `predicate`, `required`, `reason`). `reason` MUST be one of `answer_not_in_kb`, `item_unreachable`, `item_missing_from_world`, `item_never_acquired`, or `flag_never_set`.

#### Scenario: Result shape
- GIVEN a selected episode reaches its goal or fixed point
- WHEN solving finishes
- THEN the verdict contains the declared fields and typed gate reasons only

### Requirement: Audit is a precondition

The solver SHALL run `GraphAudit` first. With zero `ERROR` findings it SHALL proceed; with any `ERROR`, it MUST stop and return `completable == false` with those findings in `static_errors`, as diagnosis rather than solver failure.

#### Scenario: Audit controls execution
- GIVEN `GraphAudit` reports zero `ERROR` findings or reports an `ERROR`
- WHEN the solver starts
- THEN zero errors begin the walk, while any error prevents play and populates `static_errors`

### Requirement: Episode answer knowledge

The solver MUST derive every selected-episode macro-edge `requires_text` value (the answer, not `question` prose), then merge `passwords` and `riddle_answers` plain strings from optional `episodes/answers.yaml`; `--answers PATH` MUST replace that file. It MUST try answers through the world's movement verb and speech preposition without language-specific literals.

#### Scenario: Derived and curated answers open a passage
- GIVEN a text-gated passage and an answer only in selected answers file
- WHEN the solver walks the passage frontier
- THEN it uses world vocabulary to try that answer and can commit the crossing

### Requirement: Audit-guided incremental walk

The solver MUST BFS audit `reachable_rooms`: take present items, differentially probe verb/target/instrument combinations with snapshot/restore, then brute-force movement with the knowledge base. It MUST keep only positive progress, check the goal after every committed change including crossings, boundedly revisit blocked rooms when the progress signature changes, and set `walkthrough` to the ordered committed-command log with restored probes excluded.

#### Scenario: Happy path preserves order
- GIVEN a synthetic episode with item, text, and flag gates
- WHEN solving reaches the goal
- THEN the result is completable and the walkthrough is the deterministic committed order

### Requirement: Key-retrieval backtracking

When `requires_item` blocks a passage and the item is not carried, the solver MUST navigate through discovered crossings to the item's found room, take it, return, and retry. Each attempt MUST be bounded and snapshot-safe so the solver never remains stranded.

#### Scenario: Far key is retrieved
- GIVEN the required key is in another reachable room
- WHEN the gate blocks the current frontier
- THEN the solver returns with the key and retries the passage

### Requirement: Fixed-point diagnosis

At a fixed point, every blocked required gate MUST produce an audit-cross-referenced `GateDiagnosis`. Missing text answers map to `answer_not_in_kb`; missing, unreachable, and unacquired items map to `item_missing_from_world`, `item_unreachable`, and `item_never_acquired`; missing flags map to `flag_never_set`. A missing answer MUST identify a knowledge-base gap, not solver failure.

#### Scenario: Unsolvable gates are distinguished
- GIVEN an item is in an audit-unreachable room and a required flag is never set
- WHEN no committed progress remains
- THEN diagnoses contain `item_unreachable` and `flag_never_set` for their passages

### Requirement: World-agnostic bounded verification

The solver MUST read verbs, movement verbs, speech prepositions, targets, and vocabulary from the world. `--max-turns` MUST bound search (default `50_000`). Strict synthetic tests SHALL cover `solver_happy` with an exact walkthrough and exit 0, `solver_kb` with an answer only in `answers.yaml`, `solver_retrieve`, and `solver_unsolvable` with `item_unreachable` plus `flag_never_set`; CLI tests SHALL mirror `test_audit_graph.py` and `test_validate.py`, Fortaleza smoke SHALL not pin verdicts, branch coverage MUST exceed 99%, and `pyproject.toml` MUST omit only `autoplay/explorer.py`.

#### Scenario: Bounds and language remain external
- GIVEN a non-Spanish vocabulary and a low turn limit
- WHEN solving exceeds the limit
- THEN it stops deterministically without hardcoded commands and reports a non-completable diagnosis
