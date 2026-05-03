---
type: pr
id: PR-0289
title: "ST-29-16 small-screen seating workspace"
status: ready
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-16"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "small-screen"]
dependencies:
  - "PR-0284"
  - "PR-0286"
  - "PR-0287"
acceptance_criteria:
  - "Given `PR-0284` has introduced the phone mode shell, when the teacher opens `Sittplatser` at the `EPIC-29` phone viewport, then the room map renders as the primary work surface rather than being pushed below stacked toolbar, status, export, Smart, or student-pool chrome."
  - "Given the teacher needs viewport control on phone, when the seating workspace renders, then zoom out, zoom level, zoom in, and fit/reset are compact touch-safe controls directly associated with the map and do not overlap seats, benches, fixtures, or drag/drop targets."
  - "Given the full student pool cannot sit beside the map on phone, when the reduced seating layout renders, then students are reached through a deliberate `Visa elever` sheet/drawer/action while the default body remains map-first."
  - "Given the teacher assigns or moves students on phone, when the student sheet/drawer is used, then selecting or dragging a student keeps seat placement visible and routes through the existing seating assignment semantics rather than inventing a phone-only state model."
  - "Given `PR-0286` has merged links and file exports, when distribution is available from `Sittplatser` on phone, then one compact `Dela` affordance opens the existing `Dela och exportera` surface with `Länk` and seating file choices instead of reintroducing separate `Delade länkar` or `Exportera` rows."
  - "Given `PR-0287` has fixed Smart settings lifecycle, when Smart settings are opened from the seating toolbar on phone, then internal settings changes keep the surface open while explicit close/outside/Escape/Rules navigation still close intentionally."
  - "Given tablet, laptop, and desktop review widths render, when this slice ships, then the existing desktop seating split workspace remains intact at full-composition widths."
  - "Given visual proof is captured, when the phone seating workspace is compared with the `Sittplatser` panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`, then the interpretation preserves the approved hierarchy without requiring pixel-perfect recreation."
---

## Problem

The current `Sittplatser` workspace is a desktop split workspace: the student
pool sits beside a room canvas, with seating actions, Smart settings, export,
share, and viewport controls around that primary map. That is the right
full-composition baseline, but on phone it risks becoming a long stack where the
teacher reaches the classroom map too late.

This slice interprets only the fourth mockup screen: `Sittplatser`.

## Goal

Define and implement the phone seating experience as a map-first reduced
workspace:

- keep `PR-0284`'s active-mode plus `Lägen` shell as the entry control
- make the room map the default body and visual anchor
- keep zoom, fit/reset, and map interaction controls compact and attached to
  the map
- move the full student pool behind a deliberate `Visa elever` action, sheet,
  drawer, or equivalent reduced control
- keep distribution under one `Dela` / `Dela och exportera` affordance from
  `PR-0286`
- preserve existing desktop/laptop seating split-pane behavior and data
  semantics

## Non-goals

- No redesign of `Lägesmeny`, `Översikt`, `Grupper`, or `Regler`.
- No change to seating draft persistence, autosave, undo/redo semantics, Smart
  seating contracts, share/export contracts, room-template data, or roster/class
  switching semantics.
- No phone-only fork of the `PR-0286` `Dela och exportera` surface.
- No phone-only fork of the `PR-0287` Smart settings persistence behavior.
- No forced phone parity with the full desktop student-pool plus room-canvas
  layout.
- No public share-page renderer, PDF, Excel, or artifact-delivery changes.

## Mockup Interpretation

Use the `Sittplatser` phone panel in
`docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`
as qualitative product direction:

- the first seating-specific row after the shell should be a compact map tool
  strip, not a second page header
- zoom out, zoom level, zoom in, and `Anpassa` should read as viewport tools
  attached to the classroom map
- the room map should dominate the phone body; seats, benches, fixtures, wall
  labels, and the teacher desk must remain inspectable
- seat labels and student names may become compact, but they must not overlap
  incoherently or lose accessible names
- the student pool should be reachable through a bottom action such as
  `Visa elever (29)`, then presented in a sheet/drawer/list that supports
  assignment without permanently displacing the map
- `Dela` belongs in compact toolbar/overflow/sheet reachability and must open
  the merged `Dela och exportera` model from `PR-0286`; do not create separate
  phone rows for shared links and file export
- Smart settings belong in the existing compact Smart/settings affordance and
  must preserve the `PR-0287` lifecycle expectations
- the reduced layout should not add instructional paragraphs to explain what
  the map, zoom strip, and student action should make obvious

This is not a pixel contract. It is a workspace-priority contract: the map wins;
students, distribution, Smart settings, history, and management remain reachable
through compact subordinate surfaces.

## Frontend And Design Authorities

- `agent-docs-governance`: docs-as-code authority; no production work without
  this governed PR slice.
- `integrated-frontend-stack`: Vue 3/Vite/TypeScript stack, token-driven
  styling, CSS-owned layout geometry, dense workspace verification.
- `brutalist-academic-ui`: brutalist academic doctrine; dense workspaces are
  instruments, not stacked card pages.
