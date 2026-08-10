# Design: Explorer Graph Audit

## Technical Approach

Stage A is a deterministic loader-only diagnostic in
`src/fortress_engine/autoplay/graph_audit.py`. `GraphAudit` receives an
`EntityLoader` and selected `Episode`, builds indexes from episode data,
performs one BFS, scans integrity, and returns
`AuditReport`; it never creates `WorldState`, `EventBus`, plugins, or
`DualGraphEngine` gate state. `Finding`, `PassageRecord`, and `AuditReport` are
dataclasses. `autoplay/__init__.py` exports `GraphAudit`, `Finding`,
`PassageRecord`, and `AuditReport`.

## Interfaces / Contracts and Flow

```text
CLI -> EntityLoader -> Episode + episode data
                         |-> rooms/edges/entity indexes
                         |-> BFS(start_anchor; all edges, no gates)
                         |-> integrity scans -> sorted Findings
                         `-> typed AuditReport -> human/JSON serializer
```

`AuditReport` contains `episode`, `declared_rooms`, `reachable_rooms`,
`unreachable_rooms`, `passages`, and `findings`. Sets serialize as sorted lists.
`Finding` has `severity`, `category`,
`location`, `message`, and JSON-safe `data`. Findings sort by
`(ERROR=0/WARN=1/INFO=2, category, location)`.

### BFS

Index every loaded `MacroEdge` by `from_anchor`; incoming/outgoing indexes
include every edge incidence. `load_macro_edges` expands
`bidirectional` declarations into reverse copies, so audit does not expand or
reverse edges again. From a present start, dequeue once and enqueue every
declared-room destination (including self-loops once),
ignoring `open` and every predicate. A missing start returns an empty set and
`start_anchor_missing`; dangling endpoints never become declared rooms.

### Findings (location; data)

| Severity/category | Exact condition |
|---|---|
| ERROR `start_anchor_missing` | start not in rooms; `episode:{id}.start_anchor`; `{episode,start}` |
| ERROR `dangling_edge_endpoint` | each missing edge endpoint; `edge:{edge_id}.{endpoint}`; `{edge,from,to,missing}` |
| ERROR `dangling_spatial_anchor` | non-null anchor absent from current/shared entity IDs; `entity:{id}.spatial_anchor`; `{episode,entity,anchor}` |
| ERROR `isolated_room` | non-start room has neither incoming nor outgoing edge; `room:{id}`; `{room}` |
| WARN `orphan_room` | non-start room has no incoming but has outgoing; `room:{id}`; `{room,outgoing_edges}` |
| WARN `unreachable_room` | room absent from BFS; `room:{id}`; `{room}` |
| WARN `duplicate_passage` | repeated `(from,to,passage_name)`; `passage:{from}->{to}:{name}`; `{tuple,edge_ids}` |
| WARN `self_loop_edge` | `from_anchor == to_anchor`; `edge:{id}`; `{edge,anchor,passage}` |
| WARN `goal_unknown_entity` | recognized goal `entity`/`room`/`flag` value absent from structural IDs/references; `goal:{path}.{parameter}`; `{goal,parameter,value}` |
| WARN `entity_in_unreachable_room` | placed item/NPC anchor is unreachable; `entity:{id}.spatial_anchor`; `{episode,entity,anchor}` |
| INFO `entity_limbo_at_load` | placed item/NPC has `spatial_anchor: null`; `entity:{id}.spatial_anchor`; `{episode,entity}` |

`isolated_room` and `orphan_room` are mutually exclusive: an isolated room
has no out edge, while an orphan has at least one. Both may overlap
`unreachable_room`. Goal traversal is recursive through `and`/`or`; known flags
come from loaded `FLAG` operators and macro flag names only, without judging
setters or gates.

## Passive Gate Data

Each expanded edge becomes a `PassageRecord` serialized with exactly, and in
this order: `from`, `to`, `passage_name`, `requires_item`, `forbids_item`,
`requires_flag`, `forbids_flag`, `requires_text`, `open`, `direction`. Values
are copied verbatim, including `None` and `False`; records sort by all fields.

## File Changes

Create `graph_audit.py`; modify `autoplay/__init__.py` and `cli/main.py`; add
unit, CLI, and integration tests plus temporary YAML fixtures. `pyproject.toml`
is unchanged.

## CLI

Add `audit-graph` to `main()` with positional `world_path` and flags
`--episode`, `--json`, `--include-info`; dispatch to `cmd_audit_graph`. The
handler validates `world.yaml`, loads episodes, selects the first loaded
episode by default, and maps missing/malformed worlds and unknown episodes to
stderr/SystemExit(2). Human output groups filtered findings by severity;
INFO is hidden unless requested. JSON emits deterministic sorted-key report
data with the same INFO filter. Exit 0 means no ERROR, 1 means any ERROR, and
2 means usage/load/episode failure. `validate`, `run`, and `test` remain
unchanged.

## Testing Strategy

Use real temporary YAML fixtures: `world.yaml` is `{world_id,name}`; episodes
use the standard block; rooms are `{entity_id,type,name}`; macro files are
lists of `{macro_edge_id,from_anchor,to_anchor,direction,passage_name}`.
`audit_happy`: `alpha↔beta`, a `FLAG`-set goal, placed item. `audit_broken`:
`start_anchor: ghost`; rooms `isolated`, `orphan`, `sink`; macros `orphan->sink`,
`alpha->missing`, duplicate `alpha->sink`, and self-loop `alpha->alpha`; item anchor `ghost_room`;
goal entity/room/flag values `ghost_*`. `audit_disconnected`: reachable
`alpha->beta`, disconnected `gamma`, item anchored `gamma`. `audit_limbo`:
item `spatial_anchor: null`.

Unit tests assert every category, exact payloads/order, missing/present-start
BFS, self-loop, all passive predicates, and report set arithmetic. CLI tests
mirror `test_validate.py`: exit 0/1/2, default/explicit episode, JSON parsing,
human grouping, and INFO filtering. Integrations audit `_test_minimal` cleanly
and both Fortaleza episodes without crashes or pinned findings. Exercise every
branch with strict assertions; run the mandated whole-project `pytest
--cov=src/fortress_engine --cov-branch ... -q` (>99%) plus targeted audit
coverage because the existing config omits `autoplay/*`.

## Decisions, Risks, and Threat Matrix

| Decision | Rationale / risk |
|---|---|
| Local adjacency, no runtime graph | Pure math prevents accidental gate evaluation; loader reverse expansion is the API boundary. |
| Scan loader partitions, not `Entity.type` | Preserves entity-agnostic core; rooms are anchors, items/NPCs are placed entities. Shared player null is intentionally not limbo. |
| No loader “all flags/entities” API | Compose `load_*` methods; derive flags from data. Future loader consolidation is low-risk. |

Threat matrix: documentation paths, Git selection, commit state, push state,
and PR commands are each **N/A**—argparse dispatch has no classification,
subprocess, VCS, or PR boundary, so no adversarial RED tests apply.

## Migration / Rollout

No migration required; rollback is deleting the additive module/tests and the
CLI branch.

## Open Questions

None; no blocker.
