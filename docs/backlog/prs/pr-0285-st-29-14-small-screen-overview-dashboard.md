---
type: pr
id: PR-0285
title: "ST-29-14 small-screen overview dashboard"
status: ready
owners: "agents"
created: 2026-05-03
updated: 2026-05-04
stories:
  - "ST-29-14"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "small-screen"]
dependencies:
  - "PR-0284"
  - "PR-0286"
acceptance_criteria:
  - "Given `PR-0284` has introduced the phone mode shell, when the teacher opens `Översikt` at the `EPIC-29` phone viewport, then the overview body renders as a reduced dashboard instead of stacking the desktop roster and classroom management panels unchanged."
  - "Given a class is selected, when the phone overview renders, then class name, student count, saved state, and a compact student preview are visible before secondary management actions."
  - "Given a classroom is selected, when the phone overview renders, then classroom name and place count are visible as a compact context row or section without forcing the full desktop room preview to dominate the screen."
  - "Given no class or no classroom exists, when the phone overview renders, then the locked `ST-29-10` prerequisite copy and disabled mode reasons remain truthful without adding extra explanatory panels."
  - "Given links or file export actions exist for active grouping or seating work, when the phone overview renders, then the single `Dela` / `Dela och exportera` affordance is reachable as a compact row or action that does not become the primary default surface."
  - "Given tablet, laptop, and desktop review widths render, when this slice ships, then the existing desktop-first overview dashboard remains intact at full-composition widths."
  - "Given visual proof is captured, when the phone overview is compared with the `Översikt` panel in `docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`, then the interpretation preserves the approved hierarchy without requiring pixel-perfect recreation."
---

## Problem

The current `Översikt` is a desktop-first two-panel dashboard: one panel owns
class-list management and one panel owns classroom management. That composition
is useful at laptop and desktop widths, but on phone it becomes two stacked
management panels with large preview areas and too much action chrome before
the teacher can scan the active class state.

This slice interprets only the second mockup screen: `Översikt`.

## Goal

Define and implement the phone overview as a reduced class dashboard:

- keep `PR-0284`'s active-mode plus `Lägen` shell as the entry control
- show the active class as the default anchor
- show class list, classroom context, and the combined `Dela` distribution
  affordance as compact dashboard rows or sections
- keep class/classroom management available but visually subordinate
- preserve existing desktop/laptop overview behavior and data semantics

## Non-goals

- No redesign of the `Lägesmeny`, `Grupper`, `Sittplatser`, or `Regler`
  screens.
- No change to class-list, classroom, draft, export, share, or guest-storage
  contracts.
- No new shared-link persistence, share-artifact lifecycle, export-job, or file
  download behavior.
- No removal of the existing desktop `PlannerRosterOverviewPanel` and
  `PlannerTemplateOverviewPanel` composition at full-composition widths.
- No phone parity promise for every desktop management affordance in the
  default viewport.

## Mockup Interpretation

Use the `Översikt` phone panel in
`docs/mockups/st-29-small-screen-workspace-redesign/small-screen-workspaces-mode-sheet-mockup.png`
as qualitative product direction:

- the selected class card/context remains the first meaningful body surface
  after the phone mode row
- `Klasslista` reads as a compact section with selected-class control and a
  short multi-column name preview, not as a tall management card
- `Klassrum` reads as a compact context section with selected classroom and
  place count, not as a dominant room-canvas preview on phone
- `Dela` is a low-height row/action near the bottom of the dashboard when
  share-link or file-export state exists or can be reached
- opening `Dela` must preserve the merged `Dela och exportera` model from
  `PR-0286`, with link management and PDF/Excel export living under one small
  screen affordance rather than separate `Delade länkar` and file-export rows
- management actions such as create, edit, delete, and switch are present only
  through compact controls, menus, or subordinate rows
- the body should avoid repeated titles, helper paragraphs, and nested cards
  inside the already framed planner shell

This is not a pixel contract. It is a scan-order contract: class first,
classroom second, `Dela` reachable for links and files, management subordinate.

## Frontend And Design Authorities

- `agent-docs-governance`: docs-as-code authority; no production work without
  this governed PR slice.
- `integrated-frontend-stack`: Vue 3/Vite/TypeScript stack, token-driven
  styling, CSS-owned layout geometry, dense workspace verification.
