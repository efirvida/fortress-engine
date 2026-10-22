"""Autoplay answers — knowledge base for text-gated passages (development tool).

``AnswerBook`` merges every selected-episode macro-edge ``requires_text``
(derived) with the ``passwords``/``riddle_answers`` curated in
``episodes/answers.yaml`` (per-episode mapping) or an ``--answers`` override.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from fortress_engine.entities.loader import EntityLoader


def normalize_answer(text: str) -> str:
    """NFKD-strip-lowercase normalization key (dedup identity).

    Mirrors the engine's own text normalization, so a curated password and a
    macro-edge answer that differ only in case or diacritics still resolve to
    one knowledge-base entry.
    """
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


@dataclass(frozen=True)
class AnswerBook:
    """Knowledge base of answers the solver may speak at text-gated passages.

    Fields:
        episode_id: the selected episode.
        world_path: world directory — source of the derived macro-edge
            answers and of the default curated file ``episodes/answers.yaml``.
        answers_path: optional override file that REPLACES the default
            curated file (the derived set still applies).
    """

    episode_id: str
    world_path: Path | str
    answers_path: Path | str | None = None

    def _answers_file(self) -> Path:
        """Resolve the curated answers file (override or default)."""
        if self.answers_path is not None:
            return Path(self.answers_path)
        return Path(self.world_path) / "episodes" / "answers.yaml"

    def _derived(self) -> list[str]:
        """Every selected-episode macro-edge ``requires_text`` (as-authored)."""
        loader = EntityLoader(str(self.world_path))
        return [
            edge.requires_text
            for edge in loader.load_macro_edges(self.episode_id)
            if edge.requires_text
        ]

    def _curated(self) -> list[str]:
        """``passwords`` + ``riddle_answers`` from the curated answers file.

        An absent file yields nothing; a non-mapping shape (or a mapping
        without this episode's entry) yields nothing either.
        """
        path = self._answers_file()
        if not path.is_file():
            return []
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return []
        entry = raw.get(self.episode_id)
        if not isinstance(entry, dict):
            return []
        curated: list[str] = []
        for key in ("passwords", "riddle_answers"):
            values = entry.get(key)
            if isinstance(values, list):
                curated.extend(
                    str(value) for value in values if isinstance(value, str)
                )
        return curated

    @property
    def answers(self) -> list[str]:
        """Merged answers, deduped and sorted by normalized key.

        The derived set is authored first, then the curated set; a duplicate
        normalized key keeps its first as-authored spelling for display.
        """
        merged = [*self._derived(), *self._curated()]
        order: list[str] = []
        seen: set[str] = set()
        for text in merged:
            key = normalize_answer(text)
            if key and key not in seen:
                seen.add(key)
                order.append(text)
        return sorted(order, key=normalize_answer)
