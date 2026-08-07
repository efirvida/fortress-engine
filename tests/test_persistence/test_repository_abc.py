"""Tests for WorldStateRepository ABC and typed error classes.

TDD §4.9 — WorldStateRepository contract and persistence-abc spec.
"""

from abc import ABC, abstractmethod

import pytest

# ---------------------------------------------------------------------------
# P1.1 RED — the production module does NOT exist yet
# ---------------------------------------------------------------------------
from fortress_engine.persistence.repository import (
    WorldStateRepository,
    RepositoryError,
    NonPersistableEventError,
    CorruptEventError,
    CorruptSnapshotError,
    InvalidSlotError,
)


# ---------------------------------------------------------------------------
# ABC contract: 5 abstract methods
# ---------------------------------------------------------------------------

class TestWorldStateRepositoryABC:
    """The ABC exposes exactly five abstract methods and no mutation methods."""

    def test_is_abstract_base_class(self):
        """WorldStateRepository must be an ABC."""
        assert issubclass(WorldStateRepository, ABC)

    def test_five_abstract_methods_exist(self):
        """Exactly the five persist operations are abstract methods."""
        expected = {
            "append_event",
            "get_event_log",
            "get_latest_turn",
            "save_snapshot",
            "load_latest_snapshot",
        }
        methods = {
            name
            for name, obj in WorldStateRepository.__dict__.items()
            if hasattr(obj, "__isabstractmethod__") and obj.__isabstractmethod__
        }
        assert methods == expected, f"Expected {expected}, got {methods}"

    def test_cannot_instantiate_directly(self):
        """Instantiating the ABC directly must raise TypeError."""
        with pytest.raises(TypeError, match="abstract"):
            WorldStateRepository()  # type: ignore[abstract]

    def test_no_update_delete_or_clear_in_class_dict(self):
        """update_event, delete_event, clear_log must not exist on the ABC."""
        forbidden = {"update_event", "delete_event", "clear_log"}
        abc_attrs = set(WorldStateRepository.__dict__.keys())
        overlap = forbidden & abc_attrs
        assert not overlap, (
            f"Forbidden mutation methods found on ABC: {overlap}"
        )

    def test_no_mutable_methods_on_concrete_subclass(self):
        """A concrete subclass must not expose update/delete/clear either."""

        class ConcreteRepo(WorldStateRepository):
            def append_event(self, event):  # type: ignore[override]
                pass

            def get_event_log(self, since_turn=0):  # type: ignore[override]
                return []

            def get_latest_turn(self):  # type: ignore[override]
                return 0

            def save_snapshot(self, state, turn, save_slot):  # type: ignore[override]
                pass

            def load_latest_snapshot(self, save_slot):  # type: ignore[override]
                return None

        repo = ConcreteRepo()
        forbidden = {"update_event", "delete_event", "clear_log"}
        repo_dir = set(dir(repo))
        overlap = forbidden & repo_dir
        assert not overlap, (
            f"Forbidden mutation methods found on concrete repo dir: {overlap}"
        )


# ---------------------------------------------------------------------------
# Typed error hierarchy
# ---------------------------------------------------------------------------

class TestTypedErrors:
    """RepositoryError base class and four specific subclasses."""

    def test_repository_error_is_base_of_custom_errors(self):
        """All custom errors must inherit from RepositoryError."""
        assert issubclass(RepositoryError, Exception)
        assert issubclass(NonPersistableEventError, RepositoryError)
        assert issubclass(CorruptEventError, RepositoryError)
        assert issubclass(CorruptSnapshotError, RepositoryError)
        assert issubclass(InvalidSlotError, RepositoryError)

    def test_repository_error_is_catchable_by_exception(self):
        """RepositoryError must be an Exception subclass (so it's catchable by 'except Exception')."""
        assert isinstance(RepositoryError(), Exception)

    def test_non_persistable_event_error_message(self):
        """NonPersistableEventError carries the reason why the event can't be persisted."""
        err = NonPersistableEventError("action_output cannot be persisted")
        assert str(err) == "action_output cannot be persisted"

    def test_corrupt_event_error_message(self):
        """CorruptEventError carries the event_id that failed deserialization."""
        err = CorruptEventError("bad-json-in-payload", "event abc-123 is corrupted")
        assert str(err) == "bad-json-in-payload: event abc-123 is corrupted"

    def test_corrupt_snapshot_error_message(self):
        """CorruptSnapshotError carries the save_slot and the root cause."""
        err = CorruptSnapshotError("slot_2", "JSON parse error at offset 42")
        assert str(err) == "slot_2: JSON parse error at offset 42"

    def test_invalid_slot_error_message(self):
        """InvalidSlotError carries the slot identifier that was rejected."""
        err = InvalidSlotError("slot_5")
        assert str(err) == "slot_5"


# ---------------------------------------------------------------------------
# Method signature introspection (contract verification)
# ---------------------------------------------------------------------------

class TestAbstractMethodSignatures:
    """Each abstract method must accept the documented parameter set."""

    def test_append_event_takes_event(self):
        """append_event must accept a single positional parameter 'event'."""
        import inspect

        sig = inspect.signature(WorldStateRepository.append_event)
        params = list(sig.parameters.keys())
        # 'self' is the first parameter in the abstract definition
        assert "event" in params, f"append_event signature: {params}"

    def test_get_event_log_takes_since_turn_default_0(self):
        """get_event_log must accept since_turn with default 0."""
        import inspect

        sig = inspect.signature(WorldStateRepository.get_event_log)
        params = sig.parameters
        assert "since_turn" in params
        assert params["since_turn"].default == 0

    def test_get_latest_turn_no_params(self):
        """get_latest_turn must accept only self."""
        import inspect

        sig = inspect.signature(WorldStateRepository.get_latest_turn)
        params = [p for p in sig.parameters if p != "self"]
        assert len(params) == 0, f"Unexpected params: {params}"

    def test_save_snapshot_takes_state_turn_save_slot(self):
        """save_snapshot must accept state, turn, save_slot parameters."""
        import inspect

        sig = inspect.signature(WorldStateRepository.save_snapshot)
        params = list(sig.parameters.keys())
        expected = ["self", "state", "turn", "save_slot"]
        assert params == expected, f"save_snapshot params: {params}"

    def test_load_latest_snapshot_takes_save_slot(self):
        """load_latest_snapshot must accept save_slot parameter."""
        import inspect

        sig = inspect.signature(WorldStateRepository.load_latest_snapshot)
        params = list(sig.parameters.keys())
        assert "save_slot" in params, f"load_latest_snapshot params: {params}"
