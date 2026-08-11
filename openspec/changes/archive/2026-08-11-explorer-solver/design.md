# Design: Explorer Solver (Stage B)

## Technical Approach

`Solver` is an audit-gated, audit-guided verifier. It first runs `GraphAudit` on loader data; any `ERROR` finding returns a typed negative verdict without constructing a runtime. Otherwise it composes one `BlindExplorer` and drives its existing runtime, probing, inventory, movement, and navigation machinery. No engine-core or gameplay-world changes are made. This revision resolves the open seams so apply is mechanical: the `answers.yaml` loader collision, the exact explorer hook contract, goal-check timing, key-retrieval backtracking, the diagnosis decision table, determinism rules, guard counters, and CLI output shapes.

## Architecture Decisions

| Decision | Choice and rationale |
|---|---|
| Runtime | Compose `BlindExplorer` rather than duplicate `_build_runtime`, `_learn_vocabulary`, or `_learn_passwords`; composition preserves plugin wiring and the private `orch._state` coupling. The solver is the driver (its own BFS loop) and calls explorer sub-methods per room — it never calls `explore()`. |
| Explorer edits | Seven additive, default-off changes to `explorer.py` (see "Explorer hook contract"): `commit_hook`/`solved`/`_commit`, `turn_counter`, `ExplorationEvent.gate_code`, `_movement_pass(passwords=None)`, `_speech_marker()`, sorted iteration in `_probe_actions` and `_navigate_to`. With `commit_hook=None` and `passwords=None` the explorer's own behavior is byte-identical (verified below per change). |
| Restore | `snapshot()`/`restore()` are the only speculative-state API. `restore()` alone assigns `WorldState.from_dict`, rebinds `orch._state`, and restores edge `open` flags; solver never assigns either object directly. Every speculative action (probe, password attempt, retrieval detour, navigation) runs under a snapshot and restores on failure. |
| Knowledge | `AnswerBook` is a frozen dataclass. Effective answers = derived episode `requires_text` ∪ curated `passwords`/`riddle_answers` from `episodes/answers.yaml` (per-episode mapping) or `--answers PATH` (replaces the default file, not the derivation). Normalize/dedup by NFKD-stripped-lowercased key, keep as-authored display strings, try in sorted order. |
| Goal check | The solver's commit hook calls `explorer.goal_eval.check(explorer.state)` after every kept command and returns `False` to stop. The solver also re-checks after each sub-method returns. Loop terminates on `solved` (goal) — see "Goal-check timing". |
| Bounds | `max_turns=50_000` counts ATTEMPTED turns including restored probes (via `explorer.turn_counter`). Existing `MAX_PROBE_ITEMS=6`, solver-owned `MAX_REVISITS=8` and `MAX_RETRIEVALS_PER_GATE=8`. Queue de-duplication and probe memoization are mandatory. |
| Determinism | Every set/iterable in the walk path is sorted (queue, probe targets, movement tokens, KB answers, passage lookup, revisit order, navigation edges, diagnosis/JSON output). See "Determinism guarantees". |
| Diagnosis | Runtime-grounded: only gates actually observed blocked (or audit-passage gates inferred for fatal/no-ERROR-OUTPUT blocks) at fixed point produce a `GateDiagnosis`. `stuck_rooms` holds rooms never reached or still blocked. |

## Interfaces and Data Flow

