"""Plugin factory — entry-point discovery and instantiation.

Follows plugin-factory spec and TDD §9.2–§9.3.
This is the ONLY module that calls ``importlib.metadata.entry_points``
(architecture constant #7).

Public API: ``PluginConfig``, ``create_parser``, ``create_narrator``,
``list_available_plugins``, ``PluginNotFoundError``.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import importlib.metadata

if TYPE_CHECKING:
    from fortress_engine.plugins.parser_interface import ParserInterface
    from fortress_engine.plugins.narrator_interface import NarratorInterface


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class PluginNotFoundError(Exception):
    """Raised when a requested plugin is not found in the entry-point group."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginConfig:
    """Immutable plugin configuration with name and keyword options.

    ``options`` is passed directly to the plugin constructor as keyword
    arguments (e.g. ``vocabulary``, ``templates``, ``strict_language``).
    """

    name: str
    options: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_entry_point(group: str, name: str) -> type:
    """Resolve an entry point in *group* by *name*.

    Returns the loaded class.  Raises ``PluginNotFoundError`` when the
    requested *name* is absent, including the available names in the
    error message.

    This is the ONLY place ``importlib.metadata.entry_points`` is called
    for plugin discovery (architecture constant #7).
    """
    eps = importlib.metadata.entry_points(group=group)
    matching = {ep.name: ep for ep in eps}
    if name not in matching:
        available = sorted(matching.keys())
        raise PluginNotFoundError(
            f"Plugin '{name}' not found in group '{group}'. "
            f"Available: {available}"
        )
    return matching[name].load()


def _instantiate(
    cls: type,
    world_language: str,
    options: dict[str, Any],
) -> Any:
    """Construct *cls* with best-effort keyword passing.

    1. Try ``cls(language=world_language, **options)``.
    2. On ``TypeError`` (unknown kwargs), retry ``cls(language=world_language)``
       with a warning.
    3. If that also raises ``TypeError`` (plugin doesn't accept ``language``),
       retry ``cls()`` with a warning.

    Returns the constructed instance.
    """
    try:
        return cls(language=world_language, **options)
    except TypeError:
        warnings.warn(
            f"_instantiate: {cls.__name__} rejected keyword arguments; "
            f"retrying with language only.",
            RuntimeWarning,
            stacklevel=2,
        )
        try:
            return cls(language=world_language)
        except TypeError:
            warnings.warn(
                f"_instantiate: {cls.__name__} does not accept language; "
                f"constructing without arguments.",
                RuntimeWarning,
                stacklevel=2,
            )
            return cls()


# ---------------------------------------------------------------------------
# Public factory functions
# ---------------------------------------------------------------------------


def create_parser(
    plugin_config: PluginConfig,
    world_language: str,
) -> ParserInterface:
    """Resolve and instantiate a parser plugin.

    Injects *world_language* as the ``language`` keyword and
    ``plugin_config.options`` as additional kwargs.

    Emits a ``warnings.warn`` when the plugin's non-empty ``.language``
    differs from *world_language* (V1 never raises for this mismatch).

    Raises ``PluginNotFoundError`` when the named plugin is absent.
    """
    from fortress_engine.plugins.parser_interface import ParserInterface

    cls = _resolve_entry_point("fortress_engine.parsers", plugin_config.name)
    instance = _instantiate(cls, world_language, plugin_config.options)

    if not isinstance(instance, ParserInterface):
        raise TypeError(
            f"Plugin '{plugin_config.name}' (resolved to {cls.__name__}) "
            f"does not implement ParserInterface."
        )

    _warn_language_mismatch(plugin_config.name, instance.language, world_language)
    return instance


def create_narrator(
    plugin_config: PluginConfig,
    world_language: str,
) -> NarratorInterface:
    """Resolve and instantiate a narrator plugin.

    Works identically to ``create_parser`` but for the
    ``fortress_engine.narrators`` group.
    """
    from fortress_engine.plugins.narrator_interface import NarratorInterface

    cls = _resolve_entry_point("fortress_engine.narrators", plugin_config.name)
    instance = _instantiate(cls, world_language, plugin_config.options)

    if not isinstance(instance, NarratorInterface):
        raise TypeError(
            f"Plugin '{plugin_config.name}' (resolved to {cls.__name__}) "
            f"does not implement NarratorInterface."
        )

    _warn_language_mismatch(plugin_config.name, instance.language, world_language)
    return instance


def list_available_plugins(group: str) -> list[str]:
    """Return sorted names of all registered plugins in *group*.

    Useful for diagnostics and user-facing configuration validation.
    Does NOT load any modules — only reads entry-point metadata.
    """
    eps = importlib.metadata.entry_points(group=group)
    return sorted(ep.name for ep in eps)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _warn_language_mismatch(
    plugin_name: str,
    plugin_language: str,
    world_language: str,
) -> None:
    """Emit a warning when plugin language differs from world language.

    Only warns when *plugin_language* is non-empty and does not match
    *world_language*.  V1 never raises for this mismatch.
    """
    if plugin_language and plugin_language != world_language:
        warnings.warn(
            f"Plugin '{plugin_name}' language '{plugin_language}' "
            f"differs from world language '{world_language}'. "
            f"V1 continues; strict_language enforcement deferred to v1.1.",
            RuntimeWarning,
            stacklevel=3,
        )
