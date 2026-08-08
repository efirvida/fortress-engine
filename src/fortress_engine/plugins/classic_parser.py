"""ClassicParser — deterministic Spanish parser per TDD §4.15.

Implements the full Fortaleza vocabulary (37 constants + EXAMINAR),
NFKD normalization, V2 stopword stripping, preposition routing (CON→instrument,
A→context), speech extraction (DICIENDO/RESPONDIENDO/DECIR/RESPONDER), and
entity resolution against the spatial anchor + protagonist inventory.

The parser is entity-agnostic — Entity.type is never validated or branched on.
"""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

from fortress_engine.entities.entity import ParsedCommand
from fortress_engine.entities.loader import Vocabulary
from fortress_engine.plugins.parser_interface import ParserInterface

if TYPE_CHECKING:
    from fortress_engine.engine.state import WorldState


# ---------------------------------------------------------------------------
# DEFAULT_SPANISH_VOCABULARY — full 37-constant Fortaleza inventory + EXAMINAR
# ---------------------------------------------------------------------------

DEFAULT_SPANISH_VOCABULARY: dict = {
    "language": "es",
    "verbs": {
        "ir":           ["ATRAVESAR", "IR", "CRUZAR", "PASAR"],
        "tomar":        ["TOMAR", "COGER"],
        "dejar":        ["SOLTAR", "DEJAR"],
        "abrir":        ["ABRIR"],
        "matar":        ["MATAR", "ASESINAR"],
        "mirar":        ["OBSERVAR", "MIRAR"],
        "examinar":     ["LEER", "VER", "EXAMINAR"],
        "romper":       ["ROMPER", "FORZAR", "DESTROZAR"],
        "interrogar":   ["PREGUNTAR", "INTERROGAR"],
        "inventario":   ["INVENTARIO"],
        "dar":          ["REGALAR", "DAR"],
        "con":          ["CON"],
        "a":            ["A"],
        "terminar":     ["ABANDONAR", "TERMINAR"],
        "respondiendo": ["RESPONDIENDO"],
        "diciendo":     ["DICIENDO"],
        "ejecutar":     ["EJECUTAR"],
        "salvar":       ["SALVAR"],
        "porciento":    ["PORCIENTO"],
        "todo":         ["TODO"],
        "pesar":        ["PESAR"],
        "orinar":       ["MIAR", "ORINAR"],
        "cls":          ["CLS"],
    },
    "stopwords": [
        "el", "la", "los", "las", "un", "una", "al", "del", "por",
    ],
    "prepositions": {
        "instrument": ["con"],
        "recipient":   ["a"],
    },
    "speech_markers": ["diciendo", "respondiendo"],
    "speech_verbs":   ["decir", "responder"],
}


