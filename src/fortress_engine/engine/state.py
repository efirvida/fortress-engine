"""WorldState — mutable global state container and serialization.

Follows world-state spec §4.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from fortress_engine.entities.components import WEIGHT

if TYPE_CHECKING:
    from fortress_engine.entities.entity import Entity


LIMBO_ROOM_ID: str = "_limbo"


@dataclass
class WorldState:
    """Mutable global state at a point in time.

    Attributes:
        entities: entity_id → Entity mapping.
        flag_book: flag_name → bool mapping.
        player_controlled_entities: List of protagonist entity_ids (always
            list-shaped, never a singleton assumption).
        active_protagonist_id: The protagonist currently receiving input focus.
        current_episode_id: Currently active episode.
        turn_number: Monotonic turn counter, starts at 0.
    """

    entities: dict[str, Entity] = field(default_factory=dict)
    flag_book: dict[str, bool] = field(default_factory=dict)
    player_controlled_entities: list[str] = field(default_factory=list)
    active_protagonist_id: str = ""
    current_episode_id: str = ""
    turn_number: int = 0

    # -------------------------------------------------------------------
    # Entity access
    # -------------------------------------------------------------------

    def get_entity(self, entity_id: str) -> Entity:
        """Return the entity by *entity_id*.

        Raises:
            KeyError: If *entity_id* is not in ``entities``.
        """
        if entity_id not in self.entities:
            raise KeyError(f"Entity '{entity_id}' not found")
        return self.entities[entity_id]

    def entity_exists(self, entity_id: str) -> bool:
        """Return ``True`` if *entity_id* is present in ``entities``."""
        return entity_id in self.entities

    # -------------------------------------------------------------------
    # Flags
    # -------------------------------------------------------------------

    def set_flag(self, flag: str, value: bool) -> None:
        """Set (or overwrite) a global flag value."""
        self.flag_book[flag] = value

    def get_flag(self, flag: str) -> bool:
        """Return the flag value, ``False`` if the flag is not set."""
        return self.flag_book.get(flag, False)

    # -------------------------------------------------------------------
    # Container queries
    # -------------------------------------------------------------------

    def get_entities_in_container(self, container_id: str) -> list[Entity]:
        """Return every entity whose ``spatial_anchor`` equals *container_id*."""
        return [
            e
            for e in self.entities.values()
            if e.spatial_anchor == container_id
        ]

    def get_player_inventory(self, protagonist_id: str) -> list[Entity]:
        """Convenience: entities anchored to *protagonist_id*."""
        return self.get_entities_in_container(protagonist_id)

    def get_inventory_weight(self, protagonist_id: str) -> int:
        """Sum the ``WEIGHT`` component of every entity in the protagonist's
        inventory.  Absent ``WEIGHT`` contributes 0.
        """
        return sum(
            e.components.get(WEIGHT, 0)
            for e in self.get_entities_in_container(protagonist_id)
        )

    # -------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full state to a JSON-compatible dictionary."""
        return {
            "entities": {
                eid: _entity_to_dict(e)
                for eid, e in self.entities.items()
            },
            "flag_book": dict(self.flag_book),
            "player_controlled_entities": list(self.player_controlled_entities),
            "active_protagonist_id": self.active_protagonist_id,
            "current_episode_id": self.current_episode_id,
            "turn_number": self.turn_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldState:
        """Deserialize a dictionary produced by :meth:`to_dict`.

        Raises:
            ValueError: If *data* is not a dict or required keys are missing.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        try:
            entities_raw = data["entities"]
            flag_book = data["flag_book"]
            player_controlled_entities = data["player_controlled_entities"]
            active_protagonist_id = data["active_protagonist_id"]
            current_episode_id = data["current_episode_id"]
            turn_number = data["turn_number"]
        except KeyError as exc:
            raise ValueError(f"Missing required key: {exc}") from exc

        if not isinstance(entities_raw, dict):
            raise ValueError("'entities' must be a dict")

        entities = {
            eid: _entity_from_dict(edata)
            for eid, edata in entities_raw.items()
        }

        return cls(
            entities=entities,
            flag_book=dict(flag_book),
            player_controlled_entities=list(player_controlled_entities),
            active_protagonist_id=active_protagonist_id,
            current_episode_id=current_episode_id,
            turn_number=int(turn_number),
        )


# -------------------------------------------------------------------
# Internal entity serialization helpers
# -------------------------------------------------------------------

def _entity_to_dict(entity: Entity) -> dict[str, Any]:
    return {
        "entity_id": entity.entity_id,
        "type": entity.type,
        "name": entity.name,
        "components": dict(entity.components),
        "spatial_anchor": entity.spatial_anchor,
    }


def _entity_from_dict(data: dict[str, Any]) -> Entity:
    # Deferred import to avoid circular dependency at module level.
    from fortress_engine.entities.entity import Entity

    return Entity(
        entity_id=data["entity_id"],
        type=data["type"],
        name=data["name"],
        components=dict(data.get("components", {})),
        spatial_anchor=data.get("spatial_anchor"),
    )
