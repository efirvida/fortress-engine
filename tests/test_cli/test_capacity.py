"""World-authored inventory limits through the interactive engine interface."""

import shutil
from pathlib import Path

import pytest
import yaml

from fortress_engine.cli.main import _build_engine
from fortress_engine.events.event_types import ERROR_OUTPUT, TURN_ENDED


@pytest.mark.parametrize("capacity", [{}, {"max_weight": None}, {"max_weight": False}])
def test_world_without_numeric_limit_can_take_heavy_item(tmp_path, capacity):
    source = Path(__file__).resolve().parents[2] / "worlds" / "_test_minimal"
    world = tmp_path / "world"
    shutil.copytree(source, world)
    # The classic parser canonicalizes coger to tomar without a custom vocabulary.
    action_file = world / "episode-01" / "actions" / "pick_key.yaml"
    actions = yaml.safe_load(action_file.read_text())
    actions[0]["clique"]["verb"] = "tomar"
    action_file.write_text(yaml.safe_dump(actions))
    bundle = _build_engine(str(world))
    protagonist = bundle.state.get_entity(bundle.state.active_protagonist_id)
    protagonist.components.clear()
    protagonist.components.update(capacity)
    # The known minimal-world portable item is targeted by its real public name.
    item = bundle.state.get_entity("rusty_key")
    item.components["weight"] = 10001
    events = []
    bundle.event_bus.subscribe("*", events.append)
    bundle.orchestrator.execute_turn(f"coger {item.name}")
    assert item.spatial_anchor == protagonist.entity_id
    assert bundle.state.get_inventory_weight(protagonist.entity_id) == 10001
    assert [event.payload for event in events if event.type == ERROR_OUTPUT] == []
    assert len([event for event in events if event.type == TURN_ENDED]) == 1


def test_generated_player_has_no_numeric_limit(tmp_path):
    source = Path(__file__).resolve().parents[2] / "worlds" / "_test_minimal"
    world = tmp_path / "world"
    shutil.copytree(source, world)
    for player in (world / "shared").glob("*.yaml"):
        raw = yaml.safe_load(player.read_text())
        if isinstance(raw, dict) and raw.get("type") == "player":
            player.unlink()
    bundle = _build_engine(str(world))
    assert bundle.state.get_entity(bundle.state.active_protagonist_id).components == {}
