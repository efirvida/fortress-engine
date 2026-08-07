"""Tests for MinimalParser — RED phase (E2.1).

Verify the parser ABC contract and minimal parsing:
  movement (IR <door>), examination (EXAMINAR <target>),
  action (COGER <item>), unknown input, normalization,
  verb extraction, and subject resolution.

All tests follow Strict TDD: RED first (this file), then GREEN in parser_interface.py.
"""

import pytest

from fortress_engine.entities.entity import Entity, ParsedCommand
from fortress_engine.engine.state import WorldState


# ===================================================================
# Production import — will fail until MinimalParser is implemented
# ===================================================================

from fortress_engine.plugins.parser_interface import (
    MinimalParser,
    ParserInterface,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def world() -> WorldState:
    """Minimal world state with an active protagonist."""
    state = WorldState(
        entities={
            "hero": Entity("hero", "player", "Hero", {"max_weight": 40}, "room_a"),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
        turn_number=0,
    )
    return state


@pytest.fixture
def parser() -> MinimalParser:
    """Create a minimal parser instance."""
    return MinimalParser()


# ===================================================================
# ABC conformance
# ===================================================================


def test_parser_is_instance_of_abc(parser):
    """MinimalParser is an instance of ParserInterface."""
    assert isinstance(parser, ParserInterface)


# ===================================================================
# Movement — IR <door>
# ===================================================================


def test_parse_ir_norte(world, parser):
    """'ir norte' → verb='ir', target='norte'."""
    result = parser.parse("ir norte", world)
    assert isinstance(result, ParsedCommand)
    assert result.verb == "ir"
    assert result.target == "norte"
    assert result.subject == "hero"


def test_parse_ir_sur(world, parser):
    """'IR SUR' → normalized lowercase verb and target."""
    result = parser.parse("IR SUR", world)
    assert result.verb == "ir"
    assert result.target == "sur"


def test_parse_ir_multi_word_door(world, parser):
    """'ir puerta verde' → target='puerta verde'."""
    result = parser.parse("ir puerta verde", world)
    assert result.verb == "ir"
    assert result.target == "puerta verde"


# ===================================================================
# Examination — EXAMINAR <target>
# ===================================================================


def test_parse_examinar_target(world, parser):
    """'examinar puerta' → verb='examinar', target='puerta'."""
    result = parser.parse("examinar puerta", world)
    assert result.verb == "examinar"
    assert result.target == "puerta"
    assert result.subject == "hero"


def test_parse_examinar_multi_word(world, parser):
    """'EXAMINAR libro viejo' → normalized, target='libro viejo'."""
    result = parser.parse("EXAMINAR libro viejo", world)
    assert result.verb == "examinar"
    assert result.target == "libro viejo"


# ===================================================================
# Action — COGER <item>
# ===================================================================


def test_parse_coger_item(world, parser):
    """'coger llave' → verb='coger', target='llave'."""
    result = parser.parse("coger llave", world)
    assert result.verb == "coger"
    assert result.target == "llave"
    assert result.subject == "hero"


# ===================================================================
# Tilde normalization
# ===================================================================


def test_parse_tilde_normalization(world, parser):
    """Tildes are normalized: á→a, é→e, í→i, ó→o, ú→u, ü→u, ñ→n."""
    result = parser.parse("examinar habitación", world)
    assert result.verb == "examinar"
    assert result.target == "habitacion"


def test_parse_tilde_in_verb(world, parser):
    """Tildes in the verb are normalized."""
    # The word "dejar" has no tilde, but "déjame" would normalize "déjame" → "dejame"
    # Actually let's test a real case: there aren't many verbs with tildes
    # but let's test accented characters generically
    result = parser.parse("  ÉXITO  ", world)
    assert result.verb == "exito"


def test_parse_enye_normalization(world, parser):
    """ñ → n normalization."""
    result = parser.parse("baño puerta", world)
    assert result.verb == "bano"
    assert result.target == "puerta"


def test_parse_dieresis_normalization(world, parser):
    """ü → u normalization."""
    result = parser.parse("pingüino nieve", world)
    assert result.verb == "pinguino"


# ===================================================================
# Article stripping
# ===================================================================


def test_parse_strips_definite_articles(world, parser):
    """Articles 'el', 'la', 'los', 'las' are stripped from target."""
    result = parser.parse("coger la llave", world)
    assert result.target == "llave"


def test_parse_strips_indefinite_articles(world, parser):
    """Articles 'un', 'una' are stripped from target."""
    result = parser.parse("coger un libro", world)
    assert result.target == "libro"


def test_parse_strips_article_el(world, parser):
    """Article 'el' is stripped."""
    result = parser.parse("examinar el cuadro", world)
    assert result.target == "cuadro"


def test_parse_strips_article_los(world, parser):
    """Article 'los' is stripped."""
    result = parser.parse("mirar los cuadros", world)
    assert result.target == "cuadros"


def test_parse_strips_preposition_al(world, parser):
    """Preposition 'al' is stripped."""
    result = parser.parse("ir al norte", world)
    assert result.target == "norte"


# ===================================================================
# Single-word commands
# ===================================================================


def test_parse_single_word_verb(world, parser):
    """'inventario' → verb='inventario', target=None."""
    result = parser.parse("inventario", world)
    assert result.verb == "inventario"
    assert result.target is None
    assert result.subject == "hero"


def test_parse_mirar_no_target(world, parser):
    """'mirar' → verb='mirar', target=None."""
    result = parser.parse("mirar", world)
    assert result.verb == "mirar"
    assert result.target is None


# ===================================================================
# Unknown input — graceful, no exceptions
# ===================================================================


def test_parse_unknown_no_exception(world, parser):
    """Unknown input does not raise, returns a valid ParsedCommand."""
    result = parser.parse("xyzzy", world)
    assert isinstance(result, ParsedCommand)
    assert result.verb == "xyzzy"
    assert result.target is None


def test_parse_empty_string(world, parser):
    """Empty input returns a ParsedCommand with empty verb."""
    result = parser.parse("", world)
    assert isinstance(result, ParsedCommand)
    assert result.subject == "hero"


def test_parse_whitespace_only(world, parser):
    """Whitespace-only input is handled gracefully."""
    result = parser.parse("   ", world)
    assert isinstance(result, ParsedCommand)
    assert result.subject == "hero"


def test_parse_gibberish_no_exception(world, parser):
    """Gibberish returns a ParsedCommand — orchestrator handles error_output."""
    result = parser.parse("!!@#$%", world)
    assert isinstance(result, ParsedCommand)
    # The verb should be the raw text or a safe fallback
    assert result.subject == "hero"


# ===================================================================
# Subject resolution — always active protagonist
# ===================================================================


def test_parse_subject_resolves_to_active_protagonist(world, parser):
    """Subject is always world_state.active_protagonist_id."""
    result = parser.parse("ir norte", world)
    assert result.subject == "hero"

    # Change active protagonist
    world.entities["sidekick"] = Entity(
        "sidekick", "player", "Sidekick", {}, "room_a"
    )
    world.player_controlled_entities.append("sidekick")
    world.active_protagonist_id = "sidekick"

    result2 = parser.parse("ir norte", world)
    assert result2.subject == "sidekick"


# ===================================================================
# Stop word stripping — multiple articles and prepositions
# ===================================================================


def test_parse_strips_conjunction_del(world, parser):
    """Contraction 'del' is stripped."""
    result = parser.parse("coger la llave del cajon", world)
    assert result.target == "llave cajon"


def test_parse_strips_por(world, parser):
    """Preposition 'por' is stripped."""
    result = parser.parse("ir por la ventana", world)
    assert result.target == "ventana"


def test_parse_target_empty_after_strip(world, parser):
    """When target becomes empty after stripping articles, target is None."""
    result = parser.parse("examinar la", world)
    assert result.target is None


# ===================================================================
# Context and instrument — always None in minimal parser
# ===================================================================


def test_parse_context_always_none(world, parser):
    """Minimal parser never fills context."""
    result = parser.parse("dar llave a guardia", world)
    assert result.context is None


def test_parse_instrument_always_none(world, parser):
    """Minimal parser never fills instrument."""
    result = parser.parse("abrir puerta con llave", world)
    assert result.instrument is None


# ===================================================================
# Known game verbs pass-through
# ===================================================================


@pytest.mark.parametrize(
    "raw, expected_verb, expected_target",
    [
        ("dejar llave", "dejar", "llave"),
        ("usar llave", "usar", "llave"),
        ("abrir puerta", "abrir", "puerta"),
        ("romper jarron", "romper", "jarron"),
        ("gritar", "gritar", None),
        ("silbar", "silbar", None),
        ("esperar", "esperar", None),
        ("terminar", "terminar", None),
        ("guardar", "guardar", None),
        ("cargar", "cargar", None),
        ("grupo", "grupo", None),
    ],
)
def test_parse_known_verbs(world, parser, raw, expected_verb, expected_target):
    """Known game verbs are parsed correctly as verb+target."""
    result = parser.parse(raw, world)
    assert result.verb == expected_verb
    assert result.target == expected_target
