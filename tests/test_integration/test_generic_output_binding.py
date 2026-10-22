"""Generic authored output and target binding through the public turn interface."""

from copy import deepcopy

import pytest

from fortress_engine.engine.goal_evaluator import GoalEvaluator
from fortress_engine.engine.graph import Clique, DualGraphEngine, HyperEdge
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity, GoalConditions
from fortress_engine.events.event_bus import EventBus
from fortress_engine.plugins.classic_parser import ClassicParser
from fortress_engine.plugins.template_narrator import TemplateNarrator


def build_turn(output, target=None, operators=None, anchor="deck"):
    entities = [
        Entity("other", "actor", "Other", {}, "elsewhere"),
        Entity("pilot", "actor", "Pilot", {}, anchor),
        Entity("deck", "location", "Deck", {"description": "On deck."}, None),
        Entity("token", "artifact", "Token", {"description": "A token.",
               "weight": 0, "portable": True, "state": "old"}, "pilot"),
        Entity("second", "artifact", "Second", {}, "pilot"),
    ]
    state = WorldState(entities={e.entity_id: e for e in entities},
                       player_controlled_entities=["other", "pilot"],
                       active_protagonist_id="pilot")
    graph = DualGraphEngine()
    edge = HyperEdge("inspect", "Inspect", 1,
                     Clique(subject="player", verb="examinar", target=target),
                     operators or [], output)
    graph.add_hyper_edge(anchor or "", edge)
    bus = EventBus()
    events = []
    bus.subscribe("*", events.append)
    narrator = TemplateNarrator()
    bus.subscribe("*", lambda e: narrator.handle_event(e, state))
    orch = TurnOrchestrator(state, graph, bus, ClassicParser(), narrator,
                            GoalEvaluator(GoalConditions(conditions=[
                                {"type": "flag_is_set", "flag": "never"}
                            ], output="")), None)
    return orch, state, edge, events


def assert_turn(events, output, operators=()):
    """Pin every stable event payload and its order, excluding UUID/time."""
    expected = [
        ("turn_started", {"turn_number": 0, "active_protagonist_id": "pilot"}),
        ("input_received", {"raw_text": "examinar Token", "protagonist_id": "pilot"}),
        ("action_attempted", {"hyper_edge_id": "inspect", "clique": {
            "subject": "player", "verb": "examinar", "target": "*",
            "instrument": None, "context": None}, "protagonist_id": "pilot"}),
        *operators,
    ]
    if output:
        expected.append(("action_output", {"hyper_edge_id": "inspect",
                         "text": output, "protagonist_id": "pilot"}))
    expected.extend([
        ("action_resolved", {"hyper_edge_id": "inspect",
            "operators_executed": ["TRANSFORM"] if operators else [],
            "has_effects": bool(operators), "protagonist_id": "pilot"}),
        ("turn_ended", {"turn_number": 1, "actions_resolved": 1}),
    ])
    assert [(e.type, e.payload) for e in events] == expected
    assert [e.turn_number for e in events] == [0] * (len(events) - 1) + [1]
    assert all(e.protagonist_id == "pilot" and e.episode_id == "" for e in events)


@pytest.mark.parametrize("template,expected", [
    ("{name}|{entity_id}|{type}|{description}|{weight}|{portable}",
     "Token|token|artifact|A token.|0|True"),
    ("{unknown}|{contents}|{missing}|{bad-token}|{}",
     "{unknown}|{contents}|{missing}|{bad-token}|{}"),
    ("literal text", "literal text"),
    (None, None),
    ("", ""),
])
def test_output_contract_and_literal_preservation(template, expected, capsys):
    orch, state, edge, events = build_turn(template, "*")
    before = state.to_dict()
    orch.execute_turn("examinar Token")
    assert_turn(events, expected)
    before["turn_number"] = 1
    assert state.to_dict() == before
    assert edge.output == template
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("anchor,expected", [
    ("deck", "On deck.|Deck|{unknown}"),
    ("missing", "{description}|{name}|{unknown}"),
    (None, "{description}|{name}|{unknown}"),
])
def test_targetless_output_uses_selected_actors_current_anchor(anchor, expected, capsys):
    orch, state, edge, events = build_turn("{description}|{name}|{unknown}", anchor=anchor)
    orch.execute_turn("examinar Token")  # unconstrained target does not select Token
    assert [e.payload["text"] for e in events if e.type == "action_output"] == [expected]
    assert state.turn_number == 1
    assert events[-1].payload == {"turn_number": 1, "actions_resolved": 1}
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("entity", ["*", "token"])
def test_binding_and_concrete_operator_preservation(entity, capsys):
    op = {"type": "TRANSFORM", "entity": entity, "component": "state",
          "old_value": "old", "new_value": "new"}
    orch, state, edge, events = build_turn("{state}", "*", [op])
    templates = deepcopy(edge.operators)
    orch.execute_turn("examinar Token")
    assert state.get_entity("token").components["state"] == "new"
    assert state.get_entity("second").components == {}
    assert [e.entity_id for e in state.get_player_inventory("pilot")] == ["token", "second"]
    assert edge.operators == templates
    assert_turn(events, "new", [("entity_transformed", {
        "entity_id": "token", "component_key": "state", "old_value": "old",
        "new_value": "new", "hyper_edge_id": None})])
    assert capsys.readouterr() == ("", "")


