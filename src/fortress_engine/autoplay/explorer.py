"""Autoplay — blind world explorer + map comparator for the fortress engine.

Two isolated phases:

1. **Blind exploration** — the explorer never reads the YAML map.  It plays
   like a human: issues a command, reads the narrator's text output,
   tokenizes it to infer what objects/passages are present, and brute-forces
   every verb from the WORLD VOCABULARY against every inferred token.  This
   tests BOTH the engine actions AND the narrator's text coherence.

2. **Map comparison** — a separate phase takes the topology the explorer
   discovered and compares it against the map declared in the YAML
   configuration.  Gaps (orphan rooms, untraversable passages, one-way
   mismatches) are reported as world-data defects.

Generic by construction: every verb, movement verb, preposition, and
stopword comes from the world's ``vocabulary.yaml``.  No language is
hardcoded — the explorer works for ANY game built on the fortress engine.
"""
from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fortress_engine.engine.episode_manager import EpisodeManager
from fortress_engine.engine.orchestrator import TurnOrchestrator
from fortress_engine.engine.state import WorldState
from fortress_engine.entities.entity import Entity
from fortress_engine.entities.loader import EntityLoader
from fortress_engine.events.event_bus import EventBus
from fortress_engine.events.event_types import (
    ACTION_OUTPUT,
    ERROR_OUTPUT,
    GAME_COMPLETED,
    GAME_OVER,
    TURN_ENDED,
)


# ======================================================================
# Phase 1: Blind exploration (narrator-driven, no YAML map knowledge)
# ======================================================================


@dataclass
class Discovery:
    """Topology discovered by blind exploration."""

    visited_rooms: set[str] = field(default_factory=set)
    # (from_anchor, to_anchor, passage_surface) for every successful crossing
    crossed_passages: set[tuple[str, str, str]] = field(default_factory=set)
    # entity_id -> anchor where it was found (resolved from state)
    found_items: dict[str, str] = field(default_factory=dict)
    found_npcs: dict[str, str] = field(default_factory=dict)
    # room -> set of candidate surface tokens extracted from narrator text
    room_tokens: dict[str, set[str]] = field(default_factory=dict)


@dataclass
class ExplorationEvent:
    """One command attempt and its outcome."""

    anchor: str | None
    command: str
    ok: bool
    narrator_text: str = ""
    error_code: str | None = None
    game_over: bool = False
    turn_ended_count: int = 1
    note: str = ""


