---
type: pr
id: PR-0288
title: "ST-29-15 small-screen grouping workspace"
status: done
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-15"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "small-screen"]
dependencies:
  - "PR-0284"
  - "PR-0286"
  - "PR-0287"
acceptance_criteria:
  - "Given `PR-0284` has introduced the phone mode shell, when the teacher opens `Grupper` at the `EPIC-29` phone viewport, then grouping renders as a focused reduced workspace rather than stacked desktop student-pool and group-board lanes."
  - "Given the teacher works with groups on phone, when the grouping toolbar renders, then group count, add/remove group, shuffle, Smart, and overflow actions use compact icon-supported controls with stable touch targets."
  - "Given ungrouped students and groups cannot both dominate the phone viewport, when the reduced grouping layout renders, then the implementation explicitly chooses the active group board as the primary surface and moves ungrouped students plus non-active groups behind tabs, sheets, or compact switching controls."
  - "Given a teacher needs to move students into a group on phone, when the active group surface renders, then drop/assign affordances remain visible and do not require the full desktop student-pool rail to be present beside the board."
  - "Given export/share and Smart settings have recently changed through `PR-0286` and `PR-0287`, when this slice ships, then it preserves the single `Dela och exportera` surface and persistent Smart settings behavior instead of reintroducing separate phone-only toolbar variants."
  - "Given tablet, laptop, and desktop review widths render, when this slice ships, then the existing desktop grouping split workspace remains intact at full-composition widths."
  - "Given visual proof is captured, when the phone grouping workspace is compared with the `Grupper` panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`, then the interpretation preserves the approved hierarchy without requiring pixel-perfect recreation."
---

## Problem

The current `Grupper` workspace is a desktop split workspace: a student-pool
lane sits beside the group board. That is the right full-composition baseline,
but on phone it collapses into stacked work surfaces where neither ungrouped
students nor the active group board has enough room to function well.

This slice interprets only the third mockup screen: `Grupper`.

## Goal

Define and implement the phone grouping experience as a focused reduced
workspace:

- keep `PR-0284`'s active-mode plus `Lägen` shell as the entry control
- keep grouping work, not roster management, as the primary surface
- show group count and repeated actions through compact icon-supported controls
- let the teacher focus on one active group or ungrouped list at a time
- keep ungrouped students and other groups reachable through compact switching,
  tabs, sheets, or another explicitly chosen reduced pattern
- preserve existing desktop/laptop grouping split-pane behavior and data
  semantics

## Non-goals

- No redesign of `Lägesmeny`, `Översikt`, `Sittplatser`, or `Regler`.
- No change to grouping draft persistence, autosave, undo/redo semantics,
  Smart grouping contracts, export/share contracts, or roster/class switching
  semantics.
- No phone-only fork of the `PR-0286` `Dela och exportera` surface.
- No phone-only fork of the `PR-0287` Smart settings persistence behavior.
- No forced phone parity with the full desktop student-pool plus board layout.

## Mockup Interpretation

Use the `Grupper` phone panel in
`docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`
as qualitative product direction:

- the first grouping row should communicate group count and expose compact
  add/shuffle/overflow controls
- group count should feel like local working state, not a large management
  panel
- the active work area should be one group surface at a time, with visible group
  identity such as `Grupp 1`
- `Ej grupperade` and other groups should be reachable through compact tabs,
  chips, sheets, or another deliberate switcher rather than by stacking the
  full student pool above or below every group card
- the active group should keep a clear drop/assign area so the teacher
  understands how students move into the group on touch devices
- student rows should stay compact, draggable/assignable where supported, and
  preserve existing rule-marker visibility
- the reduced layout should not add instructional paragraphs to explain what
  the control hierarchy should make obvious

This is not a pixel contract. It is a workspace-priority contract: one active
grouping surface wins; secondary student/group context remains reachable.

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
  one stable shell, one dominant work surface, secondary context in drawers or
  compact controls, and mobile as deliberate reduced companion.
- `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md`:
  shipped desktop grouping baseline that must not be reopened at laptop or
  desktop widths.
