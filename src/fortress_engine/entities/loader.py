"""EntityLoader — recursive YAML loading with Pydantic validation, producing
runtime dataclasses.

Follows world-loading spec and tdd.md §4.12.
Entity-agnostic: no entity type constants, no closed type sets.
Pydantic is used ONLY at load time — runtime objects are plain dataclasses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from fortress_engine.entities.entity import (
    CarryOver,
    Entity,
    Episode,
    GoalCondition,
    GoalConditions,
)
from fortress_engine.engine.graph import (
    Clique,
    HyperEdge,
    MacroEdge,
)

# Regex to extract episode directory component from a path.
_EPISODE_DIR_RE = re.compile(r"episode-(\d+)")


# ---------------------------------------------------------------------------
# Pydantic load-time models
# ---------------------------------------------------------------------------


class CarryOverYAML(BaseModel):
    """Pydantic model for carry_over rules in episode YAML."""
    inventory: list[str] = []
    flags: list[str] = []


class GoalConditionYAML(BaseModel):
    """Pydantic model for a single goal condition."""
    type: str
    params: dict[str, Any] = {}


class GoalConditionsYAML(BaseModel):
    """Pydantic model for the goal conditions block."""
    conditions: list[dict[str, Any] | str] = []
    output: str = ""
    side_effects: list[dict[str, Any]] = []


class EpisodeYAML(BaseModel):
    """Pydantic model for episode YAML files (episodes/*.yaml)."""
    id: str
    name: str
    order: int
    description: str | None = None
    requires: list[str] = []
    start_anchor: str
    goal: GoalConditionsYAML
    carry_over: CarryOverYAML


class PluginConfigYAML(BaseModel):
    """Pydantic model for plugin configuration in world.yaml.

    The YAML model uses ``plugin`` as the field name (per approved spec).
    The runtime ``PluginConfig`` (factory.py) uses ``name`` — the
    conversion between them happens in the factory/bootstrap layer.
    """
    model_config = ConfigDict(extra="forbid")

    plugin: str
    options: dict[str, Any] = {}


class WorldYAML(BaseModel):
    """Pydantic model for world.yaml."""
    world_id: str
    name: str
    language: str = "es"
    parser: str | PluginConfigYAML = PluginConfigYAML(plugin="classic")  # type: ignore[assignment]
    narrator: str | PluginConfigYAML = PluginConfigYAML(plugin="template")  # type: ignore[assignment]

    @field_validator("parser", "narrator", mode="before")
    @classmethod
    def _coerce_string_to_plugin_config(cls, v: Any) -> Any:
        """Coerce a bare string value to ``PluginConfigYAML(plugin=v)``.

        Passes through dicts (for normal Pydantic validation of the
        PluginConfigYAML model) and PluginConfigYAML instances unchanged.
        """
        if isinstance(v, str):
            return PluginConfigYAML(plugin=v)
        if isinstance(v, dict):
            return v
        if isinstance(v, PluginConfigYAML):
            return v
        raise ValueError(
            f"Plugin config must be a string or a mapping, got {type(v).__name__}"
        )


class EntityYAML(BaseModel):
    """Pydantic model for entity YAML files (rooms, items, npcs, shared)."""
    entity_id: str
    type: str
    name: str
    components: dict[str, Any] = {}
    spatial_anchor: str | None = None


class CliqueYAML(BaseModel):
    """Pydantic model for the clique block inside a hyper edge YAML."""
    subject: str | None = None
    verb: str = ""
    target: str | None = None
    instrument: str | None = None
    context: str | None = None
    instrument_not: str | None = None
    instrument_any: bool = False
    flag: str | None = None
    flag_not: str | None = None
    component: dict[str, Any] | None = None


class HyperEdgeYAML(BaseModel):
    """Pydantic model for hyper edge YAML files."""
    hyper_edge_id: str
    name: str
    priority: int
    clique: CliqueYAML
    operators: list[dict[str, Any]] = []
    output: str | None = None


class MacroEdgeYAML(BaseModel):
    """Pydantic model for macro edge YAML files.

    Gates are generic predicates — there is no connection-type field.  A
    world YAML that still writes a legacy connection-type/password/answer
    field FAILS loudly at load time (``extra="forbid"``) instead of
    silently dropping it.
    """
    model_config = ConfigDict(extra="forbid")

    macro_edge_id: str
    from_anchor: str
    to_anchor: str
    direction: str
    passage_name: str
    passage_description: str = ""
    question: str | None = None
    requires_text: str | None = None
    requires_item: str | None = None
    forbids_item: str | None = None
    requires_flag: str | None = None
    forbids_flag: str | None = None
    death_message: str | None = None
    open: bool = True


class VocabularyYAML(BaseModel):
    """Pydantic model for ``shared/vocabulary.yaml``.

    Defines per-world vocabulary: verb synonyms, stopwords, routing
    prepositions, speech markers, and speech verbs.
    """
    model_config = ConfigDict(extra="forbid")

    language: str | None = None
    verbs: dict[str, list[str]]
    stopwords: list[str]
    prepositions: dict[str, list[str]]
    speech_markers: list[str]
    speech_verbs: list[str]


# ---------------------------------------------------------------------------
# Runtime dataclasses (no Pydantic)
# ---------------------------------------------------------------------------


@dataclass
class Vocabulary:
    """Runtime vocabulary — plain dataclass, never Pydantic.

    Mirrors the six sections of ``VocabularyYAML`` with the same semantics
    but no validation overhead at runtime.
    """

    language: str | None
    verbs: dict[str, list[str]]
    stopwords: list[str]
    prepositions: dict[str, list[str]]
    speech_markers: list[str]
    speech_verbs: list[str]


# ---------------------------------------------------------------------------
# Conversion helpers — Pydantic model → dataclass
# ---------------------------------------------------------------------------


def _carry_over_from_model(m: CarryOverYAML) -> CarryOver:
    return CarryOver(inventory=list(m.inventory), flags=list(m.flags))


def _goal_condition_from_dict(d: dict[str, Any]) -> GoalCondition:
    """Convert a conditions dict entry to a GoalCondition dataclass.

    Supports both flat format (params inline: ``{type, entity, room}``)
    and nested format (``{type, params: {...}}``).
    """
    if "params" in d and isinstance(d["params"], dict):
        return GoalCondition(type=d.get("type", ""), params=dict(d["params"]))
    return GoalCondition(
        type=d.get("type", ""),
        params={k: v for k, v in d.items() if k != "type"},
    )


def _goal_conditions_from_model(m: GoalConditionsYAML) -> GoalConditions:
    """Convert GoalConditionsYAML → GoalConditions dataclass.

    Each entry in conditions may be an atomic dict (kicked into a
    GoalCondition) or a composite dict (``{"and": [...]}``, ``{"or":
    [...]}``).  Both are left as-is for the GoalEvaluator to handle.
    """
    converted: list[GoalCondition | dict[str, Any]] = []
    for item in m.conditions:
        if isinstance(item, dict):
            if "and" in item or "or" in item:
                # Composite — keep as dict for recursive evaluation
                converted.append(item)
            else:
                # Atomic — convert to GoalCondition
                converted.append(_goal_condition_from_dict(item))
    return GoalConditions(
        conditions=converted,
        output=m.output,
        side_effects=list(m.side_effects),
    )


def _episode_from_model(m: EpisodeYAML) -> Episode:
    return Episode(
        id=m.id,
        name=m.name,
        order=m.order,
        description=m.description,
        requires=list(m.requires),
        start_anchor=m.start_anchor,
        goal=_goal_conditions_from_model(m.goal),
        carry_over=_carry_over_from_model(m.carry_over),
    )


def _entity_from_model(m: EntityYAML) -> Entity:
    return Entity(
        entity_id=m.entity_id,
        type=m.type,
        name=m.name,
        components=dict(m.components),
        spatial_anchor=m.spatial_anchor,
    )


def _clique_from_model(m: CliqueYAML) -> Clique:
    return Clique(
        subject=m.subject,
        verb=m.verb,
        target=m.target,
        context=m.context,
        instrument=m.instrument,
        instrument_not=m.instrument_not,
        instrument_any=m.instrument_any,
        flag=m.flag,
        flag_not=m.flag_not,
        component=dict(m.component) if m.component is not None else None,
    )


def _hyper_edge_from_model(m: HyperEdgeYAML) -> HyperEdge:
    return HyperEdge(
        hyper_edge_id=m.hyper_edge_id,
        name=m.name,
        priority=m.priority,
        clique=_clique_from_model(m.clique),
        operators=list(m.operators),
        output=m.output,
    )


def _macro_edge_from_model(m: MacroEdgeYAML) -> MacroEdge:
    return MacroEdge(
        macro_edge_id=m.macro_edge_id,
        from_anchor=m.from_anchor,
        to_anchor=m.to_anchor,
        direction=m.direction,
        passage_name=m.passage_name,
        passage_description=m.passage_description,
        question=m.question,
        requires_text=m.requires_text,
        requires_item=m.requires_item,
        forbids_item=m.forbids_item,
        requires_flag=m.requires_flag,
        forbids_flag=m.forbids_flag,
        death_message=m.death_message,
        open=m.open,
    )


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Any:
    """Load and parse a single YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc


def _glob_yaml(directory: Path) -> list[Path]:
    """Return all .yaml / .yml files in *directory* (non-recursive)."""
    result = sorted(directory.glob("*.yaml"))
    result.extend(sorted(directory.glob("*.yml")))
    return result


def _glob_yaml_recursive(directory: Path) -> list[Path]:
    """Return all .yaml / .yml files under *directory* (recursive)."""
    result = sorted(directory.rglob("*.yaml"))
    result.extend(sorted(directory.rglob("*.yml")))
    return result


def _validate_pydantic(model_cls, data: Any, path: Path, label: str) -> Any:
    """Validate *data* with *model_cls* and return the model instance.

    Raises ValueError with a descriptive message on validation failure.
    """
    try:
        if isinstance(data, list):
            return [model_cls(**item) for item in data]
        return model_cls(**data)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid {label} in {path}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# EntityLoader
# ---------------------------------------------------------------------------


class EntityLoader:
    """Load a multi-file YAML world into runtime dataclasses.

    Pydantic is used exclusively at load time for structural validation.
    Runtime objects are plain ``@dataclass`` instances.
    """

    def __init__(self, world_path: str) -> None:
        self._world_path = Path(world_path).resolve()
        if not self._world_path.is_dir():
            raise FileNotFoundError(
                f"World path not found: {self._world_path}"
            )

    # -------------------------------------------------------------------
    # World config
    # -------------------------------------------------------------------

    def load_world_config(self) -> dict[str, Any]:
        """Load and validate ``world.yaml``, returning a plain dict."""
        path = self._world_path / "world.yaml"
        if not path.is_file():
            raise FileNotFoundError(f"world.yaml not found at {path}")

        raw = _load_yaml(path)
        model = _validate_pydantic(WorldYAML, raw, path, "world config")
        return cast(WorldYAML, model).model_dump()

    # -------------------------------------------------------------------
    # Vocabulary
    # -------------------------------------------------------------------

    def load_vocabulary(self, world_path: Path | None = None) -> Vocabulary | None:
        """Load per-world vocabulary from ``<world>/shared/vocabulary.yaml``.

        When *world_path* is given, that directory is used instead of
        the loader's configured world path.

        Returns ``None`` when the vocabulary file is absent (allowing
        the parser's default-vocabulary cascade).  Raises ``ValueError``
        when the file exists but is malformed or fails validation.

        Vocabulary precedence (per design, §3): constructor override >
        world file > DEFAULT constant.  This loader only handles the
        world-file tier; controller/bootstrap maps the cascade.
        """
        target = (world_path or self._world_path) / "shared" / "vocabulary.yaml"
        if not target.is_file():
            return None

        raw = _load_yaml(target)
        model = _validate_pydantic(
            VocabularyYAML, raw, target, "vocabulary"
        )
        v = cast(VocabularyYAML, model)
        return Vocabulary(
            language=v.language,
            verbs={k: list(w) for k, w in v.verbs.items()},
            stopwords=list(v.stopwords),
            prepositions={k: list(w) for k, w in v.prepositions.items()},
            speech_markers=list(v.speech_markers),
            speech_verbs=list(v.speech_verbs),
        )

    # -------------------------------------------------------------------
    # Episodes
    # -------------------------------------------------------------------

    def load_episodes(self) -> list[Episode]:
        """Load all episodes from ``episodes/*.yaml``."""
        episodes_dir = self._world_path / "episodes"
        if not episodes_dir.is_dir():
            return []

        result: list[Episode] = []
        for path in _glob_yaml(episodes_dir):
            raw = _load_yaml(path)
            model = _validate_pydantic(EpisodeYAML, raw, path, "episode")
            result.append(_episode_from_model(cast(EpisodeYAML, model)))
        return result

    # -------------------------------------------------------------------
    # Shared entities
    # -------------------------------------------------------------------

    def load_shared_entities(self, episode_id: str) -> list[Entity]:
        """Load entities from ``shared/`` (player, vocabulary, etc.)."""
        shared_dir = self._world_path / "shared"
        if not shared_dir.is_dir():
            return []
        return self._load_entities_from_dir(shared_dir)

    # -------------------------------------------------------------------
    # Rooms / items / NPCs
    # -------------------------------------------------------------------

    def load_rooms(self, episode_id: str) -> list[Entity]:
        """Load room entities from ``episode-XX/rooms/*.yaml``."""
        return self._load_entities_from_episode_subdir(episode_id, "rooms")

    def load_items(self, episode_id: str) -> list[Entity]:
        """Load item entities from ``episode-XX/items/*.yaml``."""
        return self._load_entities_from_episode_subdir(episode_id, "items")

    def load_npcs(self, episode_id: str) -> list[Entity]:
        """Load NPC entities from ``episode-XX/npcs/*.yaml``."""
        return self._load_entities_from_episode_subdir(episode_id, "npcs")

    # -------------------------------------------------------------------
    # Graph
    # -------------------------------------------------------------------

    def load_macro_edges(self, episode_id: str) -> list[MacroEdge]:
        """Load MacroEdges from ``episode-XX/macros/*.yaml``."""
        macro_dir = self._episode_dir(episode_id) / "macros"

        result: list[MacroEdge] = []
        for path in _glob_yaml(macro_dir):
            raw = _load_yaml(path)
            models = _validate_pydantic(MacroEdgeYAML, raw, path, "macro edge")
            if isinstance(models, list):
                result.extend(
                    _macro_edge_from_model(m) for m in models
                )
            else:
                result.append(_macro_edge_from_model(models))
        return result

    def load_hyper_edges(self, episode_id: str) -> list[HyperEdge]:
        """Load HyperEdges from ``episode-XX/actions/*.yaml`` (recursive)."""
        actions_dir = self._episode_dir(episode_id) / "actions"

        result: list[HyperEdge] = []
        for path in _glob_yaml_recursive(actions_dir):
            raw = _load_yaml(path)
            models = _validate_pydantic(
                HyperEdgeYAML, raw, path, "hyper edge"
            )
            if isinstance(models, list):
                result.extend(
                    _hyper_edge_from_model(m) for m in models
                )
            else:
                result.append(_hyper_edge_from_model(models))
        return result

    # -------------------------------------------------------------------
    # Aggregated episode data
    # -------------------------------------------------------------------

    def load_episode_data(
        self, episode_id: str, episode: Episode
    ) -> dict[str, Any]:
        """Load all episode data into a dict of entity and edge lists."""
        return {
            "rooms": self.load_rooms(episode_id),
            "items": self.load_items(episode_id),
            "npcs": self.load_npcs(episode_id),
            "macro_edges": self.load_macro_edges(episode_id),
            "hyper_edges": self.load_hyper_edges(episode_id),
        }

    # -------------------------------------------------------------------
    # Integrity validation
    # -------------------------------------------------------------------

    def validate_world(self) -> list[str]:
        """Validate world integrity across all episodes.

        Checks performed:
        - Every ``start_anchor`` exists as a loaded room entity.
        - No dangling ``spatial_anchor`` references.
        - No duplicate ``(verb, target, priority)`` hyper edges in the
          same anchor (warning-level).

        Returns a list of problem messages.  Empty list = valid world.
        """
        problems: list[str] = []

        episodes = self.load_episodes()

        # Collect all known entity IDs across all episodes' rooms/items/NPCs
        # and shared entities.
        all_entity_ids: set[str] = set()

        for ep in episodes:
            eid = ep.id
            shared = self.load_shared_entities(eid)
            rooms = self.load_rooms(eid)
            items = self.load_items(eid)
            npcs = self.load_npcs(eid)

            for ent in shared + rooms + items + npcs:
                all_entity_ids.add(ent.entity_id)

        # --- start_anchor existence -----------------------------------
        for ep in episodes:
            if ep.start_anchor not in all_entity_ids:
                problems.append(
                    f"Episode '{ep.id}' start_anchor "
                    f"'{ep.start_anchor}' does not exist"
                )

        # --- dangling spatial_anchor references -----------------------
        for ep in episodes:
            eid = ep.id
            shared = self.load_shared_entities(eid)
            rooms = self.load_rooms(eid)
            items = self.load_items(eid)
            npcs = self.load_npcs(eid)

            for ent in shared + rooms + items + npcs:
                anchor = ent.spatial_anchor
                if anchor is not None and anchor not in all_entity_ids:
                    problems.append(
                        f"Entity '{ent.entity_id}' (episode '{eid}') "
                        f"has dangling spatial_anchor '{anchor}'"
                    )

        # --- duplicate (verb, target, priority) hyper edges -----------
        for ep in episodes:
            eid = ep.id
            hyper_edges = self.load_hyper_edges(eid)

            # Group by (verb, target, priority) — same anchor is
            # irrelevant for world-level validation; same episode-wide
            # triplet is flagged.
            seen: dict[tuple[str, str | None, int], str] = {}
            for he in hyper_edges:
                key = (he.clique.verb, he.clique.target, he.priority)
                if key in seen:
                    prev_id = seen[key]
                    problems.append(
                        f"Duplicate priority {he.priority} for "
                        f"(verb='{he.clique.verb}', "
                        f"target={he.clique.target!r}) in episode '{eid}': "
                        f"edges '{prev_id}' and '{he.hyper_edge_id}'"
                    )
                else:
                    seen[key] = he.hyper_edge_id

        return problems

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _episode_dir(self, episode_id: str) -> Path:
        """Resolve the episode directory from an episode ID.

        Tries ``episode-XX`` (where XX is the numeric suffix of the ID)
        as the primary convention.
        """
        m = _EPISODE_DIR_RE.search(episode_id)
        if m:
            return self._world_path / f"episode-{m.group(1)}"
        # Fallback: use the episode_id directly as the directory name
        return self._world_path / episode_id

    def _load_entities_from_dir(self, directory: Path) -> list[Entity]:
        """Load Entity objects from all YAML files in *directory* (flat)."""
        result: list[Entity] = []
        for path in _glob_yaml(directory):
            raw = _load_yaml(path)
            models = _validate_pydantic(EntityYAML, raw, path, "entity")
            if isinstance(models, list):
                result.extend(_entity_from_model(m) for m in models)
            else:
                result.append(_entity_from_model(models))
        return result

    def _load_entities_from_episode_subdir(
        self, episode_id: str, subdir: str
    ) -> list[Entity]:
        """Load Entity objects from ``episode-XX/<subdir>/*.yaml``."""
        directory = self._episode_dir(episode_id) / subdir
        return self._load_entities_from_dir(directory)
