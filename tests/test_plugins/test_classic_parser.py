"""Tests for ClassicParser — RED phase (N4.2, N4.3).

Verify the full deterministic Spanish parser:
  - 37-constant verb→canonical mapping + EXAMINAR synonym
  - Unknown verb non-throwing
  - NFKD normalization and combining-mark removal
  - V2 stopword stripping (9 stopwords)
  - CON→instrument routing
  - A→context routing
  - DICIENDO/RESPONDIENDO speech markers → text
  - DECIR/RESPONDER standalone speech → text
  - Entity resolution (exact, partial, shortest-wins, ambiguous, no-match)
  - Resolution scope: spatial anchor + protagonist inventory
  - Language default and override
  - Empty/whitespace input
  - Subject = active_protagonist_id
  - Vocabulary override vs DEFAULT_SPANISH_VOCABULARY
  - The e-word MUST NOT appear anywhere in this file.

Strict TDD: this file is written BEFORE the production module.
All imports reference symbols that do NOT exist yet.
"""

from __future__ import annotations

import pytest

from fortress_engine.entities.entity import Entity, ParsedCommand
from fortress_engine.entities.loader import Vocabulary
from fortress_engine.engine.state import WorldState


# ===================================================================
# Production import — will fail until ClassicParser is implemented
# ===================================================================

from fortress_engine.plugins.classic_parser import ClassicParser


# ===================================================================
# Helpers
# ===================================================================


def _make_vocabulary_dict(**overrides):
    """Return a minimal vocabulary dict with full 37-verb coverage."""
    default = {
        "language": "es",
        "verbs": {
            "ir": ["ATRAVESAR", "IR", "CRUZAR", "PASAR"],
            "tomar": ["TOMAR", "COGER"],
            "dejar": ["SOLTAR", "DEJAR"],
            "abrir": ["ABRIR"],
            "matar": ["MATAR", "ASESINAR"],
            "mirar": ["OBSERVAR", "MIRAR"],
            "examinar": ["LEER", "VER", "EXAMINAR"],
            "romper": ["ROMPER", "FORZAR", "DESTROZAR"],
            "interrogar": ["PREGUNTAR", "INTERROGAR"],
            "inventario": ["INVENTARIO"],
            "dar": ["REGALAR", "DAR"],
            "con": ["CON"],
            "a": ["A"],
            "terminar": ["ABANDONAR", "TERMINAR"],
            "respondiendo": ["RESPONDIENDO"],
            "diciendo": ["DICIENDO"],
            "ejecutar": ["EJECUTAR"],
            "salvar": ["SALVAR"],
            "porciento": ["PORCIENTO"],
            "todo": ["TODO"],
            "pesar": ["PESAR"],
            "orinar": ["MIAR", "ORINAR"],
            "cls": ["CLS"],
        },
        "stopwords": [
            "el", "la", "los", "las", "un", "una", "al", "del", "por",
        ],
        "prepositions": {
            "instrument": ["con"],
            "recipient": ["a"],
        },
        "speech_markers": ["diciendo", "respondiendo"],
        "speech_verbs": ["decir", "responder"],
        "messages": {},
        "movement_verbs": [],
        "system_commands": {},
    }
    default.update(overrides)
    return default


def _v(**kwargs):
    """Shorthand to create a Vocabulary from a dict."""
    return Vocabulary(**_make_vocabulary_dict(**kwargs))


# ===================================================================
# Entity names — Spanish, matching the spec scenarios
# ===================================================================

PUERTA_PRINCIPAL = "Puerta principal"
PUERTA_SECRETA = "Puerta secreta"
LLAVE = "Llave oxidada"
ESPADA = "Espada"


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def world() -> WorldState:
    """World state with protagonist and 4-room entities for resolution tests.

    Entities:
      - hero (protagonist, in room_a)
      - Puerta principal (in room_a)
      - Puerta secreta (in room_a)
      - Llave oxidada (in room_a, movable item)
      - Espada (in hero's inventory)

    This matches the spec's 4-entity resolution fixture.
    """
    state = WorldState(
        entities={
            "hero": Entity(
                "hero", "player", "Hero", {"max_weight": 40}, "room_a"),
            "room_a": Entity(
                "room_a", "room", "Sala Principal", {}, None),
            "puerta_principal": Entity(
                "puerta_principal", "portal", PUERTA_PRINCIPAL, {}, "room_a"),
            "puerta_secreta": Entity(
                "puerta_secreta", "portal", PUERTA_SECRETA, {}, "room_a"),
            "llave": Entity(
                "llave", "item", LLAVE, {}, "room_a"),
            "espada": Entity(
                "espada", "item", ESPADA, {}, "hero"),
        },
        player_controlled_entities=["hero"],
        active_protagonist_id="hero",
        current_episode_id="episode-01",
        turn_number=0,
    )
    return state


