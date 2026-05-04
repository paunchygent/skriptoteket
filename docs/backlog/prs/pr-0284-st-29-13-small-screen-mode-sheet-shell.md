---
type: pr
id: PR-0284
title: "ST-29-13 small-screen mode sheet shell"
status: done
owners: "agents"
created: 2026-05-03
updated: 2026-05-04
stories:
  - "ST-29-13"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "small-screen"]
dependencies:
  - "ST-29-13"
acceptance_criteria:
  - "Given the planner renders at the `EPIC-29` phone viewport, when the top planner shell is visible, then the four-option workspace segmented rail is replaced by one active-mode affordance plus a separate `Lägen` affordance."
  - "Given the teacher activates `Lägen` on phone, when the mode sheet opens, then it presents `Översikt`, `Grupper`, `Sittplatser`, and `Regler` as a bottom sheet with icon-supported rows, concise subtitles, disabled-state reasons where relevant, and clear current-mode state."
  - "Given the mode sheet is open, when the teacher chooses an enabled mode, presses Escape, activates close/backdrop, or tabs through the dialog, then focus, close behavior, selected-mode emission, and keyboard accessibility follow the existing dialog/drawer patterns."
  - "Given tablet, laptop, and desktop review widths render, when this slice ships, then the existing desktop-first workspace selector remains intact at full-composition widths and the phone shell does not push a stacked-card compromise back into `laptop`."
  - "Given visual proof is captured, when the phone shell and open mode sheet are compared with the `Lägesmeny` panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`, then the interpretation preserves the approved hierarchy without requiring pixel-perfect recreation."
  - "Given implementation is reviewed, when frontend code is inspected, then breakpoint/layout ownership is CSS-driven, token-driven styling is used, and no new hardcoded colors, Tailwind default palette leakage, or persistent runtime geometry measurement is introduced."
---

## Problem

The current planner top panel exposes the full four-option workspace selector
through `UiSegmentedToggle`. That is the right desktop/laptop control, but on a
phone-sized viewport it becomes a cramped rail and competes with the active
workspace. The approved mockup starts the small-screen redesign by replacing
that rail with an active-mode button and a `Lägen` bottom sheet.

This slice interprets only the first mockup screen: `Lägesmeny`.

## Goal

Create the shared small-screen shell pattern that every workspace-specific
small-screen story can build on:

- phone shows one active mode affordance and one `Lägen` affordance in the
  planner shell
- `Lägen` opens a bottom sheet for all planner modes
- the sheet lists every mode with a canonical icon, label, concise subtitle,
  enabled/disabled state, and current-mode marker
- selecting a mode reuses the existing `update:modeValue` path and save/route
  guards instead of adding a second navigation model
- desktop/laptop keep the existing workspace segmented selector

## Non-goals

- No redesign of `Översikt`, `Grupper`, `Sittplatser`, or `Regler` bodies.
- No changes to draft persistence, smart rules, export/share behavior, route
  guards, save guards, or workspace-loading semantics.
- No new global design-system primitive unless the local mode sheet cannot
  cleanly reuse the current drawer/dialog/bottom-sheet conventions.
- No JavaScript-owned breakpoint or persistent layout geometry.
- No attempt to make phone feature-parity match the full desktop composition.

## Mockup Interpretation

Use the `Lägesmeny` phone panel in
`docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`
as qualitative product direction:

- the top mode row should read as two clear controls: active workspace on the
  left, `Lägen` on the right
- the active mode affordance should be visually stronger than `Lägen`, but
  should still feel like a dense workspace control rather than a page CTA
- the old four-part segmented selector must not render on phone
- the sheet title is a short action label such as `Byt läge`
- rows are mode choices, not explanatory cards
- each row carries an icon, the teacher-facing mode name, one short supporting
  phrase, and current-mode state
- the selected/current row should be immediately visible without needing a
  separate helper paragraph
- the sheet may include a touch handle and safe-area padding if it follows the
  existing mobile sheet language

This is not a pixel contract. It is a hierarchy contract: active mode stays
near the shell, all modes are reachable, and the mode chooser is subordinate to
the live workspace.

## Frontend And Design Authorities

- `agent-docs-governance`: docs-as-code authority; no production work without
  this governed PR slice.
- `integrated-frontend-stack`: Vue 3/Vite/TypeScript stack, token-driven
  styling, CSS-owned layout geometry, dense workspace verification.
