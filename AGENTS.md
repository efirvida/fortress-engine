es# Fortaleza — Agent Instructions

## Build environment

This is a **Turbo Pascal 7 / Turbo Assembler** DOS project. You cannot build it directly on Linux/macOS/Windows — use the Docker image:

```bash
docker pull davidmpaz/dosbox-tp7:1.1-amd64
docker run --rm -p 8080:8080 -v $(pwd):/app/src/ davidmpaz/dosbox-tp7:1.1-amd64
```

Then open `http://localhost:8080` in a browser. The source is at `D:\` inside the DOS environment; `TPC.EXE` and `TASM.EXE` are on PATH.

To build: run `BUILD.BAT` from the `D:\` root.

## Build order (mandatory)

Assembly files MUST compile before Pascal files because `WIN.ASM` provides the low-level window routines for `WIN.PAS`, and `SE.ASM` provides sound routines:

```
tasm SE.ASM
tasm WIN.ASM
tpc -$G+ -B -UC:\TP\UNITS <source>
```

- `-$G+` — enable 286 code generation (required; the game uses 286 instructions)
- `-B` — build all units (not just the main program)
- `-UC:\TP\UNITS` — unit search path inside the DOSBox environment

## Entry points (two separate programs)

| File | Program | Description |
|------|---------|-------------|
| `FORT1.PAS` | `Fort1` | Part I: 33 rooms, victory at room 10 |
| `FORT2.PAS` | `Fort2` | Part II: 55 rooms, victory at room 10 |

Each compiles to its own `.EXE`. They share most units but each has its own `Present1`/`Present2` and `Instr1`/`Instr2` modules.

## Architecture

```
FORT1.PAS ─┐                             ┌─ PRESENT1.PAS
            ├── CASTLES.PAS (engine) ─────┤
FORT2.PAS ─┘                             └─ PRESENT2.PAS
                 │
     ┌───────────┼───────────────┐
     ▼           ▼               ▼
 LEXIC.PAS   VOCABL.PAS    STRCOLL.PAS
 TELETYPE.PAS  TTY.PAS    HISTTTY.PAS
 ADVIC.PAS   LETTERS.PAS  SCROLLER.PAS
 SOUNDS.PAS  EQSTRING.PAS INSTR1/2.PAS
 CMDLINE.PAS

Low-level: UTIL.PAS  CRT.PAS (Borland)  WIN.PAS + WIN.ASM  DOS.PAS (RTL)
Sound:     SE.ASM
```

- **`CASTLES.PAS`** (1346 lines) is the game engine: `Castle` object, `Thing`/`ThingCollection`, `Room`, command parsing, inventory.
- **`CRT.PAS`**, **`WIN.PAS`**, and **`WIN.ASM`** are Borland-supplied interface units (TP 6.0 era), not custom code. They wrap BIOS/DOS screen I/O.
- **`SE.ASM`** is custom sound-effect code.

## Code conventions

- Turbo Pascal 7, Object Pascal dialect (no `class`, uses `object`).
- DOS CRLF line endings in `.PAS` and `.BAT` files — don't convert to LF.
- Spanish strings and comments throughout the game.
- `BP.TP` is the Turbo Pascal IDE project file (binary). Do not edit it.
- `$D+,I-,S-` / `$D-,S-` compiler directives are set per-unit; don't blindly add new ones.

## Git expectations

- No CI, no linter, no tests. This is a preservation/archival repo.
- Ignored: `.idea/`, `*.TPU` (compiled units), `*.OBJ` (assembler objects).

## Related links

- Build tracking issue: https://github.com/merchise/fortaleza/issues/2
- Docker image: https://hub.docker.com/r/davidmpaz/dosbox-tp7
