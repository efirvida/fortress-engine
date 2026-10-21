"""Engine-known component key constants and helpers.

These are CONVENIENCE string constants — the engine NEVER validates or closes
the set of valid component keys. World authors may use any key they wish.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.entities.entity import Entity

# Component key constants used internally by the engine.
# World authors are free to use any additional keys.
WEIGHT: str = "weight"
MAX_WEIGHT: str = "max_weight"


def inventory_capacity(entity: Entity) -> int | float | None:
    """Return the authored weight limit, or None for unlimited capacity.

    Missing, None and the boolean False disable the limit. Numeric zero is
    an explicit zero-capacity limit, not an unlimited-capacity marker.
    """
    value = entity.components.get(MAX_WEIGHT)
    return None if value is None or value is False else value


def has_component(entity: Entity, key: str) -> bool:
    """Return True if *entity* contains *key* in its components dict."""
    return key in entity.components
