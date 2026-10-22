"""GameRuntime — a fully wired engine with cheap checkpoint/restore.

Dev tooling for the definition-driven solver (docs/15-solver-planner-design.md).
The real engine stays the transition function; this module only wires it
(mirroring ``cli/main.py::_build_engine``), runs single steps and snapshots the
mutable state as a compact diff against the post-``start_episode`` baseline.

No world-specific logic: the protagonist is chosen from the world's own shared
entities (see :func:`select_protagonist`), never by ``Entity.type``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Hashable

from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity, ParsedCommand
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    EPISODE_COMPLETED,
    ERROR_OUTPUT,
    GAME_OVER,
)


@dataclass(frozen=True)
class StepResult:
    """Outcome of one executed command."""

    command: str
    ok: bool
    error_code: str | None = None
    gate_code: str | None = None
    game_over: bool = False
    goal_reached: bool = False
    output: str = ""


@dataclass
class Checkpoint:
    """Compact diff against the runtime baseline.

    Attributes:
        entities: entity_id → (spatial_anchor, components) for entities that
            differ from baseline only.
        flags: full copy of the flag book.
        edges: macro_edge_id → ``open`` for edges that differ from baseline.
        turn_number: engine turn counter at capture time.
    """

    entities: dict[str, tuple[str | None, dict[str, Any]]] = field(
        default_factory=dict
    )
    flags: dict[str, bool] = field(default_factory=dict)
    edges: dict[str, bool] = field(default_factory=dict)
    turn_number: int = 0


# Same stand-in the CLI builds when a world authors no shared entity at all
# (``cli/main.py::_build_engine``); kept only so such worlds stay runnable.
_FALLBACK_PROTAGONIST = ("hero", "player", "Hero")


def select_protagonist(
    shared: list[Entity], protagonist_id: str | None = None
) -> Entity:
    """Choose the protagonist from the world's shared entities.

    ``Entity.type`` is an opaque world-owned string, so it is never consulted.
    Order: an explicit *protagonist_id*; the shared entity whose
    ``player_controlled`` component is ``True`` (PRD 4.1); the only shared entity
    when there is exactly one; otherwise the CLI's stand-in when there are none.

    Raises:
        KeyError: *protagonist_id* names no shared entity.
        ValueError: several candidates and nothing to disambiguate them.
    """
    if protagonist_id is not None:
        for entity in shared:
            if entity.entity_id == protagonist_id:
                return entity
        raise KeyError(protagonist_id)
    marked = [e for e in shared if e.components.get("player_controlled") is True]
    if len(marked) == 1:
        return marked[0]
    candidates = marked or shared
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        ids = sorted(e.entity_id for e in candidates)
        raise ValueError(
            f"ambiguous protagonist among {ids}: mark one with "
            "player_controlled: true or pass protagonist_id"
        )
    entity_id, entity_type, name = _FALLBACK_PROTAGONIST
    return Entity(entity_id, entity_type, name, {}, None)


def _freeze(value: Any) -> Hashable:
    """Return a hashable, order-insensitive-for-dicts form of *value*."""
    if isinstance(value, dict):
        return tuple(
            sorted(((repr(k), _freeze(v)) for k, v in value.items()))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(v) for v in value)
    return value


class GameRuntime:
    """Wired engine for ``(world_path, episode_id)`` with checkpoint/restore."""

    def __init__(
        self,
        world_path: str | Path,
        episode_id: str,
        protagonist_id: str | None = None,
    ):
        from fortress_engine.plugins.factory import (
            PluginConfig,
            create_narrator,
            create_parser,
        )

        self.world_path = Path(world_path)
        self.episode_id = episode_id
        self.turns = 0

        self.loader = EntityLoader(str(self.world_path))
        self.vocabulary = self.loader.load_vocabulary()
        episodes = self.loader.load_episodes()
        language = self.loader.load_world_config().get("language", "es")

        self.parser = create_parser(
            PluginConfig(name="classic", options={"vocabulary": self.vocabulary}),
            language,
        )
        self.narrator = create_narrator(PluginConfig(name="template"), language)

        player = select_protagonist(
            self.loader.load_shared_entities(episode_id), protagonist_id
        )
        self.protagonist_id = player.entity_id

        self.bus = EventBus()
        self.narrator.initialize(self.bus)
        self.state = WorldState(
            entities={player.entity_id: player},
            player_controlled_entities=[player.entity_id],
            active_protagonist_id=player.entity_id,
            current_episode_id="",
            turn_number=0,
        )
        self._events: list = []
        self.bus.subscribe("*", self._events.append)

        # Search is scoped to one episode. Do not let goal completion unload
        # this graph and replace the entity set with a successor episode.
        selected = {episode.id: episode for episode in episodes}[episode_id]
        episode_manager = EpisodeManager([selected], str(self.world_path), self.bus)
        self.graph = episode_manager.start_episode(episode_id, self.state)
        episode_manager.distribute_hyper_edges_to_anchors(
            self.graph, self.state, episode_id
        )
        self.goal_evaluator = episode_manager.goal_evaluator_for(episode_id)
        self.orchestrator = TurnOrchestrator(
            state=self.state,
            graph=self.graph,
            event_bus=self.bus,
            parser=self.parser,
            narrator=self.narrator,
            goal_evaluator=self.goal_evaluator,
            episode_manager=episode_manager,
            vocabulary=self.vocabulary,
        )

        self._events.clear()
        self._baseline_entities = {
            eid: (e.spatial_anchor, copy.deepcopy(e.components))
            for eid, e in self.state.entities.items()
        }
        self._baseline_flags = dict(self.state.flag_book)
        self._baseline_edges = {
            e.macro_edge_id: e.open for e in self.graph.iter_macro_edges()
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def anchor(self) -> str | None:
        """Return the protagonist's ``spatial_anchor``."""
        return self.state.get_entity(self.protagonist_id).spatial_anchor

    def parse(self, command: str) -> ParsedCommand:
        """Parse *command* without touching state."""
        return self.parser.parse(command, self.state)

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def step(self, command: str) -> StepResult:
        """Execute exactly one turn and summarise the emitted events."""
        self.turns += 1
        self._events.clear()
        try:
            self.orchestrator.execute_turn(command)
        except Exception:  # noqa: BLE001 — a probe must never crash the search
            self._events.clear()
            return StepResult(command, ok=False, error_code="exception")
        events = list(self._events)
        self._events.clear()

        error = next((e for e in events if e.type == ERROR_OUTPUT), None)
        game_over = any(e.type == GAME_OVER for e in events)
        output = " ".join(
            e.payload["text"]
            for e in events
            if e.type == "action_output" and e.payload.get("text")
        )
        return StepResult(
            command=command,
            ok=error is None and not game_over,
            error_code=error.payload.get("error_code") if error else None,
            gate_code=(
                (error.payload.get("data") or {}).get("gate_code")
                if error
                else None
            ),
            game_over=game_over,
            goal_reached=any(e.type == EPISODE_COMPLETED for e in events),
            output=output,
        )

    # ------------------------------------------------------------------
    # Checkpoint / restore
    # ------------------------------------------------------------------

    def checkpoint(self) -> Checkpoint:
        """Capture the current state as a diff against the baseline."""
        entities = {}
        for eid, entity in self.state.entities.items():
            base_anchor, base_components = self._baseline_entities[eid]
            if (
                entity.spatial_anchor != base_anchor
                or entity.components != base_components
            ):
                entities[eid] = (
                    entity.spatial_anchor,
                    copy.deepcopy(entity.components),
                )
        edges = {
            e.macro_edge_id: e.open
            for e in self.graph.iter_macro_edges()
            if e.open != self._baseline_edges[e.macro_edge_id]
        }
        return Checkpoint(
            entities=entities,
            flags=dict(self.state.flag_book),
            edges=edges,
            turn_number=self.state.turn_number,
        )

    def restore(self, cp: Checkpoint) -> None:
        """Reset to baseline, then apply *cp*, mutating state in place."""
        for eid, entity in self.state.entities.items():
            anchor, components = cp.entities.get(
                eid, self._baseline_entities[eid]
            )
            entity.spatial_anchor = anchor
            entity.components.clear()
            entity.components.update(copy.deepcopy(components))
        self.state.flag_book.clear()
        self.state.flag_book.update(cp.flags)
        for edge in self.graph.iter_macro_edges():
            edge.open = cp.edges.get(
                edge.macro_edge_id, self._baseline_edges[edge.macro_edge_id]
            )
        self.state.turn_number = cp.turn_number

    def state_key(self, cp: Checkpoint | None = None) -> Hashable:
        """Canonical gameplay-relevant key (excludes ``turn_number``)."""
        if cp is None:
            cp = self.checkpoint()
        return (
            tuple(
                (eid, anchor, _freeze(components))
                for eid, (anchor, components) in sorted(cp.entities.items())
            ),
            tuple(sorted(f for f, v in cp.flags.items() if v)),
            tuple(sorted(cp.edges.items())),
        )
