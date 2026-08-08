"""Tests for PluginFactory — RED phase (N2.1).

Verify plugin configuration, creation, and error handling:
  PluginConfig frozen dataclass, create_parser/create_narrator with
  language + options injection, PluginNotFoundError with available
  names, TypeError fallback on unknown kwargs, language mismatch
  warnings, and list_available_plugins.

All tests follow Strict TDD: RED first (this file), then GREEN in factory.py.
"""

from __future__ import annotations

import warnings
from dataclasses import FrozenInstanceError

import pytest

from fortress_engine.entities.entity import ParsedCommand
from fortress_engine.plugins.parser_interface import ParserInterface
from fortress_engine.plugins.narrator_interface import NarratorInterface


# ===================================================================
# Test plugin classes used for factory tests
# ===================================================================


class _SimpleParser(ParserInterface):
    """Test parser that accepts language and arbitrary **kwargs."""

    def __init__(self, language: str = "es", **kwargs) -> None:
        super().__init__(language)
        self._extra = dict(kwargs)

    @property
    def language(self) -> str:
        return self._language

    def parse(self, raw_text, world_state):
        return ParsedCommand(subject="p", verb="v")

    @property
    def extra(self) -> dict:
        return self._extra


class _SimpleNarrator(NarratorInterface):
    """Test narrator that accepts language and arbitrary **kwargs."""

    def __init__(self, language: str = "es", **kwargs) -> None:
        super().__init__(language)
        self._extra = dict(kwargs)

    @property
    def language(self) -> str:
        return self._language

    def initialize(self, event_bus):
        pass

    def handle_event(self, event, world_state):
        return "narration"

    @property
    def extra(self) -> dict:
        return self._extra


class _StrictParserNoKwargs(ParserInterface):
    """Parser that accepts language but NOT **kwargs — TypeError on extras."""

    def __init__(self, language: str = "es") -> None:
        super().__init__(language)

    @property
    def language(self) -> str:
        return self._language

    def parse(self, raw_text, world_state):
        return ParsedCommand(subject="p", verb="v")


class _LegacyNoLanguage:
    """Legacy plugin that accepts no constructor arguments at all.

    Does NOT inherit from ParserInterface so isinstance checks would fail
    in create_parser; this is used to test _instantiate fallback only.
    """

    def __init__(self) -> None:
        self._lang = ""

    @property
    def language(self) -> str:
        return self._lang

    def parse(self, raw_text, world_state):
        return ParsedCommand(subject="p", verb="v")


class _ParserWithLanguage(ParserInterface):
    """Parser that hardcodes a non-empty language regardless of input.

    The factory passes language=world_language, but this plugin hardcodes
    'fr' in its constructor — creating a genuine mismatch for warning tests.
    """

    def __init__(self, language: str = "fr") -> None:
        # Deliberately hardcode "fr", ignoring the constructor parameter.
        super().__init__("fr")

    @property
    def language(self) -> str:
        return self._language

    def parse(self, raw_text, world_state):
        return ParsedCommand(subject="p", verb="v")


class _NarratorWithLanguage(NarratorInterface):
    """Narrator that hardcodes a non-empty language regardless of input.

    Same pattern as _ParserWithLanguage — creates a mismatch for warnings.
    """

    def __init__(self, language: str = "fr") -> None:
        # Deliberately hardcode "fr", ignoring the constructor parameter.
        super().__init__("fr")

    @property
    def language(self) -> str:
        return self._language

    def initialize(self, event_bus):
        pass

    def handle_event(self, event, world_state):
        return "narration"


# ===================================================================
# PluginConfig tests
# ===================================================================


def test_plugin_config_is_frozen():
    """PluginConfig is a frozen dataclass — cannot mutate fields."""
    from fortress_engine.plugins.factory import PluginConfig

    cfg = PluginConfig(name="classic")
    assert cfg.name == "classic"
    assert cfg.options == {}

    with pytest.raises(FrozenInstanceError):
        cfg.name = "other"  # type: ignore[misc]