```python
@dataclass(frozen=True)
class GateDiagnosis:
    passage: str; predicate: str; required: str; reason: Literal[
        "answer_not_in_kb", "item_unreachable", "item_missing_from_world",
        "item_never_acquired", "flag_never_set"]

@dataclass
class SolveVerdict:
    completable: bool; episode: str; walkthrough: list[str]
    total_turns: int; probe_count: int; stuck_rooms: list[str]
    unsatisfiable_gates: list[GateDiagnosis]; static_errors: list[Finding]
    # to_dict() serializes exactly these 8 fields (walkthrough in ledger order,
    # stuck_rooms sorted, unsatisfiable_gates sorted, static_errors already sorted).

@dataclass(frozen=True)
class AnswerBook:
    answers: tuple[str, ...]      # normalized display strings, sorted by normalized key
    source: str                   # "derived:episode-01" | "derived+file:<path>"
    @classmethod
    def load(cls, loader: EntityLoader, episode_id: str,
             answers_path: Path | None = None) -> "AnswerBook": ...

@dataclass
class Solver:
    world_path: str | Path
    episode: Episode
    answers_path: Path | None = None
    max_turns: int = 50_000
    def solve(self) -> SolveVerdict: ...
```

`Solver.solve()` calls `GraphAudit(loader, episode).run()`. The report supplies `passages` (passive gate records, sorted), `reachable_rooms`, and the `findings` seam; loader item placement and the runtime `Discovery.found_items` supply retrieval/diagnosis data.

```text
CLI -> Solver -> EntityLoader/GraphAudit
                 ├─ ERROR -> SolveVerdict(static_errors)
                 └─ AnswerBook -> BlindExplorer -> committed ledger -> verdict
```

## Explorer hook contract (the seven additive changes)

The solver drives `BlindExplorer`; nothing below changes explorer behavior when unused.

**Read-only calls (no explorer change):** `explorer.anchor()`, `explorer.inventory()`, `explorer.entities_in_anchor()`, `explorer.state`, `explorer.goal_eval` (`.check(state)`), `explorer.vocabulary`, `explorer.verbs`, `explorer.movement_verbs`, `explorer.instrument_preps`, `explorer.recipient_preps`, `explorer.loader`, `explorer.episodes`, `explorer.crashes`, `explorer.events`.

**Mutating machinery (solver drives):** `snapshot()`/`restore()`, `_navigate_to(target, discovery, log)`, `_take_present_items(anchor, discovery)`, `_take_if_present(item_id)`, `_probe_actions(anchor, discovery, log, probed_cmds, probed_sets)`, `_movement_pass(anchor, tokens, discovery, log, visited, queue, in_queue, blocked_rooms, room_snap, passwords=None)`, `_progress_sig()`, `_turn(cmd)`.

**The seven additive changes (all behavior-neutral when unused):**

1. **`commit_hook: Callable[[str], bool] | None = None`** and **`solved: bool = False`** instance attributes, plus a private `_commit(command)` helper:
   ```python
   def _commit(self, command: str) -> None:
       if self.commit_hook is None:
           return
       if not self.commit_hook(command):
           self.solved = True
   ```
   `_commit` is called at every KEEP point (state change is permanent): a successful take in `_take_if_present` (after `item_id in self.inventory()`), a successful drop in `_drop_for`, the positive-progress branch of `_probe_one`, the forward+return crossings in `_movement_pass` (both the movement-verb crossing and the password `open_cmd` crossing), and each successful step of `_navigate_to`. Keep-point iteration loops check `if self.solved: return/break` after each commit so NO command is kept after the goal is met. In the one-way-sink branches `_movement_pass` restores `room_snap` and commits nothing. Default `None` ⇒ `_commit` is a no-op, `solved` stays `False`, existing behavior unchanged.
