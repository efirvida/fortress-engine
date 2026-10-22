"""Strict tests for GameRuntime (solver chunk 1)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from fortress_engine.autoplay.runtime import (
    Checkpoint,
    GameRuntime,
    StepResult,
    _freeze,
)
from fortress_engine.entities.entity import ParsedCommand

WALKTHROUGH = [
    "coger rusty key",
    "ir north",
    "ir east diciendo open sesame",
    "lever lever handle",
    "ir south",
    "finish goal shrine",
]
MINIMAL = Path(__file__).resolve().parents[2] / "worlds" / "_test_minimal"


@pytest.fixture
def rt(solver_happy: Path) -> GameRuntime:
    return GameRuntime(solver_happy, "episode-01")


def _copy_world(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


# ----------------------------------------------------------------------
# Wiring
# ----------------------------------------------------------------------


def test_wiring_and_baseline(rt: GameRuntime):
    assert rt.protagonist_id == "hero"
    assert rt.anchor() == "alpha"
    assert rt.turns == 0
    assert rt.state.active_protagonist_id == "hero"
    assert rt.state.player_controlled_entities == ["hero"]
    assert rt.orchestrator._state is rt.state
    assert rt._events == []
    assert rt.checkpoint() == Checkpoint(
        entities={}, flags={}, edges={}, turn_number=rt.state.turn_number
    )


def test_protagonist_id_comes_from_world(solver_happy: Path, tmp_path: Path):
    world = _copy_world(solver_happy, tmp_path / "w")
    player = world / "shared" / "player.yaml"
    player.write_text(player.read_text().replace('"hero"', '"avatar"'))
    actions = world / "episode-01" / "actions" / "actions.yaml"
    actions.write_text(actions.read_text().replace('"hero"', '"avatar"'))
    r = GameRuntime(world, "episode-01")
    assert r.protagonist_id == "avatar"
    assert r.state.active_protagonist_id == "avatar"
    assert r.state.player_controlled_entities == ["avatar"]
    assert r.anchor() == "alpha"
    assert r.step("coger rusty key").ok is True
    assert r.state.get_entity("rusty_key").spatial_anchor == "avatar"


def test_fallback_protagonist_when_world_has_no_player(
    solver_happy: Path, tmp_path: Path
):
    world = _copy_world(solver_happy, tmp_path / "w")
    (world / "shared" / "player.yaml").unlink()
    r = GameRuntime(world, "episode-01")
    assert r.protagonist_id == "hero"
    hero = r.state.get_entity("hero")
    assert hero.type == "player"
    assert hero.name == "Hero"
    assert hero.components == {}
    assert r.anchor() == "alpha"


def _add_shared(world: Path, name: str, entity_type: str, marked: bool | None):
    components = (
        "components:\n  player_controlled: true\n" if marked else ""
    )
    (world / "shared" / f"{name}.yaml").write_text(
        f'entity_id: "{name}"\ntype: "{entity_type}"\nname: "{name}"\n'
        f"{components}spatial_anchor: null\n"
    )


def test_protagonist_selection_never_consults_entity_type(
    solver_happy: Path, tmp_path: Path
):
    world = _copy_world(solver_happy, tmp_path / "w")
    (world / "shared" / "player.yaml").unlink()
    _add_shared(world, "avatar", "opaque-kind", None)
    r = GameRuntime(world, "episode-01")
    assert r.protagonist_id == "avatar"
    assert r.state.get_entity("avatar").type == "opaque-kind"
    assert r.state.player_controlled_entities == ["avatar"]


def test_player_controlled_marker_beats_a_type_named_player(
    solver_happy: Path, tmp_path: Path
):
    world = _copy_world(solver_happy, tmp_path / "w")
    _add_shared(world, "pilot", "crew", True)
    r = GameRuntime(world, "episode-01")
    assert r.protagonist_id == "pilot"
    assert r.state.active_protagonist_id == "pilot"
    assert r.state.player_controlled_entities == ["pilot"]


def test_explicit_protagonist_id_overrides_marker(
    solver_happy: Path, tmp_path: Path
):
    world = _copy_world(solver_happy, tmp_path / "w")
    _add_shared(world, "pilot", "crew", True)
    r = GameRuntime(world, "episode-01", protagonist_id="hero")
    assert r.protagonist_id == "hero"
    assert r.state.player_controlled_entities == ["hero"]


def test_unknown_explicit_protagonist_id_is_rejected(solver_happy: Path):
    with pytest.raises(KeyError) as error:
        GameRuntime(solver_happy, "episode-01", protagonist_id="ghost")
    assert error.value.args == ("ghost",)


@pytest.mark.parametrize("marked", [None, True])
def test_ambiguous_protagonist_is_an_explicit_error(
    solver_happy: Path, tmp_path: Path, marked
):
    world = _copy_world(solver_happy, tmp_path / "w")
    _add_shared(world, "second", "crew", marked)
    if marked:
        _add_shared(world, "first", "crew", True)
        expected = ["first", "second"]
    else:
        expected = ["hero", "second"]
    with pytest.raises(ValueError) as error:
        GameRuntime(world, "episode-01")
    assert str(error.value) == (
        f"ambiguous protagonist among {expected}: mark one with "
        "player_controlled: true or pass protagonist_id"
    )


def test_episode_id_is_honoured(solver_happy: Path):
    with pytest.raises(KeyError):
        GameRuntime(solver_happy, "episode-99")


def test_smoke_test_minimal_world():
    r = GameRuntime(MINIMAL, "episode-01")
    assert r.protagonist_id == "hero"
    assert r.anchor() is not None
    assert r.turns == 0


# ----------------------------------------------------------------------
# step / parse
# ----------------------------------------------------------------------


def test_step_success_with_output(rt: GameRuntime):
    res = rt.step("mirar")
    assert res == StepResult(
        command="mirar",
        ok=True,
        error_code=None,
        gate_code=None,
        game_over=False,
        goal_reached=False,
        output="A dark hall. A gate to the north blocks the way.",
    )
    assert rt.turns == 1
    assert rt._events == []


def test_step_gate_codes(rt: GameRuntime):
    res = rt.step("ir north")
    assert (res.ok, res.error_code, res.gate_code) == (
        False,
        "blocked",
        "requires_item",
    )
    assert rt.anchor() == "alpha"
    rt.step("coger rusty key")
    rt.step("ir north")
    res = rt.step("ir east")
    assert (res.ok, res.error_code, res.gate_code) == (
        False,
        "blocked",
        "text_closed",
    )


def test_step_no_action_has_no_gate_code(rt: GameRuntime):
    res = rt.step("xyzzy")
    assert (res.ok, res.error_code, res.gate_code) == (False, "no_action", None)
    assert res.output == ""


def test_step_full_walkthrough_reaches_goal(rt: GameRuntime):
    results = [rt.step(c) for c in WALKTHROUGH]
    assert all(r.ok for r in results)
    assert [r.goal_reached for r in results] == [False] * 5 + [True]
    assert results[-1].output == "Mision completada."
    assert rt.anchor() == "delta"
    assert rt.turns == 6
    assert rt.state.get_flag("quest_done") is True


def test_completion_isolated_from_successor_episode(solver_happy: Path):
    """Selected-episode search can restore after success in a chained world."""
    source = solver_happy / "episodes" / "episode-01.yaml"
    successor = yaml.safe_load(source.read_text())
    successor.update(id="chapter-next", order=2, requires=["episode-01"])
    (source.parent / "chapter-next.yaml").write_text(yaml.safe_dump(successor))
    shutil.copytree(solver_happy / "episode-01", solver_happy / "chapter-next")
    runtime = GameRuntime(solver_happy, "episode-01")
    initial = runtime.checkpoint()
    initial_key = runtime.state_key()
    original_graph = runtime.graph
    original_entities = set(runtime.state.entities)

    results = [runtime.step(command) for command in WALKTHROUGH]
    assert [result.ok for result in results] == [True] * 6
    assert [result.goal_reached for result in results] == [False] * 5 + [True]
    assert runtime.state.current_episode_id == "episode-01"
    assert runtime.orchestrator._graph is original_graph
    assert set(runtime.state.entities) == original_entities
    runtime.checkpoint()  # Valid even after the goal step.
    runtime.restore(initial)
    assert runtime.checkpoint() == initial
    assert runtime.state_key() == initial_key
    assert runtime.anchor() == "alpha"
    assert runtime.state.current_episode_id == "episode-01"
    assert runtime.orchestrator._goal_evaluator is runtime.goal_evaluator
    replay = [runtime.step(command) for command in WALKTHROUGH]
    assert [result.ok for result in replay] == [True] * 6
    assert [result.goal_reached for result in replay] == [False] * 5 + [True]


def test_step_events_do_not_accumulate(rt: GameRuntime):
    for _ in range(3):
        rt.step("mirar")
        assert rt._events == []
    # goal_reached reflects only the current step's events: a pre-goal
    # step after a restore does not inherit the later goal event.
    cp = rt.checkpoint()
    for c in WALKTHROUGH:
        assert rt.step(c).ok is True
    assert rt._events == []
    rt.restore(cp)
    assert rt.step("mirar").goal_reached is False


def test_step_game_over(solver_happy: Path, tmp_path: Path):
    world = _copy_world(solver_happy, tmp_path / "w")
    macros = world / "episode-01" / "macros" / "macros.yaml"
    macros.write_text(
        macros.read_text().replace(
            'requires_item: "rusty_key"',
            'requires_item: "rusty_key"\n  death_message: "Mueres."',
        )
    )
    r = GameRuntime(world, "episode-01")
    res = r.step("ir north")
    assert res.ok is False
    assert res.game_over is True
    assert res.error_code is None
    assert res.gate_code is None
    assert res.goal_reached is False


def test_step_exception_is_caught(rt: GameRuntime, monkeypatch):
    def boom(_raw: str) -> None:
        rt._events.append(object())
        raise RuntimeError("boom")

    monkeypatch.setattr(rt.orchestrator, "execute_turn", boom)
    res = rt.step("mirar")
    assert res == StepResult("mirar", ok=False, error_code="exception")
    assert rt.turns == 1
    assert rt._events == []


def test_parse_is_pure(rt: GameRuntime):
    before = rt.checkpoint()
    parsed = rt.parse("coger rusty key")
    assert isinstance(parsed, ParsedCommand)
    assert parsed.verb == "coger"
    assert parsed.target == "rusty_key"
    assert rt.checkpoint() == before
    assert rt.turns == 0


# ----------------------------------------------------------------------
# checkpoint / restore / state_key
# ----------------------------------------------------------------------


def test_checkpoint_is_a_compact_diff(rt: GameRuntime):
    rt.step("coger rusty key")
    rt.step("ir north")
    rt.step("ir east diciendo open sesame")
    cp = rt.checkpoint()
    assert cp.entities == {"hero": ("gamma", {}), "rusty_key": ("hero", {})}
    assert cp.flags == {}
    assert cp.edges == {"beta_to_gamma": True, "beta_to_gamma_reverse": True}
    assert cp.turn_number == rt.state.turn_number
    assert cp.turn_number > 0


def test_checkpoint_deep_copies_components(rt: GameRuntime):
    key = rt.state.get_entity("rusty_key")
    key.components["nested"] = {"a": [1, 2]}
    cp = rt.checkpoint()
    key.components["nested"]["a"].append(3)
    assert cp.entities["rusty_key"] == ("alpha", {"nested": {"a": [1, 2]}})


def test_restore_roundtrip_is_exact(rt: GameRuntime):
    rt.step("coger rusty key")
    rt.step("ir north")
    mid = rt.checkpoint()
    mid_key = rt.state_key()
    state_obj = rt.orchestrator._state
    entity_objs = dict(rt.state.entities)
    components_obj = rt.state.get_entity("rusty_key").components
    flags_obj = rt.state.flag_book

    for c in WALKTHROUGH[2:]:
        rt.step(c)
    assert rt.anchor() == "delta"
    assert rt.state_key() != mid_key

    rt.restore(mid)
    assert rt.checkpoint() == mid
    assert rt.state_key() == mid_key
    assert rt.anchor() == "beta"
    assert rt.state.get_flag("quest_done") is False
    assert rt.state.flag_book == {}
    assert rt.state.turn_number == mid.turn_number
    # In place: no rebinding.
    assert rt.orchestrator._state is state_obj is rt.state
    assert rt.state.entities == entity_objs
    assert all(rt.state.entities[k] is v for k, v in entity_objs.items())
    assert rt.state.get_entity("rusty_key").components is components_obj
    assert rt.state.flag_book is flags_obj
    # Closed edge re-closed: gate is text-closed again.
    res = rt.step("ir east")
    assert (res.error_code, res.gate_code) == ("blocked", "text_closed")
    # And the walkthrough is still replayable after restore.
    rt.restore(mid)
    assert [rt.step(c).ok for c in WALKTHROUGH[2:]] == [True] * 4
    assert rt.anchor() == "delta"


def test_restore_baseline_checkpoint_resets_everything(rt: GameRuntime):
    root = rt.checkpoint()
    root_key = rt.state_key()
    for c in WALKTHROUGH:
        rt.step(c)
    rt.restore(root)
    assert rt.anchor() == "alpha"
    assert rt.state.get_entity("rusty_key").spatial_anchor == "alpha"
    assert rt.state.flag_book == {}
    assert rt.state_key() == root_key
    assert {e.macro_edge_id: e.open for e in rt.graph.iter_macro_edges()} == (
        rt._baseline_edges
    )


def test_restore_resets_component_changes_in_place(rt: GameRuntime):
    key = rt.state.get_entity("rusty_key")
    comps = key.components
    key.components["rust"] = {"level": [1]}
    cp = rt.checkpoint()
    key.components["rust"]["level"].append(2)
    key.components["extra"] = True
    rt.restore(cp)
    assert key.components is comps
    assert key.components == {"rust": {"level": [1]}}
    # Mutating after restore must not corrupt the checkpoint (deep copy).
    key.components["rust"]["level"].append(9)
    assert cp.entities["rusty_key"][1] == {"rust": {"level": [1]}}
    root = Checkpoint(turn_number=0)
    rt.restore(root)
    assert key.components == {}


def test_restore_flags_exact(rt: GameRuntime):
    rt.state.set_flag("a", True)
    rt.state.set_flag("b", False)
    cp = rt.checkpoint()
    assert cp.flags == {"a": True, "b": False}
    rt.state.set_flag("c", True)
    rt.restore(cp)
    assert rt.state.flag_book == {"a": True, "b": False}


def test_state_key_excludes_turn_number_and_false_flags(rt: GameRuntime):
    base = rt.state_key()
    rt.step("mirar")
    rt.step("mirar")
    assert rt.state.turn_number > 0 or rt.turns == 2
    assert rt.state_key() == base
    rt.state.set_flag("zero", False)
    assert rt.state_key() == base
    rt.state.set_flag("one", True)
    key = rt.state_key()
    assert key != base
    assert key == ((), ("one",), ())
    hash(key)


def test_state_key_exact_value_and_cp_argument(rt: GameRuntime):
    rt.step("coger rusty key")
    cp = rt.checkpoint()
    expected = ((("rusty_key", "hero", ()),), (), ())
    assert rt.state_key(cp) == expected
    assert rt.state_key() == expected
    rt.step("ir north")
    # Explicit cp wins over current state.
    assert rt.state_key(cp) == expected
    assert rt.state_key() != expected


def test_state_key_includes_edges(rt: GameRuntime):
    for c in WALKTHROUGH[:3]:
        rt.step(c)
    key = rt.state_key()
    assert key[2] == (("beta_to_gamma", True), ("beta_to_gamma_reverse", True))


def test_state_key_is_hashable_with_nested_components(rt: GameRuntime):
    rt.state.get_entity("rusty_key").components["m"] = {
        "l": [1, {"x": {2, 3}}],
        "t": (4,),
    }
    key = rt.state_key()
    assert key[0] == (
        (
            "rusty_key",
            "alpha",
            (("'m'", (("'l'", (1, (("'x'", frozenset({2, 3})),))), ("'t'", (4,)))),),
        ),
    )
    hash(key)


def test_freeze_scalar_dict_order_independent():
    assert _freeze(5) == 5
    assert _freeze("x") == "x"
    assert _freeze({"b": 1, "a": 2}) == _freeze({"a": 2, "b": 1})
    assert _freeze([1, 2]) == (1, 2)
    assert _freeze(frozenset({1})) == frozenset({1})


# ----------------------------------------------------------------------
# Capacity: the runtime adds no numeric default of its own
# ----------------------------------------------------------------------


def _world_with_capacity(src: Path, dst: Path, max_weight: str | None) -> Path:
    """Copy *src* with a weighted key and the protagonist's ``max_weight``."""
    world = _copy_world(src, dst)
    key = world / "episode-01" / "items" / "rusty_key.yaml"
    key.write_text(key.read_text() + "components:\n  weight: 1000\n")
    if max_weight is not None:
        player = world / "shared" / "player.yaml"
        player.write_text(
            player.read_text() + f"components:\n  max_weight: {max_weight}\n"
        )
    return world


@pytest.mark.parametrize("max_weight", [None, "null", "false"])
def test_absent_null_or_false_capacity_is_unlimited(
    solver_happy: Path, tmp_path: Path, max_weight: str | None
):
    world = _world_with_capacity(solver_happy, tmp_path / "w", max_weight)
    r = GameRuntime(world, "episode-01")
    res = r.step("coger rusty key")
    assert res.ok is True
    assert res.error_code is None
    assert res.output == "Tomas la llave."
    assert r.state.get_entity("rusty_key").spatial_anchor == "hero"


def test_numeric_zero_capacity_is_an_explicit_limit(
    solver_happy: Path, tmp_path: Path
):
    world = _world_with_capacity(solver_happy, tmp_path / "w", "0")
    r = GameRuntime(world, "episode-01")
    before = r.state_key()
    res = r.step("coger rusty key")
    assert res.ok is False
    assert res.error_code == "operator_failed"
    assert r.state.get_entity("rusty_key").spatial_anchor == "alpha"
    assert r.state_key() == before
