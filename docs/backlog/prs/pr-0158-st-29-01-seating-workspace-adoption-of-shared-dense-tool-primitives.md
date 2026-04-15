---
type: pr
id: PR-0158
title: "ST-29-01: seating workspace adoption of shared dense-tool primitives"
status: canceled
owners: "agents"
created: 2026-03-28
updated: 2026-04-01
stories:
  - "ST-29-01"
tags: ["frontend", "klassrumskartan", "design-system", "workspace", "ux"]
dependencies:
  - "EPIC-29"
  - "PR-0157"
acceptance_criteria:
  - "Given `Sittplatser` is the first proving ground for ST-29-01, when this slice ships, then its repeated toolbar and viewport operations consume the shared dense-tool primitives instead of planner-local one-off button treatments."
  - "Given export in seating is a canonical branching action, when this slice ships, then the seating export control renders as the shared split-button pattern rather than as an app-local special case."
  - "Given `Smart` is a compact teacher-facing on/off control with deeper rule tuning, when this slice ships, then the seating workspace uses the shared compound-control pattern: labeled toggle plus configure-context child action that routes into `Regler`."
  - "Given seating still needs strong discoverability for repeated controls, when this slice ships, then undo, redo, history, zoom, fit view, export, and overflow expose the shared labels/tooltips/accessibility contract without reintroducing long text-heavy action rows."
---

## Problem

The primitive layer only becomes real when one dense workspace consumes it end to end. `Sittplatser`
is the best first proving ground because it exercises repeated actions, viewport controls, split
export behavior, and the `Smart` to `Regler` relationship in one place.

## Status note (2026-04-01)

This slice is canceled as originally framed. The later shipped planner work validated and adopted
the shared desktop/control direction through a broader mix of overview, grouping, seating, rules,
and Smart-settings changes than this older "first proving ground in `Sittplatser`" plan assumed.

The remaining backlog need is no longer a seating-first primitive adoption pass. It is the
cross-surface follow-on tightening now tracked in `ST-29-11`, `ST-29-12`, and later `ST-29-08`.

## Goal

Adopt the shared ST-29-01 primitives in the seating workspace without yet attempting the wider
shell overhaul from later stories.

## Non-goals

- Redesigning `Översikt`, `Grupper`, and `Regler` in the same PR.
- Re-cutting the entire planner shell.
- Introducing new semantic action categories beyond the frozen v1 set.
- Solving all mobile/reduced-layout behavior in this slice.

## Implementation plan

1. Swap local seating action controls to shared primitives.
   - Replace planner-local icon buttons and menu triggers where a shared control now exists.

2. Normalize export as a shared split pattern.
   - Refactor the seating export cluster to consume the shared split-button behavior and canonical
     symbol/label contract.

3. Normalize `Smart` as a compound control.
   - Keep visible on/off state.
   - Route the configure child action into the rules workspace instead of adding toolbar drawers.

4. Verify seating typography/density stays compact.
   - Preserve the dense-tool target.
   - Do not reintroduce helper-band or panel-stack regressions during the primitive swap.

## PR-sized execution checklist

- [ ] Update seating workspace action surfaces in `src/views/apps/components/`
- [ ] Replace or retire planner-local primitive stopgaps that become redundant
- [ ] Add or update seating Vitest coverage
- [ ] Run live proof on the local planner route
- [ ] Record verification in `.codex/handoff.md` if implementation proceeds

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- `pdm run fe-test -- --run src/views/apps/components/PlannerExportActionGroup.spec.ts`
- `pdm run fe-test -- --run src/views/apps/useRoomViewportZoom.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`

## Rollback plan

- Revert the seating adoption slice if the shared primitives do not yet hold up in a live workspace.
- Keep the shared primitive layer from `PR-0157` intact unless the contract itself proves wrong.