2. **`turn_counter: int = 0`** incremented as the first statement of `_turn` — counts every attempted turn including restored probes. Default behavior unaffected (counter is only read by the solver).
3. **`ExplorationEvent.gate_code: str | None = None`**, populated in `_turn` from `error.payload.get("data", {}).get("gate_code")` when the `ERROR_OUTPUT` event exists. Default `None`; existing tests unaffected. This is the seam the diagnosis table reads (the orchestrator nests `gate_code` inside `data`; the top-level `error_code` is only ever `"blocked"`).
4. **`_movement_pass(..., passwords: Iterable[str] | None = None)`** — when `None`, uses `self.passwords` (exact current behavior); when the solver passes its `AnswerBook.answers`, the inline text-gate brute-force tries those instead. The loop iterates `sorted(passwords or self.passwords)`.
5. **`_speech_marker()`** returns `self.vocabulary.speech_markers[0]` when present, else `"diciendo"`. `_movement_pass` builds password commands with `self._speech_marker()` instead of the hardcoded `"diciendo"` literal. For the Fortaleza world `speech_markers == ["diciendo", ...]` so behavior is unchanged; this removes the only language literal from the walk path (spec: "without language-specific literals").
6. **`_probe_actions` iterates sorted targets**: `for target in sorted(new_targets):` and `for target in sorted(anchor_entities - new_targets):`. Same set, ordered iteration — semantic no-op, makes the probe matrix cross-run deterministic.
7. **`_navigate_to` iterates `sorted(discovery.crossed_passages)`** instead of the raw set, so path selection is deterministic (lexicographically-first among shortest BFS paths). Same reachability result, no behavior change for `explore()`.

Note on coverage: `explorer.py` is the omitted file, so these additive edits are not measured by the gate; the solver's own handling of the hook return values IS measured in `test_solver.py`.

## Solver Flow

The solver drives one BFS over `sorted(report.reachable_rooms)`. Restore points and commit-hook timing are explicit.

```mermaid
sequenceDiagram
    participant S as Solver
    participant A as GraphAudit
    participant X as BlindExplorer
    participant K as AnswerBook
    participant T as TurnOrchestrator
    participant G as GoalEvaluator

    S->>A: run()
    A-->>S: report(reachable rooms, passages, findings)
    alt ERROR exists
        S-->>S: verdict(static_errors); return
    else audit passes
        S->>X: build runtime (BlindExplorer)
        S->>K: load(derived requires_text + curated answers)
        S->>X: set commit_hook = ledger + goal check
        loop queue (sorted reachable_rooms) and not X.solved
            S->>X: _navigate_to(room) under snapshot
            X->>T: execute_turn(movement steps)
            S->>X: _take_present_items(anchor)
            S->>X: _probe_actions(anchor, ...)  (differential, sorted)
            loop each probe candidate
                X->>X: snapshot(); _turn(candidate)
                alt no progress or death
                    X->>X: restore(probe)
                else kept progress
                    X->>X: _commit(cmd) -> ledger += cmd; G.check(state)
                    alt goal met
                        X->>X: solved = True (stop)
                    end
                end
            end
            S->>X: _movement_pass(tokens=sorted audit passages u blocked, passwords=K.answers)
            loop movement/password attempt
                X->>X: snapshot(); _turn()
                alt crossing kept (bidirectional)
                    X->>X: _commit(fwd); _commit(back); G.check(state)
                else blocked/fatal
                    X->>X: restore/room_snap; block token
                end
            end
            S->>S: GateObserver: token -> gate_code (from log tail)
            loop blocked requires_item gate, item not carried, attempts < 8
                S->>X: snapshot(); mark ledger segment
                S->>X: _navigate_to(item room) -> _take_if_present(item) -> _navigate_to(back)
                alt any step fails
                    S->>X: restore(backtrack); truncate ledger segment
                else key acquired
                    S->>X: re-run _movement_pass on remaining blocked tokens (cross now)
                end
            end
            S->>S: goal check (belt-and-braces) after each sub-method
            S->>S: sig changed? -> requeue blocked rooms within MAX_REVISITS
        end
        S->>S: fixed-point diagnosis(report, KB, observations)
        S-->>S: SolveVerdict(walkthrough, diagnoses)
    end
    Note over S,G: Goal checks follow every kept action/crossing; restored probes, failed answers, and truncated detours stay out of the ledger.
```

### Goal-check timing (concrete)

The engine checks the goal only after micro actions (`orchestrator.execute_turn` step 12), never after crossings (`_handle_movement` → `_post_action_checks` only checks `player_dead`). Therefore:

