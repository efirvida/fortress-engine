"""Atomic operators — five pure functions that mutate WorldState.

Follows atomic-operators spec and tdd.md §4.3.

Operators are bus-free: they return OperatorResult with events_payload that
the TurnOrchestrator converts into state-change EngineEvents.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Union, TYPE_CHECKING

from fortress_engine.engine.state import LIMBO_ROOM_ID, WorldState
from fortress_engine.entities.components import WEIGHT, MAX_WEIGHT

if TYPE_CHECKING:
    from fortress_engine.engine.graph import DualGraphEngine


# ---------------------------------------------------------------------------
# Operator dataclasses (tdd.md §3.4)
# ---------------------------------------------------------------------------

@dataclass
class TransferOp:
    """TRANSFER: move an entity between containers."""
    type: str = "TRANSFER"
    entity: str = ""
    from_container: str | None = None
    to_container: str | None = None


@dataclass
class TransformOp:
    """TRANSFORM: change a component of an entity."""
    type: str = "TRANSFORM"
    entity: str = ""
    component: str = ""
    old_value: Any = None
    new_value: Any = None


@dataclass
class CombineOp:
    """COMBINE: destroy inputs, produce output."""
    type: str = "COMBINE"
    input_entities: list[str] | None = None
    output_entity: str = ""

    def __post_init__(self) -> None:
        if self.input_entities is None:
            self.input_entities = []


@dataclass
class FlagOp:
    """FLAG: set a global flag."""
    type: str = "FLAG"
    flag: str = ""
    value: bool = False


@dataclass
class TeleportOp:
    """TELEPORT: change spatial anchor."""
    type: str = "TELEPORT"
    entity: str = ""
    from_anchor: str | None = None
    to_anchor: str = ""


Operator = Union[TransferOp, TransformOp, CombineOp, FlagOp, TeleportOp]


# ---------------------------------------------------------------------------
# OperatorResult
# ---------------------------------------------------------------------------

@dataclass
class OperatorResult:
    """Returned by every execute_* function.

    Attributes:
        success: Whether the operator executed successfully.
        error_message: Human-readable error description on failure.
        events_payload: Dict payload for state-change EngineEvent (see
            13-event-system.md §2.3).  ``None`` on failure.
    """
    success: bool
    error_message: str | None = None
    events_payload: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Error message constants (PRD §4.4)
# ---------------------------------------------------------------------------

_MSG_NOT_PORTABLE: str = "Usted no puede cargar con eso."
_MSG_TOO_HEAVY: str = "Sería demasiado peso."


# ===================================================================
# TRANSFER (tdd.md §4.3)
# ===================================================================

def execute_transfer(
    state: WorldState, op: TransferOp, protagonist_id: str
) -> OperatorResult:
    """Move *op.entity* from *op.from_container* to *op.to_container*.

    Weight validation is applied **only** when the destination is the active
    protagonist's inventory.  Other containers are unrestricted.
    """
    entity_id = op.entity
    to_container = op.to_container

    if not state.entity_exists(entity_id):
        return OperatorResult(
            success=False,
            error_message=f"Entity '{entity_id}' not found",
        )

    entity = state.get_entity(entity_id)

    # --- container validation --------------------------------------
    if (
        op.from_container is not None
        and entity.spatial_anchor != op.from_container
    ):
        return OperatorResult(
            success=False,
            error_message=(
                f"Entity '{entity_id}' is not in container "
                f"'{op.from_container}'"
            ),
        )

    if to_container is not None and not state.entity_exists(to_container):
        return OperatorResult(
            success=False,
            error_message=f"Container '{to_container}' not found",
        )

    # --- weight / portability validation (protagonist inventory only) ---
    if to_container is not None and to_container == protagonist_id:
        # Non-portable check: 'portable' defaults to True (GDD 2.3).
        if entity.components.get("portable", True) is False:
            return OperatorResult(
                success=False,
                error_message=_MSG_NOT_PORTABLE,
            )

        item_weight: int = entity.components.get(WEIGHT, 0)

        protagonist = state.get_entity(protagonist_id)
        max_capacity: int = protagonist.components.get(MAX_WEIGHT, 40)

        # Individual weight exceeds max capacity.
        if item_weight > max_capacity:
            return OperatorResult(
                success=False,
                error_message=_MSG_NOT_PORTABLE,
            )

        # Inventory capacity check.
        current_weight = state.get_inventory_weight(protagonist_id)
        if current_weight + item_weight > max_capacity:
            return OperatorResult(
                success=False,
                error_message=_MSG_TOO_HEAVY,
            )

    # --- apply mutation ---
    entity.spatial_anchor = to_container

    return OperatorResult(
        success=True,
        events_payload={
            "entity_id": entity_id,
            "from_container_id": op.from_container,
            "to_container_id": to_container,
        },
    )


# ===================================================================
# TRANSFORM (tdd.md §4.3)
# ===================================================================

def execute_transform(
    state: WorldState, op: TransformOp
) -> OperatorResult:
    """Change *op.component* from *op.old_value* to *op.new_value*.

    Fails if the entity does not exist or the current component value does not
    match *op.old_value*.
    """
    entity_id = op.entity

    if not state.entity_exists(entity_id):
        return OperatorResult(
            success=False,
            error_message=f"Entity '{entity_id}' not found",
        )

    entity = state.get_entity(entity_id)
    current_value = entity.components.get(op.component)

    if current_value != op.old_value:
        return OperatorResult(
            success=False,
            error_message=(
                f"Transform on '{entity_id}': expected component "
                f"'{op.component}' to be {op.old_value!r}, "
                f"got {current_value!r}"
            ),
        )

    entity.components[op.component] = op.new_value

    return OperatorResult(
        success=True,
        events_payload={
            "entity_id": entity_id,
            "component_key": op.component,
            "old_value": op.old_value,
            "new_value": op.new_value,
        },
    )


# ===================================================================
# COMBINE (tdd.md §4.3)
# ===================================================================

def execute_combine(
    state: WorldState, op: CombineOp, anchor_id: str
) -> OperatorResult:
    """Destroy *op.input_entities* and anchor *op.output_entity* at *anchor_id*.

    All input entities and the output entity must exist.
    """
    # Validate all inputs exist.
    for eid in op.input_entities:
        if not state.entity_exists(eid):
            return OperatorResult(
                success=False,
                error_message=f"Combine: input entity '{eid}' not found",
            )

    # Validate output entity exists.
    if not state.entity_exists(op.output_entity):
        return OperatorResult(
            success=False,
            error_message=(
                f"Combine: output entity '{op.output_entity}' not found"
            ),
        )

    # Destroy inputs.
    for eid in op.input_entities:
        state.get_entity(eid).spatial_anchor = None

    # Anchor output.
    state.get_entity(op.output_entity).spatial_anchor = anchor_id

    return OperatorResult(
        success=True,
        events_payload={
            "input_entity_ids": list(op.input_entities),
            "output_entity_id": op.output_entity,
        },
    )


# ===================================================================
# FLAG (tdd.md §4.3)
# ===================================================================

def execute_flag(state: WorldState, op: FlagOp) -> OperatorResult:
    """Set *op.flag* to *op.value*. Always succeeds."""
    old_value = state.get_flag(op.flag)
    state.set_flag(op.flag, op.value)

    return OperatorResult(
        success=True,
        events_payload={
            "flag_name": op.flag,
            "old_value": old_value,
            "new_value": op.value,
        },
    )


# ===================================================================
# TELEPORT (tdd.md §4.3)
# ===================================================================

def execute_teleport(state: WorldState, op: TeleportOp) -> OperatorResult:
    """Change *op.entity*'s spatial_anchor to *op.to_anchor*.

    Fails if the entity or the destination anchor does not exist.
    """
    if not state.entity_exists(op.entity):
        return OperatorResult(
            success=False,
            error_message=f"Teleport: entity '{op.entity}' not found",
        )

    if not state.entity_exists(op.to_anchor):
        return OperatorResult(
            success=False,
            error_message=f"Teleport: destination anchor '{op.to_anchor}' not found",
        )

    entity = state.get_entity(op.entity)
    entity.spatial_anchor = op.to_anchor

    return OperatorResult(
        success=True,
        events_payload={
            "entity_id": op.entity,
            "from_anchor_id": op.from_anchor,
            "to_anchor_id": op.to_anchor,
        },
    )


# ===================================================================
# Factory & dispatcher
# ===================================================================

_OP_TO_CLASS: dict[str, type] = {
    "TRANSFER": TransferOp,
    "TRANSFORM": TransformOp,
    "COMBINE": CombineOp,
    "FLAG": FlagOp,
    "TELEPORT": TeleportOp,
}


def operator_from_dict(data: dict[str, Any]) -> Operator:
    """Convert a plain dict to the corresponding operator dataclass.

    The ``type`` key determines which class is instantiated.

    Raises:
        ValueError: If ``type`` is missing/unknown, or *data* contains a key
            that is not a field of the selected operator class.
    """
    op_type = data.get("type")
    cls = _OP_TO_CLASS.get(op_type)
    if cls is None:
        raise ValueError(f"Unknown operator type: {op_type!r}")

    allowed_keys = {f.name for f in fields(cls)}
    for key in data:
        if key not in allowed_keys:
            raise ValueError(
                f"Unknown key {key!r} for operator type {op_type!r}"
            )

    kwargs: dict[str, Any] = {
        k: v for k, v in data.items() if k != "type"
    }

    return cls(**kwargs)  # type: ignore[call-arg]


def execute_operator(
    state: WorldState,
    op_data: dict[str, Any],
    protagonist_id: str,
    graph: DualGraphEngine | None,
) -> OperatorResult:
    """Dispatch *op_data* to the matching ``execute_*`` function.

    Args:
        state: The current world state (mutated on success).
        op_data: Plain dict with at least ``"type"``.
        protagonist_id: Needed for TRANSFER weight validation.
        graph: Optional dual-graph — reserved for future room-level
               validation directly from the graph.

    Returns:
        OperatorResult with ``success=True`` and a state-change payload, or
        ``success=False`` with an error message.
    """
    op_type = op_data.get("type", "")

    if op_type not in _OP_TO_CLASS:
        return OperatorResult(
            success=False,
            error_message=f"Unknown operator type: {op_type!r}",
        )

    op = operator_from_dict(op_data)

    if isinstance(op, TransferOp):
        return execute_transfer(state, op, protagonist_id)
    elif isinstance(op, TransformOp):
        return execute_transform(state, op)
    elif isinstance(op, CombineOp):
        # Derive anchor_id from the active protagonist's location.
        if not state.entity_exists(protagonist_id):
            return OperatorResult(
                success=False,
                error_message=f"Entity '{protagonist_id}' not found",
            )
        anchor_id = state.get_entity(protagonist_id).spatial_anchor
        if anchor_id is None:
            anchor_id = LIMBO_ROOM_ID
        return execute_combine(state, op, anchor_id)
    elif isinstance(op, FlagOp):
        return execute_flag(state, op)
    elif isinstance(op, TeleportOp):
        return execute_teleport(state, op)
    else:
        # Unreachable by construction: op_type was validated against
        # _OP_TO_CLASS above and operator_from_dict returns exactly one of
        # the five operator classes this isinstance chain covers.
        # Kept as a defensive fallback; excluded from coverage with
        # justification (AGENTS.md testing hard gate).
        return OperatorResult(  # pragma: no cover
            success=False,
            error_message=f"Unhandled operator type: {op_type!r}",
        )
