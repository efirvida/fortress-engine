"""AnswerBook — knowledge base of answers for text-gated passages.

Contract: every selected-episode macro-edge ``requires_text`` (derived) is
merged with the curated ``passwords``/``riddle_answers`` of
``episodes/answers.yaml`` (episode_id -> mapping), deduped on the
NFKD-lowercase-no-marks key, and exposed sorted by that key in as-authored
form. ``answers_path`` REPLACES only the curated file; derivation still
applies.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

import fortress_engine.autoplay as autoplay
from fortress_engine.autoplay import answers as answers_module
from fortress_engine.autoplay.answers import AnswerBook, normalize_answer
from fortress_engine.entities.loader import EntityLoader


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _episode_yaml(episode_id: str) -> str:
    return (
        f"id: {episode_id}\n"
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


def _edge(index: int, requires_text: str | None) -> str:
    text = f'  requires_text: "{requires_text}"\n  open: false\n' if requires_text else ""
    return (
        f'- macro_edge_id: "edge{index}"\n'
        '  from_anchor: "alpha"\n'
        f'  to_anchor: "room{index}"\n'
        '  direction: "unidirectional"\n'
        f'  passage_name: "door{index}"\n'
        f"{text}"
    )


def _world(
    tmp_path: Path,
    *,
    derived: dict[str, list[str | None]] | None = None,
    answers: str | None = None,
    name: str = "world",
) -> Path:
    """World with one macros file per episode and an optional answers.yaml."""
    world = tmp_path / name
    _write(world / "world.yaml", 'world_id: "w"\nname: "W"\n')
    for episode_id, texts in (derived or {}).items():
        _write(world / "episodes" / f"{episode_id}.yaml", _episode_yaml(episode_id))
        if texts:
            _write(
                world / episode_id / "macros" / "macros.yaml",
                "".join(_edge(i, text) for i, text in enumerate(texts)),
            )
    if answers is not None:
        _write(world / "episodes" / "answers.yaml", answers)
    return world


class TestNormalize:
    def test_strips_marks_and_lowercases(self) -> None:
        assert normalize_answer("Ábrete Sésamo") == "abrete sesamo"

    def test_upper_and_lower_are_equal_keys(self) -> None:
        assert normalize_answer("OPEN SESAME") == normalize_answer("open sesame")

    def test_combining_diacritics_normalized(self) -> None:
        assert normalize_answer("e\u0301l sol") == "el sol"

    def test_precomposed_and_decomposed_are_equal_keys(self) -> None:
        assert normalize_answer("\u00f1and\u00fa") == normalize_answer("n\u0303andu\u0301") == "nandu"

    def test_compatibility_forms_fold(self) -> None:
        assert normalize_answer("ＡＢＣ①") == "abc1"

    def test_empty_stays_empty_and_whitespace_is_kept(self) -> None:
        assert normalize_answer("") == ""
        assert normalize_answer("  X ") == "  x "


class TestDerived:
    def test_every_requires_text_in_authored_form_sorted(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": ["Zorro", "Ábrete Sésamo", None, "mu"]})
        assert AnswerBook("episode-01", world).answers == ["Ábrete Sésamo", "mu", "Zorro"]

    def test_no_macros_directory_yields_empty(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": []})
        assert AnswerBook("episode-01", world).answers == []

    def test_edges_without_requires_text_contribute_nothing(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": [None, None]})
        assert AnswerBook("episode-01", world).answers == []

    def test_only_selected_episode_is_derived(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path, derived={"episode-01": ["uno"], "episode-02": ["dos"]}
        )
        assert AnswerBook("episode-01", world).answers == ["uno"]
        assert AnswerBook("episode-02", world).answers == ["dos"]

    def test_bidirectional_reverse_does_not_duplicate(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": []})
        _write(
            world / "episode-01" / "macros" / "macros.yaml",
            '- macro_edge_id: "e"\n  from_anchor: "a"\n  to_anchor: "b"\n'
            '  direction: "bidirectional"\n  passage_name: "p"\n'
            '  requires_text: "clave"\n  open: false\n',
        )
        assert AnswerBook("episode-01", world).answers == ["clave"]

    def test_accepts_str_world_path(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": ["x"]})
        assert AnswerBook("episode-01", str(world)).answers == ["x"]


class TestCurated:
    def test_passwords_then_riddle_answers_sorted(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            answers=(
                "episode-01:\n"
                "  passwords: [Zeta, beta]\n"
                "  riddle_answers: ['Álamo']\n"
            ),
        )
        assert AnswerBook("episode-01", world).answers == ["Álamo", "beta", "Zeta"]

    def test_only_selected_episode_entry_is_used(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            answers=(
                "episode-01:\n  passwords: [uno]\n"
                "episode-02:\n  passwords: [dos]\n"
            ),
        )
        assert AnswerBook("episode-02", world).answers == ["dos"]

    def test_unknown_episode_id_is_empty_not_error(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            derived={"episode-01": ["uno"]},
            answers="episode-01:\n  passwords: [uno]\n",
        )
        assert AnswerBook("episode-99", world).answers == []
        assert AnswerBook("nonsense", world).answers == []

    def test_key_with_only_one_list_is_enough(self, tmp_path: Path) -> None:
        world = _world(tmp_path, answers="episode-01:\n  riddle_answers: [solo]\n")
        assert AnswerBook("episode-01", world).answers == ["solo"]

    def test_other_keys_in_entry_are_ignored(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            answers="episode-01:\n  hints: [nope]\n  passwords: [si]\n",
        )
        assert AnswerBook("episode-01", world).answers == ["si"]


class TestMalformed:
    def test_non_list_values_are_dropped(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            answers=(
                "episode-01:\n"
                "  passwords: just-a-string\n"
                "  riddle_answers: {a: b}\n"
            ),
        )
        assert AnswerBook("episode-01", world).answers == []

    def test_non_string_items_are_dropped_strings_kept(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            answers=(
                "episode-01:\n"
                "  passwords: [42, ok, null, true, [nested], {k: v}, 1.5]\n"
                "  riddle_answers: [yes2]\n"
            ),
        )
        assert AnswerBook("episode-01", world).answers == ["ok", "yes2"]

    def test_empty_string_items_are_dropped(self, tmp_path: Path) -> None:
        world = _world(tmp_path, answers="episode-01:\n  passwords: ['', real]\n")
        assert AnswerBook("episode-01", world).answers == ["real"]

    @pytest.mark.parametrize(
        "content",
        ["- a\n- b\n", "just text\n", "", "episode-01: scalar\n", "episode-01: [x]\n",
         "episode-01:\n"],
    )
    def test_non_mapping_shapes_yield_derived_only(self, tmp_path: Path, content: str) -> None:
        world = _world(tmp_path, derived={"episode-01": ["base"]}, answers=content)
        assert AnswerBook("episode-01", world).answers == ["base"]

    def test_invalid_yaml_propagates_yaml_error(self, tmp_path: Path) -> None:
        # Kept as-is from the original (not swallowed); reported, not fixed.
        import yaml

        world = _world(tmp_path, answers="episode-01: [unclosed\n")
        with pytest.raises(yaml.YAMLError):
            AnswerBook("episode-01", world).answers


class TestAbsentFile:
    def test_absent_default_file_is_empty_curated(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": ["solo derivada"]})
        assert not (world / "episodes" / "answers.yaml").exists()
        assert AnswerBook("episode-01", world).answers == ["solo derivada"]

    def test_absent_override_file_is_empty_curated(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            derived={"episode-01": ["derivada"]},
            answers="episode-01:\n  passwords: [default]\n",
        )
        missing = tmp_path / "nope.yaml"
        assert AnswerBook("episode-01", world, answers_path=missing).answers == ["derivada"]

    def test_directory_as_answers_path_is_empty_curated(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": ["derivada"]})
        book = AnswerBook("episode-01", world, answers_path=tmp_path)
        assert book.answers == ["derivada"]

    def test_missing_world_directory_propagates_loader_error(self, tmp_path: Path) -> None:
        # Kept as-is from the original (derivation runs first); reported.
        ghost = tmp_path / "ghost"
        with pytest.raises(FileNotFoundError) as excinfo:
            AnswerBook("episode-01", ghost).answers
        assert str(excinfo.value) == f"World path not found: {ghost.resolve()}"


class TestMergeDedupSort:
    def test_derived_first_wins_spelling_over_curated(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            derived={"episode-01": ["Ábrete Sésamo"]},
            answers="episode-01:\n  passwords: ['ABRETE sesamo', otra]\n",
        )
        assert AnswerBook("episode-01", world).answers == ["Ábrete Sésamo", "otra"]

    def test_case_only_variants_among_derived_keep_first(self, tmp_path: Path) -> None:
        world = _world(tmp_path, derived={"episode-01": ["Open Sesame", "OPEN SESAME"]})
        assert AnswerBook("episode-01", world).answers == ["Open Sesame"]

    def test_curated_duplicates_keep_first_in_file_order(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            answers=(
                "episode-01:\n  passwords: [Sol, sól]\n  riddle_answers: [SOL, luna]\n"
            ),
        )
        assert AnswerBook("episode-01", world).answers == ["luna", "Sol"]

    def test_merged_output_sorted_by_normalized_key_not_raw(self, tmp_path: Path) -> None:
        # Raw order would be ['Zeta', 'beta', 'álamo']; key order differs.
        world = _world(
            tmp_path,
            derived={"episode-01": ["Zeta", "álamo"]},
            answers="episode-01:\n  passwords: [beta]\n",
        )
        book = AnswerBook("episode-01", world)
        assert book.answers == ["álamo", "beta", "Zeta"]
        keys = [normalize_answer(a) for a in book.answers]
        assert keys == ["alamo", "beta", "zeta"]

    def test_sort_is_stable_regardless_of_source_order(self, tmp_path: Path) -> None:
        a = _world(tmp_path, derived={"episode-01": ["b", "a"]}, name="a")
        b = _world(tmp_path, derived={"episode-01": ["a", "b"]}, name="b")
        assert AnswerBook("episode-01", a).answers == AnswerBook("episode-01", b).answers == ["a", "b"]


class TestOverride:
    def _world(self, tmp_path: Path) -> Path:
        return _world(
            tmp_path,
            derived={"episode-01": ["derivada"]},
            answers="episode-01:\n  passwords: [por defecto]\n",
        )

    def test_override_replaces_curated_but_not_derived(self, tmp_path: Path) -> None:
        world = self._world(tmp_path)
        alt = tmp_path / "alt.yaml"
        alt.write_text("episode-01:\n  passwords: [override]\n", encoding="utf-8")
        assert AnswerBook("episode-01", world, answers_path=alt).answers == [
            "derivada",
            "override",
        ]

    def test_default_file_is_used_without_override(self, tmp_path: Path) -> None:
        world = self._world(tmp_path)
        assert AnswerBook("episode-01", world).answers == ["derivada", "por defecto"]

    def test_override_accepts_str_path(self, tmp_path: Path) -> None:
        world = self._world(tmp_path)
        alt = tmp_path / "alt.yaml"
        alt.write_text("episode-01:\n  riddle_answers: [r]\n", encoding="utf-8")
        assert AnswerBook("episode-01", world, answers_path=str(alt)).answers == ["derivada", "r"]

    def test_override_without_this_episode_leaves_only_derived(self, tmp_path: Path) -> None:
        world = self._world(tmp_path)
        alt = tmp_path / "alt.yaml"
        alt.write_text("episode-02:\n  passwords: [x]\n", encoding="utf-8")
        assert AnswerBook("episode-01", world, answers_path=alt).answers == ["derivada"]


class TestDataclassAndWiring:
    def test_frozen_with_declared_fields(self, tmp_path: Path) -> None:
        book = AnswerBook("episode-01", tmp_path)
        assert [f.name for f in dataclasses.fields(book)] == [
            "episode_id",
            "world_path",
            "answers_path",
        ]
        assert book.answers_path is None
        with pytest.raises(dataclasses.FrozenInstanceError):
            book.episode_id = "x"  # type: ignore[misc]

    def test_package_exports_same_objects(self) -> None:
        assert autoplay.AnswerBook is AnswerBook
        assert autoplay.normalize_answer is normalize_answer
        # Existing exports are preserved.
        for name in ("ActionDomain", "GameRuntime", "StepResult", "Checkpoint", "candidates"):
            assert hasattr(autoplay, name)

    def test_module_imports_only_allowed_dependencies(self) -> None:
        tree = ast.parse(Path(answers_module.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        assert imported == {
            "__future__",
            "unicodedata",
            "dataclasses",
            "pathlib",
            "typing",
            "yaml",
            "fortress_engine.entities.loader",
        }

    def test_answers_yaml_coexists_with_episode_loading(self, tmp_path: Path) -> None:
        world = _world(
            tmp_path,
            derived={"episode-01": ["clave"]},
            answers="episode-01:\n  passwords: [otra]\n",
        )
        episodes = EntityLoader(str(world)).load_episodes()
        assert [e.id for e in episodes] == ["episode-01"]
        assert AnswerBook("episode-01", world).answers == ["clave", "otra"]