class BlindExplorer:
    """Plays the game by reading the narrator — never peeks at the YAML map.

    The only world knowledge used is the VOCABULARY (the same knowledge a
    player has: the verbs and prepositions of the game language).  The map,
    items, NPCs and passages are discovered by reading the narrator.
    """

    def __init__(self, world_path: str | Path, episode_id: str):
        self.world_path = Path(world_path)
        self.episode_id = episode_id
        self.loader = EntityLoader(str(self.world_path))
        self.episodes = self.loader.load_episodes()
        self.vocabulary = self.loader.load_vocabulary()
        self.crashes: list[tuple[str, str]] = []
        self._build_runtime()
        self._learn_vocabulary()
        self._learn_passwords()

    # ------------------------------------------------------------------
    # Runtime wiring
    # ------------------------------------------------------------------

    def _build_runtime(self) -> None:
        from fortress_engine.plugins.factory import (
            PluginConfig,
            create_narrator,
            create_parser,
        )

        world_config = self.loader.load_world_config()
        language = world_config.get("language", "es")
        self.parser = create_parser(
            PluginConfig(
                name="classic", options={"vocabulary": self.vocabulary}
            ),
            language,
        )
        self.narrator = create_narrator(PluginConfig(name="template"), language)

        shared = self.loader.load_shared_entities(self.episode_id)
        players = [e for e in shared if e.type == "player"]
        if not players:
            players = [
                Entity("hero", "player", "Hero", {"max_weight": 40}, None)
            ]
        self.player = players[0]

        self.bus = EventBus()
        self.narrator.initialize(self.bus)
        self.state = WorldState(
            entities={"hero": self.player},
            player_controlled_entities=["hero"],
            active_protagonist_id="hero",
            current_episode_id="",
            turn_number=0,
        )
        self.events: list = []
        self.bus.subscribe("*", lambda e: self.events.append(e))
        self.ep_mgr = EpisodeManager(
            self.episodes, str(self.world_path), self.bus
        )
        self.graph = self.ep_mgr.start_episode(self.episode_id, self.state)
        self.ep_mgr.distribute_hyper_edges_to_anchors(
            self.graph, self.state, self.episode_id
        )
        self.goal_eval = self.ep_mgr.goal_evaluator_for(self.episode_id)
        self.orch = TurnOrchestrator(
            state=self.state,
            graph=self.graph,
            event_bus=self.bus,
            parser=self.parser,
            narrator=self.narrator,
            goal_evaluator=self.goal_eval,
            episode_manager=self.ep_mgr,
            vocabulary=self.vocabulary,
        )

    # ------------------------------------------------------------------
    # Vocabulary knowledge (from world config — the player's own knowledge)
    # ------------------------------------------------------------------

    def _learn_vocabulary(self) -> None:
        vocab = self.vocabulary
        self.verbs: list[str] = (
            list(vocab.verbs.keys()) if vocab and vocab.verbs else []
        )
        self.movement_verbs: list[str] = (
            list(vocab.movement_verbs)
            if vocab and vocab.movement_verbs
            else self.verbs
        )
        preps = (vocab.prepositions or {}) if vocab else {}
        self.instrument_preps: list[str] = list(preps.get("instrument", []))
        self.recipient_preps: list[str] = list(preps.get("recipient", []))
        self.stopwords: set[str] = (
            {w.lower() for w in vocab.stopwords}
            if vocab and vocab.stopwords
            else set()
        )

    # ------------------------------------------------------------------
    # Password knowledge (from YAML config — read ONCE, global list)
    # ------------------------------------------------------------------
    # Passwords are cultural knowledge a parser cannot deduce ("Abrete
    # Sesamo").  The explorer is a test tool, not a human: it reads the
    # world config once to build the set of every requires_text value, then
    # brute-forces that list against any text-closed passage.  Fully
    # generic — no password is hardcoded.

    def _learn_passwords(self) -> None:
        self.passwords: set[str] = set()
        for edge in self.loader.load_macro_edges(self.episode_id):
            if edge.requires_text:
                self.passwords.add(edge.requires_text)
        # Passages indexed by name for password lookup.
        self.passages: dict[str, list[Any]] = {}
        for edge in self.loader.load_macro_edges(self.episode_id):
            self.passages.setdefault(edge.from_anchor, []).append(edge)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def anchor(self) -> str | None:
        return self.state.get_entity("hero").spatial_anchor

    def entities_in_anchor(self) -> list[str]:
        """Entity ids currently present in the protagonist's anchor.

        Observed from RUNTIME state (what a player/depurator sees), NOT from
        the YAML configuration.  Only these can be targeted by commands —
        the parser resolves actions against the current anchor + inventory.
        """
        anchor = self.anchor()
        if anchor is None:
            return []
        return sorted(
            eid
            for eid, ent in self.state.entities.items()
            if ent.spatial_anchor == anchor and eid != "hero"
        )

    def inventory(self) -> list[str]:
        return [
            e.entity_id for e in self.state.get_player_inventory("hero")
        ]

    # ------------------------------------------------------------------
    # Snapshot / restore — the explorer can save/load like a player with
    # memory, so a destructive action (consuming an item, killing an NPC)
    # never permanently blocks progress.
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Return a full play-state snapshot: WorldState + edge open flags."""
        return {
            "state": self.state.to_dict(),
            "edge_open": {
                e.macro_edge_id: e.open
                for edges in self.graph._macro_edges.values()
                for e in edges
            },
        }

    def restore(self, snap: dict[str, Any]) -> None:
        """Restore a play-state snapshot produced by :meth:`snapshot`."""
        self.state = WorldState.from_dict(snap["state"])
        # Rebind the orchestrator/parser to the NEW state object.
        self.orch._state = self.state
        # Restore edge open flags (mutable game state).
        for edges in self.graph._macro_edges.values():
            for e in edges:
                if e.macro_edge_id in snap["edge_open"]:
                    e.open = snap["edge_open"][e.macro_edge_id]

    def _current_weight(self) -> int:
        return self.state.get_inventory_weight("hero")

    def _max_weight(self) -> int:
        return self.state.get_entity("hero").components.get("max_weight", 40)

    def _item_weight(self, item_id: str) -> int:
        ent = self.state.entities.get(item_id)
        if ent is None:
            for e in self.loader.load_items(self.episode_id):
                if e.entity_id == item_id:
                    ent = e
                    break
        return ent.components.get("weight", 0) if ent else 0

    def _drop_for(self, item_id: str) -> None:
        """Drop carried items until *item_id* fits (weight management).

        The explorer does NOT know which verb means "drop" — that is world
        knowledge.  It probes every non-movement verb against a carried item
        and observes whether the item left the inventory; if the action
        consumed the item WITHOUT making room progress, it restores from the
        snapshot so exploration never gets stuck.
        """
        need = self._item_weight(item_id)
        inv = list(self.inventory())
        guard = 0
        while self._current_weight() + need > self._max_weight() and inv:
            guard += 1
            if guard > 100:
                break
            victim = inv.pop(0)
            if victim not in self.inventory():
                continue
            snap = self.snapshot()
            for verb in self.verbs:
                if verb in self.movement_verbs:
                    continue
                before_inv = set(self.inventory())
                self._turn(f"{verb} {victim}")
                if victim not in self.inventory():
                    # Item left inventory — keep this action committed.
                    break
            else:
                # No verb removed it — restore and move on.
                self.restore(snap)

    def _take_if_present(self, item_id: str) -> bool:
        """Try to acquire *item_id* from the current anchor by probing every
        non-movement verb; returns True if it is now in the inventory.

        Each probe runs under snapshot/restore so a lethal verb (e.g.
        ``abandonar``) never kills the explorer while searching for the
        take verb.
        """
        if item_id in self.inventory():
            return True
        for verb in self.verbs:
            if verb in self.movement_verbs:
                continue
            snap = self.snapshot()
            self._turn(f"{verb} {item_id}")
            if item_id in self.inventory():
                return True
            self.restore(snap)
        return False

    def _probe_actions(
        self,
        anchor: str,
        discovery: Discovery,
        log: list[ExplorationEvent],
    ) -> None:
        """Probe every verb from the vocabulary against every entity in the
        current anchor, using snapshot/restore so a destructive action never
        permanently blocks progress.

        For each (verb, target) the explorer snapshots, executes, observes
        what changed (inventory, flags, crossings), and KEEPS the action only
        if it produced observable progress; otherwise it restores.  This is
        fully generic: the explorer never assumes a verb means "take", "give",
        "kill" or "drop".
        """
        targets = set(self.entities_in_anchor()) | set(self.inventory())
        # Measure progress: inventory + flags + reachable exits.
        def progress_sig() -> tuple:
            return (
                tuple(sorted(self.inventory())),
                tuple(sorted(k for k, v in self.state.flag_book.items() if v)),
            )

        for target in targets:
            for verb in self.verbs:
                if verb in self.movement_verbs:
                    continue
                # Direct verb+target.
                self._probe_one(
                    anchor, verb, target, None, discovery, log, progress_sig
                )
                # verb+target with each carried item as instrument.
                for item in list(self.inventory()):
                    for prep in self.instrument_preps:
                        self._probe_one(
                            anchor, verb, target, item, discovery, log,
                            progress_sig, use_instrument=True, prep=prep,
                        )
                # verb+carried-item with target as recipient.
                for item in list(self.inventory()):
                    for prep in self.recipient_preps:
                        self._probe_one(
                            anchor, verb, item, target, discovery, log,
                            progress_sig, prep=prep,
                        )

    def _probe_one(
        self,
        anchor: str,
        verb: str,
        target: str,
        instrument: str | None,
        discovery: Discovery,
        log: list[ExplorationEvent],
        progress_sig,
        use_instrument: bool = False,
        prep: str | None = None,
    ) -> None:
        """Execute one candidate command with snapshot/restore."""
        if use_instrument:
            cmd = f"{verb} {target} {prep} {instrument}"
        elif prep:
            cmd = f"{verb} {instrument} {prep} {target}"
        else:
            cmd = f"{verb} {target}"

        before = progress_sig()
        snap = self.snapshot()
        ev = self._turn(cmd)
        log.append(ev)
        after = progress_sig()

        if ev.game_over:
            # Death is never committed progress — restore immediately.
            self.restore(snap)
        elif ev.ok and after != before:
            # Observable progress — keep it committed.
            # Record any newly acquired items.
            for item_id in self.inventory():
                if item_id not in before[0]:
                    discovery.found_items[item_id] = anchor
        else:
            # No progress or destructive — restore to keep exploring.
            self.restore(snap)

    # ------------------------------------------------------------------
    # Turn execution
    # ------------------------------------------------------------------

    def _turn(self, command: str) -> ExplorationEvent:
        anchor_before = self.anchor()
        narrator_text = ""
        try:
            before = len(self.events)
            self.orch.execute_turn(command)
            te = self.events[before:]
            for e in te:
                if e.type == ACTION_OUTPUT:
                    narrator_text += " " + e.payload.get("text", "")
        except Exception as exc:  # noqa: BLE001 — explorer must never crash
            self.crashes.append((command, repr(exc)))
            return ExplorationEvent(
                anchor=anchor_before,
                command=command,
                ok=False,
                note=f"EXCEPTION: {exc!r}",
            )

        turn_ended = sum(1 for e in te if e.type == TURN_ENDED)
        error = next((e for e in te if e.type == ERROR_OUTPUT), None)
        game_over = any(e.type == GAME_OVER for e in te)

        return ExplorationEvent(
            anchor=anchor_before,
            command=command,
            ok=error is None and not game_over,
            narrator_text=narrator_text.strip(),
            error_code=error.payload.get("error_code") if error else None,
            game_over=game_over,
            turn_ended_count=turn_ended,
            note=(f" turn_ended={turn_ended}" if turn_ended != 1 else ""),
        )

    # ------------------------------------------------------------------
    # Tokenization of narrator text (language from vocabulary)
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text.lower())
        return "".join(c for c in text if not unicodedata.combining(c))

    def _tokenize(self, text: str) -> list[str]:
        """Extract candidate surface names from narrator prose.

        Produces unigrams, bigrams and trigrams after stopword removal, so a
        multi-word object like ``"puerta principal"`` survives as a bigram.
        """
        words = re.findall(r"\w+", self._normalize(text))
        words = [
            w for w in words if w not in self.stopwords and len(w) > 1
        ]
        grams: list[str] = []
        for n in (1, 2, 3):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i : i + n])
                grams.append(gram)
        return grams

    # ------------------------------------------------------------------
    # Command generation (verbs/prepositions from the world vocabulary)
    # ------------------------------------------------------------------

    def _movement_commands(self, token: str) -> list[str]:
        return [f"{v} {token}" for v in self.movement_verbs]

    def _action_commands(self, token: str) -> list[str]:
        """Action commands for *token*: verb+token, and with carried
        instruments / recipients using the world's prepositions."""
        cmds: list[str] = []
        for verb in self.verbs:
            if verb in self.movement_verbs:
                continue
            cmds.append(f"{verb} {token}")
            for item in self.inventory():
                for prep in self.recipient_preps:
                    cmds.append(f"{verb} {item} {prep} {token}")
            for item in self.inventory():
                for prep in self.instrument_preps:
                    cmds.append(f"{verb} {token} {prep} {item}")
        return cmds

    def _look_commands(self) -> list[str]:
        """Ambient verbs: non-movement verbs with no object (``mirar``,
        ``look``...).

        Danger verbs (those that kill the player, e.g. ``abandonar``) are
        excluded: the explorer probes each candidate once with
        snapshot/restore and drops any that cause ``game_over``.
        """
        candidates = [
            verb for verb in self.verbs if verb not in self.movement_verbs
        ]
        safe: list[str] = []
        for verb in candidates:
            snap = self.snapshot()
            ev = self._turn(verb)
            if ev.ok and not ev.game_over:
                safe.append(verb)
            self.restore(snap)
        return safe

    # ------------------------------------------------------------------
    # Blind exploration driver
    # ------------------------------------------------------------------

    def explore(self, max_rooms: int | None = None):
        """Play the game by reading the narrator.  Returns the discovered
        topology and the full event log."""
        discovery = Discovery()
        log: list[ExplorationEvent] = []
        start = self.anchor()
        if start is None:
            return discovery, log

        visited: set[str] = set()
        queue: deque = deque([start])
        visited.add(start)
        guard = 0

        while queue and (max_rooms is None or len(visited) < max_rooms):
            guard += 1
            if guard > 20_000:
                break
            anchor = queue.popleft()
            if anchor != self.anchor():
                self._navigate_to(anchor, discovery, log)

            # 1. Look around — read the narrator (for room discovery tokens).
            room_tokens: set[str] = set()
            for cmd in self._look_commands():
                ev = self._turn(cmd)
                log.append(ev)
                room_tokens.update(self._tokenize(ev.narrator_text))
            discovery.room_tokens.setdefault(anchor, set()).update(room_tokens)

            # 1b. Try to acquire every item present in this anchor (observed
            # from runtime state — a player sees what is in the room).  The
            # explorer does not know which verb means "take": it probes all
            # non-movement verbs and observes whether the item entered the
            # inventory.
            for item_id in self.entities_in_anchor():
                if item_id in self.inventory():
                    continue
                if self._take_if_present(item_id):
                    discovery.found_items[item_id] = anchor

            # 2. Try movement through every inferred token.  If a passage is
            # text-closed, brute-force the GLOBAL password list read from the
            # YAML config (cultural knowledge a human player would have).
            for token in room_tokens:
                for cmd in self._movement_commands(token):
                    ev = self._turn(cmd)
                    log.append(ev)
                    new_anchor = self.anchor()
                    if (
                        ev.ok
                        and not ev.game_over
                        and new_anchor
                        and new_anchor != anchor
                    ):
                        discovery.crossed_passages.add(
                            (anchor, new_anchor, token)
                        )
                        if new_anchor not in visited:
                            visited.add(new_anchor)
                            queue.append(new_anchor)
                        # Return to keep exploring this room.
                        back = self._turn(cmd)
                        log.append(back)
                        break  # one movement verb is enough per token

                    # Text-closed: try each password from the YAML list.
                    if ev.error_code in ("blocked", "text_closed"):
                        for password in self.passwords:
                            if not password or len(password) < 2:
                                continue
                            open_cmd = (
                                f"{self.movement_verbs[0]} {token} "
                                f"diciendo {password}"
                            )
                            ev2 = self._turn(open_cmd)
                            log.append(ev2)
                            if ev2.ok and not ev2.game_over:
                                # Password found — cross now.
                                ev3 = self._turn(cmd)
                                log.append(ev3)
                                if ev3.ok and self.anchor() != anchor:
                                    discovery.crossed_passages.add(
                                        (anchor, self.anchor(), token)
                                    )
                                    if self.anchor() not in visited:
                                        visited.add(self.anchor())
                                        queue.append(self.anchor())
                                    back = self._turn(cmd)
                                    log.append(back)
                                break

            # 3. Probe every verb against every entity in this anchor,
            # snapshot/restore so destructive actions never block progress.
            self._probe_actions(anchor, discovery, log)

        discovery.visited_rooms = visited
        return discovery, log

    def _navigate_to(
        self,
        target: str,
        discovery: Discovery,
        log: list[ExplorationEvent],
    ) -> None:
        """Move to *target* using only already-discovered crossings."""
        start = self.anchor()
        if start == target:
            return
        q: deque = deque([(start, [])])
        seen = {start}
        while q:
            node, path = q.popleft()
            for (f, t, p) in discovery.crossed_passages:
                if f != node or t in seen:
                    continue
                seen.add(t)
                np = path + [p]
                if t == target:
                    verb = (
                        self.movement_verbs[0]
                        if self.movement_verbs
                        else "ir"
                    )
                    for passage in np:
                        ev = self._turn(f"{verb} {passage}")
                        log.append(ev)
                    return
                q.append((t, np))


