# Fortress Engine

**Build worlds. Write no code.**

A semantic graph engine for interactive fiction. Define rooms, items, NPCs, and
puzzles as data — YAML files — and the engine brings them to life. Worlds are
just graphs; the engine is the interpreter.

## What is this?

Fortress Engine is a **data-driven virtual machine for conversational
adventures**. A narrative designer writes YAML files describing rooms, objects,
characters, and puzzles. The engine loads those files, builds a dual-layer
semantic graph, and runs the world turn by turn — parsing player commands,
validating actions through the graph, and producing output through a pluggable
narrator.

It is not a game. It is not tied to any specific world. The same engine can run
a sci-fi mystery, a fantasy dungeon crawl, or a faithful replica of a 1995 DOS
text adventure — without changing a single line of engine code.

## Inspiration

Fortress Engine was inspired by **"La Fortaleza"** (1995), a classic Spanish
text adventure by **Miguel Enrique Cepero** from Cuba's **Merchise Group**. It
was one of the most popular games of its kind in the Spanish-speaking world:
88 rooms, ~120 items, ~50 NPCs, 93 puzzles, and over 22,000 words of original
Spanish prose.

The original Turbo Pascal source code is preserved in
[`docs/original-source/`](docs/original-source/) as a tribute and reference.
Fortaleza itself is the engine's first example world — proof that a data-driven
architecture can faithfully replicate a complex, hand-crafted interactive
fiction work.

## Why a graph engine?

Traditional IF engines encode game logic as nested conditionals in code: "if the
player has the key AND the door is closed AND the troll is dead, then open the
door." As worlds grow, this becomes unmaintainable spaghetti.

Fortress Engine replaces conditionals with **graph topology**:

- **Dual-layer graph**: a **Macro Graph** maps physical space (rooms and their
  connections with access predicates), while **Micro Graphs** inside each room
  model interactions between objects and characters.
- **Hyper-edges with participation cliques**: actions are not functions. They are
  nodes in the micro-graph that require a specific set of participants — player,
  target, instrument, context — to be connected in the graph. If the clique
  doesn't form, the action is impossible. Validation becomes path-finding.
- **Five atomic operators**: the entire state machine of every world boils down
  to five primitive operations — `TRANSFER`, `TRANSFORM`, `COMBINE`, `FLAG`,
  `TELEPORT`. No world-specific logic ever enters the engine.

The result: a designer defines "what connects to what" and "who participates in
which action." The engine figures out the rest.

## Quick example

A room, defined in YAML:

```yaml
# worlds/fortaleza/rooms/library.yaml
entity_id: "room-06"
type: room
name: "Biblioteca"
components:
  description: |
    Estás en una inmensa biblioteca. Estantes de
    madera oscura se alzan hasta el techo abovedado.
    Un cíclope enorme bloquea la salida norte.
  exits:
    south: room-05
    north: { room: room-07, requires_flag: "ciclope_muerto" }
```

A puzzle as a hyper-edge. Two hyper-edges share the same verb + target; the
engine evaluates them by priority — the first with a valid participation clique
wins:

```yaml
# worlds/fortaleza/actions/kill-cyclops-mace.yaml
action_id: "matar-ciclope-maza"
verb: "matar"
target: "ciclope-01"
priority: 10
participation_clique:
  subject: player
  instrument: "maza"
output: "El cíclope cae con un rugido ensordecedor."
operators:
  - type: TRANSFER
    entity: ciclope-01
    destination: null
  - type: FLAG
    flag: ciclope_muerto
    value: true
```

```yaml
# worlds/fortaleza/actions/kill-cyclops-fallback.yaml
action_id: "matar-ciclope-fallback"
verb: "matar"
target: "ciclope-01"
priority: 0
participation_clique:
  subject: player
  instrument_any: true
output: "¡Tus golpes rebotan inútilmente en su piel pétrea!"
operators: []
```

## Features

- **Data-driven worlds** — rooms, items, NPCs, and puzzles defined entirely in
  YAML. No code required to build an adventure.
- **Dual graph architecture** — macro graph for space, micro graphs for
  interactions. Clean separation of topology and semantics.
