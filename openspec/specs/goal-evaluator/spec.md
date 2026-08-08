# Goal Evaluator Specification

## Purpose

Evaluate episode victory conditions against current `WorldState` without world-specific logic.

## Requirements

### Requirement: Six atomic conditions

`GoalEvaluator(conditions: GoalConditions)` SHALL expose `check(state) -> bool`, `_evaluate_condition`, `_evaluate_composite`, `output`, and `side_effects`. It SHALL support `entity_in_room`, `entity_not_in_room`, `entity_dead`, `flag_is_set`, `flag_is_not_set`, and `entity_has_component`.

#### Scenario: Evaluate location and death

- GIVEN an entity in `room-2` and another with `spatial_anchor=None`
- WHEN goals require `entity_in_room` for the first and `entity_dead` for the second
- THEN `check` returns true

#### Scenario: Missing flag is not set

- GIVEN a goal containing `flag_is_not_set("secret")` and no such flag
- WHEN `check` runs
- THEN it returns true

### Requirement: Recursive composition

The evaluator SHALL recursively support dictionaries `{ "and": [...] }` and `{ "or": [...] }`, including nested mixtures, and SHALL compare component values with raw `==`.

#### Scenario: Nested boolean goal

- GIVEN an `and` containing one true condition and an `or` containing a second true alternative
- WHEN `check` runs
- THEN it returns true

### Requirement: Episode handoff

The design MUST bind the next episode's `GoalEvaluator` after a transition; after approval, the next episode MUST evaluate its own goal before final completion. `EpisodeManager.goal_evaluator_for(episode_id) -> GoalEvaluator` SHALL return a fresh evaluator bound to that episode's goal, and the orchestrator SHALL rebind it after `transition_to_next()`.

#### Scenario: Approved handoff

- GIVEN Part I is complete and design is approved
- WHEN episode-02 starts and its ritual completes
- THEN episode-02's goal, not episode-01's, becomes `True` and final completion is emitted

#### Scenario: Pre-transition completion stays canonical

- GIVEN Part I is being completed
- WHEN the episode-completion event is evaluated
- THEN episode-01's goal still evaluates `True` and the transition fires before any Part II evaluation

## Contract notes

`GoalCondition` has `type: str` and `params: dict[str, Any]`. `GoalConditions` has `conditions`, `output`, and `side_effects: list[dict] = []`.

`GoalConditions` contains `conditions`, `output`, and `side_effects` (default empty list). Unknown entity IDs SHALL evaluate false rather than satisfy a goal.