@pytest.fixture
def parser() -> ClassicParser:
    """Create a ClassicParser with default vocabulary."""
    return ClassicParser()


@pytest.fixture
def full_vocabulary() -> Vocabulary:
    """Full 37-verb vocabulary matching the spec table."""
    return _v()


# ===================================================================
# Safety net — imports must resolve
# ===================================================================


def test_classic_parser_importable():
    """ClassicParser is importable from its module."""
    assert ClassicParser is not None


def test_classic_parser_is_instance_of_parser_interface():
    """ClassicParser is a ParserInterface."""
    from fortress_engine.plugins.parser_interface import ParserInterface
    assert isinstance(ClassicParser(), ParserInterface)


# ===================================================================
# N4.2 — 37-constant verb→canonical mapping + EXAMINAR
# ===================================================================


# Canonical verb table from spec (38 total: 37 Fortaleza + EXAMINAR)
VERB_MAPPINGS = [
    ("atravesar", "ir"),          # 1
    ("ir", "ir"),                 # 2
    ("tomar", "tomar"),           # 3
    ("coger", "tomar"),           # 4
    ("soltar", "dejar"),          # 5
    ("dejar", "dejar"),           # 6
    ("abrir", "abrir"),           # 7
    ("matar", "matar"),           # 8
    ("asesinar", "matar"),        # 9
    ("observar", "mirar"),        # 10
    ("mirar", "mirar"),           # 11
    ("leer", "examinar"),         # 12
    ("ver", "examinar"),          # 13
    ("romper", "romper"),         # 14
    ("forzar", "romper"),         # 15
    ("preguntar", "interrogar"),  # 16
    ("interrogar", "interrogar"), # 17
    ("inventario", "inventario"), # 18
    ("regalar", "dar"),           # 19
    ("dar", "dar"),               # 20
    ("con", "con"),               # 21
    ("a", "a"),                   # 22
    ("abandonar", "terminar"),    # 23
    ("terminar", "terminar"),     # 24
    ("respondiendo", "respondiendo"), # 25
    ("diciendo", "diciendo"),     # 26
    ("ejecutar", "ejecutar"),     # 27
    ("salvar", "salvar"),         # 28
    ("destrozar", "romper"),      # 29
    ("cruzar", "ir"),             # 30
    ("porciento", "porciento"),   # 31
    ("todo", "todo"),             # 32
    ("pesar", "pesar"),           # 33
    ("miar", "orinar"),           # 34
    ("orinar", "orinar"),         # 35
    ("cls", "cls"),               # 36
    ("pasar", "ir"),              # 37
    ("examinar", "examinar"),     # EXTRA — TDD §4.15 synonym
]


@pytest.mark.parametrize("input_verb, expected_canonical", VERB_MAPPINGS)
def test_verb_canonicalizes(world, parser, input_verb, expected_canonical):
    """Every Fortaleza verb maps to its canonical form."""
    result = parser.parse(input_verb, world)
    assert result.verb == expected_canonical, (
        f"'{input_verb}' should canonicalize to '{expected_canonical}', "
        f"got '{result.verb}'"
    )
    assert result.subject == "hero"


# ===================================================================
# N4.2 — Unknown verb non-throwing
# ===================================================================


def test_parse_unknown_verb_non_throwing(world, parser):
    """Unknown verbs MUST NOT raise — return verb as-is."""
    result = parser.parse("xyzzy", world)
    assert isinstance(result, ParsedCommand)
    assert result.verb == "xyzzy"
    assert result.target is None
    assert result.subject == "hero"


def test_parse_gibberish_non_throwing(world, parser):
    """Gibberish input is never rejected."""
    result = parser.parse("!!@#$%", world)
    assert isinstance(result, ParsedCommand)
    assert result.subject == "hero"


# ===================================================================
# N4.2 — Normalization (NFKD + combining-mark strip)
# ===================================================================


def test_normalize_tilde_in_verb(world, parser):
    """áéíóú → aeiou in verb."""
    result = parser.parse("abrir habitación", world)
    assert result.verb == "abrir"
    assert result.target == "habitacion"


def test_normalize_tilde_in_verb_front(world, parser):
    """Tilde removal in the verb position."""
    result = parser.parse("éxito meta", world)
    assert result.verb == "exito"
    assert result.target == "meta"