def test_unbound_operator_preserves_failure_and_templates(capsys):
    op = {"type": "TRANSFORM", "entity": "*", "component": "state",
          "old_value": "old", "new_value": "new"}
    orch, state, edge, events = build_turn("literal", operators=[op])
    before = state.to_dict()
    orch.execute_turn("examinar Token")
    assert [(e.type, e.payload) for e in events][3:5] == [
        ("error_output", {"error_code": "operator_failed", "data": {
            "op_code": "entity_not_found", "entity_id": "*"}, "protagonist_id": "pilot"}),
        ("action_output", {"hyper_edge_id": "inspect", "text": "literal",
                           "protagonist_id": "pilot"}),
    ]
    before["turn_number"] = 1  # existing failed micro-action turn semantics
    assert state.to_dict() == before
    assert edge.operators == [op]
    assert events[-2].payload == {"hyper_edge_id": "inspect", "operators_executed": [],
                                 "has_effects": False, "protagonist_id": "pilot"}
    assert events[-1].payload == {"turn_number": 1, "actions_resolved": 1}
    assert capsys.readouterr() == ("", "")


def test_rejected_wildcard_preserves_existing_turn_semantics(capsys):
    orch, state, edge, events = build_turn("{name}", "*", [{"type": "FLAG", "flag": "x", "value": True}])
    state.get_entity("token").spatial_anchor = "elsewhere"
    before = state.to_dict()
    orch.execute_turn("examinar Token")
    assert [(e.type, e.payload) for e in events] == [
        ("turn_started", {"turn_number": 0, "active_protagonist_id": "pilot"}),
        ("input_received", {"raw_text": "examinar Token", "protagonist_id": "pilot"}),
        ("error_output", {"error_code": "no_action", "data": {
            "verb": "examinar", "protagonist_id": "pilot"}, "protagonist_id": "pilot"}),
        ("turn_ended", {"turn_number": 1, "actions_resolved": 0}),
    ]
    before["turn_number"] = 1  # rejection already consumes a micro-action turn
    assert state.to_dict() == before
    assert edge.operators == [{"type": "FLAG", "flag": "x", "value": True}]
    assert capsys.readouterr() == ("", "")


def test_components_override_identity_and_replacements_are_not_recursive():
    orch, state, edge, events = build_turn("{name}|{description}|{state}", "token")
    state.get_entity("token").components.update(name="Alias", description="{state}")
    orch.execute_turn("examinar Token")
    assert [e.payload["text"] for e in events if e.type == "action_output"] == ["Alias|{state}|old"]


def test_wildcard_transfer_reuses_template_for_each_named_inventory_entity():
    op = {"type": "TRANSFER", "entity": "*", "from_container": "pilot",
          "to_container": "deck"}
    orch, state, edge, events = build_turn("{name}", "*", [op])
    for turn, (name, entity_id) in enumerate([("Second", "second"), ("Token", "token")], 1):
        events.clear()
        orch.execute_turn(f"examinar {name}")
        assert state.get_entity(entity_id).spatial_anchor == "deck"
        assert [e.payload for e in events if e.type == "entity_transferred"] == [{
            "entity_id": entity_id, "from_container_id": "pilot",
            "to_container_id": "deck", "hyper_edge_id": None}]
        assert [e.payload["text"] for e in events if e.type == "action_output"] == [name]
        assert events[-1].payload == {"turn_number": turn, "actions_resolved": 1}
        assert edge.operators == [op]
    assert state.get_player_inventory("pilot") == []


def test_anchor_fallback_reads_post_operator_location():
    orch, state, edge, events = build_turn("{name}", operators=[{
        "type": "TELEPORT", "entity": "pilot", "to_anchor": "token"}])
    orch.execute_turn("examinar Token")
    assert state.get_entity("pilot").spatial_anchor == "token"
    assert [e.payload["text"] for e in events if e.type == "action_output"] == ["Token"]


def test_only_the_entity_field_is_bound_other_wildcards_stay_literal(capsys):
    op = {"type": "TRANSFER", "entity": "token", "from_container": "pilot",
          "to_container": "*"}
    orch, state, edge, events = build_turn("{name}", "*", [op])
    orch.execute_turn("examinar Token")
    assert state.get_entity("token").spatial_anchor == "pilot"
    assert [e for e in events if e.type == "entity_transferred"] == []
    assert edge.operators == [op]
    assert [(e.type, e.payload) for e in events][3:5] == [
        ("error_output", {"error_code": "operator_failed", "data": {
            "op_code": "container_not_found", "container_id": "*"},
            "protagonist_id": "pilot"}),
        ("action_output", {"hyper_edge_id": "inspect", "text": "Token",
                           "protagonist_id": "pilot"}),
    ]
    assert capsys.readouterr() == ("", "")