- `.codex/rules/045-huleedu-design-system.md`: token-first styling, no Tailwind
  default palette leakage, icon-supported dense controls, and dense-action
  primitive ownership.
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`:
  canvas first, one stable shell, compact action rows, secondary context in
  drawers/menus/inspectors, and mobile as deliberate reduced companion.
- `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md`:
  shipped desktop seating baseline that must not be reopened at laptop or
  desktop widths.
- `docs/backlog/prs/pr-0286-st-29-11-share-export-affordance-consolidation.md`:
  current share/export toolbar composition that this slice must preserve.
- `docs/backlog/prs/pr-0287-st-29-11-smart-settings-popover-persistence.md`:
  current Smart settings behavior that this slice must preserve.
- `docs/mockups/st-29-small-screen-workspace-redesign/README.md`: approved
  mockup bundle and submission policy for this lane.

## Current Frontend Entry Points

- Seating workspace pane:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- Seating toolbar:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- Room scene surface:
  `frontend/apps/skriptoteket/src/views/apps/components/RoomSceneSurface.vue`
- Room canvas:
  `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`
- Seat node and student token presentation:
  `frontend/apps/skriptoteket/src/views/apps/components/SeatNode.vue` and
  `frontend/apps/skriptoteket/src/views/apps/components/RoomSeatToken.vue`
- Shared student pool:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
- Seating Smart/settings drawer:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingSettingsDrawer.vue`
- Combined share/export panel:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerShareExportPanel.vue`
- Shared workspace shell:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Guest workspace shell:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- Shared planner layout tokens:
  `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`
- Seating viewport and export tests:
  `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts`,
  and
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.overflow.spec.ts`

## Implementation Plan

1. Start from `PlannerSeatingWorkspacePane.vue` and keep the current desktop
   split workspace intact at `laptop` and `desktop` widths.
2. Add a phone-specific seating composition that activates only below the full
   desktop-composition range established by `EPIC-29`.
3. Make the room scene the primary phone surface. The student pool should not
   render as a full sibling rail or stacked card above the map by default.
4. Keep seating state mutations in the existing planner state/composables. The
   reduced view should rearrange presentation and event routing, not create a
   second seating assignment model.
5. Preserve `useRoomViewportZoom` and existing fit/reset behavior. Phone zoom
   controls should call the same viewport operations and remain CSS-positioned
   or locally composed, not driven by persistent JS geometry.
6. Preserve room-scene semantics: assignment, drag/drop or select-to-place,
   seat removal, wall labels, fixture rendering, and rule-marker visibility
   must continue to route through the existing room canvas/seat components.
7. Introduce a `Visa elever` student sheet/drawer/list only if it remains thin
   and prop/event-driven. It should expose student access without permanently
   hiding the active map.
8. Adapt the seating toolbar for phone through existing dense controls and
   overflow behavior. Do not add text-heavy action rows or duplicate `Dela`,
   export, or Smart settings controls.
9. Preserve the `PR-0286` `Dela och exportera` composition: seating link
   management and `Affisch (A3)`, `Affisch (A4)`, and `Excel (.xlsx)` actions
   stay inside one distribution surface.
10. Preserve the `PR-0287` Smart settings lifecycle and keep `Öppna Regler` as
    the intentional navigation close path.
11. If a new phone-only seating component is clearer, keep it thin and
    prop/event-driven so `PlannerSeatingWorkspacePane.vue` stays under SRP and
    file-size expectations.
12. Use CSS-owned layout and token-driven styles. Do not add measured viewport
    sizing, JS breakpoint duplication, hardcoded colors, or Tailwind default
    palette colors.
13. Add focused component tests for phone scan order, map-first rendering,
    zoom/fit control reachability, student-sheet reachability, assignment path,
    merged `Dela` reachability, toolbar compactness, and desktop preservation.
14. Add live browser proof for `phone`, `tablet`, `laptop`, and `desktop`.
    Phone proof must include a screenshot compared qualitatively against the
    mockup's `Sittplatser` panel.
15. Update `ST-29-16`, this PR task, and `.codex/handoff.md` with exact proof
    commands and artifact paths during implementation closeout.

## Test Plan

- `pdm run fe-test -- --run PlannerSeatingWorkspacePane PlannerSeatingWorkspaceToolbar RoomCanvas RoomSceneSurface PlannerStudentPool PlannerShareExportPanel`
- `pdm run fe-test -- --run useRoomViewportZoom`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof at:
  - `phone`: `390x844`, `Sittplatser` reduced workspace with map-first body,
    compact zoom/fit controls, and `Visa elever` reachability
  - `tablet`: `768x1024`, reduced companion behavior without desktop bleed
  - `laptop`: `1366x768`, existing desktop split workspace still present
  - `desktop`: `1440x900`, existing desktop split workspace still present

## Rollback Plan

Revert the phone-specific seating composition and any local student
sheet/drawer component while leaving desktop seating, current toolbar
share/export behavior, Smart settings behavior, seating draft state, room
viewport zoom, and workspace routing intact.
