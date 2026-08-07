"""GoalEvaluator — evaluate episode victory conditions against WorldState.

Follows goal-evaluator spec and tdd.md §4.5.
Entity-agnostic: no entity type constants or closed sets.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.entities.entity import GoalCondition, GoalConditions
    from fortress_engine.engine.state import WorldState


class GoalEvaluator:
    """Evaluate victory conditions without world-specific logic.

    Supports six atomic condition types plus recursive ``and``/``or``
    composition via nested dicts.
    """

    def __init__(self, conditions: GoalConditions) -> None:
        self._conditions = conditions

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def check(self, state: WorldState) -> bool:
        """Evaluate whether all victory conditions are satisfied.

        Each entry in ``conditions.conditions`` is either a
        :class:`GoalCondition` (evaluated atomically) or a composite dict
        (``{"and": [...]}`` or ``{"or": [...]}``).  All top-level entries
        must be true (implicit AND).
        """
        for item in self._conditions.conditions:
            if isinstance(item, dict):
                ok = self._evaluate_composite(item, state)
            else:
                ok = self._evaluate_condition(item, state)
            if not ok:
                return False
        return True

    # -------------------------------------------------------------------
    # Atomic conditions
    # -------------------------------------------------------------------

    def _evaluate_condition(
        self, condition: GoalCondition, state: WorldState
    ) -> bool:
        """Dispatch a single atomic condition to its handler."""
        ctype = condition.type
        params = condition.params

        if ctype == "entity_in_room":
            return self._eval_entity_in_room(params, state)
        elif ctype == "entity_not_in_room":
            return self._eval_entity_not_in_room(params, state)
        elif ctype == "entity_dead":
            return self._eval_entity_dead(params, state)
        elif ctype == "flag_is_set":
            return self._eval_flag_is_set(params, state)
        elif ctype == "flag_is_not_set":
            return self._eval_flag_is_not_set(params, state)
        elif ctype == "entity_has_component":
            return self._eval_entity_has_component(params, state)
        else:
            # Unknown condition type → false (spec: never silently pass)
            return False

    # -------------------------------------------------------------------
    # Composite
    # -------------------------------------------------------------------

    def _evaluate_composite(
        self, node: dict[str, Any], state: WorldState
    ) -> bool:
        """Evaluate a composite ``and``/``or`` node recursively."""
        for key, children in node.items():
            if key == "and":
                return all(self._evaluate_item(child, state) for child in children)
            elif key == "or":
                return any(self._evaluate_item(child, state) for child in children)
        # Unknown composite key → false
        return False

    def _evaluate_item(
        self, item: GoalCondition | dict[str, Any], state: WorldState
    ) -> bool:
        """Evaluate a single item (condition or sub-composite)."""
        if isinstance(item, dict):
            return self._evaluate_composite(item, state)
        return self._evaluate_condition(item, state)

    # -------------------------------------------------------------------
    # Per-type handlers
    # -------------------------------------------------------------------

    @staticmethod
    def _eval_entity_in_room(params: dict[str, Any], state: WorldState) -> bool:
        """entity's spatial_anchor == room."""
        entity_id = params.get("entity")
        room_id = params.get("room")
        if not state.entity_exists(entity_id):
            return False
        entity = state.get_entity(entity_id)
        return entity.spatial_anchor == room_id

    @staticmethod
    def _eval_entity_not_in_room(params: dict[str, Any], state: WorldState) -> bool:
        """entity's spatial_anchor != room (missing entity = not in room)."""
        entity_id = params.get("entity")
        room_id = params.get("room")
        if not state.entity_exists(entity_id):
            return True
        entity = state.get_entity(entity_id)
        return entity.spatial_anchor != room_id

    @staticmethod
    def _eval_entity_dead(params: dict[str, Any], state: WorldState) -> bool:
        """entity's spatial_anchor is None (destroyed/limbo)."""
        entity_id = params.get("entity")
        if not state.entity_exists(entity_id):
            return False
        entity = state.get_entity(entity_id)
        return entity.spatial_anchor is None

    @staticmethod
    def _eval_flag_is_set(params: dict[str, Any], state: WorldState) -> bool:
        """Flag exists and is True."""
        flag = params.get("flag", "")
        return state.get_flag(flag) is True

    @staticmethod
    def _eval_flag_is_not_set(params: dict[str, Any], state: WorldState) -> bool:
        """Flag is False or absent."""
        flag = params.get("flag", "")
        return state.get_flag(flag) is False

    @staticmethod
    def _eval_entity_has_component(
        params: dict[str, Any], state: WorldState
    ) -> bool:
        """entity.components[component] == value (raw equality)."""
        entity_id = params.get("entity")
        component_key = params.get("component")
        expected_value = params.get("value")
        if not state.entity_exists(entity_id):
            return False
        entity = state.get_entity(entity_id)
        actual = entity.components.get(component_key)
        if actual is None and component_key not in entity.components:
            return False
        return actual == expected_value

    # -------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------

    @property
    def output(self) -> str:
        """Victory text displayed when the goal is met."""
        return self._conditions.output

    @property
    def side_effects(self) -> list[dict[str, Any]]:
        """Additional effects applied on goal completion."""
        return list(self._conditions.side_effects)
