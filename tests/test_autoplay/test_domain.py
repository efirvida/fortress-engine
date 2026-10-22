"""Strict tests for the advisory action domain (T2 first slice).

Two worlds: the shared ``solver_happy`` fixture (known walkthrough) and an
inline ``forge`` world whose ids, names, verbs, prepositions and entity types
are deliberately unlike any shipped world (protagonist ``avatar``).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from fortress_engine.autoplay.domain import (
    UNREACHED_COST,
    ActionDomain,
    CandidateSet,
    CommandSpec,
    RAction,
    Rejected,
    candidates,
)
from fortress_engine.autoplay.runtime import GameRuntime
from fortress_engine.entities.entity import Entity

from .conftest import _episode_yaml, _write

WALKTHROUGH = [
    "coger rusty key",
    "ir north",
    "ir east diciendo open sesame",
    "lever lever handle",
    "ir south",
    "finish goal shrine",
]

FORGE_GOAL = """\
    - and:
        - type: flag_is_set
          params: {flag: lit}
        - or:
            - type: entity_dead
              params: {entity: gem}
            - type: entity_in_room
              params: {entity: gem, room: vault}
    - type: entity_in_room
      params: {entity: avatar, room: vault}
    - type: entity_has_component
      params: {entity: chest, component: state, value: open}
    - type: flag_is_not_set
      params: {flag: lit}
    - type: entity_not_in_room
      params: {entity: twin_a, room: hall}
    - type: flag_is_set
      params: {flag: never_set}"""

FORGE_VOCABULARY = """\
language: "es"
verbs:
  go: ["go"]
  give: ["give"]
  smash: ["smash"]
  clean: ["clean"]
  look: ["look"]
  douse: ["douse"]
  forge: ["forge"]
  burn: ["burn"]
  far: ["far"]
  aid: ["aid"]
  pick: ["pick"]
stopwords: []
prepositions:
  instrument: ["using"]
  recipient: ["onto"]
speech_markers: ["saying"]
speech_verbs: []
movement_verbs: ["go"]
messages: {}
system_commands:
  save: ["save"]