def test_normalize_enye(world, parser):
    """ñ → n normalization."""
    result = parser.parse("mirar cañon", world)
    assert result.verb == "mirar"
    assert result.target == "canon"


def test_normalize_dieresis(world, parser):
    """ü → u normalization."""
    result = parser.parse("tomar pingüino", world)
    assert result.verb == "tomar"
    assert result.target == "pinguino"


def test_normalize_combining_marks_target(world, parser):
    """Combining marks removed from target tokens."""
    result = parser.parse("ver muñeco", world)
    assert result.verb == "examinar"
    assert result.target == "muneco"


# ===================================================================
# N4.2 — V2 stopword stripping (9 stopwords)
# ===================================================================


STOPWORDS = ["el", "la", "los", "las", "un", "una", "al", "del", "por"]


@pytest.mark.parametrize("stopword", STOPWORDS)
def test_strips_stopword(world, parser, stopword):
    """Each V2 stopword is stripped from the target phrase."""
    result = parser.parse(f"abrir {stopword} puerta", world)
    assert result.target == "puerta"


def test_strips_multiple_stopwords(world, parser):
    """Multiple stopwords are stripped from target."""
    result = parser.parse("abrir la puerta del castillo", world)
    assert result.target == "puerta castillo"


def test_target_empty_after_stopword_strip(world, parser):
    """When target becomes empty after stripping, target is None."""
    result = parser.parse("mirar el", world)
    assert result.target is None


# ===================================================================
# N4.2 — CON → instrument routing
# ===================================================================


def test_con_routes_to_instrument(world, parser):
    """CON routes following tokens to instrument field."""
    result = parser.parse("abrir puerta con llave oxidada", world)
    assert result.verb == "abrir"
    assert result.target == "puerta"
    assert result.instrument is not None
    assert "llave" in result.instrument


def test_con_entity_resolution(world, parser):
    """CON routes to instrument with entity resolution."""
    result = parser.parse("abrir puerta con llave oxidada", world)
    # "llave" should resolve to entity "llave" (Llave oxidada)
    assert result.instrument == "llave"


def test_con_without_match(world, parser):
    """CON instrument without entity match returns raw phrase."""
    result = parser.parse("abrir puerta con martillo magico", world)
    assert result.instrument == "martillo magico"


# ===================================================================
# N4.2 — A → context routing
# ===================================================================


def test_a_routes_to_context(world, parser):
    """A routes following tokens to context field."""
    result = parser.parse("dar llave a guardia", world)
    assert result.verb == "dar"
    assert result.target == "llave"
    assert result.context == "guardia"


def test_a_stopword_does_not_route(world, parser):
    """'al' is a stopword — does NOT route to context."""
    result = parser.parse("ir al norte", world)
    assert result.verb == "ir"
    assert result.target == "norte"
    assert result.context is None


def test_a_entity_resolution(world, parser):
    """A routes to context with entity resolution when target matches."""
    result = parser.parse("dar espada a puerta principal", world)
    assert result.context == "puerta_principal"


# ===================================================================
# N4.2 — DICIENDO / RESPONDIENDO → text (preserving stopwords)
# ===================================================================


def test_diciendo_extracts_text(world, parser):
    """DICIENDO splits remainder into text, stopwords preserved."""
    result = parser.parse("abrir puerta diciendo treinta y nueve", world)
    assert result.verb == "abrir"
    assert result.target == "puerta"
    assert result.text == "treinta y nueve"


def test_diciendo_preserves_stopwords_in_text(world, parser):
    """Speech text after DICIENDO keeps stopwords ('la', 'el', etc.)."""
    result = parser.parse("abrir puerta diciendo la palabra magica", world)
    assert result.text == "la palabra magica"


def test_respondiendo_extracts_text(world, parser):
    """RESPONDIENDO splits remainder into text."""
    result = parser.parse("abrir puerta respondiendo el sol", world)
    assert result.verb == "abrir"
    assert result.target == "puerta"
    assert result.text == "el sol"


def test_speech_text_normalized(world, parser):
    """Speech text is normalized (tildes removed)."""
    result = parser.parse("abrir puerta diciendo ábrete sésamo", world)
    assert result.text == "abrete sesamo"


def test_speech_marker_without_tail(world, parser):
    """DICIENDO at end of input → text is None."""
    result = parser.parse("abrir puerta diciendo", world)
    assert result.text is None


def test_diciendo_entity_resolution_for_target(world, parser):
    """Target before DICIENDO is entity-resolved; text is separate."""
    result = parser.parse("abrir puerta principal diciendo abracadabra", world)
    assert result.target == "puerta_principal"
    assert result.text == "abracadabra"


