# Goal Evaluator — Episode handoff (delta)

## Purpose

Bind the next episode's `GoalEvaluator` after a transition so each episode is evaluated against its own goal conditions, making the final `game_completed` reachable after the Part II ritual.

## MODIFIED Requirements

### Requirement: Design-gated evaluator handoff

The design MUST propose binding the next episode's `GoalEvaluator`; implementation MAY occur only after explicit design approval. After approval, the next episode MUST evaluate its own goal before final completion.

#### Scenario: Approved handoff
- **GIVEN** Part I is complete and design is approved
- **WHEN** episode-02 starts and its ritual completes
- **THEN** episode-02's goal, not episode-01's, becomes `True` and final completion is emitted

#### Scenario: Pre-transition completion stays canonical
- **GIVEN** Part I is being completed
- **WHEN** the episode-completion event is evaluated
- **THEN** episode-01's goal still evaluates `True` and the transition fires before any Part II evaluation
