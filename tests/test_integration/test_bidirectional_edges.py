"""Bidirectional loading → graph validation → orchestrator event contracts."""

import pytest
import yaml

from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus
from fortress_engine.plugins.classic_parser import ClassicParser
from fortress_engine.plugins.template_narrator import TemplateNarrator


@pytest.mark.parametrize("locked", [False, True])
@pytest.mark.parametrize("start", ["a", "b"])
def test_loaded_passage_round_trip(tmp_path, locked, start, capsys):
    def write(name, data):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data), encoding="utf-8")

    write("episodes/episode-01.yaml", dict(
        id="episode-01", name="Test", order=1, start_anchor=start,
        goal={"conditions": [{"type": "flag_is_set", "flag": "finished"}]},
        carry_over={"inventory": [], "flags": []},
    ))
    for anchor in ["a", "b"]:
        write(f"episode-01/rooms/{anchor}.yaml", dict(
            entity_id=anchor, type="place", name=anchor, components={}))
    write("episode-01/macros/door.yaml", dict(
        macro_edge_id="door", from_anchor="a", to_anchor="b",
        direction="bidirectional", passage_name="puerta",
        requires_text="ábrete" if locked else None, open=not locked,
    ))
    loader = EntityLoader(str(tmp_path))
    episodes = loader.load_episodes()
    bus = EventBus()
    state = WorldState(entities={"hero": Entity("hero", "actor", "Hero", {}, None)},
                       player_controlled_entities=["hero"], active_protagonist_id="hero")
    manager = EpisodeManager(episodes, str(tmp_path), bus)
    graph = manager.start_episode("episode-01", state)
    narrator = TemplateNarrator()
    orch = TurnOrchestrator(state, graph, bus, ClassicParser(), narrator,
                            manager.goal_evaluator_for("episode-01"), manager)
    events = []
    bus.subscribe("*", events.append)
    assert len(list(graph.iter_macro_edges())) == 2
    if locked:
        before = state.to_dict()
        orch.execute_turn("abrir puerta diciendo incorrecto")
        assert state.to_dict() == before
        assert [e.open for e in graph.iter_macro_edges()] == [False, False]
        assert [e.type for e in events] == [
            "turn_started", "input_received", "action_attempted", "error_output", "turn_ended"]
        assert events[-2].payload == {
            "error_code": "blocked", "data": {"passage_name": "puerta",
                "required_text": "ábrete", "gate_code": "text_closed"},
            "protagonist_id": "hero"}
        assert events[-1].payload == {"turn_number": 0, "actions_resolved": 0}
        events.clear()
    for turn, destination in enumerate(["b" if start == "a" else "a", start], 1):
        events.clear()
        command = "abrir puerta diciendo ABRETE" if locked and turn == 1 else "ir puerta"
        orch.execute_turn(command)
        assert state.get_entity("hero").spatial_anchor == destination
        assert state.turn_number == turn
        assert [e.open for e in graph.iter_macro_edges()] == [True, True]
        assert [e.type for e in events] == [
            "turn_started", "input_received", "action_attempted", "entity_teleported",
            "entity_entered", "action_resolved", "turn_ended"]
        assert events[-2].payload == {
            "hyper_edge_id": "door" if destination == "b" else "door_reverse",
            "operators_executed": ["TELEPORT"], "has_effects": True,
            "protagonist_id": "hero"}
        assert events[-1].payload == {"turn_number": turn, "actions_resolved": 1}
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
