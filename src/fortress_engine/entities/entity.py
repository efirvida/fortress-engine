"""Entity model — runtime value objects for the Fortress engine.

All types are stdlib @dataclass. engine NEVER validates or closes entity types,
component keys, or component values. Entity semantics come from graph data and
components, not inheritance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """An entity in the game world.

    Attributes:
        entity_id: Unique identifier.
        type: Opaque entity type string (e.g. "item", "room", "npc", "portal").
              The engine MUST NOT validate or restrict this field.
        name: Human-readable display name.
        components: Opaque key-value component dictionary. Values are raw YAML
                    primitives — the engine MUST NOT coerce or narrow them.
        spatial_anchor: Container entity_id, or None for limbo/destroyed.
    """

    entity_id: str
    type: str
    name: str
    components: dict[str, Any]
    spatial_anchor: str | None


@dataclass
class ParsedCommand:
    """Structured parse result from the parser plugin.

    Attributes:
        subject: Entity_id of the acting entity (None for impersonal commands).
        verb: Normalized lowercase verb.
        target: Entity_id of the target (None when absent).
        context: Optional contextual entity_id (e.g. second protagonist).
        instrument: Entity_id of the instrument (None when absent).
    """

    subject: str | None
    verb: str
    target: str | None
    context: str | None = None
    instrument: str | None = None


@dataclass
class GoalCondition:
    """An atomic victory condition.

    Attributes:
        type: Condition type (e.g. "flag_is_set", "entity_dead").
        params: Type-specific parameters.
    """

    type: str
    params: dict[str, Any]


@dataclass
class GoalConditions:
    """Composite victory condition tree with and/or nesting.

    Attributes:
        conditions: List of GoalCondition or composite dicts
                    (e.g. {"and": [...], "or": [...]}).
        output: Victory text displayed when goal is met.
        side_effects: Additional effects applied on goal completion.
    """

    conditions: list[GoalCondition | dict[str, Any]]
    output: str
    side_effects: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CarryOver:
    """Rules for what persists across episode transitions.

    Attributes:
        inventory: Item entity_ids to carry, ["*"] for all, [] for none.
        flags: Flag names to carry, ["*"] for all, [] for none.
    """

    inventory: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


@dataclass
class Episode:
    """Definition of a single game episode.

    Attributes:
        id: Unique episode identifier (e.g. "episode-01").
        name: Human-readable episode name.
        order: Sequential position.
        description: Introductory flavour text.
        requires: IDs of episodes that must be completed first ([] = independent).
        start_anchor: Entity_id of the anchor where the player starts.
        goal: Victory conditions for this episode.
        carry_over: Rules for what carries to the next episode.
    """

    id: str
    name: str
    order: int
    description: str | None
    requires: list[str]
    start_anchor: str
    goal: GoalConditions
    carry_over: CarryOver