- **Per-kept-command check** (primary): the solver-owned hook
  ```python
  def _on_commit(self, cmd: str) -> bool:
      self.ledger.append(cmd)
      return not self.explorer.goal_eval.check(self.explorer.state)
  ```
  returns `False` the instant the goal is true, so `_commit` sets `solved` and no later command is kept. This covers kept actions, successful crossings, KB-open crossings, key-take, and return crossings (all keep points).
- **Post-batch re-check**: the solver calls `explorer.goal_eval.check(explorer.state)` after every sub-method returns (catches any transition the engine fired mid-micro-action).
- **Loop termination**: `while queue and not explorer.solved and not guard_exhausted`. On `solved`, `completable=True` and `walkthrough = ledger` (the exact ordered committed commands; restored probes/failed answers/truncated detours absent).

### Key-retrieval backtracking (concrete)

Trigger: a passage blocked with observed `gate_code == "requires_item"` (or audit-inferred `requires_item`) and the required item not carried.

- **Where the item is**: runtime first — `discovery.found_items[item_id]` (populated by `_probe_one` and `_take_present_items` at the moment of acquisition); fallback to static placement `loader.load_items(episode_id)` `spatial_anchor`. If neither exists (entity absent or `spatial_anchor is None` at load) → `item_missing_from_world`.
- **Per-gate bounded attempts**: `MAX_RETRIEVALS_PER_GATE = 8`. Each attempt:
  1. `snap = explorer.snapshot()`; record `ledger_len = len(self.ledger)`.
  2. `explorer._navigate_to(item_room, discovery, log)` — if it fails (no discovered crossing, e.g. the item sits behind the very gate being opened), `restore(snap)`, truncate `del self.ledger[ledger_len:]`, and diagnose.
  3. `explorer._take_if_present(item_id)` — if it fails after the two-attempt verb probe + `_drop_for` weight management, restore + truncate → `item_never_acquired`.
  4. `explorer._navigate_to(from_anchor, discovery, log)` (the gate's room) — if it fails (one-way/dynamic path break), restore + truncate → `item_unreachable`.
  5. On success the key is carried; the solver re-runs `_movement_pass` on the remaining blocked tokens of that room so the gate crossing is committed through the normal keep path (the hook records it and checks the goal).
- **Ledger truncation semantics**: `del self.ledger[ledger_len:]` removes exactly the commands committed during the failed detour so the walkthrough stays truthful (replayable without the dead-end). Topology discoveries (`crossed_passages`, `found_items`) from a restored detour are KEPT — they are real, reusable knowledge; only walkthrough commands are reverted.
- **Retrieval exhausted** (8 failed attempts): diagnose via the item's static anchor and audit reachability (`item_unreachable` if the anchor is outside `report.reachable_rooms` or was never dynamically reached; else `item_never_acquired`).

### Stuck diagnosis mapping (decision table)

Sources: (a) runtime observation — `ExplorationEvent.error_code == "blocked"` with `gate_code` from the event (solver's `GateObserver` maps each blocked token to its latest observed `gate_code`); (b) audit `PassageRecord` for the passage (passive predicates, engine evaluation order text → requires_item → forbids_item → requires_flag → forbids_flag); (c) effective `AnswerBook`; (d) inventory; (e) static item placement + `report.reachable_rooms`. For a blocked passage with NO observed gate_code (fatal `game_over` blocks emit no `ERROR_OUTPUT`), the predicate is inferred as the first audit predicate unsatisfied at fixed point.

| Observed / inferred predicate | Condition at fixed point | reason | required |
|---|---|---|---|
| `requires_text` | `PassageRecord.requires_text` (normalized) ∉ effective KB | `answer_not_in_kb` | the `requires_text` value |
| `requires_item` X | X not a loaded item, or `spatial_anchor is None` at load (limbo) | `item_missing_from_world` | X |
| `requires_item` X | X anchored in a room ∉ `reachable_rooms`, or detour `_navigate_to` never reached it | `item_unreachable` | X |
| `requires_item` X | X reachable but take/retrieval exhausted | `item_never_acquired` | X |
| `requires_item` X | X IS carried yet gate still blocked | next predicate in engine order wins; if none, `item_never_acquired` (world contradiction, noted in message) | X |
| `forbids_item` X | X carried and no verb can drop it (drop loop exhausted) | `item_never_acquired` (proxy; message states the drop is impossible) | X |
| `requires_flag` F | `state.get_flag(F)` false at fixed point | `flag_never_set` | F |
| `forbids_flag` F | F set and no operator unsets it | `flag_never_set` (proxy; message states F cannot be cleared) | F |

Exact messages: `answer_not_in_kb` → ``DATA gap: answer for '<passage>' is absent from the knowledge base`` (pinned by tasks); `item_unreachable` → ``item '<X>' required by '<passage>' is in audit-unreachable room '<room>'``; `item_missing_from_world` → ``item '<X>' required by '<passage>' is missing from the world or in limbo at load``; `item_never_acquired` → ``item '<X>' required by '<passage>' could not be acquired after fixed point``; `flag_never_set` → ``flag '<F>' required by '<passage>' is never set``. `stuck_rooms` = `sorted(unvisited ∪ {room for room, tokens in blocked_rooms.items() if tokens})`. Diagnoses sort by `(passage, predicate, required, reason)` and are deduplicated.

### Determinism guarantees (exact ordering rules)

Cross-run byte-determinism of `walkthrough`, JSON, and diagnosis requires every walk-path iterable to be ordered:

1. Initial queue: `sorted(report.reachable_rooms)` (audit returns a `set`).
2. Revisit requeue: iterate `sorted(blocked_rooms)` keys; each room's token set is fed to `_movement_pass` via `sorted(...)`.
3. Movement tokens per room: `sorted({p.passage_name for p in report.passages if p.from_anchor == anchor} ∪ blocked tokens)`.
4. KB answers: `AnswerBook.answers` sorted by normalized key (dedup on NFKD-stripped-lowercased key, display keeps the as-authored string).
5. Probe matrix: `_probe_actions` iterates `sorted(new_targets)` and `sorted(anchor_entities - new_targets)` (explorer change #6); `_movement_pass` already sorts tokens and passwords.
6. Navigation: `_navigate_to` iterates `sorted(discovery.crossed_passages)` (explorer change #7).
7. Diagnosis and output: `unsatisfiable_gates` sorted as above; `stuck_rooms` sorted; `Discovery` sets serialized sorted; JSON emitted with `sort_keys=True`.
8. Ledger order is semantic (temporal), never sorted.

### Guard counters (exact constants, increments, verdicts)

| Constant | Default | Owner | Increment / trigger point | Fires when |
|---|---|---|---|---|
| `max_turns` | 50_000 (CLI `--max-turns`) | solver | read after each sub-method; metric = `explorer.turn_counter` (incremented on every `_turn` call, restored probes included) | `turn_counter > max_turns` → `guard_exhausted` |
| `MAX_PROBE_ITEMS` | 6 | explorer (`_probe_actions`) | caps the instrument/recipient window | — |
| `MAX_REVISITS` | 8 | solver loop | per blocked-room requeue (revisit count) | room dropped from further requeues; no diagnosis of its own |
| `MAX_RETRIEVALS_PER_GATE` | 8 | solver | per `requires_item` gate retrieval attempt | exhausted → diagnosis (`item_unreachable`/`item_never_acquired`) |

Guard verdicts: `max_turns` exhaustion is NOT one of the 5 gate reasons. It yields `completable=False`, `unsatisfiable_gates=[]`, `stuck_rooms` = rooms still queued/blocked at termination, `total_turns` = the observed counter (may slightly exceed `max_turns` because the guard is checked between sub-method calls), and a CLI guard line. The spec's fixed `SolveVerdict` fields are preserved; `guard_exhausted` is derived by the CLI from `total_turns >= max_turns and not completable`.

## answers.yaml / KB collision seam (resolved)

`EntityLoader.load_episodes()` globs `episodes/*.yaml` (+ `*.yml`) non-recursively and validates every file as `EpisodeYAML`. A `episodes/answers.yaml` would therefore fail Pydantic validation and break `load_episodes()` — and with it `BlindExplorer.__init__`, `validate_world`, `audit-graph`, and `solve`.

**Resolution: a filename-exact, documented one-line skip in `load_episodes()`.** The metadata file stays at `episodes/answers.yaml` (the spec contract, discoverable next to episode data):

```python
def load_episodes(self) -> list[Episode]:
    ...
    for path in _glob_yaml(episodes_dir):
        if path.name == "answers.yaml":  # solver metadata, not an episode
            continue
        ...
```

Rationale: (a) no gameplay semantics change — no world ships an `answers.yaml` today, so the skip only triggers for the new optional metadata file; (b) `_glob_yaml` is shared by rooms/items/npcs/macros/actions dirs and MUST NOT skip there — the skip is scoped to `load_episodes`; (c) `--answers PATH` is loaded directly by `AnswerBook` and never passes through the loader. No loader re-glob or directory move is needed.

**Regression tests** (in `tests/test_entities/test_loader.py`, same commit as the skip):
- `test_load_episodes_skips_answers_yaml`: a world with a valid `episodes/episode-01.yaml` PLUS an `episodes/answers.yaml` containing the mapping shape (`episode-01: {passwords: [...], riddle_answers: [...]}`) → `load_episodes()` returns exactly `["episode-01"]` without raising.
- `test_load_episodes_does_not_skip_other_yaml`: the same world with `episodes/notes.yaml` (invalid EpisodeYAML) still raises `ValueError` — pins that the exemption is filename-exact, not a blanket YAML exemption.

## CLI, Files, and Testing

### CLI output shapes

`cmd_solve` beside `cmd_audit_graph`: `--episode` (default first loaded), `--answers PATH`, `--json`, `--max-turns N` (default 50_000). Exit 0 completable / 1 diagnosed-not-completable / 2 usage-load-or-unknown-episode. Human output:

```
Verdict: COMPLETABLE (episode-01) — 1234 turns (567 probes)
Walkthrough:
  1. ir puerta diciendo Abrete Sesamo
  2. tomar llave
  ...
```

```
Verdict: NOT COMPLETABLE (episode-01) — 1234 turns (567 probes)
Unsatisfiable gates:
  - passage 'puerta_cerrada' requires_item 'llave' -> item_unreachable (item 'llave' is in audit-unreachable room 'bodega')
  - passage 'puerta_principal' requires_text 'Abrete Sesamo' -> DATA gap: answer for 'puerta_principal' is absent from the knowledge base
Stuck rooms: sala_norte, sala_este
Guard exhausted after 50000 turns (max 50000).
Static audit errors:
  - [start_anchor_missing] episode:episode-01.start_anchor — Start anchor 'ghost' is not a declared room
```

JSON: `json.dumps(verdict.to_dict(), sort_keys=True)` with exactly the 8 `SolveVerdict` fields; each `GateDiagnosis` as `{"passage", "predicate", "required", "reason"}`; `walkthrough` kept in ledger order; `stuck_rooms`/`unsatisfiable_gates` sorted; `static_errors` are the audit `Finding.to_dict()` list. `total_turns = explorer.turn_counter` (attempted, restored probes included); `probe_count` = number of probe commands executed (solver diffs the shared log length around each `_probe_actions` call — restored probes are counted as attempts).

### Files

- `src/fortress_engine/autoplay/solver.py` — `GateDiagnosis`, `SolveVerdict` (+`to_dict`), `AnswerBook`, `GateObserver`, `Solver`. Export from `autoplay/__init__.py`.
- `src/fortress_engine/entities/loader.py` — one-line `answers.yaml` skip in `load_episodes()`.
- `src/fortress_engine/autoplay/explorer.py` — the seven additive hooks/changes above (all default-off).
- `src/fortress_engine/cli/main.py` — `solve` subcommand + `cmd_solve`.
- `pyproject.toml` — narrow `omit` from `src/fortress_engine/autoplay/*` to `src/fortress_engine/autoplay/explorer.py`.
- `worlds/fortaleza/episodes/answers.yaml` — OPTIONAL curated KB (only if cheap and safe; never modifies existing gameplay data).

### Tests (strict, >99% branch gate)

Fixture worlds in `tests/test_autoplay/conftest.py` using the Stage A builder partitions (exact YAML shapes from `build_audit_*`): `solver_happy` (item + text + flag gates, exact walkthrough + exit 0), `solver_kb` (answer ONLY in `episodes/answers.yaml`, proving KB file load + brute-force), `solver_retrieve` (key item in a far reachable room), `solver_unsolvable` (item in an audit-unreachable room → `item_unreachable`; never-set goal flag → `flag_never_set`; exit 1). Additional coverage: loader-skip regression pair, each diagnosis reason (exact messages), ledger excludes restored probes/failed answers, ledger truncation on failed detour, guard termination (low `--max-turns`), determinism (two runs byte-identical JSON; `sort_keys`), non-Spanish vocabulary (movement verb + speech marker from vocabulary, e.g. an English fixture where the marker is not "diciendo"), audit-ERROR world never constructs `BlindExplorer`, CLI exit 0/1/2 and JSON parse, minimal-world end-to-end integration, unpinned Fortaleza smoke (`solve worlds/fortaleza --json`, no-crash + structure only — the world is mid-rewrite and has known unsolvable gates like `requires_item: "nada"`; verdicts MUST NOT be pinned).

Whole-project gate: `pytest --cov=src/fortress_engine --cov-branch --cov-report=term-missing -q` (>99% branch WITH the narrowed omit; solver measured). Targeted solver coverage: temporary config without `omit` + dotted `--cov=fortress_engine.autoplay.solver` (the file-path form collects no data — Stage A proven). The seven explorer edits live in the omitted file so they add no gate burden, but their default-off branches are still exercised by `test_solver.py` through the solver's use of the hooks.

### Task-boundary delta

No material task boundary change; the design sharpens task 2.1 (loader skip + `_movement_pass(passwords)` + `_speech_marker` + `_navigate_to` sort + regression tests) and task 2.3 (commit/turn-budget/gate_code hooks + sorted `_probe_actions`), which already name these responsibilities. `sdd-apply` can proceed on the existing 10 tasks.

## Risks and Open Questions

- Search explosion is controlled, not theoretically complete; guard termination is reported as negative evidence (guard line, `completable=false`, empty `unsatisfiable_gates`).
- `restore()` depends on private `orch._state`; the single restore path and the snapshot-safe detour contract contain the risk.
- The seven explorer edits are in the coverage-omitted file; their correctness is enforced by solver-driven tests, not the gate — apply must keep the default-off invariants.
- `forbids_item`/`forbids_flag` have no dedicated reason in the closed 5-reason set; they map to proxies (`item_never_acquired`/`flag_never_set`) with explicit messages.
- Hyper-edge spoken riddles remain out of scope (cliques have no text predicate); the moving Fortaleza world gets smoke coverage only, never pinned verdicts.

## Threat Matrix

All rows are **N/A**: the argparse addition and additive explorer hooks have no documentation execution, Git selection, commit, push, PR, subprocess, or executable-classification boundary; no adversarial RED tests are required.

## Migration / Rollout

No migration; additive tool with rollback by removing solver, the CLI branch, the loader skip + regression tests, the explorer hooks, tests, and coverage narrowing.