- **Hyper-edge action system** — actions validated through participation
  cliques, not if/else trees.
- **Five atomic operators** — `TRANSFER`, `TRANSFORM`, `COMBINE`, `FLAG`,
  `TELEPORT`. Every piece of world logic composes from these five building blocks.
- **Pluggable parser** — classic deterministic parser (37 verbs, ~180 nouns,
  partial name matching) ships with MVP. AI/LLM-based intentional parser planned
  for v1.2.
- **Pluggable narrator** — template-based output in MVP, AI-powered immersive
  prose in the roadmap.
- **Multi-episode worlds** — split large adventures into episodes with victory
  conditions, carry-over rules between parts.
- **Multi-protagonist support** — the engine treats playable characters as a
  collection from day one. Puzzle cliques can require multiple protagonists.
- **Event sourcing persistence** — saves are logs of executed hyper-edges, not
  snapshots. Fully replayable, fully debuggable.
- **World validation** — the loader checks for dangling references, duplicate
  priorities, undeclared flags, and unreachable rooms.

## Getting started

**Requirements:** Python 3.11+

```bash
pip install fortress-engine
```

Run the Fortaleza example world:

```bash
fortress-engine run fortaleza
```

Play through the first episode — the classic 33-room adventure — with the
original Spanish text preserved word-for-word.

To create your own world:

```bash
fortress-engine init my-world
```

This scaffolds a directory with the expected structure. Edit the YAML files, add
rooms, items, and actions, then:

```bash
fortress-engine run my-world
```

## Project structure

```
fortress-engine/
├── src/fortress_engine/   # engine source
│   ├── cli/               # command-line interface
│   ├── engine/            # core: graph engine, turn orchestrator
│   ├── entities/          # entity system (UUID, components, anchors)
│   ├── events/            # event bus (engine ↔ UI communication)
│   ├── persistence/       # event sourcing + repository interface
│   └── plugins/           # parser and narrator plugin interfaces
├── worlds/
│   └── fortaleza/         # first example world (88 rooms, 93 puzzles)
├── tests/                 # pytest suite
├── docs/                  # design documents (PRD, GDD, TDD) + original source
├── pyproject.toml
└── LICENSE
```

## Documentation

Design documents live in [`docs/`](docs/):

| Document | Description |
|----------|-------------|
| [`prd.md`](docs/prd.md) | Product Requirements Document — architecture, features, roadmap |
| [`gdd.md`](docs/gdd.md) | Game Design Document — narrative design, world-building conventions |
| [`tdd.md`](docs/tdd.md) | Technical Design Document — implementation details, stack decisions |
| [`original-source/`](docs/original-source/) | Original Fortaleza Turbo Pascal source code (preserved as tribute) |

The docs also include the complete Fortaleza world analysis: story, rooms,
items, NPCs, puzzles, vocabulary, room graph, walkthrough, puzzle dependencies,
and victory conditions.

## License

Fortress Engine is licensed under the **GNU General Public License v3.0**
([LICENSE](LICENSE)).

The original Fortaleza game — source code and creative content — is copyright
© 1992–2013 **Miguel Enrique Cepero**, released under GPLv3+, and preserved in
[`docs/original-source/`](docs/original-source/) with permission.

## Credits

- **Miguel Enrique Cepero** — author of the original "La Fortaleza" (1995),
  without which this project would not exist.
- **Merchise Group** — the Cuban software collective that published the original
  game and preserved its source code for over two decades.

## Status

**Early development — MVP in progress.** The engine architecture is designed and
the Fortaleza world data is being authored. The v1.0 milestone is a playable
Fortaleza Part I that runs the documented walkthrough command-for-command.

Roadmap highlights:

- **v1.0 (MVP):** core engine, classic parser, template narrator, Fortaleza
  Part I & II as data, event sourcing saves.
- **v1.1:** world editor CLI, world validator, multi-protagonist user commands,
  hint system.
- **v1.2:** AI-based intentional parser, AI immersive narrator, NPC generative
  brains.

Contributions, ideas, and bug reports are welcome.
