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


def has_component(entity: Entity, key: str) -> bool:
    """Return True if *entity* contains *key* in its components dict."""
    return key in entity.components
