# Proposal: Static Explorer Graph Audit

## Intent

Fortaleza's blind explorer fails to cover the world, but evidence cannot separate graph defects, intentional design, and explorer heuristics. Stage A supplies a deterministic YAML-only diagnosis before Stage B brute-force, which requires zero `ERROR` findings.

## Scope

### In Scope
- `src/fortress_engine/autoplay/graph_audit.py`: pure `EntityLoader` BFS over `load_macro_edges` from `start_anchor`, with dataclass reports; no runtime, plugins, or `WorldState`.
- `audit-graph` CLI with human and CI output.
- Strict unit, CLI, and integration tests using synthetic `tmp_path` worlds.

### Out of Scope
- Stage B brute-force/completability redesign (future report consumer).
- Narrator-text checks, or edits to `worlds/fortaleza`; the tool reports defects, never fixes data.
- Changing the existing `validate` command.

## Capabilities

### New Capabilities
- `graph-audit`: static integrity, reachability tiers, gates, and findings.

### Modified Capabilities
- `cli-entry-point`: register `audit-graph`; existing commands remain unchanged.

## Approach

Choose pure-static Approach A: loader plus local adjacency map (or pure graph indexing), optimized for deterministic, fast, KISS/SRP-friendly tests. Reject Approach B (runtime/plugins/`WorldState`) because wiring and mutation add fragility to pure edge-list math.

Tiers are **unconditional** (no item/flag predicates; text gates passable), **conditional** (item/flag predicates are statically undecidable), and **unreachable** (declared minus both), with per-passage gates. The 16-category contract is:

| Severity | Categories |
|---|---|
| ERROR | `start_anchor_missing`, `dangling_edge_endpoint`, `dangling_spatial_anchor`, `isolated_room`, `gate_unknown_entity` |
| WARN | `orphan_room`, `unreachable_room`, `gated_only_room`, `gate_item_other_episode`, `goal_unknown_entity`, `duplicate_passage`, `self_loop_edge` |
| INFO | `entity_limbo_at_load`, `closed_edge_without_text_gate`, `flag_never_set`, `text_gated_passage` |

Legal limbo and the closed-without-text engine quirk remain INFO.

## CLI, Architecture, and Affected Areas

`fortress-engine audit-graph <world_path> [--episode ID] [--json] [--include-info]` uses an argparse subparser and `cmd_audit_graph`; the first episode is the default. JSON emits `AuditReport` (`episode`, `declared_rooms`, `unconditionally_reachable`, `conditionally_reachable`, `unreachable_rooms`, and findings with severity/category/location/message/data). Exit `0` means no errors, `1` means errors/load failure, and argparse errors remain `2`; INFO requires `--include-info`.

The development-only `autoplay/` tool uses dataclasses, preserves entity-agnostic engine core, and adds no world logic to it. New/modified areas: `autoplay/graph_audit.py`, `cli/main.py`, and audit tests. `validate_world` remains independent because audit checks are stricter per episode; overlap is deferred to a deliberate later contract change.

## Testing, Risks, Rollback, and Success

Strict TDD fixtures `audit_happy`, `audit_broken`, `audit_gated`, and `audit_limbo` cover all categories, tiers, JSON, episode selection, and exit codes; whole-project branch coverage must stay above 99%. Minimal-world integration must pass; Fortaleza integration is smoke/category-only and never pins exact findings while the world moves.

Undecidable gates are conditional, moving findings use non-exact assertions, and exhaustive fixtures protect coverage. Keeping `validate_world` unchanged limits overlap risk. Rollback is additive: remove the module/tests and revert the CLI addition; no migration or world-data rollback is needed.

Success is deterministic reports, CI-safe JSON/exit behavior, all 16 categories tested, and zero `ERROR`s exposed as Stage B's explicit precondition.
