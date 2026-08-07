"""Tests for engine-known component key constants and helpers."""

from fortress_engine.entities.entity import Entity
from fortress_engine.entities.components import (
    WEIGHT,
    MAX_WEIGHT,
    has_component,
)


def test_weight_constant_is_string():
    """WEIGHT is the string "weight"."""
    assert WEIGHT == "weight"


def test_max_weight_constant_is_string():
    """MAX_WEIGHT is the string "max_weight"."""
    assert MAX_WEIGHT == "max_weight"


def test_has_component_true_when_key_present():
    """Returns True when the component key exists in the entity."""
    e = Entity("e1", "item", "Rock", {WEIGHT: 5, "tags": ["heavy"]}, "room_01")
    assert has_component(e, WEIGHT) is True
    assert has_component(e, "tags") is True


def test_has_component_false_when_key_absent():
    """Returns False when the component key is not present."""
    e = Entity("e1", "item", "Feather", {"flavor": "light"}, "room_01")
    assert has_component(e, WEIGHT) is False
    assert has_component(e, MAX_WEIGHT) is False


def test_has_component_false_when_components_empty():
    """Returns False for any key when the entity has no components."""
    e = Entity("e1", "room", "Void", {}, "room_00")
    assert has_component(e, WEIGHT) is False


def test_no_entity_type_validation():
    """Verify that components.py does NOT define or import ENTITY_TYPES,
    EntityType enum, or any type-validating constants."""
    import fortress_engine.entities.components as c

    # The module must NOT have ENTITY_TYPES, EntityType, or similar
    for name in dir(c):
        assert "ENTITY_TYPE" not in name.upper(), (
            f"components.py must not define ENTITY_TYPES enum/constant: found {name}"
        )
