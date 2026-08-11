"""AnswerBook — the solver's curated knowledge base (explorer-solver 2.1).

RED phase: references ``fortress_engine.autoplay.solver.AnswerBook`` and
``normalize_answer`` which do not exist yet.

Contract: every selected-episode macro-edge ``requires_text`` (derived) is
merged with the curated ``passwords``/``riddle_answers`` from
``episodes/answers.yaml`` (per-episode mapping), deduped on the
NFKD-strip-lowercase key, and exposed sorted by that key in as-authored form.
An ``answers_path`` override REPLACES the default curated file (derivation
still applies).
"""

from __future__ import annotations

from pathlib import Path

from fortress_engine.autoplay.solver import AnswerBook, normalize_answer


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _episode_yaml() -> str:
    return (
        "id: episode-01\n"
        "name: Episode\n"
        "order: 1\n"
        "requires: []\n"
        "start_anchor: alpha\n"
        "goal:\n"
        "  conditions: []\n"
        "  output: ''\n"
        "  side_effects: []\n"
        "carry_over:\n"
        "  inventory: []\n"
        "  flags: []\n"
    )


def _two_text_world(tmp_path: Path) -> Path:
    """World with two text-gated passages differing only in case."""
    world = tmp_path / "two_text"
    _write(world / "world.yaml", 'world_id: "two"\nname: "Two"\n')
    _write(world / "episodes" / "episode-01.yaml", _episode_yaml())
    _write(world / "episode-01" / "rooms" / "alpha.yaml", 'entity_id: "alpha"\ntype: "room"\nname: "Alpha"\n')
    _write(world / "episode-01" / "rooms" / "beta.yaml", 'entity_id: "beta"\ntype: "room"\nname: "Beta"\n')
    _write(world / "episode-01" / "rooms" / "gamma.yaml", 'entity_id: "gamma"\ntype: "room"\nname: "Gamma"\n')
    _write(
        world / "episode-01" / "macros" / "macros.yaml",
        '- macro_edge_id: "north"\n'
        '  from_anchor: "alpha"\n'
        '  to_anchor: "beta"\n'
        '  direction: "bidirectional"\n'
        '  passage_name: "north"\n'
        '  requires_text: "Open Sesame"\n'
        '  open: false\n'
        '- macro_edge_id: "east"\n'
        '  from_anchor: "alpha"\n'
        '  to_anchor: "gamma"\n'
        '  direction: "bidirectional"\n'
        '  passage_name: "east"\n'
        '  requires_text: "OPEN SESAME"\n'
        '  open: false\n',
    )
    return world


class TestNormalize:
    """normalize_answer — the NFKD-strip-lowercase dedup identity."""

    def test_strips_marks_and_lowercases(self) -> None:
        assert normalize_answer("Ábrete Sésamo") == "abrete sesamo"

    def test_upper_and_accented_case_are_equal_keys(self) -> None:
        assert normalize_answer("OPEN SESAME") == normalize_answer("open sesame")

    def test_combining_diacritics_normalized(self) -> None:
        assert normalize_answer("e\u0301l sol") == "el sol"


class TestDerivation:
    """Macro-edge requires_text is the derived source."""

    def test_derives_requires_text_from_macro_edges(self, solver_happy: Path) -> None:
        book = AnswerBook(episode_id="episode-01", world_path=solver_happy)
        assert "open sesame" in book.answers

    def test_no_macro_edges_yields_empty_answers(self, audit_limbo: Path) -> None:
        book = AnswerBook(episode_id="episode-01", world_path=audit_limbo)
        assert book.answers == []


class TestMerge:
    """Curated passwords/riddle_answers merge with the derived set."""

    def test_curated_passwords_and_riddle_answers_merged(
        self, solver_kb: Path
    ) -> None:
        book = AnswerBook(episode_id="episode-01", world_path=solver_kb)
        answers = book.answers
        assert "open sesame" in answers
        assert "el enigma del guardian" in answers

    def test_override_replaces_default_file_not_derivation(
        self, solver_kb: Path, tmp_path: Path
    ) -> None:
        alt = tmp_path / "alt-answers.yaml"
        alt.write_text(
            "episode-01:\n  passwords:\n    - \"only override\"\n",
            encoding="utf-8",
        )
        book = AnswerBook("episode-01", solver_kb, answers_path=alt)
        answers = book.answers
        assert "only override" in answers
        assert "open sesame" in answers
        assert "el enigma del guardian" not in answers

    def test_non_mapping_answers_file_yields_derived_only(
        self, solver_kb: Path, tmp_path: Path
    ) -> None:
        alt = tmp_path / "list-answers.yaml"
        alt.write_text("- just\n- a list\n", encoding="utf-8")
        book = AnswerBook("episode-01", solver_kb, answers_path=alt)
        assert book.answers == ["open sesame"]

    def test_non_mapping_episode_entry_yields_derived_only(
        self, solver_kb: Path, tmp_path: Path
    ) -> None:
        alt = tmp_path / "scalar-answers.yaml"
        alt.write_text("episode-01: not-a-mapping\n", encoding="utf-8")
        book = AnswerBook("episode-01", solver_kb, answers_path=alt)
        assert book.answers == ["open sesame"]


class TestDedup:
    """Dedup on the normalized key; first as-authored form is displayed."""

    def test_case_only_variants_dedup_to_first(self, tmp_path: Path) -> None:
        world = _two_text_world(tmp_path)
        book = AnswerBook("episode-01", world)
        assert book.answers == ["Open Sesame"]

    def test_derived_and_curated_same_key_dedup(self, solver_kb: Path) -> None:
        book = AnswerBook("episode-01", solver_kb)
        assert book.answers.count("open sesame") == 1


class TestSort:
    """Answers are sorted by their normalized key (deterministic order)."""

    def test_answers_sorted_by_normalized_key(self, solver_kb: Path) -> None:
        book = AnswerBook("episode-01", solver_kb)
        answers = book.answers
        keys = [normalize_answer(a) for a in answers]
        assert keys == sorted(keys)