- `brutalist-academic-ui`: brutalist academic doctrine; dense workspace
  surfaces are instruments, not card stacks.
- `.codex/rules/045-huleedu-design-system.md`: token-first styling, no Tailwind
  default palette leakage, dense workspace exception for theatrical button
  motion, shared dense-control sizing/radius ownership.
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`:
  one stable shell, canvas/work-surface first, compact action rows, desktop
  as source composition, mobile as deliberate reduced companion.
- `docs/mockups/st-29-small-screen-workspace-redesign/README.md`: approved
  mockup bundle and submission policy for this lane.

## Current Frontend Entry Points

- Shared top shell:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- Authenticated planner shell consumer:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Guest/public planner shell consumer:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- Existing desktop selector primitive:
  `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`
- Existing mobile bottom-sheet reference:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerShareLinksPanel.vue`
- Existing icon vocabulary:
  `frontend/apps/skriptoteket/src/components/icons/`

## Implementation Plan

1. Add a small-screen mode-switcher path to `PlannerTopPanel.vue` while keeping
   the current `UiSegmentedToggle` as the desktop/laptop workspace selector.
2. Keep the existing `workspaceOptions` computation as the single source of
   mode labels, disabled states, data-test hooks, and selected mode.
3. Introduce a local mode-sheet component only if it keeps `PlannerTopPanel.vue`
   under the repo's SRP/file-size expectations; otherwise keep the surface
   thin and extract immediately.
4. Use CSS breakpoints to choose between desktop segmented selector and phone
   active-mode-plus-`Lägen` controls.
5. Reuse local dense controls and icon components where they fit. If a control
   must be new, keep it local to the planner shell until `ST-29-11` or a later
   primitive task promotes it.
6. Model the phone sheet on the existing `PlannerShareLinksPanel` mobile
   bottom-sheet behavior: backdrop, fixed bottom surface, safe-area padding,
   dialog semantics, and close affordance.
7. Wire mode selection through the existing `update:modeValue` emit so
   `PlannerWorkspaceShell.vue` and `ClassroomPlannerGuestWorkspaceShell.vue`
   keep their current save guards, route flow, disabled-reason handling, and
   help-context sync.
8. Add focused component tests for the phone shell and mode sheet, including
   no four-option rail at phone width, sheet row contents, current state,
   disabled reasons, mode selection, close behavior, and focus/keyboard basics.
9. Add browser proof for `phone`, `tablet`, `laptop`, and `desktop` using the
   `EPIC-29` viewport names. The phone proof must include closed and open sheet
   screenshots compared qualitatively against the mockup.
10. Update `ST-29-13`, this PR task, and `.codex/handoff.md` with exact proof
    commands and artifact paths during implementation closeout.

## Test Plan

- `pdm run fe-test -- --run PlannerTopPanel PlannerWorkspaceShell ClassroomPlannerGuestWorkspaceShell`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof at:
  - `phone`: `390x844`, closed shell and open `Lägen` sheet
  - `tablet`: `768x1024`, reduced companion behavior without desktop bleed
  - `laptop`: `1366x768`, existing desktop selector still present
  - `desktop`: `1440x900`, existing desktop selector still present

## Implementation Closeout

Implemented and verified on 2026-05-04 as the shared small-screen shell slice.

Key outcomes:

- Phone/tablet render a compact active-mode control plus `Lägen`; the four-way
  segmented selector is retained only at full desktop composition widths.
- `Lägen` opens a bottom sheet with icon-supported rows for `Översikt`,
  `Grupper`, `Sittplatser`, and `Regler`, including current-state and
  disabled-state handling through the existing mode update path.
- The shell uses Hule design tokens rather than mockup-specific colors or
  Tailwind default palette classes.

Verification:

- `pdm run fe-test -- --run PlannerTopPanel PlannerClassWorkspace PlannerGroupingWorkspacePane PlannerSeatingWorkspacePane PlannerRulesWorkspacePane RoomCanvas PlannerShareExportPanel`
- Signed local HuleEdu browser proof:
  `st-29-small-screen-remaining-proof: ok artifacts=.artifacts/st-29-small-screen-remaining-workspaces`

## Rollback Plan

Revert the planner top-panel small-screen branch and any local mode-sheet
component while leaving the existing `UiSegmentedToggle` desktop selector and
workspace mode selection events intact. Rollback should restore the previous
single segmented selector without touching planner state, draft persistence,
or workspace routing.