- `brutalist-academic-ui`: brutalist academic doctrine; dense workspace
  surfaces are instruments, not stacked card pages.
- `.codex/rules/045-huleedu-design-system.md`: token-first styling, no Tailwind
  default palette leakage, structure before labels, and dense-workspace chrome
  discipline.
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`:
  one stable shell, secondary means secondary, dead-space discipline, and
  mobile as deliberate reduced companion.
- `docs/backlog/stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md`:
  shipped desktop overview baseline that must not be reopened at laptop or
  desktop widths.
- `docs/backlog/prs/pr-0286-st-29-11-share-export-affordance-consolidation.md`:
  current single `Dela och exportera` affordance that small-screen overview
  must preserve instead of splitting links from file export.
- `docs/mockups/st-29-small-screen-workspace-redesign/README.md`: approved
  mockup bundle and submission policy for this lane.

## Current Frontend Entry Points

- Overview composition shell:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- Class-list overview panel:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue`
- Classroom overview panel:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerTemplateOverviewPanel.vue`
- Overview capability hints:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerOverviewCapabilities.ts`
- Authenticated overview consumer:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- Public guest overview consumer:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestOverviewView.vue`
- Share-flow state currently exposed to live workspaces:
  `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
- Combined share/export panel reference:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerShareExportPanel.vue`
- Prior share-link panel/bottom-sheet reference:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerShareLinksPanel.vue`
- Overview CSS baseline:
  `frontend/apps/skriptoteket/src/assets/main.css`

## Implementation Plan

1. Start from the current `PlannerClassWorkspace.vue` overview shell and keep
   desktop/laptop behavior unchanged.
2. Add a phone-specific overview composition path that activates only below the
   full desktop-composition range established by `EPIC-29`.
3. Keep existing class/classroom selection and modal events as the source of
   truth. The reduced view should rearrange presentation, not fork behavior.
4. Replace the default phone body stack with compact sections for:
   - active class and saved/status context
   - class-list preview and class selector
   - classroom selector plus name/place count
   - compact `Dela` reachability when share or file-export state is available
5. Decide explicitly whether the first implementation can reuse existing
   `PlannerRosterOverviewPanel` / `PlannerTemplateOverviewPanel` through
   responsive variants or whether a thin `PlannerSmallScreenOverviewDashboard`
   component is cleaner under SRP and file-size limits.
6. If `Dela` needs overview-level state that is not currently passed into
   `PlannerClassWorkspace.vue`, extend only the presentation-safe distribution
   summary props/events needed for a compact row. Do not split links and files
   into separate small-screen rows, do not change share/export lifecycle
   semantics, and do not move share creation or file export into a hidden
   overview workflow unless that is explicitly accepted in the implementation
   review.
7. Preserve `ST-29-10` prerequisite copy and disabled mode reasons exactly.
8. Use CSS-owned layout and token-driven styles. Do not add measured viewport
   sizing, JS breakpoint duplication, or Tailwind default palette colors.
9. Add focused component tests for phone overview scan order, reduced class and
   classroom sections, no unchanged desktop panel stack at phone width,
   prerequisite states, and desktop preservation.
10. Add live browser proof for `phone`, `tablet`, `laptop`, and `desktop`.
    Phone proof must include a screenshot compared qualitatively against the
    mockup's `Översikt` panel.
11. Update `ST-29-14`, this PR task, and `.codex/handoff.md` with exact proof
    commands and artifact paths during implementation closeout.

## Test Plan

- `pdm run fe-test -- --run PlannerClassWorkspace PlannerRosterOverviewPanel PlannerTemplateOverviewPanel PlannerShareExportPanel`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof at:
  - `phone`: `390x844`, `Översikt` closed mode shell and reduced dashboard body
  - `tablet`: `768x1024`, reduced companion behavior without desktop bleed
  - `laptop`: `1366x768`, existing desktop overview dashboard still present
  - `desktop`: `1440x900`, existing desktop overview dashboard still present

## Rollback Plan

Revert the phone-specific overview composition and any overview-level `Dela`
presentation props/events while leaving the existing desktop overview panels,
class/classroom CRUD flows, route shell, guest overview, share lifecycle, and
export lifecycle semantics intact.