def test_plugin_config_defaults():
    """PluginConfig options default to an empty dict."""
    from fortress_engine.plugins.factory import PluginConfig

    cfg = PluginConfig(name="template")
    assert cfg.name == "template"
    assert cfg.options == {}


def test_plugin_config_with_options():
    """PluginConfig stores explicit options."""
    from fortress_engine.plugins.factory import PluginConfig

    cfg = PluginConfig(name="classic", options={"vocabulary": "custom"})
    assert cfg.name == "classic"
    assert cfg.options == {"vocabulary": "custom"}


def test_plugin_config_options_are_independent():
    """Each PluginConfig instance has its own options dict (not shared)."""
    from fortress_engine.plugins.factory import PluginConfig

    a = PluginConfig(name="a", options={"x": 1})
    b = PluginConfig(name="b")
    assert a.options == {"x": 1}
    assert b.options == {}
    a.options["x"] = 99
    assert b.options == {}  # b unaffected by mutation in a


# ===================================================================
# create_parser tests — language injection + options
# ===================================================================


def test_create_parser_injects_language(monkeypatch):
    """create_parser passes world_language to the plugin class as 'language'."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        _resolve_entry_point,
        create_parser,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _SimpleParser,
    )

    cfg = PluginConfig(name="simple")
    instance = create_parser(cfg, world_language="en")

    assert instance.language == "en"
    assert isinstance(instance, ParserInterface)


def test_create_parser_passes_options(monkeypatch):
    """create_parser passes PluginConfig.options as keyword arguments."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_parser,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _SimpleParser,
    )

    cfg = PluginConfig(name="simple", options={"vocabulary": "test_vocab", "score": 42})
    instance = create_parser(cfg, world_language="es")

    assert instance.extra == {"vocabulary": "test_vocab", "score": 42}


# ===================================================================
# create_narrator tests — language injection + options
# ===================================================================


def test_create_narrator_injects_language(monkeypatch):
    """create_narrator passes world_language to the plugin class as 'language'."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_narrator,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _SimpleNarrator,
    )

    cfg = PluginConfig(name="simple")
    instance = create_narrator(cfg, world_language="en")

    assert instance.language == "en"
    assert isinstance(instance, NarratorInterface)


def test_create_narrator_passes_options(monkeypatch):
    """create_narrator passes PluginConfig.options as keyword arguments."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_narrator,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _SimpleNarrator,
    )

    cfg = PluginConfig(name="simple", options={"templates": {}, "cache": True})
    instance = create_narrator(cfg, world_language="es")

    assert instance.extra == {"templates": {}, "cache": True}


# ===================================================================
# PluginNotFoundError — missing plugin with availability info
# ===================================================================


def test_create_parser_missing_plugin_raises_with_available_names(monkeypatch):
    """PluginNotFoundError includes the requested name and available names."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        PluginNotFoundError,
        create_parser,
    )

    # Real entry point resolution — 'xyzzy' won't be found.
    cfg = PluginConfig(name="xyzzy")
    with pytest.raises(PluginNotFoundError) as excinfo:
        create_parser(cfg, world_language="es")

    msg = str(excinfo.value)
    assert "xyzzy" in msg
    assert "fortress_engine.parsers" in msg
    # The available list should contain the real entry point 'classic'
    assert "classic" in msg


def test_create_narrator_missing_plugin_raises_with_available_names(monkeypatch):
    """PluginNotFoundError for narrator includes available names."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        PluginNotFoundError,
        create_narrator,
    )

    cfg = PluginConfig(name="nonexistent")
    with pytest.raises(PluginNotFoundError) as excinfo:
        create_narrator(cfg, world_language="es")

    msg = str(excinfo.value)
    assert "nonexistent" in msg
    assert "fortress_engine.narrators" in msg
    # The available list should contain the real entry point 'template'
    assert "template" in msg


# ===================================================================
# Language mismatch → warning (never raise)
# ===================================================================


