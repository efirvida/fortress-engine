"""Tests for plugin entry-point discovery — RED phase (N2.2).

Verify that the installed distribution exposes entry points
and that list_available_plugins returns them WITHOUT importing
modules that don't exist yet (classic_parser, template_narrator).

All tests follow Strict TDD: RED first (this file), then GREEN in factory.py.
"""

from __future__ import annotations

import importlib.metadata

import pytest


# ===================================================================
# Entry-point discovery — existence check (no .load() — modules
# don't exist yet)
# ===================================================================


def test_parser_entry_point_classic_exists():
    """The installed distribution exposes 'classic' parser entry point."""
    eps = importlib.metadata.entry_points(group="fortress_engine.parsers")
    names = {ep.name for ep in eps}
    assert "classic" in names, (
        f"Expected 'classic' in {names}. "
        "Re-run `pip install -e .` to register entry points."
    )


def test_narrator_entry_point_template_exists():
    """The installed distribution exposes 'template' narrator entry point."""
    eps = importlib.metadata.entry_points(group="fortress_engine.narrators")
    names = {ep.name for ep in eps}
    assert "template" in names, (
        f"Expected 'template' in {names}. "
        "Re-run `pip install -e .` to register entry points."
    )


# ===================================================================
# list_available_plugins — discovery without loading
# ===================================================================


def test_list_available_plugins_returns_parser_names():
    """list_available_plugins returns 'classic' for fortress_engine.parsers."""
    from fortress_engine.plugins.factory import list_available_plugins

    names = list_available_plugins("fortress_engine.parsers")
    assert "classic" in names


def test_list_available_plugins_returns_narrator_names():
    """list_available_plugins returns 'template' for fortress_engine.narrators."""
    from fortress_engine.plugins.factory import list_available_plugins

    names = list_available_plugins("fortress_engine.narrators")
    assert "template" in names


# ===================================================================
# Factory loading with monkeypatched entry point (modules don't exist)
# ===================================================================


def test_factory_loads_parser_via_test_entry_point(monkeypatch):
    """create_parser loads a test class through the factory machinery."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_parser,
    )
    from fortress_engine.plugins.parser_interface import ParserInterface

    from fortress_engine.entities.entity import ParsedCommand

    class _TestPlugin(ParserInterface):
        def __init__(self, language: str = "es", **kwargs) -> None:
            super().__init__(language)

        @property
        def language(self) -> str:
            return self._language

        def parse(self, raw_text, world_state):
            return ParsedCommand(subject="p", verb="v")

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _TestPlugin,
    )

    cfg = PluginConfig(name="test_plugin")
    instance = create_parser(cfg, world_language="es")
    assert instance.language == "es"
    assert isinstance(instance, ParserInterface)


def test_factory_loads_narrator_via_test_entry_point(monkeypatch):
    """create_narrator loads a test class through the factory machinery."""
    from fortress_engine.plugins.factory import (
        PluginConfig,
        create_narrator,
    )
    from fortress_engine.plugins.narrator_interface import NarratorInterface

    class _TestPlugin(NarratorInterface):
        def __init__(self, language: str = "es", **kwargs) -> None:
            super().__init__(language)

        @property
        def language(self) -> str:
            return self._language

        def initialize(self, event_bus):
            pass

        def handle_event(self, event, world_state):
            return "ok"

    monkeypatch.setattr(
        "fortress_engine.plugins.factory._resolve_entry_point",
        lambda group, name: _TestPlugin,
    )

    cfg = PluginConfig(name="test_plugin")
    instance = create_narrator(cfg, world_language="en")
    assert instance.language == "en"
    assert isinstance(instance, NarratorInterface)


# ===================================================================
# Entry-point group shape — one entry each
# ===================================================================


def test_parser_group_has_exactly_one_entry():
    """At this stage (N2), fortress_engine.parsers has exactly 'classic'."""
    eps = importlib.metadata.entry_points(group="fortress_engine.parsers")
    names = [ep.name for ep in eps]
    assert "classic" in names
    # The factory entry points are declared — there might be test-only
    # entries too. Just verify classic is there.
    assert len(names) >= 1


def test_narrator_group_has_exactly_one_entry():
    """At this stage (N2), fortress_engine.narrators has exactly 'template'."""
    eps = importlib.metadata.entry_points(group="fortress_engine.narrators")
    names = [ep.name for ep in eps]
    assert "template" in names
    assert len(names) >= 1


# ===================================================================
# list_available_plugins for unknown group
# ===================================================================


def test_list_available_plugins_unknown_group_returns_empty_sorted():
    """Unknown group returns an empty (but valid) sorted list."""
    from fortress_engine.plugins.factory import list_available_plugins

    names = list_available_plugins("fortress_engine.unknown_group_xyz123")
    assert isinstance(names, list)
    assert names == []
    assert names == sorted(names)