- `docs/backlog/prs/pr-0286-st-29-11-share-export-affordance-consolidation.md`:
  current share/export toolbar composition that this slice must preserve.
- `docs/backlog/prs/pr-0287-st-29-11-smart-settings-popover-persistence.md`:
  current Smart settings behavior that this slice must preserve.
- `docs/mockups/st-29-small-screen-workspace-redesign/README.md`: approved
  mockup bundle and submission policy for this lane.

## Current Frontend Entry Points

- Grouping workspace pane:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- Grouping toolbar:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- Group board:
  `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`
- Group card:
  `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`
- Shared student pool:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
- Shared workspace shell:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Guest workspace shell:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- Shared planner layout tokens:
  `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`
- Grouping/export/share and Smart settings tests:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts`
  and
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.overflow.spec.ts`

## Implementation Plan

1. Start from `PlannerGroupingWorkspacePane.vue` and keep the current desktop
   split workspace intact at `laptop` and `desktop` widths.
2. Add a phone-specific grouping composition that activates only below the
   full desktop-composition range established by `EPIC-29`.
3. Decide the primary phone surface explicitly. The default interpretation is:
   active group board first; ungrouped students and non-active groups reachable
   through a compact switcher/sheet.
4. Keep grouping state mutations in `useClassroomState`; the reduced view
   should rearrange presentation and event routing, not create a separate
   grouping state model.
5. Preserve group-card semantics: rename, move, remove, assign/drop, and
   student removal must continue to route through the existing group board/card
   mutations where those actions remain available on phone.
6. Preserve student rule markers in both ungrouped and assigned student rows.
7. Adapt the grouping toolbar for phone through existing dense controls and
   overflow behavior. Do not add text-heavy action rows or duplicate `Dela`,
   export, or Smart settings controls.
8. If a new phone-only grouping component is clearer, keep it thin and
   prop/event-driven so `PlannerGroupingWorkspacePane.vue` stays under SRP and
   file-size expectations.
9. Use CSS-owned layout and token-driven styles. Do not add measured viewport
   sizing, JS breakpoint duplication, or Tailwind default palette colors.
10. Add focused component tests for phone scan order, group switching,
    ungrouped-student reachability, assignment/drop affordance visibility,
    toolbar compactness, and desktop preservation.
11. Add live browser proof for `phone`, `tablet`, `laptop`, and `desktop`.
    Phone proof must include a screenshot compared qualitatively against the
    mockup's `Grupper` panel.
12. Update `ST-29-15`, this PR task, and `.codex/handoff.md` with exact proof
    commands and artifact paths during implementation closeout.

## Test Plan

- `pdm run fe-test -- --run PlannerGroupingWorkspacePane PlannerGroupingWorkspaceToolbar GroupBoard PlannerStudentPool`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof at:
  - `phone`: `390x844`, `Grupper` reduced workspace with active group surface
  - `tablet`: `768x1024`, reduced companion behavior without desktop bleed
  - `laptop`: `1366x768`, existing desktop split workspace still present
  - `desktop`: `1440x900`, existing desktop split workspace still present

## Implementation Closeout

Implemented and verified on 2026-05-04 as the small-screen grouping workspace
slice.

Key outcomes:

- Phone/tablet render a reduced grouping body with compact group counts,
  horizontal group tabs, and one active student/group surface at a time.
- The existing desktop grouping split remains the full-composition layout at
  laptop/desktop widths.
- Toolbar actions remain compact and the shared action bar is width-bounded on
  small screens so it does not force page-level horizontal overflow.

Verification:

- `pdm run fe-test -- --run PlannerTopPanel PlannerClassWorkspace PlannerGroupingWorkspacePane PlannerSeatingWorkspacePane PlannerRulesWorkspacePane RoomCanvas PlannerShareExportPanel`
- Signed local HuleEdu browser proof:
  `st-29-small-screen-remaining-proof: ok artifacts=.artifacts/st-29-small-screen-remaining-workspaces`

## Rollback Plan

Revert the phone-specific grouping composition and any local grouping switcher
or sheet component while leaving desktop grouping, current toolbar
share/export behavior, Smart settings behavior, grouping draft state, and
workspace routing intact.