def test_create_parser_language_mismatch_warns(monkeypatch):
    """When plugin.language differs from world_language and is non-empty,
    a warning is emitted but the instance is still returned."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_parser,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _ParserWithLanguage,
    )

    cfg = PluginConfig(name="fr_parser")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = create_parser(cfg, world_language="es")

    assert instance is not None
    assert instance.language == "fr"

    mismatch_warnings = [
        x for x in w
        if "language" in str(x.message).lower()
        and "fr" in str(x.message)
    ]
    assert len(mismatch_warnings) >= 1


def test_create_narrator_language_mismatch_warns(monkeypatch):
    """Narrator language mismatch also warns but returns the instance."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_narrator,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _NarratorWithLanguage,
    )

    cfg = PluginConfig(name="fr_narrator")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = create_narrator(cfg, world_language="es")

    assert instance is not None
    assert instance.language == "fr"

    mismatch_warnings = [
        x for x in w
        if "language" in str(x.message).lower()
        and "fr" in str(x.message)
    ]
    assert len(mismatch_warnings) >= 1


def test_create_parser_no_warning_when_language_matches(monkeypatch):
    """No warning is emitted when plugin.language matches world_language."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_parser,
    )

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _SimpleParser,
    )

    cfg = PluginConfig(name="simple")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = create_parser(cfg, world_language="es")

    assert instance.language == "es"
    # No warnings should have been emitted for language mismatch
    lang_warnings = [
        x for x in w
        if "differs from world language" in str(x.message).lower()
    ]
    assert len(lang_warnings) == 0


def test_create_parser_no_warning_when_plugin_language_empty(monkeypatch):
    """No warning when plugin.language is empty string (guard short-circuits)."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_parser,
    )
    from fortress_engine.entities.entity import ParsedCommand

    class _EmptyLangParser(ParserInterface):
        def __init__(self, language: str = "") -> None:
            super().__init__("")

        @property
        def language(self) -> str:
            return self._language

        def parse(self, raw_text, world_state):
            return ParsedCommand(subject="p", verb="v")

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _EmptyLangParser,
    )

    cfg = PluginConfig(name="empty")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = create_parser(cfg, world_language="es")

    assert instance.language == ""
    lang_warnings = [
        x for x in w
        if "differs from world language" in str(x.message).lower()
    ]
    assert len(lang_warnings) == 0


# ===================================================================
# TypeError fallback — unknown kwargs → retry without them
# ===================================================================


def test_instantiate_typeerror_from_options_fallback_with_warning():
    """A plugin that rejects unknown kwargs triggers TypeError fallback
    with a warning, then succeeds with language only."""
    from fortress_engine.plugins.factory import _instantiate

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = _instantiate(
            _StrictParserNoKwargs,
            world_language="es",
            options={"unknown_option": 123},
        )

    assert instance is not None
    assert isinstance(instance, ParserInterface)
    assert instance.language == "es"

    # Warning was emitted about retrying
    retry_warnings = [
        x for x in w
        if "retry" in str(x.message).lower()
    ]
    assert len(retry_warnings) >= 1


def test_instantiate_no_warning_when_options_accepted():
    """No TypeError warning when plugin accepts the options."""
    from fortress_engine.plugins.factory import _instantiate

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = _instantiate(
            _SimpleParser,
            world_language="es",
            options={"extra": "ok"},
        )

    assert instance.extra == {"extra": "ok"}
    # No TypeError-related warnings
    typeerror_warnings = [
        x for x in w
        if "rejected keyword" in str(x.message).lower()
        or "retry" in str(x.message).lower()
    ]
    assert len(typeerror_warnings) == 0


def test_instantiate_typeerror_from_language_fallback_cls_only():
    """A plugin that rejects 'language' entirely falls back to cls()
    best-effort, emitting two warnings."""
    from fortress_engine.plugins.factory import _instantiate

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instance = _instantiate(
            _LegacyNoLanguage,
            world_language="es",
            options={},
        )

    assert instance is not None
    # Instance should have been created via cls() fallback
    assert instance.language == ""

    fallback_warnings = [
        x for x in w
        if "without argument" in str(x.message).lower()
        or "language" in str(x.message).lower()
    ]
    assert len(fallback_warnings) >= 1


