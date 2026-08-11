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
from typing import Any, Callable, Iterable

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
    gate_code: str | None = None
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
        # Solver seams (default off — behavior unchanged when unused):
        # ``commit_hook`` is called for every KEPT command; returning False
        # marks the goal as reached (``solved``).  ``turn_counter`` counts
        # every attempted turn, including restored probes.
        self.commit_hook: Callable[[str], bool] | None = None
        self.solved: bool = False
        self.turn_counter: int = 0
        self._build_runtime()
        self._learn_vocabulary()
        self._learn_passwords()

    def _commit(self, command: str) -> None:
        """Register *command* as kept progress with the optional commit hook.

        A hook returning ``False`` marks the exploration as solved (goal
        reached); keep-point loops then stop so no post-goal commands run.
        The default ``None`` makes this a no-op — explorer behavior is
        unchanged unless a hook is installed.
        """
        if self.commit_hook is not None and self.commit_hook(command) is False:
            self.solved = True

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

        The LIGHTEST carried items are dropped first: heavy items are far
        more likely to be plot keys (tools, artifacts) than 1kg filler, so
        sacrificing a heavy item to carry a lighter one would strand
        exploration.
        """
        need = self._item_weight(item_id)
        guard = 0
        while (
            self._current_weight() + need > self._max_weight()
            and not self.solved
        ):
            guard += 1
            if guard > 100:
                break
            candidates = [
                i for i in self.inventory()
                if self._item_weight(i) < need
            ]
            if not candidates:
                break
            victim = min(candidates, key=self._item_weight)
            snap = self.snapshot()
            for verb in self.verbs:
                if verb in self.movement_verbs:
                    continue
                before_inv = set(self.inventory())
                self._turn(f"{verb} {victim}")
                if victim not in self.inventory():
                    # Item left inventory — keep this action committed.
                    self._commit(f"{verb} {victim}")
                    break
            else:
                # No verb removed it — restore and move on.
                self.restore(snap)

    def _take_if_present(self, item_id: str) -> bool:
        """Try to acquire *item_id* from the current anchor by probing every
        non-movement verb; returns True if it is now in the inventory.

        Each probe runs under snapshot/restore so a lethal verb (e.g.
        ``abandonar``) never kills the explorer while searching for the
        take verb.  If the item is too heavy for the current inventory, the
        explorer first drops carried items (via the world's own drop verb)
        until it fits — otherwise a carry cap would permanently block items
        such as the hacha that unlock passages.
        """
        if item_id in self.inventory():
            return True
        for attempt in range(2):
            for verb in self.verbs:
                if self.solved:
                    return item_id in self.inventory()
                if verb in self.movement_verbs:
                    continue
                snap = self.snapshot()
                self._turn(f"{verb} {item_id}")
                if item_id in self.inventory():
                    self._commit(f"{verb} {item_id}")
                    return True
                self.restore(snap)
            if attempt == 0:
                # Make room (drop light fillers) and retry once — a key item
                # may have failed only because the carry weight was full.
                self._drop_for(item_id)
        return False

    def _probe_actions(
        self,
        anchor: str,
        discovery: Discovery,
        log: list[ExplorationEvent],
        probed_cmds: dict[str, set[str]],
        probed_sets: dict[str, tuple[set[str], set[str]]],
    ) -> None:
        """Probe verbs against entities in the current anchor, using
        snapshot/restore so a destructive action never permanently blocks
        progress.

        For each (verb, target) the explorer snapshots, executes, observes
        what changed (inventory, flags, crossings), and KEEPS the action only
        if it produced positive observable progress (acquired an item or set
        a flag); otherwise it restores.  Fully generic: the explorer never
        assumes a verb means "take", "give", "kill" or "drop".

        Revisits are DIFFERENTIAL: a (verb, target) already probed, and
        instrument/recipient combos already probed for a given target/item
        pair, are skipped.  Only NEW targets (entities newly seen in the
        anchor) and NEW carried items (as instruments/recipients) are probed
        — a freshly acquired item can unlock an action on an old target
        (e.g. ``romper cama con hacha``), but a command that previously did
        nothing does not need re-probing.
        """
        # Probe targets are the room's OWN entities (what a player sees in the
        # room); carried items only matter as instruments/recipients.  Probing
        # carried items as TARGETS (e.g. ``mirar maza``) almost never opens a
        # passage and bloats the matrix, so it is skipped.
        current_targets = set(self.entities_in_anchor())
        current_items = list(self.inventory())
        anchor_entities = set(self.entities_in_anchor())
        seen_targets, seen_items = probed_sets.get(anchor, (set(), set()))
        new_targets = current_targets - seen_targets
        new_items = set(current_items) - seen_items

        def progress_sig() -> tuple:
            return (
                tuple(sorted(self.inventory())),
                tuple(sorted(k for k, v in self.state.flag_book.items() if v)),
            )

        # Instrument/recipient probing is bounded to the most recently
        # carried items (plus items present in the room): a fresh acquisition
        # is the one most likely to unlock a new action on an old target
        # (e.g. ``romper cama con hacha``), and capping the window keeps the
        # probe matrix from exploding as the inventory grows.
        MAX_PROBE_ITEMS = 6
        instrument_items = sorted(anchor_entities & set(current_items))
        instrument_items += [i for i in reversed(current_items)
                             if i not in instrument_items][:MAX_PROBE_ITEMS]

        # 1. Direct verb+target for NEW targets, plus instrument/recipient
        #    combos using the bounded instrument window.  Targets iterate in
        #    sorted order so exploration is byte-deterministic.
        for target in sorted(new_targets):
            if self.solved:
                return
            for verb in self.verbs:
                if verb in self.movement_verbs:
                    continue
                self._probe_one(
                    anchor, verb, target, None, discovery, log, progress_sig,
                    probed_cmds,
                )
                if self.solved:
                    return
                for item in instrument_items:
                    for prep in self.instrument_preps:
                        self._probe_one(
                            anchor, verb, target, item, discovery, log,
                            progress_sig, probed_cmds, use_instrument=True,
                            prep=prep,
                        )
                        if self.solved:
                            return
                    for prep in self.recipient_preps:
                        self._probe_one(
                            anchor, verb, item, target, discovery, log,
                            progress_sig, probed_cmds, prep=prep,
                        )
                        if self.solved:
                            return

        # 2. For targets seen before, only NEW items used against the room's
        #    OWN entities (anchor targets, not carried items) can unlock a new
        #    action (e.g. ``romper cama con hacha``).  Direct verb+target was
        #    already probed; combos among carried items never open a passage.
        for target in sorted(anchor_entities - new_targets):
            if self.solved:
                return
            for verb in self.verbs:
                if verb in self.movement_verbs:
                    continue
                for item in new_items:
                    for prep in self.instrument_preps:
                        self._probe_one(
                            anchor, verb, target, item, discovery, log,
                            progress_sig, probed_cmds, use_instrument=True,
                            prep=prep,
                        )
                        if self.solved:
                            return
                    for prep in self.recipient_preps:
                        self._probe_one(
                            anchor, verb, item, target, discovery, log,
                            progress_sig, probed_cmds, prep=prep,
                        )
                        if self.solved:
                            return

        probed_sets[anchor] = (current_targets, set(current_items))

    def _probe_one(
        self,
        anchor: str,
        verb: str,
        target: str,
        instrument: str | None,
        discovery: Discovery,
        log: list[ExplorationEvent],
        progress_sig,
        probed_cmds: dict[str, set[str]],
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

        tried = probed_cmds.setdefault(anchor, set())
        if cmd in tried:
            return
        tried.add(cmd)

        before = progress_sig()
        snap = self.snapshot()
        ev = self._turn(cmd)
        log.append(ev)
        after = progress_sig()

        if ev.game_over:
            # Death is never committed progress — restore immediately.
            self.restore(snap)
            return
        before_inv, before_flags = before
        after_inv, after_flags = after
        gained = set(after_inv) - set(before_inv)
        flags_changed = before_flags != after_flags
        if ev.ok and (gained or flags_changed):
            # POSITIVE progress — keep it committed: the explorer acquired an
            # item or set a flag.  A pure item REMOVAL (e.g. ``dejar x``)
            # without any gain or flag change is not progress and is restored,
            # so a carried key/item (e.g. the panuelo that unlocks a passage)
            # is never needlessly dropped.
            for item_id in gained:
                discovery.found_items[item_id] = anchor
            self._commit(cmd)
        else:
            # No progress or destructive — restore to keep exploring.
            self.restore(snap)

    # ------------------------------------------------------------------
    # Turn execution
    # ------------------------------------------------------------------

    def _turn(self, command: str) -> ExplorationEvent:
        self.turn_counter += 1
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
            gate_code=(
                (error.payload.get("data") or {}).get("gate_code")
                if error
                else None
            ),
            game_over=game_over,
            turn_ended_count=turn_ended,
            note=(f" turn_ended={turn_ended}" if turn_ended != 1 else ""),
        )

    def _speech_marker(self) -> str:
        """Return the world's speech marker (e.g. "diciendo"), or the
        documented fallback when the world defines none.

        Replaces the hardcoded literal in the password open command so a
        non-Spanish world (or a world with a custom marker) still opens its
        text-gated passages.
        """
        if self.vocabulary and self.vocabulary.speech_markers:
            return self.vocabulary.speech_markers[0]
        return "diciendo"

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

    def _progress_sig(self) -> tuple:
        """Inventory + flags signature — used to detect whether a probe pass
        changed anything (so movement passes are only re-run when useful)."""
        return (
            tuple(sorted(self.inventory())),
            tuple(sorted(k for k, v in self.state.flag_book.items() if v)),
        )

    def _collect_room_tokens(
        self,
        anchor: str,
        discovery: Discovery,
        log: list[ExplorationEvent],
    ) -> set[str]:
        """Look around — read the narrator (for room discovery tokens)."""
        room_tokens: set[str] = set()
        for cmd in self._look_commands():
            ev = self._turn(cmd)
            log.append(ev)
            room_tokens.update(self._tokenize(ev.narrator_text))
        discovery.room_tokens.setdefault(anchor, set()).update(room_tokens)
        return room_tokens

    def _take_present_items(
        self,
        anchor: str,
        discovery: Discovery,
    ) -> bool:
        """Try to acquire every item present in this anchor (observed from
        runtime state — a player sees what is in the room).  The explorer
        does not know which verb means "take": it probes all non-movement
        verbs and observes whether the item entered the inventory.
        Returns True if at least one item was acquired."""
        took = False
        for item_id in self.entities_in_anchor():
            if item_id in self.inventory():
                continue
            if self._take_if_present(item_id):
                discovery.found_items[item_id] = anchor
                took = True
        return took

    def _movement_pass(
        self,
        anchor: str,
        tokens: set[str],
        discovery: Discovery,
        log: list[ExplorationEvent],
        visited: set[str],
        queue: deque,
        in_queue: set[str],
        blocked_rooms: dict[str, set[str]],
        room_snap: dict[str, Any] | None = None,
        passwords: Iterable[str] | None = None,
    ) -> bool:
        """Try movement through *tokens* (all inferred tokens, or only the
        previously-blocked ones on a re-run/revisit).

        On a successful crossing the explorer returns to the current room;
        if the reverse crossing is observed it is recorded too, so
        ``_navigate_to`` can later travel back through the discovery tree.
        A crossing into a one-way dead-end (the return fails) is recorded
        but *room_snap* is restored so the explorer never gets trapped in a
        sink room.  A passage that stays blocked (item, flag or text gate)
        is remembered in *blocked_rooms* for a later re-visit.

        Text-closed passages brute-force the GLOBAL password list read from
        the YAML config (cultural knowledge a human player would have).

        No per-token snapshot is taken: a blocked/no-action attempt leaves
        state unchanged, and a fatal movement gate emits ``game_over``
        WITHOUT mutating state (the engine does not teleport or set flags on
        a fatal gate).  The only restore point needed is the room-entry
        snapshot, used when a one-way crossing strands the explorer.
        """
        crossed_any = False
        for token in sorted(tokens):
            if self.solved:
                return True
            gate_blocked = False
            crossed = False
            for cmd in self._movement_commands(token):
                ev = self._turn(cmd)
                log.append(ev)
                new_anchor = self.anchor()
                if ev.game_over:
                    # Fatal gate (forbids_item/requires_item + death_message):
                    # the engine does not change state, so the explorer is
                    # still alive in this room.  Remember the token so the
                    # room is re-visited once the needed item/flag is acquired.
                    gate_blocked = True
                    continue
                if ev.ok and new_anchor and new_anchor != anchor:
                    discovery.crossed_passages.add(
                        (anchor, new_anchor, token)
                    )
                    blocked_rooms.get(anchor, set()).discard(token)
                    if new_anchor not in visited:
                        visited.add(new_anchor)
                        queue.append(new_anchor)
                        in_queue.add(new_anchor)
                    crossed = True
                    crossed_any = True
                    self._commit(cmd)
                    if self.solved:
                        # Goal reached by the crossing — stop, do not return.
                        return True
                    # Return to keep exploring this room.
                    back = self._turn(cmd)
                    log.append(back)
                    if self.anchor() == anchor:
                        # Bidirectional — record the reverse crossing so
                        # navigation can come back through this passage.
                        discovery.crossed_passages.add(
                            (new_anchor, anchor, token)
                        )
                        self._commit(cmd)
                    elif room_snap is not None:
                        # One-way / sink: restore so the explorer is not
                        # trapped in the destination; the crossing is already
                        # recorded and the destination is queued.  Nothing is
                        # committed for the failed return.
                        self.restore(room_snap)
                    break  # one movement verb is enough per token

                if ev.error_code in ("blocked", "text_closed"):
                    # A real gate (item/flag/text).  Try each password from
                    # the knowledge base (text gates); remember the room for
                    # a later re-visit once the needed item/flag is acquired.
                    gate_blocked = True
                    password_source = (
                        self.passwords if passwords is None else passwords
                    )
                    for password in sorted(password_source):
                        if not password or len(password) < 2:
                            continue
                        open_cmd = (
                            f"{self.movement_verbs[0]} {token} "
                            f"{self._speech_marker()} {password}"
                        )
                        ev2 = self._turn(open_cmd)
                        log.append(ev2)
                        if ev2.game_over:
                            continue
                        if ev2.ok and not ev2.game_over:
                            # The open command already crossed into the new
                            # room — record the discovery NOW.
                            opened_anchor = self.anchor()
                            if opened_anchor and opened_anchor != anchor:
                                discovery.crossed_passages.add(
                                    (anchor, opened_anchor, token)
                                )
                                blocked_rooms.get(anchor, set()).discard(token)
                                if opened_anchor not in visited:
                                    visited.add(opened_anchor)
                                    queue.append(opened_anchor)
                                    in_queue.add(opened_anchor)
                                crossed = True
                                crossed_any = True
                                self._commit(open_cmd)
                                if self.solved:
                                    return True
                            # Return to the current room to keep exploring it
                            # (the door is open now).
                            back = self._turn(cmd)
                            log.append(back)
                            if self.anchor() == anchor:
                                discovery.crossed_passages.add(
                                    (opened_anchor, anchor, token)
                                )
                                self._commit(cmd)
                            elif room_snap is not None:
                                self.restore(room_snap)
                            break
                    if crossed:
                        break
            if not crossed and gate_blocked:
                blocked_rooms.setdefault(anchor, set()).add(token)
        return crossed_any

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
        in_queue: set[str] = {start}
        visited.add(start)
        guard = 0
        # Rooms where a movement token was blocked (item/flag/text gate),
        # mapped to the tokens that failed.  They are re-queued (bounded)
        # when the inventory/flags change so a later-acquired item or flag
        # can unlock them.
        blocked_rooms: dict[str, set[str]] = {}
        # Signature observed the last time each blocked room was processed.
        room_sig: dict[str, tuple] = {}
        revisit: dict[str, int] = {}
        MAX_REVISITS = 8
        # Commands already probed per room (memoized across visits/revisits
        # so a revisited room does not re-probe the same command matrix).
        probed_cmds: dict[str, set[str]] = {}
        # Per-room sets of already-probed targets and carried items, so a
        # revisit only probes NEW targets/items (differential probing).
        probed_sets: dict[str, tuple[set[str], set[str]]] = {}

        def _requeue(room: str) -> None:
            """Re-queue *room* unless it is already queued (dedup — a room
            must never be queued twice, which would re-probe it repeatedly)."""
            if room not in in_queue:
                queue.append(room)
                in_queue.add(room)

        while queue and not self.solved and (
            max_rooms is None or len(visited) < max_rooms
        ):
            guard += 1
            if guard > 20_000:
                break
            anchor = queue.popleft()
            in_queue.discard(anchor)
            if anchor != self.anchor():
                if not self._navigate_to(anchor, discovery, log):
                    # Could not navigate there yet (one-way chain or unknown
                    # crossing) — re-queue instead of processing the WRONG
                    # room.  Bounded by the guard + a retry cap.
                    revisit[anchor] = revisit.get(anchor, 0) + 1
                    if revisit[anchor] <= MAX_REVISITS:
                        _requeue(anchor)
                    continue

            room_tokens = self._collect_room_tokens(anchor, discovery, log)

            # Room-entry snapshot: the restore point for a one-way sink (a
            # crossing whose return fails would otherwise trap the explorer
            # in a dead-end destination).
            room_snap = self.snapshot()

            # Take + move, then probe once, then re-run take + movement so an
            # item or flag acquired by the probe pass unlocks a gated passage
            # in the SAME room visit.  The movement re-run only re-tries the
            # tokens that were blocked (already-crossed passages are skipped).
            self._take_present_items(anchor, discovery)
            self._movement_pass(
                anchor, room_tokens | blocked_rooms.get(anchor, set()),
                discovery, log, visited, queue, in_queue, blocked_rooms,
                room_snap,
            )
            self._probe_actions(anchor, discovery, log, probed_cmds, probed_sets)
            # Re-run movement so an item or flag acquired by the probe pass
            # unlocks a gated passage in the SAME room visit.  Only the
            # blocked tokens are re-tried (already-crossed ones are skipped).
            self._movement_pass(
                anchor, blocked_rooms.get(anchor, set()),
                discovery, log, visited, queue, in_queue, blocked_rooms,
                room_snap,
            )

            # Re-visit blocked rooms whose gates may now be satisfiable —
            # new items/flags were acquired somewhere else since they were
            # last processed.  Bounded by MAX_REVISITS + the hard guard.
            # (Revisits are enabled via DISABLE_REVISITS flag for profiling.)
            sig_now = self._progress_sig()
            if not getattr(self, "_no_revisit", False):
                for room in list(blocked_rooms):
                    if room in visited and room_sig.get(room) != sig_now:
                        if revisit.get(room, 0) < MAX_REVISITS:
                            revisit[room] = revisit.get(room, 0) + 1
                            _requeue(room)
            room_sig[anchor] = sig_now

        discovery.visited_rooms = visited
        return discovery, log

    def _navigate_to(
        self,
        target: str,
        discovery: Discovery,
        log: list[ExplorationEvent],
    ) -> bool:
        """Move to *target* using only already-discovered crossings.

        Reverse crossings are recorded when the return trip was observed, so
        the BFS can travel back up the discovery tree as well as forward.
        Returns True only if the protagonist actually arrives at *target*.
        """
        start = self.anchor()
        if start == target:
            return True
        q: deque = deque([(start, [])])
        seen = {start}
        while q:
            node, path = q.popleft()
            for (f, t, p) in sorted(discovery.crossed_passages):
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
                        cmd = f"{verb} {passage}"
                        ev = self._turn(cmd)
                        log.append(ev)
                        if ev.game_over or not ev.ok:
                            # A step failed (e.g. one-way in reverse) — abort.
                            return False
                        self._commit(cmd)
                        if self.solved:
                            return True
                    return self.anchor() == target
                q.append((t, np))
        return False


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
