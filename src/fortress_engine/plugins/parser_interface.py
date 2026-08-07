"""Parser interface ABC — contract for parser plugins.

Follows plugin-contracts spec and tdd.md §4.13.
The MinimalParser implementation is included in this module.
"""

from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from fortress_engine.entities.entity import ParsedCommand

if TYPE_CHECKING:
    from fortress_engine.engine.state import WorldState


# ---------------------------------------------------------------------------
# Stop words stripped from the target (articles, prepositions, contractions)
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "el", "la", "los", "las", "un", "una",
    "al", "del", "por",
})


def _normalize(text: str) -> str:
    """Lowercase and remove Spanish diacritics (tildes, dieresis, enye).

    áéíóúüñ → aeiouun
    """
    text = text.strip().lower()
    # NFD decomposition separates base chars from combining marks;
    # filtering out Mn (nonspacing marks) strips tildes and dieresis.
    # ñ → n is a compatibility decomposition (NFKD).
    text = unicodedata.normalize("NFKD", text)
    # Remove combining marks (covers tildes and dieresis after NFKD)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def _strip_stop_words(tokens: list[str]) -> list[str]:
    """Remove leading stop words from a token list."""
    return [t for t in tokens if t not in _STOP_WORDS]


class ParserInterface(ABC):
    """Abstract parser that converts raw player text into a ParsedCommand."""

    @abstractmethod
    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        """Parse *raw_text* into a structured command."""
        ...


class MinimalParser(ParserInterface):
    """Minimal Spanish parser — tokenize, normalize, extract verb + target.

    Behaviour:
        - Strips and lowercases input, normalises tildes/dieresis/enye
          (á→a, é→e, í→i, ó→o, ú→u, ü→u, ñ→n).
        - Splits on whitespace; first token is verb, remaining tokens are
          target after stripping known articles and prepositions.
        - Subject is resolved from ``world_state.active_protagonist_id``.
        - Context and instrument are always ``None``.
        - Unknown / gibberish input is never rejected — the returned
          ``ParsedCommand`` may have an unknown verb, and the orchestrator
          handles the ``error_output`` path when no clique matches.
    """

    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        tokens = raw_text.strip().split()
        if not tokens:
            return ParsedCommand(
                subject=world_state.active_protagonist_id,
                verb="",
                target=None,
            )

        verb = _normalize(tokens[0])

        # Build target from remaining tokens after normalising and
        # stripping stop words.
        target_tokens = _strip_stop_words([_normalize(t) for t in tokens[1:]])
        target = " ".join(target_tokens) if target_tokens else None

        return ParsedCommand(
            subject=world_state.active_protagonist_id,
            verb=verb,
            target=target,
        )