# ===================================================================
# list_available_plugins
# ===================================================================


def test_list_available_plugins_returns_sorted_names():
    """list_available_plugins returns sorted names for a valid group."""
    from fortress_engine.plugins.factory import list_available_plugins

    names = list_available_plugins("fortress_engine.parsers")
    assert isinstance(names, list)
    assert "classic" in names
    # Sorted
    assert names == sorted(names)


def test_list_available_plugins_empty_group():
    """list_available_plugins returns empty list for non-existent group."""
    from fortress_engine.plugins.factory import list_available_plugins

    names = list_available_plugins("fortress_engine.nonexistent_group_xyz")
    assert names == []


# ===================================================================
# _resolve_entry_point — full body (including .load())
# ===================================================================


def test_resolve_entry_point_loads_successfully(monkeypatch):
    """_resolve_entry_point calls .load() and returns the class when found.

    Monkeypatches entry_points (not _resolve_entry_point) so the full
    body executes, including the ``matching[name].load()`` path.
    """
    from fortress_engine.plugins.factory import _resolve_entry_point
    from unittest.mock import MagicMock
    import importlib.metadata

    mock_ep = MagicMock()
    mock_ep.name = "test_plugin"
    mock_ep.load.return_value = _SimpleParser

    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda *, group: [mock_ep],
    )

    cls = _resolve_entry_point("fortress_engine.parsers", "test_plugin")
    assert cls is _SimpleParser
    mock_ep.load.assert_called_once()


def test_resolve_entry_point_available_list_includes_all(monkeypatch):
    """When a plugin is missing, all registered names appear in the error."""
    from fortress_engine.plugins.factory import (
        _resolve_entry_point,
        PluginNotFoundError,
    )
    from unittest.mock import MagicMock
    import importlib.metadata

    def _make_ep(name):
        m = MagicMock()
        m.name = name
        return m

    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda *, group: [
            _make_ep("first"),
            _make_ep("second"),
            _make_ep("third"),
        ],
    )

    with pytest.raises(PluginNotFoundError) as excinfo:
        _resolve_entry_point("some_group", "missing")

    msg = str(excinfo.value)
    assert "missing" in msg
    assert "some_group" in msg
    assert "first" in msg
    assert "second" in msg
    assert "third" in msg


# ===================================================================
# PluginNotFoundError attribute access
# ===================================================================


def test_plugin_not_found_error_stores_name():
    """PluginNotFoundError can store the requested name for programmatic use."""
    from fortress_engine.plugins.factory import PluginNotFoundError

    err = PluginNotFoundError("Plugin 'x' not found in group 'g'. Available: []")
    assert "x" in str(err)


def test_plugin_not_found_error_is_exception():
    """PluginNotFoundError is a proper Exception subclass."""
    from fortress_engine.plugins.factory import PluginNotFoundError

    assert issubclass(PluginNotFoundError, Exception)


# ===================================================================
# create_parser / create_narrator validates interface
# ===================================================================


def test_create_parser_rejects_non_parser_class(monkeypatch):
    """create_parser rejects a class that doesn't implement ParserInterface."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_parser,
    )

    class NotAParser:
        pass

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: NotAParser,
    )

    cfg = PluginConfig(name="bad")
    with pytest.raises(TypeError, match="ParserInterface"):
        create_parser(cfg, world_language="es")


def test_create_narrator_rejects_non_narrator_class(monkeypatch):
    """create_narrator rejects a class that doesn't implement NarratorInterface."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_narrator,
    )

    class NotANarrator:
        pass

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: NotANarrator,
    )

    cfg = PluginConfig(name="bad")
    with pytest.raises(TypeError, match="NarratorInterface"):
        create_narrator(cfg, world_language="es")