"""


def _he(edge_id: str, verb: str, target=None, operators=(), **clique) -> dict:
    return {
        "hyper_edge_id": edge_id,
        "name": edge_id,
        "priority": 0,
        "clique": {"subject": "player", "verb": verb, "target": target, **clique},
        "operators": list(operators),
        "output": "",
    }


def _edge(edge_id: str, to: str, passage: str, **gates) -> dict:
    return {
        "macro_edge_id": edge_id,
        "from_anchor": "hall",
        "to_anchor": to,
        "direction": "unidirectional",
        "passage_name": passage,
        **gates,
    }


def _entity(entity_id: str, etype: str, name: str, anchor, **components) -> str:
    return json.dumps(
        {
            "entity_id": entity_id,
            "type": etype,
            "name": name,
            "components": components,
            "spatial_anchor": anchor,
        }
    )


def build_forge(
    tmp_path: Path, goal: str = FORGE_GOAL, vocabulary: str | None = FORGE_VOCABULARY
) -> Path:
    world = tmp_path / "forge"
    ep = world / "episode-01"
    _write(world / "world.yaml", 'world_id: "forge"\nname: "Forge"\n')
    _write(world / "episodes" / "episode-01.yaml", _episode_yaml("episode-01", "hall", goal))
    for room in ("hall", "vault", "cellar"):
        _write(ep / "rooms" / f"{room}.yaml", _entity(room, "locus", room.title(), None, description=room))
    items = [
        ("gem", "x1", "Gem", "hall", {}),
        ("chest", "x2", "Chest", "hall", {"state": "shut"}),
        ("twin_a", "x1", "Twin", "hall", {}),
        ("twin_b", "x1", "Twin", "hall", {}),
        ("hammer", "x3", "Hammer", "avatar", {}),
        ("relic", "x1", "Relic", None, {}),
        ("ghost", "x1", "Ghost", "vault", {}),
    ]
    for eid, etype, name, anchor, comps in items:
        _write(ep / "items" / f"{eid}.yaml", _entity(eid, etype, name, anchor, **comps))
    _write(
        ep / "macros" / "macros.yaml",
        json.dumps(
            [
                _edge("m_gate", "vault", "gate", requires_text="xyzzy", open=False),
                _edge("m_stairs", "cellar", "stairs", requires_item="hammer", requires_flag="lit"),
                _edge("m_big", "vault", "Big Door"),
                _edge("m_hatch", "cellar", "hatch", requires_text="open  sesame", open=False),
            ]
        ),
    )
    operators = [
        {"type": "TRANSFER", "entity": "hammer", "to_container": "vault"},
        {"type": "TRANSFORM", "entity": "gem", "component": "glow", "old_value": None, "new_value": "bright"},
        {"type": "COMBINE", "input_entities": ["gem"], "output_entity": "relic"},
        {"type": "TELEPORT", "entity": "avatar", "to_anchor": "vault"},
        {"type": "TELEPORT", "entity": "twin_a", "to_anchor": "cellar"},
        {"type": "WIBBLE"},
    ]
    _write(
        ep / "actions" / "actions.yaml",
        json.dumps(
            [
                _he("e_give", "give", "*", [{"type": "TRANSFER", "entity": "*", "to_container": "chest"}], context="chest"),
                _he(
                    "e_smash", "smash", "chest",
                    [
                        {"type": "TRANSFORM", "entity": "chest", "component": "state",
                         "old_value": "shut", "new_value": "open"},
                        {"type": "FLAG", "flag": "lit", "value": True},
                    ],
                    instrument="hammer", component={"state": "shut"},
                ),
                _he("e_clean", "clean", "gem", instrument="*", instrument_any=True),
                _he("e_look", "look"),
                _he("e_douse", "douse", "gem", [{"type": "FLAG", "flag": "lit", "value": False}]),
                _he("e_forge", "forge", "gem", operators, flag="lit"),
                _he("e_burn", "burn", "gem", [{"type": "TRANSFER", "entity": "gem", "to_container": None}]),
                _he("e_far", "far", "ghost"),
                _he("e_aid", "aid", "gem", instrument="ghost"),
                _he("e_pick", "pick", "*"),
            ]
        ),
    )
    _write(world / "shared" / "player.yaml", _entity("avatar", "zz0", "Avatar", None))
    if vocabulary is not None:
        _write(world / "shared" / "vocabulary.yaml", vocabulary)
    return world


@pytest.fixture
def rt(solver_happy: Path) -> GameRuntime:
    return GameRuntime(solver_happy, "episode-01")


@pytest.fixture
def forge(tmp_path: Path) -> GameRuntime:
    return GameRuntime(build_forge(tmp_path), "episode-01")


def _by_edge(domain: ActionDomain, edge_id: str) -> list[RAction]:
    return [a for a in domain.actions if a.spec.edge_id == edge_id]


# ----------------------------------------------------------------------
# solver_happy: exact candidates, walkthrough coverage
# ----------------------------------------------------------------------


def test_start_state_candidate_set_is_exact(rt: GameRuntime):
    cs = candidates(rt)
    assert cs.actions == (
        RAction(
            CommandSpec("move", "ir", passage="north", edge_id="alpha_to_beta"),
            frozenset({("at", "alpha"), ("loc", "rusty_key", "hero")}),
            frozenset({("at", "beta")}),
            "ir north",
        ),
        RAction(
            CommandSpec("act", "mirar", edge_id="he_mirar"),
            frozenset(),
            frozenset(),
            "mirar",
        ),
        RAction(
            CommandSpec("act", "coger", target="rusty_key", edge_id="he_take_key"),
            frozenset({("here", "rusty_key")}),
            frozenset({("loc", "rusty_key", "hero")}),
            "coger Rusty Key",
        ),
    )
    assert cs.unrenderable == ()
    assert cs.skipped == (
        Rejected(
            CommandSpec("act", "lever", target="lever_obj", edge_id="he_lever"),
            "target 'lever_obj' not present",
        ),
        Rejected(
            CommandSpec("act", "finish", target="goal_shrine", edge_id="he_finish"),
            "target 'goal_shrine' not present",
        ),
    )
    assert cs.commands() == ("ir north", "mirar", "coger Rusty Key")


def test_every_walkthrough_step_is_a_candidate_where_legal(rt: GameRuntime):
    for step in WALKTHROUGH:
        cs = candidates(rt)
        expected = rt.parse(step)
        matches = [c for c in cs.commands() if rt.parse(c) == expected]
        assert len(matches) == 1, (step, cs.commands())
        result = rt.step(matches[0])
        assert result.ok, (matches[0], result)
    assert result.goal_reached


def test_text_gate_is_spoken_with_vocabulary_words_only_while_closed(rt: GameRuntime):
    for step in WALKTHROUGH[:2]:
        rt.step(step)
    assert "ir east diciendo open sesame" in candidates(rt).commands()
    rt.step(WALKTHROUGH[2])  # speaking the text opens the gate for good
    assert rt.step("ir east").ok  # back through the reverse side
    assert rt.anchor() == "beta"
    commands = candidates(rt).commands()
    assert "ir east" in commands
    assert "ir east diciendo open sesame" not in commands


def test_already_true_additions_stay_candidates(rt: GameRuntime):
    rt.step("coger rusty key")
    # The key is already carried, yet the take action is still a candidate.
    assert candidates(rt).commands() == ("ir north", "mirar", "coger Rusty Key")
    rt.step("ir north")
    assert candidates(rt).commands() == (
        "ir east diciendo open sesame", "ir north", "mirar", "coger Rusty Key",
    )


# ----------------------------------------------------------------------
# heuristic and ranking (solver_happy)
# ----------------------------------------------------------------------


def test_facts_and_heuristic_are_exact(rt: GameRuntime):
    domain = ActionDomain(rt)
    facts = domain.facts()
    assert facts == frozenset(
        {
            ("at", "alpha"),
            ("loc", "rusty_key", "alpha"),
            ("loc", "lever_obj", "gamma"),
            ("loc", "goal_shrine", "delta"),
        }
    )
    assert domain.h(facts) == 9
    assert domain.h(facts) == 9  # pure
    assert domain.h(facts | {("flag", "quest_done")}) == 0


def test_h_decreases_along_walkthrough_to_zero(rt: GameRuntime):
    domain = ActionDomain(rt)
    values = []
    for step in WALKTHROUGH:
        values.append(domain.h(domain.facts()))
        rt.step(step)
    values.append(domain.h(domain.facts()))
    assert values == [9, 7, 5, 3, 2, 1, 0]


def test_rank_orders_enabled_helpful_first_and_never_drops(rt: GameRuntime):
    domain = ActionDomain(rt)
    cs = candidates(rt)
    ranked = domain.rank(cs, domain.facts())
    assert ranked.commands() == ("coger Rusty Key", "mirar", "ir north")
    assert Counter(ranked.actions) == Counter(cs.actions)
    assert len(ranked.actions) == len(cs.actions)
    assert (ranked.unrenderable, ranked.skipped) == (cs.unrenderable, cs.skipped)
    assert domain.rank(cs, domain.facts()) == ranked  # deterministic


# ----------------------------------------------------------------------
# forge world: opaque types, non-"hero" protagonist, wildcards, prepositions
# ----------------------------------------------------------------------


def test_forge_candidates_use_world_vocabulary_and_names(forge: GameRuntime):
    assert forge.protagonist_id == "avatar"
    cs = candidates(forge)
    assert cs.commands() == (
        "go gate saying xyzzy",
        "go stairs",
        "give Chest onto Chest",
        "give Gem onto Chest",
        "give Hammer onto Chest",
        "give Twin onto Chest",
        "smash Chest using Hammer",
        "clean Gem using Chest",
        "clean Gem using Gem",
        "clean Gem using Hammer",
        "clean Gem using Twin",
        "look",
        "douse Gem",
        "forge Gem",
        "burn Gem",
        "pick Chest",
        "pick Gem",
        "pick Hammer",
        "pick Twin",
    )
    assert [(r.spec.edge_id, r.reason) for r in cs.skipped] == [
        ("e_far", "target 'ghost' not present"),
        ("e_aid", "instrument 'ghost' not present"),
    ]


def test_forge_unrenderable_actions_are_recorded_with_reasons(forge: GameRuntime):
    cs = candidates(forge)
    assert [(r.spec, r.reason) for r in cs.unrenderable] == [
        (
            CommandSpec("move", "go", passage="Big Door", edge_id="m_big"),
            "parser resolved target 'big door', expected 'Big Door'",
        ),
        (
            CommandSpec("move", "go", passage="hatch", speech="open  sesame", edge_id="m_hatch"),
            "parser resolved text 'open sesame', expected 'open  sesame'",
        ),
        (
            CommandSpec("act", "give", target="twin_a", context="chest", edge_id="e_give"),
            "parser resolved target 'twin_b', expected 'twin_a'",
        ),
        (
            CommandSpec("act", "clean", target="gem", instrument="twin_a", edge_id="e_clean"),
            "parser resolved instrument 'twin_b', expected 'twin_a'",
        ),
        (
            CommandSpec("act", "pick", target="twin_a", edge_id="e_pick"),
            "parser resolved target 'twin_b', expected 'twin_a'",
        ),
    ]
    rendered = {a.spec.edge_id for a in cs.actions}
    assert not rendered & {"m_big", "m_hatch"}


def test_negative_only_and_drop_actions_stay_candidates(forge: GameRuntime):
    domain = ActionDomain(forge)
    commands = domain.candidates().commands()
    douse = _by_edge(domain, "e_douse")[0]
    assert douse.add == frozenset()  # FLAG false adds nothing positive
    assert "douse Gem" in commands
    assert "burn Gem" in commands  # deletion
    assert "give Hammer onto Chest" in commands  # inventory drop
    ranked = domain.rank(domain.candidates(), domain.facts())
    assert Counter(ranked.actions) == Counter(domain.candidates().actions)


def test_rank_is_a_deterministic_permutation(forge: GameRuntime):
    domain = ActionDomain(forge)
    cs = domain.candidates()
    facts = domain.facts()
    first = domain.rank(cs, facts)
    assert first.actions != cs.actions  # order is advisory, not identity
    assert Counter(first.actions) == Counter(cs.actions)
    assert len(first.actions) == len(cs.actions) == 19
    assert domain.rank(cs, facts) == first == ActionDomain(forge).rank(cs, facts)


def test_relaxed_effects_of_every_operator(forge: GameRuntime):
    domain = ActionDomain(forge)
    (forge_action,) = _by_edge(domain, "e_forge")
    assert forge_action.pre == frozenset({("here", "gem"), ("flag", "lit")})
    assert forge_action.add == frozenset(
        {
            ("loc", "hammer", "vault"),
            ("comp", "gem", "glow", "'bright'"),
            ("gone", "gem"),
            ("here", "relic"),
            ("at", "vault"),
            ("loc", "twin_a", "cellar"),
        }
    )
    (smash,) = _by_edge(domain, "e_smash")
    assert smash.pre == frozenset(
        {("here", "chest"), ("here", "hammer"), ("comp", "chest", "state", "'shut'")}
    )
    assert smash.add == frozenset({("comp", "chest", "state", "'open'"), ("flag", "lit")})
    (burn,) = _by_edge(domain, "e_burn")
    assert burn.add == frozenset({("gone", "gem")})
    (look,) = _by_edge(domain, "e_look")
    assert (look.pre, look.add, look.command) == (frozenset(), frozenset(), None)


def test_relaxed_wildcards_ground_over_every_non_structural_entity_once(forge: GameRuntime):
    domain = ActionDomain(forge)
    gives = _by_edge(domain, "e_give")  # edge is registered under all 3 anchors
    assert sorted(a.spec.target for a in gives) == [
        "chest", "gem", "ghost", "hammer", "relic", "twin_a", "twin_b",
    ]
    gem = next(a for a in gives if a.spec.target == "gem")
    assert gem.pre == frozenset({("here", "gem"), ("here", "chest")})
    assert gem.add == frozenset({("loc", "gem", "chest")})
    assert len(_by_edge(domain, "e_clean")) == 7
    stairs = _by_edge(domain, "m_stairs")[0]
    assert stairs.pre == frozenset({("at", "hall"), ("loc", "hammer", "avatar"), ("flag", "lit")})


def test_forge_facts_are_keyed_by_the_worlds_protagonist(forge: GameRuntime):
    facts = ActionDomain(forge).facts()
    assert ("at", "hall") in facts
    assert ("loc", "hammer", "avatar") in facts
    assert ("gone", "relic") in facts
    assert ("comp", "chest", "state", "'shut'") in facts
    assert not any("hero" in f for f in facts)


def test_goal_costs_are_finite_and_unreached_atoms_are_penalised(forge: GameRuntime):
    domain = ActionDomain(forge)
    value = domain.h(domain.facts())
    # never_set (unreachable atom) = UNREACHED_COST; the rest: lit 1 (smash) +
    # gem gone 1 (burn) + avatar at vault 1 (gate) + chest open 1 (smash).
    assert value == UNREACHED_COST + 4 == 104


def test_negative_and_satisfied_goals_cost_nothing_and_prune_nothing(tmp_path: Path):
    goal = (
        "    - type: flag_is_not_set\n      params: {flag: lit}\n"
        "    - type: entity_not_in_room\n      params: {entity: gem, room: vault}\n"
        "    - type: entity_in_room\n      params: {entity: avatar, room: hall}"
    )
    easy = GameRuntime(build_forge(tmp_path / "easy", goal), "episode-01")
    hard = GameRuntime(build_forge(tmp_path / "hard"), "episode-01")
    domain = ActionDomain(easy)
    assert domain.h(domain.facts()) == 0
    assert domain.candidates() == ActionDomain(hard).candidates()


def test_fortaleza_style_nested_goal_is_understood(tmp_path: Path):
    goal = (
        "    - type: and\n      conditions:\n"
        "        - type: flag_is_set\n          params: {flag: lit}\n"
        "        - type: or\n          conditions:\n"
        "            - type: entity_dead\n              params: {entity: gem}"
    )
    rt = GameRuntime(build_forge(tmp_path, goal), "episode-01")
    domain = ActionDomain(rt)
    assert domain.h(domain.facts()) == 2


# ----------------------------------------------------------------------
# vocabulary gaps are recorded, never guessed
# ----------------------------------------------------------------------


def _reasons(rt: GameRuntime, edge_ids: set[str]) -> set[str]:
    return {r.reason for r in candidates(rt).unrenderable if r.spec.edge_id in edge_ids}


@pytest.mark.parametrize(
    ("old", "new", "edges", "reason"),
    [
        ('movement_verbs: ["go"]', "movement_verbs: []", {"m_gate", "m_stairs"},
         "no movement verb in vocabulary"),
        ('speech_markers: ["saying"]', "speech_markers: []", {"m_gate"},
         "no speech marker in vocabulary"),
        ("go: [\"go\"]", "walk: [\"go\"]", {"m_gate", "m_stairs"},
         "parser resolved verb 'walk', expected one of ['go']"),
        ('instrument: ["using"]', "instrument: []", {"e_smash"},
         "no instrument preposition in vocabulary"),
        ('recipient: ["onto"]', "recipient: []", {"e_give"},
         "no recipient preposition in vocabulary"),
    ],
)
def test_vocabulary_gaps_are_recorded_as_unrenderable(tmp_path, old, new, edges, reason):
    vocabulary = FORGE_VOCABULARY.replace(old, new)
    assert vocabulary != FORGE_VOCABULARY
    rt = GameRuntime(build_forge(tmp_path, vocabulary=vocabulary), "episode-01")
    assert reason in _reasons(rt, edges)
    recorded = {r.spec.edge_id for r in candidates(rt).unrenderable}
    assert edges <= recorded


def test_world_without_vocabulary_records_every_move_and_preposition_use(tmp_path: Path):
    rt = GameRuntime(build_forge(tmp_path, vocabulary=None), "episode-01")
    cs = candidates(rt)
    reasons = {r.spec.edge_id: r.reason for r in cs.unrenderable if r.spec.kind == "move"}
    assert reasons == {
        "m_gate": "no movement verb in vocabulary",
        "m_stairs": "no movement verb in vocabulary",
        "m_big": "no movement verb in vocabulary",
        "m_hatch": "no movement verb in vocabulary",
    }
    # Acts that need no vocabulary word still render; the rest are recorded.
    assert cs.commands() == (
        "look", "douse Gem", "forge Gem", "burn Gem",
        "pick Chest", "pick Gem", "pick Hammer", "pick Twin",
    )
    assert {r.spec.edge_id for r in cs.unrenderable if r.spec.kind == "act"} == {
        "e_give", "e_smash", "e_clean", "e_pick",  # e_pick: only the twin clash
    }


def test_wildcard_with_nothing_present_is_skipped_not_dropped(forge: GameRuntime):
    forge.state.get_entity("hammer").spatial_anchor = "vault"
    forge.state.get_entity("avatar").spatial_anchor = "cellar"
    skipped = {r.spec.edge_id: r.reason for r in candidates(forge).skipped}
    assert skipped["e_pick"] == "no entity present for target wildcard"
    assert skipped["e_give"] == "context 'chest' not present"
    assert skipped["e_clean"] == "target 'gem' not present"


def test_protagonist_in_limbo_has_no_candidates(forge: GameRuntime):
    forge.state.get_entity("avatar").spatial_anchor = None
    assert candidates(forge) == CandidateSet()
    assert ActionDomain(forge).facts() >= frozenset({("loc", "gem", "hall")})
    assert not any(f[0] == "at" for f in ActionDomain(forge).facts())


# ----------------------------------------------------------------------
# Entity.type is never consulted
# ----------------------------------------------------------------------


class _TypeTrap(Entity):
    """An Entity whose ``type`` cannot be read (assignment is ignored)."""

    @property
    def type(self):  # type: ignore[override]
        raise AssertionError("Entity.type must never be read by the domain")

    @type.setter
    def type(self, value):
        pass


def test_domain_never_reads_entity_type(forge: GameRuntime):
    state = forge.state
    expected = ActionDomain(forge).candidates()
    for eid, e in list(state.entities.items()):
        state.entities[eid] = _TypeTrap(eid, "ignored", e.name, e.components, e.spatial_anchor)
    domain = ActionDomain(forge)
    cs = domain.candidates()
    facts = domain.facts()
    assert cs == expected
    assert domain.rank(cs, facts).commands() != ()
    assert domain.h(facts) == 104
