---
type: adr
id: ADR-0047
title: "Layout editor v1 (typed layout output + platform renderer)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-29
links:
  - "PRD-script-hub-v0.2"
  - "ADR-0022"
  - "ADR-0024"
  - "EPIC-14"
---

## Context

Some tools (notably seating/room planning) need an interactive UI where a user can:

- see a “room layout” with physical objects (desks, door, window, whiteboard)
- assign “tokens” (students) to “slots” (seats)
- iterate, fine-tune, and then finalize to an artifact + a JSON representation
- return later and continue from remembered settings/previous arrangements

The current contract supports:

- typed outputs (markdown/table/json/html_sandboxed) and typed action forms
- persisted `state` and session turn-taking (`start_action`)

But it does **not** support tool-provided interactive UI JavaScript (by design). `html_sandboxed` renders in a fully
sandboxed iframe (no scripts), so it cannot be used as an interactive editor.

We need a **platform-rendered**, **typed**, and **replayable** interactive component that tools can drive via data, while
preserving the security posture: “tools ship data, platform ships UI code”.

## Decision

Add a new UI contract output kind: `layout_editor_v1`.

`layout_editor_v1` is a **data-first** spec for a small layout “engine chassis” that is not coupled to a single domain
semantic. Domain semantics (e.g. “desk”, “door”) are expressed as **conventions** in `kind` + `props` rather than being
hard-coded into the foundation.

Think of this as a **Sims-like builder framework**:

- The platform provides the chassis (grid, snapping, non-overlap, assignment mechanics, renderer).
- A tool / curated app provides the **available conventions** (“furniture”, “walls”, “room objects”) and current scene.
- The platform renders and edits that scene without executing any tool-provided client code.

The v1 editor supports **assignment editing** (token ↔ slot) with:

- click/keyboard-first editing (baseline)
- optional drag/drop enhancement (separate sprint)
- a batch “apply changes” flow that calls `start_action` once per commit

The layout structure itself (nodes/groups/objects) is tool-owned and produced by the tool each turn. The editor does not
allow arbitrary free-form drawing or geometry editing in v1.

Geometry is **grid- and anchor-based**:

- Containers define a discrete **grid**, and child nodes occupy grid slots (no overlap).
- Border objects (door/window/whiteboard) snap to the **room border** via edge anchors.
- “Multi-seat desks” are modeled as compositions (multiple 1-seat desks grouped inside a single grid slot).
- Interactions follow conventions: same-type entities are swappable (not stackable/overlapping).

## Contract (proposed)

### 1) New output kind

Extend `UiOutputKind` with:

- `layout_editor_v1`

and introduce a new discriminated output model:

- `UiLayoutEditorV1Output(kind="layout_editor_v1", title?, spec)`

### 2) Core primitives (foundation)

The `spec` is built from three primitives:

1) **Nodes**: a scene graph of rectangular objects (container or leaf).
2) **Ports**: attachment points on nodes that can hold at most one assigned token (a “slot”).
3) **Tokens**: assignable items (students), with optional metadata.

This keeps the foundation generic and composable, while allowing domain semantics as conventions.

### 3) Conventions, prefabs, and palette (builder flexibility)

To enable custom “furniture” and “wall” semantics per tool without rebuilding the engine, `layout_editor_v1` supports a
tool-provided **conventions catalog**:

- A convention is an “implementation” for how a node should be placed/rendered/interacted with (within the chassis).
- Conventions are identified by a stable `convention_id` (tool-owned namespace).
- Nodes reference conventions by `convention_id` and may override/extend via `props`.

Optionally, the tool may also provide:

- a **palette** (what the user is allowed to place)
- **prefabs** (composed objects; e.g., “4 desks in a rectangle”)

The v1 renderer uses the palette/prefabs to enable a “build mode” where users can place, move, and delete nodes, while
still keeping layout behavior constrained and predictable (grid/edge snapping, non-overlap, swap rules).

Decision: v1 includes **palette/prefab placement and editing** (in addition to assignment editing). The renderer supports
placing, moving, and deleting nodes using the palette/prefabs, constrained by grid/edge snapping and swap rules.

#### Prefab concept (v1)

A prefab is a tool-provided template for a composed object:

- Instantiated entirely client-side (platform renderer), by cloning node templates and generating unique IDs.
- Inserted as a new **group node** occupying one parent grid cell, with children arranged by a nested grid.
- Used to express “desk configurations” (2/3/4 in a row, 4 as a rectangle, etc.) without introducing multi-seat desk nodes.