# ---------------------------------------------------------------------------
# Normalization helper
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Lowercase and remove Spanish diacritics (tildes, dieresis, enye).

    áéíóúüñ → aeiouun

    Identical to the module-level helper in parser_interface.py.
    Duplicated to avoid coupling internal helpers across modules.
    """
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


# ---------------------------------------------------------------------------
# ClassicParser
# ---------------------------------------------------------------------------


class ClassicParser(ParserInterface):
    """Deterministic Spanish parser with full Fortaleza vocabulary.

    Implements the 5-step algorithm from the design:
      1. Normalize (NFKD + combining-mark strip)
      2. Tokenize on whitespace
      3. Strip V2 stopwords from command/entity phrases (NOT from speech text)
      4. Verb lookup → canonical via synonym groups
      5. Speech-marker scan → split text
      6. Preposition routing: CON → instrument, A → context
      7. Entity resolution against spatial anchor + protagonist inventory

    Constructor:
        language: Language code (default "es").
        vocabulary: Override vocabulary — a Vocabulary dataclass or a dict
                    with keys ``verbs``, ``stopwords``, ``prepositions``,
                    ``speech_markers``, ``speech_verbs``, and optional
                    ``language``.  When None (default), the hardcoded
                    ``DEFAULT_SPANISH_VOCABULARY`` is used.

    Vocabulary cascade (per design §3):
        constructor override > DEFAULT_SPANISH_VOCABULARY

    The e-word MUST NOT appear anywhere in this module.
    """

    def __init__(
        self,
        language: str = "es",
        vocabulary: Vocabulary | dict | None = None,
    ) -> None:
        super().__init__(language)

        # Resolve vocabulary cascade: override → default constant
        if vocabulary is not None:
            if isinstance(vocabulary, Vocabulary):
                vocab_dict = _vocabulary_to_dict(vocabulary)
            else:
                vocab_dict = dict(vocabulary)
        else:
            vocab_dict = dict(DEFAULT_SPANISH_VOCABULARY)

        # The vocabulary dict may carry a language field (informational).
        # The constructor's *language* parameter always takes precedence.
        # Only use the vocabulary language when no explicit override was
        # given (i.e., language is still the default "es").
        # Since the constructor already set self._language, we do NOT
        # override it from the vocabulary.

        # --- Build internal lookup tables ---

        # Verb synonym → canonical map
        self._verb_map: dict[str, str] = {}
        for canonical, synonyms in vocab_dict["verbs"].items():
            # The canonical itself is also a valid input (e.g. "ir" → "ir")
            self._verb_map[canonical.lower()] = canonical.lower()
            for syn in synonyms:
                self._verb_map[syn.lower()] = canonical.lower()

        # Stopwords (for entity/command phrases, NOT speech text)
        self._stopwords: frozenset[str] = frozenset(
            w.lower() for w in vocab_dict.get("stopwords", [])
        )

        # Prepositions: instrument_preps, recipient_preps
        preps = vocab_dict.get("prepositions", {})
        self._instrument_preps: frozenset[str] = frozenset(
            w.lower() for w in preps.get("instrument", [])
        )
        self._recipient_preps: frozenset[str] = frozenset(
            w.lower() for w in preps.get("recipient", [])
        )

        # Speech markers — split target from spoken text
        self._speech_markers: tuple[str, ...] = tuple(
            w.lower() for w in vocab_dict.get("speech_markers", [])
        )

        # Standalone speech verbs (DECIR, RESPONDER)
        self._speech_verbs: frozenset[str] = frozenset(
            w.lower() for w in vocab_dict.get("speech_verbs", [])
        )

    # -------------------------------------------------------------------
    # ParserInterface contract
    # -------------------------------------------------------------------

    @property
    def language(self) -> str:
        """Return the language code for this parser instance."""
        return self._language

    def parse(self, raw_text: str, world_state: WorldState) -> ParsedCommand:
        """Parse *raw_text* into a structured ``ParsedCommand``.

        Algorithm:
            1. Normalize (NFKD, lowercase, combining-mark strip)
            2. Tokenize on whitespace
            3. If empty → return empty command
            4. Verb lookup → canonical (unknown verbs kept as-is, non-throwing)
            5. Speech-marker scan (DICIENDO/RESPONDIENDO) → split ``text``
            6. Standalone speech verbs (DECIR/RESPONDER) → whole remainder to
               ``text``
            7. Preposition routing (CON→instrument, A→context)
            8. Entity resolution (anchor + inventory scope)
        """
        text = _normalize(raw_text)

        tokens = text.split()
        if not tokens:
            return ParsedCommand(
                subject=world_state.active_protagonist_id,
                verb="",
                target=None,
            )

        verb = self._verb_map.get(tokens[0], tokens[0])
        rest = tokens[1:]

        # --- Speech extraction ------------------------------------------
        spoken_text: str | None = None

        # 5. Speech-marker scan: DICIENDO/RESPONDIENDO split remainder
        for marker in self._speech_markers:
            if marker in rest:
                marker_idx = rest.index(marker)
                after_marker = rest[marker_idx + 1:]
                spoken_text = " ".join(after_marker) if after_marker else None
                rest = rest[:marker_idx]
                break

        # 6. Standalone speech verbs: whole remainder is text
        if verb in self._speech_verbs and spoken_text is None:
            spoken_text = " ".join(rest) if rest else None
            rest = []

        # --- Stopword stripping (entity phrases only — not speech) ------
        entity_tokens = self._strip_stopwords(rest)

        # --- Preposition routing ----------------------------------------
        target_tokens, instrument_tokens, context_tokens = \
            self._route_prepositions(entity_tokens)

        # --- Entity resolution ------------------------------------------
        target = self._resolve_phrase(target_tokens, world_state)
        instrument = self._resolve_phrase(instrument_tokens, world_state)
        context = self._resolve_phrase(context_tokens, world_state)

        return ParsedCommand(
            subject=world_state.active_protagonist_id,
            verb=verb,
            target=target,
            context=context,
            instrument=instrument,
            text=spoken_text,
        )

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _strip_stopwords(self, tokens: list[str]) -> list[str]:
        """Remove stopwords from a token list.

        Applied to command/entity phrases ONLY — never to speech text.
        """
        return [t for t in tokens if t not in self._stopwords]

    def _route_prepositions(
        self, tokens: list[str]
    ) -> tuple[list[str], list[str], list[str]]:
        """Split tokens into (target, instrument, context) groups.

        CON (and synonyms) route following tokens to instrument.
        A (and synonyms) route following tokens to context.
        The remaining tokens become the target phrase.

        If A appears in instrument tokens, it's skipped (already consumed).
        Tokens are processed left-to-right; the first occurrence of a
        preposition captures everything until the next preposition.
        """
        target: list[str] = []
        instrument: list[str] = []
        context: list[str] = []

        # Determine the first preposition index (CON or A)
        i = 0
        n = len(tokens)

        while i < n:
            token = tokens[i]
            if token in self._instrument_preps:
                # Everything after CON until next preposition is instrument
                i += 1
                while i < n and tokens[i] not in self._instrument_preps \
                      and tokens[i] not in self._recipient_preps:
                    instrument.append(tokens[i])
                    i += 1
                continue
            elif token in self._recipient_preps:
                # Everything after A is context (to end, or until CON)
                i += 1
                while i < n and tokens[i] not in self._instrument_preps:
                    context.append(tokens[i])
                    i += 1
                continue
            else:
                target.append(token)
                i += 1

        return target, instrument, context

    def _resolve_phrase(
        self, tokens: list[str], world_state: WorldState
    ) -> str | None:
        """Resolve a token phrase to an entity_id.

        Returns:
            - ``entity_id`` if exactly one entity matches.
            - Raw phrase (joined tokens) if no match or ambiguous.
            - ``None`` if *tokens* is empty.
        """
        if not tokens:
            return None

        phrase = " ".join(tokens)

        # Build the search scope: current spatial anchor + protagonist inventory
        protagonist_id = world_state.active_protagonist_id
        try:
            protagonist = world_state.get_entity(protagonist_id)
            anchor_id = protagonist.spatial_anchor
        except KeyError:
            anchor_id = None

        candidates: dict[str, str] = {}  # normalized_name → entity_id

        for eid, entity in world_state.entities.items():
            if entity.spatial_anchor == anchor_id or \
               entity.spatial_anchor == protagonist_id:
                candidates[_normalize(entity.name)] = eid

        # --- Exact match ---
        if phrase in candidates:
            return candidates[phrase]

        # --- Partial match (Equals algorithm from original Fortaleza) ---
        input_words = set(tokens)
        partials: list[tuple[int, str]] = []  # (word_count, entity_id)

        for norm_name, eid in candidates.items():
            entity_words = set(norm_name.split())
            if input_words.issubset(entity_words):
                word_count = len(entity_words)
                partials.append((word_count, eid))

        if not partials:
            # No match at all → return raw phrase
            return phrase

        # Shortest name wins
        partials.sort(key=lambda x: x[0])
        shortest = partials[0]

        # Check for ties at the shortest length
        ties = [p for p in partials if p[0] == shortest[0]]
        if len(ties) > 1:
            # Ambiguous → return raw phrase unresolved
            return phrase

        return shortest[1]


# ---------------------------------------------------------------------------
# Vocabulary conversion helper
# ---------------------------------------------------------------------------


def _vocabulary_to_dict(v: Vocabulary) -> dict:
    """Convert a Vocabulary dataclass to the internal dict format."""
    return {
        "language": v.language,
        "verbs": {k: list(w) for k, w in v.verbs.items()},
        "stopwords": list(v.stopwords),
        "prepositions": {k: list(w) for k, w in v.prepositions.items()},
        "speech_markers": list(v.speech_markers),
        "speech_verbs": list(v.speech_verbs),
    }