# ===================================================================
# N4.2 — DECIR / RESPONDER standalone → text
# ===================================================================


def test_decir_standalone_puts_remainder_in_text(world, parser):
    """Standalone DECIR puts whole remainder into text."""
    result = parser.parse("decir treinta y nueve", world)
    assert result.verb == "decir"
    assert result.target is None
    assert result.text == "treinta y nueve"


def test_responder_standalone_puts_remainder_in_text(world, parser):
    """Standalone RESPONDER puts whole remainder into text."""
    result = parser.parse("responder el sol", world)
    assert result.verb == "responder"
    assert result.target is None
    assert result.text == "el sol"


# ===================================================================
# N4.3 — Entity resolution (exact, partial, shortest-wins, ambiguous,
#        no-match)
# ===================================================================


def test_entity_exact_match(world, parser):
    """Exact name match returns entity_id."""
    result = parser.parse("abrir puerta principal", world)
    assert result.target == "puerta_principal"


def test_entity_exact_match_other(world, parser):
    """Exact match for the other door works too."""
    result = parser.parse("abrir puerta secreta", world)
    assert result.target == "puerta_secreta"


def test_entity_partial_single_word(world, parser):
    """Partial match with single word resolves to shortest entity name."""
    result = parser.parse("mirar puerta", world)
    # "puerta" appears in both "Puerta principal" and "Puerta secreta"
    # Both are 2 words. Shortest-wins means same length → ambiguous → raw
    assert result.target == "puerta"


def test_entity_partial_unique_match(world, parser):
    """Partial where only one entity contains all input words."""
    result = parser.parse("mirar principal", world)
    assert result.target == "puerta_principal"


def test_entity_partial_secreta(world, parser):
    """'secreta' only matches Puerta secreta."""
    result = parser.parse("mirar secreta", world)
    assert result.target == "puerta_secreta"


def test_entity_no_match(world, parser):
    """No entity matches → target is raw phrase."""
    result = parser.parse("mirar alfombra roja", world)
    assert result.target == "alfombra roja"


def test_entity_inventory_scope(world, parser):
    """Entities in protagonist inventory are searchable."""
    result = parser.parse("mirar espada", world)
    assert result.target == "espada"


def test_entity_not_in_scope_not_found(world, parser):
    """Entities not in anchor or inventory are not resolved."""
    # Add entity in a different room — should not be found
    world.entities["otra_llave"] = Entity(
        "otra_llave", "item", "Llave dorada", {}, "room_b"
    )
    result = parser.parse("mirar llave dorada", world)
    # This won't match room_b's entity — raw phrase returned
    assert result.target == "llave dorada"


# ===================================================================
# N4.3 — Inventory + anchor scope
# ===================================================================


def test_entity_in_anchor_resolves(world, parser):
    """Entity in current spatial anchor is found."""
    result = parser.parse("examinar llave oxidada", world)
    assert result.target == "llave"


def test_entity_in_inventory_resolves(world, parser):
    """Entity in protagonist inventory is found."""
    result = parser.parse("dejar espada", world)
    assert result.target == "espada"


# ===================================================================
# N4.3 — Language default and override
# ===================================================================


def test_language_default_es():
    """ClassicParser() defaults language to 'es'."""
    p = ClassicParser()
    assert p.language == "es"


def test_language_override_en():
    """ClassicParser(language='en') stores 'en'."""
    p = ClassicParser(language="en")
    assert p.language == "en"


def test_language_read_only():
    """language is a read-only property."""
    p = ClassicParser()
    with pytest.raises(AttributeError):
        p.language = "fr"  # type: ignore[misc]


# ===================================================================
# N4.3 — Empty / whitespace input
# ===================================================================


def test_empty_input(world, parser):
    """Empty string returns ParsedCommand with empty verb."""
    result = parser.parse("", world)
    assert isinstance(result, ParsedCommand)
    assert result.subject == "hero"
    assert result.verb == ""


def test_whitespace_only(world, parser):
    """Whitespace-only input is handled gracefully."""
    result = parser.parse("   ", world)
    assert isinstance(result, ParsedCommand)
    assert result.subject == "hero"
    assert result.verb == ""


# ===================================================================
# N4.3 — Subject = active_protagonist_id
# ===================================================================


def test_subject_is_active_protagonist(world, parser):
    """Subject is always world_state.active_protagonist_id."""
    result = parser.parse("ir norte", world)
    assert result.subject == "hero"

    # Change protagonist
    world.entities["sidekick"] = Entity(
        "sidekick", "player", "Sidekick", {}, "room_a"
    )
    world.player_controlled_entities.append("sidekick")
    world.active_protagonist_id = "sidekick"

    result2 = parser.parse("ir norte", world)
    assert result2.subject == "sidekick"