### 4) Geometry model (grid + anchors)

To keep the chassis flexible while still producing “sensible geometry”, the contract provides:

- **Container layout**: how children are placed (v1: grid).
- **Child placement**: where a child is placed within its parent (v1: grid cell or edge anchor).

#### Container layout: `grid`

`layout: { "type": "grid", "columns": 1..N, "max_rows"?: 1..M }`

The renderer maps grid cells to rectangles sized by UI design tokens (not tool-provided pixel geometry).

#### Child placement: `grid`

`placement: { "type": "grid", "row": 0.., "col": 0.., "row_span"?: 1.., "col_span"?: 1.. }`

In v1, desk groups occupy a single grid slot (`row_span=1`, `col_span=1`) by convention.

#### Child placement: `edge`

For room-border objects:

`placement: { "type": "edge", "edge": "north|south|east|west", "offset": 0.., "span"?: 1.. }`

The renderer snaps the node to the corresponding border segment. Offsets are discrete “slots” along the edge, derived
from the room grid (e.g. `offset` corresponds to a column index for north/south edges).

#### Non-overlap and snapping invariants

The spec is considered **invalid** (renderer shows an error state) if:

- Two siblings in the same `grid` container occupy overlapping grid cells/spans.
- Two siblings on the same edge occupy overlapping edge segments.

This prevents stacking/overlaps by definition and keeps layout behavior predictable.

### 5) Swap and snap rules (by convention)

The renderer applies the following conventions:

- **Non-overlap**: nodes cannot stack; placement collisions must be resolved by swap or rejection.
- **Swap**: nodes with the same `swap_group` may swap positions when a move collides with an occupied target.
  - This enables “conventions of the same type being swappable” (e.g. desk ↔ desk; window ↔ window).
- **Snap**: all placements snap to discrete grid cells or edge slots.

For ports/tokens:

- Each student slot port holds at most one token (student).
- Assigning a token to an occupied slot swaps tokens by default (same-type swap convention for slots).

### 6) Proposed spec sketch (v1)

```json
{
  "schema_version": 1,
  "layout_id": "room-a-2026-01-01",
  "root_node_id": "room",
  "conventions": [
    {
      "convention_id": "room.v1",
      "kind": "room",
      "category": "room",
      "swap_group": null,
      "placement_rules": { "allowed": ["grid"] },
      "props_schema_hint": { "title": "string?" }
    },
    {
      "convention_id": "group.row.v1",
      "kind": "group",
      "category": "group",
      "swap_group": "row",
      "placement_rules": { "allowed": ["grid"] }
    },
    {
      "convention_id": "furniture.desk.single.v1",
      "kind": "desk",
      "category": "furniture",
      "swap_group": "desk",
      "placement_rules": { "allowed": ["grid"] },
      "ports": [{ "port_kind": "student_slot", "max_tokens": 1 }]
    },
    {
      "convention_id": "wall.whiteboard.v1",
      "kind": "whiteboard",
      "category": "wall",
      "swap_group": "wall_item",
      "placement_rules": { "allowed": ["edge"] }
    },
    {
      "convention_id": "wall.door.v1",
      "kind": "door",
      "category": "wall",
      "swap_group": "wall_item",
      "placement_rules": { "allowed": ["edge"] }
    }
  ],
  "palette": [
    { "palette_id": "desk.single", "label": "Bänk", "convention_id": "furniture.desk.single.v1" },
    { "palette_id": "desk.4.rectangle", "label": "4 bänkar (rektangel)", "prefab_id": "prefab.desk.rectangle.4.v1" },
    { "palette_id": "whiteboard", "label": "Whiteboard", "convention_id": "wall.whiteboard.v1" }
  ],
  "prefabs": [
    {
      "prefab_id": "prefab.desk.rectangle.4.v1",
      "label": "4 bänkar (rektangel)",
      "root": {
        "kind": "group",
        "convention_id": "group.row.v1",
        "layout": { "type": "grid", "columns": 2 }
      },
      "children": [
        { "kind": "desk", "convention_id": "furniture.desk.single.v1", "placement": { "type": "grid", "row": 0, "col": 0 } },
        { "kind": "desk", "convention_id": "furniture.desk.single.v1", "placement": { "type": "grid", "row": 0, "col": 1 } },
        { "kind": "desk", "convention_id": "furniture.desk.single.v1", "placement": { "type": "grid", "row": 1, "col": 0 } },
        { "kind": "desk", "convention_id": "furniture.desk.single.v1", "placement": { "type": "grid", "row": 1, "col": 1 } }
      ]
    }
  ],
  "nodes": [
    {
      "node_id": "room",
      "kind": "room",
      "convention_id": "room.v1",
      "label": "Klassrum A",
      "layout": { "type": "grid", "columns": 5 },
      "children": ["row-1", "row-2", "wb-1", "door-1"]
    },
    {
      "node_id": "row-1",
      "kind": "group",
      "convention_id": "group.row.v1",
      "label": "Rad 1",
      "layout": { "type": "grid", "columns": 5 },
      "placement": { "type": "grid", "row": 0, "col": 0 },
      "children": ["desk-1", "desk-2", "desk-3"]
    },
    {
      "node_id": "desk-1",
      "kind": "desk",
      "convention_id": "furniture.desk.single.v1",
      "label": "Bänk 1",
      "placement": { "type": "grid", "row": 0, "col": 0 },
      "ports": [{ "port_id": "seat-desk-1", "kind": "slot", "label": "Plats" }]
    },
    {
      "node_id": "wb-1",
      "kind": "whiteboard",
      "convention_id": "wall.whiteboard.v1",
      "label": "Whiteboard",
      "placement": { "type": "edge", "edge": "north", "offset": 2 }
    },
    {
      "node_id": "door-1",
      "kind": "door",
      "convention_id": "wall.door.v1",
      "label": "Dörr",
      "placement": { "type": "edge", "edge": "west", "offset": 1 }
    }
  ],
  "tokens": [
    { "token_id": "student-anna", "label": "Anna", "meta": { "gender": "f" } }
  ],
  "assignments_by_port_id": {
    "seat-desk-1": "student-anna"
  },
  "editor": {
    "apply_action_id": "layout.apply",
    "finalize_action_id": "layout.finalize"
  }
}
```

