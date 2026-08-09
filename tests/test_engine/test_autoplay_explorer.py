"""Smoke tests for the blind world explorer + map comparator.

The explorer must discover rooms by reading the narrator alone (no YAML
map knowledge), and the comparator must report gaps against the declared map.
"""
from pathlib import Path

import pytest

from fortress_engine.autoplay import BlindExplorer, MapComparator


_WORLD = Path(__file__).resolve().parents[2] / "worlds" / "fortaleza"


def test_explorer_discovers_rooms_without_reading_yaml():
    """The blind explorer discovers rooms by reading the narrator and
    brute-forcing generic passage names — without reading the YAML map."""
    ex = BlindExplorer(_WORLD, "episode-01")
    discovery, log = ex.explore()
    # Must discover the start room and at least a few neighbours.
    assert len(discovery.visited_rooms) >= 5
    # Must have crossed at least one passage.
    assert len(discovery.crossed_passages) >= 1
    # No crashes allowed.
    assert ex.crashes == []


def test_explorer_no_crash_on_every_command():
    """Every command the explorer tries must produce exactly one turn_ended
    and never raise an exception."""
    ex = BlindExplorer(_WORLD, "episode-01")
    discovery, log = ex.explore()
    for ev in log:
        assert "EXCEPTION" not in ev.note, f"crash: {ev.command} -> {ev.note}"
        if ev.turn_ended_count > 0:
            assert ev.turn_ended_count == 1, (
                f"{ev.command}: turn_ended={ev.turn_ended_count}"
            )


def test_comparator_reports_unreachable_rooms():
    """The comparator reports declared rooms the explorer never reached."""
    ex = BlindExplorer(_WORLD, "episode-01")
    discovery, _ = ex.explore()
    comp = MapComparator(_WORLD, "episode-01").compare(discovery)
    # The map declares 33 rooms; the blind explorer does not reach the
    # gated ones on a first pass, so there must be unreachable rooms.
    assert len(comp.unreachable_rooms) > 0
    # Every unreachable room is genuinely declared.
    for room in comp.unreachable_rooms:
        assert room in comp.declared_rooms
    # Visited rooms are a subset of declared rooms.
    assert discovery.visited_rooms <= comp.declared_rooms


def test_explorer_inventory_and_weight_helpers():
    """Weight helpers work on the real world (fallback to disk)."""
    ex = BlindExplorer(_WORLD, "episode-01")
    assert ex._max_weight() >= 20
    # An item not yet in state resolves from disk.
    w = ex._item_weight("maza")
    assert w > 0
    assert ex._current_weight() >= 0


def test_explorer_action_commands_use_vocabulary():
    """Command generation uses the world vocabulary verbs + prepositions
    (no hardcoded language)."""
    ex = BlindExplorer(_WORLD, "episode-01")
    # Give the hero an item so instrument/recipient commands appear.
    from fortress_engine.entities.loader import EntityLoader

    loader = EntityLoader(str(_WORLD))
    items = {e.entity_id: e for e in loader.load_items("episode-01")}
    ex.state.entities["maza"] = items["maza"]
    items["maza"].spatial_anchor = "hero"

    cmds = ex._action_commands("bruja")
    joined = " | ".join(cmds)
    # Verbs come from the vocabulary (mirar, dar, matar...), prepositions too.
    assert "mirar bruja" in cmds or "ver bruja" in cmds or "romper bruja" in cmds
    assert "dar maza a bruja" in joined
    assert "romper bruja con maza" in joined


def test_explorer_movement_commands_use_vocabulary():
    """Movement commands come from the world's movement_verbs."""
    ex = BlindExplorer(_WORLD, "episode-01")
    cmds = ex._movement_commands("puerta")
    assert any(c.startswith("ir ") for c in cmds) or any(
        c.startswith("abrir ") for c in cmds
    )


def test_explorer_unknown_world_still_builds():
    """A world without a player entity falls back to a default hero."""
    import tempfile
    from pathlib import Path

    from fortress_engine.autoplay import BlindExplorer

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "episodes").mkdir()
        (base / "episodes" / "ep-01.yaml").write_text(
            'id: "ep-01"\nname: "Ep"\norder: 1\nstart_anchor: "r1"\n'
            "goal:\n  conditions: []\n  output: \"Win!\"\n"
            "carry_over:\n  inventory: []\n  flags: []\n"
        )
        (base / "ep-01").mkdir()
        (base / "ep-01" / "rooms").mkdir()
        (base / "ep-01" / "rooms" / "r1.yaml").write_text(
            'entity_id: "r1"\ntype: "room"\nname: "R1"\n'
            "components:\n  description: \"Una sala.\"\n"
            "spatial_anchor: null\n"
        )
        (base / "world.yaml").write_text('world_id: "test"\nname: "Test"\n')
        ex = BlindExplorer(base, "ep-01")
        assert ex.anchor() == "r1"
        # No player entity → default hero with a capacity.
        assert ex._max_weight() == 40
        # Unknown item weight resolves to 0 (defensive fallback).
        assert ex._item_weight("ghost") == 0


def test_explorer_start_without_anchor_returns_empty():
    """A world with a start anchor that is not a declared room still builds;
    the explorer visits the protagonist's anchor and crosses nothing."""
    import tempfile
    from pathlib import Path

    from fortress_engine.autoplay import BlindExplorer

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "episodes").mkdir()
        (base / "episodes" / "ep-01.yaml").write_text(
            'id: "ep-01"\nname: "Ep"\norder: 1\nstart_anchor: "missing"\n'
            "goal:\n  conditions: []\n  output: \"Win!\"\n"
            "carry_over:\n  inventory: []\n  flags: []\n"
        )
        (base / "ep-01").mkdir()
        (base / "ep-01" / "rooms").mkdir()
        (base / "world.yaml").write_text('world_id: "test"\nname: "Test"\n')
        ex = BlindExplorer(base, "ep-01")
        discovery, log = ex.explore()
        # The hero starts at "missing" (not a declared room) — visited but
        # nothing crossed.
        assert discovery.visited_rooms == {"missing"}
        assert discovery.crossed_passages == set()
