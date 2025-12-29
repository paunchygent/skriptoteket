---
type: sprint
id: SPR-2026-06-23
title: "Sprint 2026-06-23: Tool layout editor v1 (contract + renderer)"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-06-23
ends: 2026-07-06
objective: "Add a first-class, platform-rendered layout editor output type (v1) for multi-step tools, enabling placement/editing + click-to-assign seating workflows."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-14"]
stories: ["ST-14-25", "ST-14-26"]
adrs: ["ADR-0047"]
---

## Objective

Enable tools to render and edit a structured “layout” (room + objects + slots + assignments) via a **typed UI output**
and a **platform-rendered editor component** (no arbitrary tool JS).

This sprint targets a **2-day vertical slice**: palette placement/editing + click-to-assign + apply changes (no drag/drop
yet).

Reference context:

- Tool editor DX review + seating planner north-star: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
- Contract v2.x enabling work: `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`

## Scope (committed stories)

- [ST-14-25: UI contract v2.x: layout editor output (layout_editor_v1)](../stories/story-14-25-ui-contract-layout-editor-v1-output.md)
- [ST-14-26: UI renderer: layout editor v1 (click-to-assign + apply)](../stories/story-14-26-ui-renderer-layout-editor-v1-click-assign.md)

## Out of scope

- Drag/drop interactions (planned next sprint).
- Free-form drawing/resizing/rotating geometry.
- Allowing tools to ship arbitrary client-side JavaScript.

## Decisions required (ADRs)

- ADR-0047 (proposed): Layout editor v1 (typed layout output + platform renderer).

## Risks / edge cases

- Payload size: student lists + layouts must fit policy budgets (use artifacts/settings when needed).
- Concurrency: interactive sessions already use optimistic concurrency; layout apply must handle conflicts cleanly.
- Accessibility: click-to-assign must be keyboard accessible; drag/drop can be incremental later.

## Execution plan (suggested)

1) Backend: add a new output kind `layout_editor_v1` and normalize/limit its payload like JSON outputs.
2) Frontend: add a layout editor renderer component that:
   - shows room objects + desk groups + slots
   - supports palette + prefab placement/editing for room objects/furniture (snap to grid/edges, no overlap, swap-by-convention)
   - supports click-to-select slot and assign/unassign/swap students
   - keeps local edits and submits an “apply changes” action back to the tool
3) Add a small demo tool (script bank or curated app) to exercise the flow end-to-end.

## Demo checklist

- Paste/upload roster → parse students → render layout editor output.
- Place/move/remove desk/wall objects from the palette; apply changes; tool returns updated layout.
- Place a prefab (e.g. 4 desks in a rectangle); apply changes; tool returns updated layout.
- Assign students to slots via click-to-assign; apply changes; tool returns updated layout.
- Finalize → artifact download + JSON output.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types` (if OpenAPI types change)
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
