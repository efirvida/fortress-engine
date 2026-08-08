"""Tests for WorldYAML language/plugin fields, PluginConfigYAML, Vocabulary,
and vocabulary loading (N3 — world-yaml-extensions spec).

Strict TDD: RED phase — all imports reference production symbols that do NOT
exist yet. This file MUST fail on first run.
"""

from __future__ import annotations

import pytest

from fortress_engine.entities.loader import (
    EntityLoader,
    PluginConfigYAML,
    VocabularyYAML,
    WorldYAML,
    Vocabulary,
)


# ===================================================================
# Helpers
# ===================================================================


def _write_yaml(path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ===================================================================
# N3.1 — PluginConfigYAML model
# ===================================================================


class TestPluginConfigYAML:
    """PluginConfigYAML validates plugin name + options."""

    def test_plugin_with_options(self):
        """PluginConfigYAML accepts plugin and options."""
        cfg = PluginConfigYAML(plugin="classic", options={"strict": True})
        assert cfg.plugin == "classic"
        assert cfg.options == {"strict": True}

    def test_plugin_defaults(self):
        """PluginConfigYAML defaults options to empty dict."""
        cfg = PluginConfigYAML(plugin="template")
        assert cfg.plugin == "template"
        assert cfg.options == {}

    def test_plugin_missing_name_rejected(self):
        """PluginConfigYAML rejects missing plugin field."""
        with pytest.raises(ValueError, match="plugin"):
            PluginConfigYAML()  # type: ignore[call-arg]

    def test_plugin_extra_fields_forbidden(self):
        """PluginConfigYAML forbids extra fields."""
        with pytest.raises(ValueError, match="unk"):
            PluginConfigYAML(plugin="x", unknown=123)  # type: ignore[call-arg]


# ===================================================================
# N3.1 — WorldYAML language + plugin fields
# ===================================================================


class TestWorldYAMLLanguage:
    """WorldYAML new fields: language, parser, narrator."""

    def test_full_config_object_form(self):
        """WorldYAML parses language + object-form parser/narrator."""
        model = WorldYAML(
            world_id="w1",
            name="Test",
            language="en",
            parser=PluginConfigYAML(plugin="classic", options={"strict": True}),
            narrator=PluginConfigYAML(plugin="template", options={}),
        )
        assert model.language == "en"
        assert isinstance(model.parser, PluginConfigYAML)
        assert model.parser.plugin == "classic"
        assert model.parser.options == {"strict": True}
        assert isinstance(model.narrator, PluginConfigYAML)
        assert model.narrator.plugin == "template"

    def test_defaults_when_missing(self):
        """WorldYAML defaults language='es', parser='classic', narrator='template'."""
        model = WorldYAML(world_id="w1", name="Test")
        assert model.language == "es"
        assert isinstance(model.parser, PluginConfigYAML)
        assert model.parser.plugin == "classic"
        assert model.parser.options == {}
        assert isinstance(model.narrator, PluginConfigYAML)
        assert model.narrator.plugin == "template"
        assert model.narrator.options == {}

    def test_language_only(self):
        """WorldYAML with language only defaults parser/narrator."""
        model = WorldYAML(world_id="w1", name="Test", language="en")
        assert model.language == "en"
        assert model.parser.plugin == "classic"
        assert model.narrator.plugin == "template"

    def test_parser_default_narrator_object(self):
        """WorldYAML with only narrator specified defaults parser."""
        model = WorldYAML(
            world_id="w1",
            name="Test",
            narrator=PluginConfigYAML(plugin="custom", options={"voice": "robotic"}),
        )
        assert model.language == "es"
        assert model.parser.plugin == "classic"
        assert model.narrator.plugin == "custom"
        assert model.narrator.options == {"voice": "robotic"}


class TestWorldYAMLCoercion:
    """String → PluginConfigYAML coercion via field_validator."""

    def test_parser_bare_string_coerced(self):
        """Bare string parser: 'classic' coerces to PluginConfigYAML."""
        model = WorldYAML(world_id="w1", name="Test", parser="classic")  # type: ignore[arg-type]
        assert isinstance(model.parser, PluginConfigYAML)
        assert model.parser.plugin == "classic"
        assert model.parser.options == {}

    def test_narrator_bare_string_coerced(self):
        """Bare string narrator: 'template' coerces to PluginConfigYAML."""
        model = WorldYAML(world_id="w1", name="Test", narrator="template")  # type: ignore[arg-type]
        assert isinstance(model.narrator, PluginConfigYAML)
        assert model.narrator.plugin == "template"
        assert model.narrator.options == {}

    def test_both_bare_strings_coerced(self):
        """Both parser and narrator coerced from bare strings."""
        model = WorldYAML(
            world_id="w1", name="Test", parser="custom_parser", narrator="custom_narrator"  # type: ignore[arg-type]
        )
        assert model.parser.plugin == "custom_parser"
        assert model.narrator.plugin == "custom_narrator"

    def test_parser_object_form_preserved(self):
        """Object-form parser passes through unmodified."""
        cfg = PluginConfigYAML(plugin="classic", options={"debug": True})
        model = WorldYAML(world_id="w1", name="Test", parser=cfg)
        assert model.parser is cfg
        assert model.parser.options == {"debug": True}

    def test_parser_dict_form_passes_through_validator(self):
        """Dict passed as parser value goes through before validator
        (covers the ``isinstance(v, dict)`` branch in the field_validator)."""
        model = WorldYAML(
            world_id="w1",
            name="Test",
            parser={"plugin": "custom", "options": {"debug": True}},  # type: ignore[arg-type]
        )
        assert isinstance(model.parser, PluginConfigYAML)
        assert model.parser.plugin == "custom"
        assert model.parser.options == {"debug": True}

    def test_narrator_dict_form_passes_through_validator(self):
        """Dict passed as narrator value goes through before validator."""
        model = WorldYAML(
            world_id="w1",
            name="Test",
            narrator={"plugin": "custom_narr", "options": {"voice": "deep"}},  # type: ignore[arg-type]
        )
        assert isinstance(model.narrator, PluginConfigYAML)
        assert model.narrator.plugin == "custom_narr"
        assert model.narrator.options == {"voice": "deep"}

    def test_invalid_plugin_type_rejected(self):
        """Non-string, non-dict parser value is rejected."""
        with pytest.raises(ValueError, match="parser"):
            WorldYAML(world_id="w1", name="Test", parser=123)  # type: ignore[arg-type]

    def test_narrator_invalid_type_rejected(self):
        """Non-string, non-dict narrator value is rejected."""
        with pytest.raises(ValueError, match="narrator"):
            WorldYAML(world_id="w1", name="Test", narrator=[])  # type: ignore[arg-type]

    def test_world_yaml_extra_fields_forbidden_on_vocabulary(self):
        """VocabularyYAML (not WorldYAML) forbids extra fields.

        This tests the constraint on VocabularyYAML, not WorldYAML.
        WorldYAML itself has extra fields allowed for backward-compat.
        """
        with pytest.raises(ValueError, match="unk"):
            VocabularyYAML(
                verbs={"ir": ["ATRAVESAR"]},
                stopwords=["el"],
                prepositions={"instrument": ["con"]},
                speech_markers=["diciendo"],
                speech_verbs=["decir"],
                unknown_field=42,  # type: ignore[call-arg]
            )


# ===================================================================
# N3.2 — VocabularyYAML Pydantic model
# ===================================================================


class TestVocabularyYAML:
    """VocabularyYAML validates the 6-section vocabulary schema."""

    def test_full_vocabulary(self):
        """VocabularyYAML with all 6 sections parses correctly."""
        model = VocabularyYAML(
            language="fr",
            verbs={"ir": ["ATRAVESAR", "CRUZAR"], "tomar": ["COGER"]},
            stopwords=["el", "la", "un", "una"],
            prepositions={"instrument": ["con"], "recipient": ["a"]},
            speech_markers=["diciendo", "respondiendo"],
            speech_verbs=["decir", "responder"],
        )
        assert model.language == "fr"
        assert model.verbs == {"ir": ["ATRAVESAR", "CRUZAR"], "tomar": ["COGER"]}
        assert model.stopwords == ["el", "la", "un", "una"]
        assert model.prepositions == {"instrument": ["con"], "recipient": ["a"]}
        assert model.speech_markers == ["diciendo", "respondiendo"]
        assert model.speech_verbs == ["decir", "responder"]

    def test_language_defaults_to_none(self):
        """VocabularyYAML language defaults to None when not specified."""
        model = VocabularyYAML(
            verbs={"ir": ["IR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=[],
            speech_verbs=[],
        )
        assert model.language is None

    def test_verbs_required(self):
        """VocabularyYAML rejects missing verbs."""
        with pytest.raises(ValueError, match="verbs"):
            VocabularyYAML(  # type: ignore[call-arg]
                stopwords=["el"],
                prepositions={"instrument": ["con"]},
                speech_markers=[],
                speech_verbs=[],
            )

    def test_stopwords_required(self):
        """VocabularyYAML rejects missing stopwords."""
        with pytest.raises(ValueError, match="stopwords"):
            VocabularyYAML(  # type: ignore[call-arg]
                verbs={"ir": ["IR"]},
                prepositions={"instrument": ["con"]},
                speech_markers=[],
                speech_verbs=[],
            )

    def test_prepositions_with_empty_dicts(self):
        """VocabularyYAML with empty sub-dicts in prepositions is valid."""
        model = VocabularyYAML(
            verbs={"ir": ["IR"]},
            stopwords=["el"],
            prepositions={"instrument": [], "recipient": []},
            speech_markers=[],
            speech_verbs=[],
        )
        assert model.prepositions == {"instrument": [], "recipient": []}


# ===================================================================
# N3.2 — Vocabulary runtime dataclass
# ===================================================================


class TestVocabularyDataclass:
    """Vocabulary dataclass mirrors VocabularyYAML at runtime."""

    def test_round_trip_all_fields(self):
        """Vocabulary stores all 9 sections from YAML model."""
        vocab = Vocabulary(
            language="es",
            verbs={"ir": ["ATRAVESAR", "CRUZAR"], "tomar": ["COGER"]},
            stopwords=["el", "la", "los"],
            prepositions={"instrument": ["con"], "recipient": ["a"]},
            speech_markers=["diciendo"],
            speech_verbs=["decir"],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        assert vocab.language == "es"
        assert vocab.verbs == {"ir": ["ATRAVESAR", "CRUZAR"], "tomar": ["COGER"]}
        assert vocab.stopwords == ["el", "la", "los"]
        assert vocab.prepositions == {"instrument": ["con"], "recipient": ["a"]}
        assert vocab.speech_markers == ["diciendo"]
        assert vocab.speech_verbs == ["decir"]

    def test_language_none(self):
        """Vocabulary language can be None."""
        vocab = Vocabulary(
            language=None,
            verbs={},
            stopwords=[],
            prepositions={"instrument": [], "recipient": []},
            speech_markers=[],
            speech_verbs=[],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        assert vocab.language is None

    def test_equality(self):
        """Two Vocabularies with same data are equal."""
        v1 = Vocabulary(
            language="es",
            verbs={"ir": ["ATRAVESAR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=["diciendo"],
            speech_verbs=["decir"],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        v2 = Vocabulary(
            language="es",
            verbs={"ir": ["ATRAVESAR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=["diciendo"],
            speech_verbs=["decir"],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        assert v1 == v2

    def test_inequality(self):
        """Two Vocabularies with different data are not equal."""
        v1 = Vocabulary(
            language="es",
            verbs={"ir": ["ATRAVESAR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=["diciendo"],
            speech_verbs=["decir"],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        v2 = Vocabulary(
            language="en",
            verbs={"go": ["WALK"]},
            stopwords=["the"],
            prepositions={"instrument": ["with"]},
            speech_markers=["saying"],
            speech_verbs=["say"],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        assert v1 != v2

    def test_from_yaml_model(self):
        """Vocabulary can be constructed from a VocabularyYAML model."""
        yaml_model = VocabularyYAML(
            language="es",
            verbs={"ir": ["ATRAVESAR"], "tomar": ["COGER"]},
            stopwords=["el", "la"],
            prepositions={"instrument": ["con"], "recipient": ["a"]},
            speech_markers=["diciendo"],
            speech_verbs=["decir"],
        )
        vocab = Vocabulary(
            language=yaml_model.language,
            verbs=dict(yaml_model.verbs),
            stopwords=list(yaml_model.stopwords),
            prepositions={
                k: list(v) for k, v in yaml_model.prepositions.items()
            },
            speech_markers=list(yaml_model.speech_markers),
            speech_verbs=list(yaml_model.speech_verbs),
            messages=dict(yaml_model.messages),
            movement_verbs=list(yaml_model.movement_verbs),
            system_commands={
                k: list(v) for k, v in yaml_model.system_commands.items()
            },
        )
        assert vocab.language == "es"
        assert vocab.verbs == {"ir": ["ATRAVESAR"], "tomar": ["COGER"]}


# ===================================================================
# N3.2 — EntityLoader.load_vocabulary
# ===================================================================


class TestLoadVocabulary:
    """EntityLoader.load_vocabulary reads shared/vocabulary.yaml."""

    def _make_world(self, tmp_path, vocab_content: str | None = None):
        """Create a minimal world with optional vocabulary.yaml."""
        base = tmp_path / "world"
        _write_yaml(
            base / "world.yaml",
            "world_id: test\nname: Test\n",
        )
        if vocab_content is not None:
            _write_yaml(base / "shared" / "vocabulary.yaml", vocab_content)
        # else: no vocab file
        return base

    # -- happy path ----------------------------------------------------

    def test_load_vocabulary_happy_path(self, tmp_path):
        """load_vocabulary loads a valid vocabulary.yaml."""
        base = self._make_world(
            tmp_path,
            """\
language: es
verbs:
  ir: [ATRAVESAR, CRUZAR]
  tomar: [COGER]
stopwords:
  - el
  - la
prepositions:
  instrument: [con]
  recipient: [a]
speech_markers:
  - diciendo
speech_verbs:
  - decir
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()

        assert vocab is not None
        assert isinstance(vocab, Vocabulary)
        assert vocab.language == "es"
        assert vocab.verbs == {"ir": ["ATRAVESAR", "CRUZAR"], "tomar": ["COGER"]}
        assert vocab.stopwords == ["el", "la"]
        assert vocab.prepositions == {
            "instrument": ["con"],
            "recipient": ["a"],
        }
        assert vocab.speech_markers == ["diciendo"]
        assert vocab.speech_verbs == ["decir"]

    def test_load_vocabulary_with_world_path_override(self, tmp_path):
        """load_vocabulary accepts an explicit world_path."""
        base = self._make_world(
            tmp_path,
            """\
language: en
verbs:
  go: [WALK]
stopwords:
  - the
prepositions:
  instrument: [with]
speech_markers: []
speech_verbs: []
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary(world_path=base)

        assert vocab is not None
        assert vocab.language == "en"
        assert vocab.verbs == {"go": ["WALK"]}

    def test_load_vocabulary_uses_default_path(self, tmp_path):
        """load_vocabulary without args uses the loader's world path."""
        base = self._make_world(
            tmp_path,
            """\
language: es
verbs:
  mirar: [OBSERVAR]
stopwords: [el]
prepositions:
  instrument: [con]
speech_markers: []
speech_verbs: []
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()

        assert vocab is not None
        assert vocab.language == "es"
        assert vocab.verbs == {"mirar": ["OBSERVAR"]}

    def test_load_vocabulary_preserves_mutability_isolation(self, tmp_path):
        """load_vocabulary returns a Vocabulary whose lists/dicts are independent
        copies, so modifying the result doesn't affect internal state."""
        base = self._make_world(
            tmp_path,
            """\
language: es
verbs:
  ir: [ATRAVESAR]
stopwords: [el, la]
prepositions:
  instrument: [con]
speech_markers: [diciendo]
speech_verbs: [decir]
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()
        assert vocab is not None

        # Mutate the returned object
        vocab.verbs["ir"].append("CRUZAR")
        vocab.stopwords.append("los")
        vocab.prepositions["instrument"].append("de")

        # Reload — should get fresh data, not the mutations
        vocab2 = loader.load_vocabulary()
        assert vocab2 is not None
        assert vocab2.verbs == {"ir": ["ATRAVESAR"]}
        assert vocab2.stopwords == ["el", "la"]

    # -- missing file --------------------------------------------------

    def test_load_vocabulary_missing_file_returns_none(self, tmp_path):
        """load_vocabulary returns None when vocabulary.yaml is absent
        (allows parser's default cascade)."""
        base = self._make_world(tmp_path, None)
        # Don't write vocabulary.yaml
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()
        assert vocab is None

    def test_load_vocabulary_missing_shared_dir_returns_none(self, tmp_path):
        """load_vocabulary returns None when shared/ doesn't exist."""
        base = tmp_path / "minimal"
        _write_yaml(base / "world.yaml", "world_id: test\nname: Test\n")
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()
        assert vocab is None

    # -- malformed file ------------------------------------------------

    def test_load_vocabulary_malformed_yaml_raises(self, tmp_path):
        """load_vocabulary raises ValueError on invalid YAML."""
        base = self._make_world(tmp_path, "not: valid: yaml: [")
        loader = EntityLoader(str(base))

        with pytest.raises(ValueError, match="Invalid YAML"):
            loader.load_vocabulary()

    def test_load_vocabulary_missing_required_fields_raises(self, tmp_path):
        """load_vocabulary raises ValueError when required sections are missing."""
        base = self._make_world(
            tmp_path,
            """\
language: es
# missing verbs, stopwords, etc.
""",
        )
        loader = EntityLoader(str(base))

        with pytest.raises(ValueError, match="vocabulary"):
            loader.load_vocabulary()

    def test_load_vocabulary_rejects_invalid_verb_structure(self, tmp_path):
        """load_vocabulary rejects verbs that aren't dict[str, list[str]]."""
        base = self._make_world(
            tmp_path,
            """\
verbs: "not a dict"
stopwords: [el]
prepositions:
  instrument: [con]
speech_markers: []
speech_verbs: []
""",
        )
        loader = EntityLoader(str(base))

        with pytest.raises(ValueError, match="vocabulary"):
            loader.load_vocabulary()


# ===================================================================
# L1 (engine-language-agnostic) — VocabularyYAML +3 optional sections
# ===================================================================


class TestVocabularyYAMLExtensions:
    """VocabularyYAML gains messages, movement_verbs, system_commands."""

    def test_new_sections_present(self):
        """VocabularyYAML parses messages, movement_verbs, system_commands."""
        model = VocabularyYAML(
            verbs={"ir": ["ATRAVESAR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=[],
            speech_verbs=[],
            messages={"error_output.no_action": "No entiendes."},
            movement_verbs=["ir", "abrir"],
            system_commands={
                "save": ["guardar"],
                "load": ["cargar"],
                "quit": ["terminar"],
                "wait": ["esperar"],
                "group": ["grupo"],
                "switch": ["cambiar a"],
            },
        )
        assert model.messages == {"error_output.no_action": "No entiendes."}
        assert model.movement_verbs == ["ir", "abrir"]
        assert model.system_commands == {
            "save": ["guardar"],
            "load": ["cargar"],
            "quit": ["terminar"],
            "wait": ["esperar"],
            "group": ["grupo"],
            "switch": ["cambiar a"],
        }

    def test_new_sections_absent_default_empty(self):
        """VocabularyYAML defaults new sections to empty when not provided."""
        model = VocabularyYAML(
            verbs={"ir": ["ATRAVESAR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=[],
            speech_verbs=[],
        )
        assert model.messages == {}
        assert model.movement_verbs == []
        assert model.system_commands == {}

    def test_extra_forbid_rejects_misspelled_section(self):
        """VocabularyYAML extra='forbid' still detects unknown keys."""
        with pytest.raises(ValueError, match="unk"):
            VocabularyYAML(
                verbs={"ir": ["ATRAVESAR"]},
                stopwords=["el"],
                prepositions={"instrument": ["con"]},
                speech_markers=[],
                speech_verbs=[],
                unkown_section=42,  # type: ignore[call-arg]
            )

    def test_full_design_example_parses(self):
        """The full vocabulary.yaml example from design.md Data Design parses."""
        model = VocabularyYAML(
            language="es",
            verbs={
                "ir": ["atravesar", "cruzar", "pasar"],
                "tomar": ["coger"],
                "abrir": [],
            },
            stopwords=["el", "la", "los", "las", "un", "una", "al", "del", "por"],
            prepositions={"instrument": ["con"], "recipient": ["a"]},
            speech_markers=["diciendo", "respondiendo"],
            speech_verbs=["decir", "responder"],
            messages={
                "error_output.no_action": "No entiendes cómo hacer '{verb}' aquí.",
                "error_output.blocked": "No puedes ir por ahí.",
            },
            movement_verbs=["ir", "abrir"],
            system_commands={
                "save": ["guardar", "save"],
                "load": ["cargar", "load"],
                "quit": ["terminar", "abandonar", "quit"],
                "wait": ["esperar", "wait"],
                "group": ["grupo", "group"],
                "switch": ["cambiar a"],
            },
        )
        assert model.language == "es"
        assert model.messages == {
            "error_output.no_action": "No entiendes cómo hacer '{verb}' aquí.",
            "error_output.blocked": "No puedes ir por ahí.",
        }
        assert model.movement_verbs == ["ir", "abrir"]
        assert model.system_commands["save"] == ["guardar", "save"]
        assert model.system_commands["switch"] == ["cambiar a"]


# ===================================================================
# L1 — Vocabulary dataclass gains new fields
# ===================================================================


class TestVocabularyDataclassExtensions:
    """Vocabulary runtime dataclass mirrors the 3 new sections."""

    def test_new_fields_round_trip(self):
        """Vocabulary stores all 9 sections including messages, movement_verbs,
        system_commands."""
        vocab = Vocabulary(
            language="es",
            verbs={"ir": ["ATRAVESAR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=["diciendo"],
            speech_verbs=["decir"],
            messages={"error_output.no_action": "No entiendes."},
            movement_verbs=["ir", "abrir"],
            system_commands={"save": ["guardar"]},
        )
        assert vocab.messages == {"error_output.no_action": "No entiendes."}
        assert vocab.movement_verbs == ["ir", "abrir"]
        assert vocab.system_commands == {"save": ["guardar"]}

    def test_new_fields_default_empty(self):
        """Vocabulary new fields can be empty."""
        vocab = Vocabulary(
            language=None,
            verbs={},
            stopwords=[],
            prepositions={"instrument": []},
            speech_markers=[],
            speech_verbs=[],
            messages={},
            movement_verbs=[],
            system_commands={},
        )
        assert vocab.messages == {}
        assert vocab.movement_verbs == []
        assert vocab.system_commands == {}

    def test_equality_includes_new_fields(self):
        """Two Vocabularies with different new fields are not equal."""
        v1 = Vocabulary(
            language="es",
            verbs={"ir": ["IR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=[],
            speech_verbs=[],
            messages={"error_output.no_action": "No entiendes."},
            movement_verbs=["ir"],
            system_commands={"save": ["guardar"]},
        )
        v2 = Vocabulary(
            language="es",
            verbs={"ir": ["IR"]},
            stopwords=["el"],
            prepositions={"instrument": ["con"]},
            speech_markers=[],
            speech_verbs=[],
            messages={},
            movement_verbs=["ir"],
            system_commands={"save": ["guardar"]},
        )
        assert v1 != v2


# ===================================================================
# L1 — load_vocabulary carries new sections
# ===================================================================


class TestLoadVocabularyExtensions:
    """EntityLoader.load_vocabulary carries messages, movement_verbs,
    system_commands through to the Vocabulary dataclass."""

    def _make_world(self, tmp_path, vocab_content: str | None = None):
        base = tmp_path / "world"
        _write_yaml(
            base / "world.yaml",
            "world_id: test\nname: Test\n",
        )
        if vocab_content is not None:
            _write_yaml(base / "shared" / "vocabulary.yaml", vocab_content)
        return base

    def test_load_new_sections(self, tmp_path):
        """load_vocabulary loads messages, movement_verbs, system_commands."""
        base = self._make_world(
            tmp_path,
            """\
language: es
verbs:
  ir: [ATRAVESAR]
stopwords: [el]
prepositions:
  instrument: [con]
speech_markers: []
speech_verbs: []
messages:
  error_output.no_action: "No entiendes."
movement_verbs: [ir, abrir]
system_commands:
  save: [guardar, save]
  load: [cargar, load]
  quit: [terminar]
  wait: [esperar]
  group: [grupo]
  switch: [cambiar a]
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()

        assert vocab is not None
        assert vocab.messages == {"error_output.no_action": "No entiendes."}
        assert vocab.movement_verbs == ["ir", "abrir"]
        assert vocab.system_commands == {
            "save": ["guardar", "save"],
            "load": ["cargar", "load"],
            "quit": ["terminar"],
            "wait": ["esperar"],
            "group": ["grupo"],
            "switch": ["cambiar a"],
        }

    def test_load_absent_new_sections_back_compat(self, tmp_path):
        """load_vocabulary with existing Epic #3 shape (no new sections)
        returns a Vocabulary where new fields are empty."""
        base = self._make_world(
            tmp_path,
            """\
language: es
verbs:
  ir: [ATRAVESAR, CRUZAR]
  tomar: [COGER]
stopwords:
  - el
  - la
prepositions:
  instrument: [con]
  recipient: [a]
speech_markers:
  - diciendo
speech_verbs:
  - decir
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()

        assert vocab is not None
        assert vocab.messages == {}
        assert vocab.movement_verbs == []
        assert vocab.system_commands == {}

    def test_load_preserves_mutability_isolation_new_fields(self, tmp_path):
        """Mutating returned Vocabulary new fields doesn't affect reload."""
        base = self._make_world(
            tmp_path,
            """\
language: es
verbs:
  ir: [ATRAVESAR]
stopwords: [el]
prepositions:
  instrument: [con]
speech_markers: []
speech_verbs: []
messages:
  error_output.no_action: "No entiendes."
movement_verbs: [ir]
system_commands:
  save: [guardar]
""",
        )
        loader = EntityLoader(str(base))
        vocab = loader.load_vocabulary()
        assert vocab is not None

        # Mutate
        vocab.messages["new_key"] = "mutated"
        vocab.movement_verbs.append("abrir")
        vocab.system_commands["save"].append("save")

        # Reload
        vocab2 = loader.load_vocabulary()
        assert vocab2 is not None
        assert vocab2.messages == {"error_output.no_action": "No entiendes."}
        assert vocab2.movement_verbs == ["ir"]
        assert vocab2.system_commands == {"save": ["guardar"]}


# ===================================================================
# N3.1 + N3.4 — WorldYAML model_dump includes new fields
# ===================================================================


class TestWorldYAMLModelDump:
    """WorldYAML.model_dump() includes language + plugin fields."""

    def test_model_dump_includes_language_and_plugins(self):
        """model_dump serializes language, parser, narrator."""
        model = WorldYAML(
            world_id="w1",
            name="Test",
            language="en",
            parser=PluginConfigYAML(plugin="classic"),
            narrator=PluginConfigYAML(plugin="template"),
        )
        dump = model.model_dump()
        assert dump["language"] == "en"
        assert dump["parser"] == {"plugin": "classic", "options": {}}
        assert dump["narrator"] == {"plugin": "template", "options": {}}

    def test_model_dump_with_defaults(self):
        """model_dump includes defaults for language and plugins."""
        model = WorldYAML(world_id="w1", name="Test")
        dump = model.model_dump()
        assert dump["language"] == "es"
        assert dump["parser"] == {"plugin": "classic", "options": {}}
        assert dump["narrator"] == {"plugin": "template", "options": {}}


# ===================================================================
# N3.4 — Backward-compat: existing world.yaml fixtures still work
# ===================================================================


class TestWorldYAMLBackwardCompat:
    """Existing world.yaml fixtures (world_id + name only) must still work."""

    def test_minimal_world_yaml_still_valid(self):
        """WorldYAML with only world_id and name (no language/plugins) validates."""
        model = WorldYAML(world_id="t", name="T")
        assert model.world_id == "t"
        assert model.name == "T"
        assert model.language == "es"
        assert model.parser.plugin == "classic"

    def test_world_yaml_from_dict_minimal(self):
        """WorldYAML(**dict) with only required keys works (used by load_world_config)."""
        model = WorldYAML(**{"world_id": "test_world", "name": "Test World"})
        assert model.world_id == "test_world"
        assert model.name == "Test World"
        assert model.language == "es"
