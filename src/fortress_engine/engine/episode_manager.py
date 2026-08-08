"""EpisodeManager — load and transition between story episodes.

Follows tdd.md §4.6 and turn-orchestrator spec (episode transitions, carry_over).
The engine is entity-agnostic: it knows about ``spatial_anchor`` and
``anchor``, never about "rooms", "items", or "npcs".  World-level
vocabulary lives in world data, not in the engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fortress_engine.entities.entity import CarryOver, Episode, Entity
from fortress_engine.engine.state import WorldState
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    EPISODE_STARTED,
    EPISODE_TRANSITION,
    EngineEvent,
)

if TYPE_CHECKING:
    from fortress_engine.engine.graph import DualGraphEngine


class EpisodeManager:
    """Loads episodes from YAML, manages transitions, and applies carry_over."""

    def __init__(
        self,
        episodes: list[Episode],
        world_path: str,
        event_bus: EventBus,
    ) -> None:
        """Initialise the manager with all world episodes.

        Marks those with ``requires == []`` as available.
        """
        self._episodes: dict[str, Episode] = {ep.id: ep for ep in episodes}
        self._world_path = world_path
        self._event_bus = event_bus

        # Available episodes are those with no prerequisites.
        self._available_ids: set[str] = {
            ep.id for ep in episodes if not ep.requires
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_episode(self, episode_id: str, state: WorldState) -> DualGraphEngine:
        """Load the episode from disk, populate *state*, and return the graph.

        Actions performed:
        1. Load episode data (rooms, items, NPCs, macro/hyper edges) via
           :class:`~fortress_engine.entities.loader.EntityLoader`.
        2. Merge all entities into *state*.
        3. Build a fresh :class:`~fortress_engine.engine.graph.DualGraphEngine`
           from rooms and macro edges.
        4. Register hyper edges indexed by their anchor.
        5. Teleport the active protagonist to ``start_anchor``.
        6. Emit ``episode_started``.

        Returns:
            The constructed ``DualGraphEngine``.
        """
        from fortress_engine.entities.loader import EntityLoader
        from fortress_engine.engine.graph import DualGraphEngine

        episode = self._episodes[episode_id]

        loader = EntityLoader(self._world_path)

        # Load episode data from disk.
        data = loader.load_episode_data(episode_id, episode)
        shared = loader.load_shared_entities(episode_id)

        # Merge all entities into state.
        # Only add entities that do NOT already exist — preserve in-memory
        # entity mutations (e.g. spatial_anchor changes from gameplay).
        all_entities = shared + data["rooms"] + data["items"] + data["npcs"]
        for ent in all_entities:
            if ent.entity_id not in state.entities:
                state.entities[ent.entity_id] = ent

        # Build macro graph.
        graph = DualGraphEngine()
        graph.build_macro_graph(data["rooms"], data["macro_edges"])

        # Register hyper edges under start_anchor, then distribute to all
        # anchors so actions work regardless of protagonist position.
        for he in data["hyper_edges"]:
            graph.add_hyper_edge(episode.start_anchor, he)

        # Distribute hyper edges to all spatial_anchors in the episode.
        # The engine is entity-agnostic: we iterate spatial_anchor values
        # without referencing world-level concepts like "rooms" or "items".
        self.distribute_hyper_edges_to_anchors(graph, state, episode_id)

        # Teleport the active protagonist to the episode start_anchor.
        protagonist = state.get_entity(state.active_protagonist_id)
        from_anchor = protagonist.spatial_anchor
        protagonist.spatial_anchor = episode.start_anchor

        # Update state metadata.
        state.current_episode_id = episode_id
        state.turn_number = 0

        # Emit entity_entered for the player arriving at start_anchor.
        from fortress_engine.events.event_types import ENTITY_ENTERED
        self._event_bus.emit(
            EngineEvent.create(
                ENTITY_ENTERED,
                turn_number=state.turn_number,
                payload={
                    "entity_id": state.active_protagonist_id,
                    "entity_name": protagonist.name,
                    "from_anchor_id": from_anchor,
                    "to_anchor_id": episode.start_anchor,
                    "protagonist_id": state.active_protagonist_id,
                },
                protagonist_id=state.active_protagonist_id,
                episode_id=episode_id,
            )
        )

        # Emit episode_started.
        self._event_bus.emit(
            EngineEvent.create(
                EPISODE_STARTED,
                turn_number=state.turn_number,
                payload={
                    "episode_id": episode_id,
                    "episode_name": episode.name,
                    "start_anchor_id": episode.start_anchor,
                },
                protagonist_id=state.active_protagonist_id,
                episode_id=episode_id,
            )
        )

        return graph  # type: ignore[return-value]

    def transition_to_next(
        self,
        current_episode_id: str,
        state: WorldState,
        current_graph: DualGraphEngine,
    ) -> DualGraphEngine | None:
        """Transition from *current_episode_id* to the next episode.

        Returns the new graph, or ``None`` if there is no next episode.
        """
        from fortress_engine.engine.graph import DualGraphEngine

        current = self._episodes[current_episode_id]

        # Find the next episode (higher order, earliest order wins).
        next_ep: Episode | None = None
        for ep in self._episodes.values():
            if ep.order > current.order and current_episode_id in ep.requires:
                if next_ep is None or ep.order < next_ep.order:  # pragma: no branch — only one match in 2-ep world
                    next_ep = ep

        if next_ep is None:
            return None

        next_id = next_ep.id

        # 1. Apply carry_over from the current episode definition.
        #    This drops unwanted items and clears unwanted flags.
        self.apply_carry_over(current.carry_over, state)

        # 2. Capture entities that survive the transition.
        #    start_episode will load fresh data from disk, so we must
        #    preserve the protagonist and any items still in inventory.
        kept_entities: dict[str, Entity] = {}
        for p_id in state.player_controlled_entities:
            kept_entities[p_id] = state.get_entity(p_id)
            for item in state.get_player_inventory(p_id):
                kept_entities[item.entity_id] = item

        # 3. Unload the current graph.
        self.unload_graph(current_graph)

        # 4. Emit episode_transition (before loading the new episode).
        self._event_bus.emit(
            EngineEvent.create(
                EPISODE_TRANSITION,
                turn_number=state.turn_number,
                payload={
                    "from_episode_id": current_episode_id,
                    "to_episode_id": next_id,
                    "carry_over_applied": {
                        "inventory": current.carry_over.inventory,
                        "flags": current.carry_over.flags,
                    },
                },
                protagonist_id=state.active_protagonist_id,
                episode_id=current_episode_id,
            )
        )

        # 5. Load the next episode.  This writes fresh entities into
        #    state.entities and teleports the protagonist to the new
        #    start_anchor.  We must restore the kept entities afterwards
        #    to preserve inventory items that survived carry_over.
        new_graph = self.start_episode(next_id, state)

        # 6. Restore carried entities — overwrite any disk-loaded copies.
        for eid, ent in kept_entities.items():
            state.entities[eid] = ent

        # 7. Re-teleport protagonist to the new episode's start_anchor
        #    (start_episode already did this, but restoring the old
        #     protagonist might have overwritten it).
        protagonist = state.get_entity(state.active_protagonist_id)
        protagonist.spatial_anchor = next_ep.start_anchor

        return new_graph  # type: ignore[return-value]

    def distribute_hyper_edges_to_anchors(
        self,
        graph: "DualGraphEngine",
        state: WorldState,
        episode_id: str,
    ) -> None:
        """Distribute hyper edges from the episode start_anchor to all anchors.

        ``start_episode()`` registers all hyper edges under the episode's
        ``start_anchor`` only.  Because the engine resolves hyper edges by
        anchor, edges defined at the start anchor would be unreachable from
        any other anchor.  This copies every registered hyper edge to every
        anchor in the graph so actions work regardless of the protagonist's
        current anchor.

        The engine is entity-agnostic: it operates on ``graph._anchors``
        (the macro-graph node index), not on world-level concepts like
        "rooms" or "items".

        Args:
            graph: The graph built by ``start_episode()``.
            state: Current world state (unused, kept for API symmetry).
            episode_id: The active episode ID (unused, kept for symmetry
                with ``start_episode`` and future per-episode filtering).
        """
        _ = state  # reserved for future filtering
        _ = episode_id  # reserved for future per-episode filtering

        start_anchor = self._episodes[episode_id].start_anchor

        # Collect ALL unique hyper edges registered under start_anchor.
        start_edges: list[object] = []
        for verb_edges in graph._hyper_edges.get(start_anchor, {}).values():
            start_edges.extend(verb_edges)

        if not start_edges:
            return

        # Collect all anchors from the graph (entity-agnostic).
        target_anchors: set[str] = set(graph._anchors.keys())

        # Distribute: copy every edge from start_anchor to every other anchor.
        # Skip anchors that already have hyper edges registered (avoid duplicates).
        for anchor_id in target_anchors:
            if anchor_id == start_anchor:
                continue
            if graph._hyper_edges.get(anchor_id):
                continue  # anchor already has edges; don't duplicate
            for edge in start_edges:
                graph.add_hyper_edge(anchor_id, edge)

    def apply_carry_over(self, carry_over: CarryOver, state: WorldState) -> None:
        """Apply carry-over rules to *state*.

        - ``inventory: ["*"]`` — keep all items in protagonist inventory.
        - ``inventory: ["item_x", ...]`` — keep only specific items.
        - ``inventory: []`` — drop everything from inventory.
        - ``flags: ["*"]`` — keep all flags.
        - ``flags: ["flag_a", ...]`` — keep only specific flags.
        - ``flags: []`` — clear all flags.
        """
        protagonist_id = state.active_protagonist_id

        # --- Inventory ---
        if carry_over.inventory == ["*"]:
            # Keep everything: no removal needed.
            pass
        elif carry_over.inventory:
            # Keep only specific items — move others out of inventory.
            keep_ids = set(carry_over.inventory)
            for item in state.get_player_inventory(protagonist_id):
                if item.entity_id not in keep_ids:
                    item.spatial_anchor = None  # sent to limbo
        else:
            # Empty list: drop everything from inventory.
            for item in state.get_player_inventory(protagonist_id):
                item.spatial_anchor = None  # sent to limbo

        # --- Flags ---
        if carry_over.flags == ["*"]:
            # Keep all flags: no change.
            pass
        elif carry_over.flags:
            # Keep only specific flags — remove others.
            keep_flags = set(carry_over.flags)
            for flag_name in list(state.flag_book.keys()):
                if flag_name not in keep_flags:
                    del state.flag_book[flag_name]
        else:
            # Empty list: clear all flags.
            state.flag_book.clear()

    def get_available_episodes(self) -> list[Episode]:
        """Return episodes that can be started (no prerequisites unsatisfied)."""
        return [
            self._episodes[eid]
            for eid in self._available_ids
            if eid in self._episodes
        ]

    def unload_graph(self, graph: DualGraphEngine) -> None:
        """Clear the graph's internal data structures."""
        graph._anchors.clear()
        graph._macro_edges.clear()
        graph._hyper_edges.clear()