Notes:

- “Desk with 3 seats” is modeled as **3 desk nodes** (each with one slot) grouped together, rather than a single node
  with multiple seats.
- A “multi-desk composition” occupies a single parent grid slot by convention, and arranges its desks inside that slot
  (renderer-defined; tool provides the group + child desks).
- `meta` is intentionally flexible; it may be used for colors/filters/hints. Size limits are enforced by the normalizer.

### 7) How edits are submitted (apply semantics)

The renderer maintains a local “draft” and submits changes in one batch via `start_action`.

Recommended input shape (v1):

- `action_id = spec.editor.apply_action_id`
- `input = { "layout_id": "...", "draft_scene": { "root_node_id": "...", "nodes": [...], "assignments_by_port_id": { ... } } }`

The UI should only enable “Apply” if the tool has provided the corresponding `next_actions` entry (so the tool remains in
control of allowed operations).

## Policy & normalization

- `layout_editor_v1` is allowed in `DEFAULT` UI policy (not curated-only).
- The output is normalized deterministically similarly to `json` outputs:
  - canonicalize JSON-like structures
  - enforce size budgets/caps
  - drop/trim on overflow with a system notice

## Renderer requirements (v1)

- Platform-rendered Vue component; no tool JS.
- Baseline interactions:
  - click-to-select slot
  - pick student (or unassign) via list/search
  - keyboard operable (tab/enter/escape; clear actions)
  - “unsaved changes” indicator and “Apply changes” action
- Optional semantics:
  - known `kind` values (`room`, `desk`, `door`, `window`, `whiteboard`) get nicer rendering
  - unknown kinds fall back to generic rectangle + label

## Incremental path to drag/drop

After v1 click-to-assign is stable, add drag/drop using a well-known library (e.g. `interactjs`) as an enhancement:

- drag a student token onto a slot to assign
- drop on occupied slot swaps (same-type swap convention for slots)
- click/keyboard flow remains supported and tested

## Consequences

### Benefits

- Unlocks interactive tool UX (seating planner) without weakening security posture.
- Keeps the foundation generic: future interactive editors can reuse nodes/ports/tokens patterns.
- Fits existing turn-taking model (`start_action`, persisted state, replayable ui_payload).

### Tradeoffs / risks

- Introduces a new interactive renderer surface that must be maintained and tested.
- Payload size needs careful caps; larger datasets may require artifacts/settings/state (rather than UI payload).

## Open questions

- Should the renderer support an optional “tool-provided constraints legend” (e.g. gender balance) for in-UI guidance?
- Should we standardize any additional layout types beyond `grid` (e.g. `stack`) before there is a concrete use case?
- Should we standardize a minimal set of `swap_group` conventions (e.g. `desk`, `wall_item`) or keep it entirely tool-owned?
