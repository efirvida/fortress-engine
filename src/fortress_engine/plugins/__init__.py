"""Plugin system — parser and narrator contracts, factory, and implementations."""

from fortress_engine.plugins.classic_parser import ClassicParser
from fortress_engine.plugins.factory import (
    PluginConfig,
    PluginNotFoundError,
    create_parser,
    create_narrator,
    list_available_plugins,
)
from fortress_engine.plugins.template_narrator import TemplateNarrator

__all__ = [
    "ClassicParser",
    "PluginConfig",
    "PluginNotFoundError",
    "TemplateNarrator",
    "create_parser",
    "create_narrator",
    "list_available_plugins",
]