# ===================================================================
# N4.3 — Vocabulary override vs DEFAULT_SPANISH_VOCABULARY
# ===================================================================


def test_default_spanish_vocabulary(world):
    """ClassicParser() without override uses DEFAULT_SPANISH_VOCABULARY."""
    p = ClassicParser()
    result = p.parse("coger espada", world)
    assert result.verb == "tomar"


def test_vocabulary_dict_override(world):
    """Constructor override with a dict changes verb mapping."""
    custom = _make_vocabulary_dict(
        verbs={"custom": ["COGER"]},  # override: COGER → custom
    )
    p = ClassicParser(vocabulary=custom)
    result = p.parse("coger espada", world)
    assert result.verb == "custom"


def test_vocabulary_dataclass_override(world, full_vocabulary):
    """Constructor override with a Vocabulary dataclass works."""
    p = ClassicParser(vocabulary=full_vocabulary)
    result = p.parse("coger llave", world)
    assert result.verb == "tomar"


def test_vocabulary_override_does_not_affect_default(world, full_vocabulary):
    """Override on one parser does not affect another instance."""
    p1 = ClassicParser(vocabulary=full_vocabulary)
    p2 = ClassicParser()
    result1 = p1.parse("coger espada", world)
    result2 = p2.parse("coger espada", world)
    assert result1.verb == "tomar"
    assert result2.verb == "tomar"


def test_vocabulary_override_stopwords(world):
    """Override can change stopword list."""
    custom = _make_vocabulary_dict(stopwords=[])
    p = ClassicParser(vocabulary=custom)
    result = p.parse("abrir la puerta", world)
    assert result.target == "la puerta"


# ===================================================================
# N4.2 — DEJAR TODO
# ===================================================================


def test_dejar_todo(world, parser):
    """DEJAR TODO: verb='dejar', target='todo'."""
    result = parser.parse("dejar todo", world)
    assert result.verb == "dejar"
    assert result.target == "todo"


# ===================================================================
# N4.3 — Context/instrument edge cases
# ===================================================================


def test_con_followed_by_a(world, parser):
    """CON then A routes correctly: instrument takes tokens after CON,
    A is treated as context if exists after CON tokens."""
    # "abrir puerta con llave a bruja"
    result = parser.parse("abrir puerta con llave a bruja", world)
    assert result.target == "puerta"
    assert result.instrument == "llave"
    assert result.context == "bruja"


def test_a_before_con(world, parser):
    """A before CON: both routed correctly."""
    result = parser.parse("dar llave a guardia con mano", world)
    assert result.verb == "dar"
    assert result.target == "llave"
    assert result.context == "guardia"
    assert result.instrument == "mano"


def test_no_prepositions(world, parser):
    """When no prepositions present, context and instrument are None."""
    result = parser.parse("mirar puerta", world)
    assert result.context is None
    assert result.instrument is None


# ===================================================================
# Speech verb interaction with entity resolution
# ===================================================================


def test_decir_does_not_resolve_target(world, parser):
    """DECIR puts whole remainder in text, no target resolution."""
    result = parser.parse("decir puerta principal", world)
    assert result.verb == "decir"
    assert result.target is None
    assert result.text == "puerta principal"


def test_diciendo_target_still_resolved(world, parser):
    """DICIENDO extracts text but target before marker is entity-resolved."""
    result = parser.parse("mirar principal diciendo hola", world)
    assert result.verb == "mirar"
    assert result.target == "puerta_principal"
    assert result.text == "hola"


# ===================================================================
# Verify the e-word is NOT in the production module
# ===================================================================


def test_e_word_not_in_classic_parser_module():
    """The e-word MUST NOT appear anywhere in classic_parser.py."""
    import inspect
    from fortress_engine.plugins import classic_parser
    source = inspect.getsource(classic_parser)
    assert "esperar" not in source.lower(), (
        "the e-word found in classic_parser.py — this MUST NOT appear"
    )


# ===================================================================
# Edge case: protagonist not in entities (KeyError branch)
# ===================================================================


def test_protagonist_not_in_entities(world, parser):
    """When active_protagonist_id is not in entities, parser handles it
    gracefully (anchor_id = None, no entities in scope)."""
    world.active_protagonist_id = "missing_hero"
    result = parser.parse("mirar puerta", world)
    assert result.verb == "mirar"
    assert result.target == "puerta"  # raw phrase, unresolved
