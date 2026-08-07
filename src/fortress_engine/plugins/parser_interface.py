"""Parser interface ABC — contract for parser plugins.

Follows plugin-contracts spec and tdd.md §4.13.
The MinimalParser implementation arrives in Slice E2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortress_engine.entities.entity import ParsedCommand
    from fortress_engine.engine.state import WorldState


class ParserInterface(ABC):
    """Abstract parser that converts raw player text into a ParsedCommand."""

    @abstractmethod
    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        """Parse *raw_text* into a structured command."""
        ...