# ======================================================================
# Phase 2: Map comparison (discovered topology vs YAML-declared map)
# ======================================================================


@dataclass
class MapComparison:
    """Discrepancies between the YAML map and what the explorer discovered."""

    declared_rooms: set[str] = field(default_factory=set)
    discovered_rooms: set[str] = field(default_factory=set)
    unreachable_rooms: list[str] = field(default_factory=list)
    undeclared_rooms_visited: list[str] = field(default_factory=list)
    declared_passages: set[tuple[str, str, str]] = field(default_factory=set)
    crossed_passages: set[tuple[str, str, str]] = field(default_factory=set)
    untraversable_passages: list[str] = field(default_factory=list)
    one_way_bidirectional: list[str] = field(default_factory=list)
    items_found: dict[str, str] = field(default_factory=dict)
    items_not_found: list[str] = field(default_factory=list)
    npcs_found: dict[str, str] = field(default_factory=dict)
    npcs_not_found: list[str] = field(default_factory=list)


class MapComparator:
    """Compares a blind discovery against the YAML-declared map."""

    def __init__(self, world_path: str | Path, episode_id: str):
        self.loader = EntityLoader(str(world_path))
        self.episode_id = episode_id

    def compare(self, discovery: Discovery) -> MapComparison:
        comp = MapComparison()
        comp.discovered_rooms = discovery.visited_rooms
        comp.crossed_passages = discovery.crossed_passages
        comp.items_found = discovery.found_items
        comp.npcs_found = discovery.found_npcs

        comp.declared_rooms = {
            e.entity_id for e in self.loader.load_rooms(self.episode_id)
        }
        comp.unreachable_rooms = sorted(
            comp.declared_rooms - discovery.visited_rooms
        )
        comp.undeclared_rooms_visited = sorted(
            discovery.visited_rooms - comp.declared_rooms
        )

        for edge in self.loader.load_macro_edges(self.episode_id):
            comp.declared_passages.add(
                (edge.from_anchor, edge.to_anchor, edge.passage_name)
            )
        comp.untraversable_passages = sorted(
            f"{f}->{t} [{p}]"
            for (f, t, p) in (
                comp.declared_passages - discovery.crossed_passages
            )
        )

        fwd: set[tuple[str, str, str]] = set(discovery.crossed_passages)
        for edge in self.loader.load_macro_edges(self.episode_id):
            if edge.direction != "bidirectional":
                continue
            key = (edge.from_anchor, edge.to_anchor, edge.passage_name)
            reverse = (edge.to_anchor, edge.from_anchor, edge.passage_name)
            if key in fwd and reverse not in fwd:
                comp.one_way_bidirectional.append(
                    f"{edge.from_anchor}<->{edge.to_anchor} "
                    f"[{edge.passage_name}]"
                )

        declared_items = {
            e.entity_id: e.spatial_anchor
            for e in self.loader.load_items(self.episode_id)
        }
        comp.items_not_found = sorted(
            set(declared_items) - set(discovery.found_items)
        )
        declared_npcs = {
            e.entity_id: e.spatial_anchor
            for e in self.loader.load_npcs(self.episode_id)
        }
        comp.npcs_not_found = sorted(
            set(declared_npcs) - set(discovery.found_npcs)
        )
        return comp
