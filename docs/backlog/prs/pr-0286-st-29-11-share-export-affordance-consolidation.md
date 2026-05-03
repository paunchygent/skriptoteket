---
type: pr
id: PR-0286
title: "ST-29-11 share/export affordance consolidation"
status: done
owners: "agents"
created: 2026-05-03
updated: 2026-05-03
stories:
  - "ST-29-11"
  - "ST-26-06"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "toolbar", "sharing", "export"]
dependencies:
  - "PR-0275"
  - "PR-0281"
acceptance_criteria:
  - "Given the teacher works in `Grupper` or `Sittplatser`, when the toolbar renders, then the separate `Exportera` split affordance is no longer shown beside `Dela`; outward distribution is entered through one stable `Dela` affordance."
  - "Given the teacher opens `Dela`, when the panel renders on desktop or phone, then it is titled `Dela och exportera` and groups link management under `Länk` and file export actions under `Filer`."
  - "Given the teacher is in `Grupper`, when they inspect `Filer`, then `Excel (.xlsx)` remains the default/standard export and `PDF (A4 stående)` remains available without changing the existing export job contracts."
  - "Given the teacher is in `Sittplatser`, when they inspect `Filer`, then `Affisch (A3)` remains the default/standard export while `Affisch (A4)` and `Excel (.xlsx)` remain available without changing the existing export job contracts."
  - "Given share creation, share revocation, or export creation is busy, when the panel and toolbar are inspected, then busy feedback stays inside the initiating control or the combined panel and does not add or remove toolbar siblings that shift the secondary action row."
  - "Given implementation is reviewed, when the frontend code is inspected, then share-link orchestration and export-job orchestration remain separate state machines; only the user-facing action surface is consolidated."
  - "Given visual proof is captured, when the result is compared with `docs/mockups/st-29-11-share-export-affordance/share-export-affordance-mockup.png`, then the hierarchy and single-affordance model match the approved direction without requiring pixel-perfect recreation."
---

## Problem

Klassrumskartan currently exposes two adjacent outward-distribution affordances
in `Grupper` and `Sittplatser`: the split `Exportera` control for file
artifacts and the `Dela` control for share links. That split reflects the
current implementation seams, but it asks the teacher to distinguish between
two delivery channels before they have chosen what they want to send.

The product direction is now clearer: `Dela` should be the stable toolbar entry
for getting the current grouping or seating work out of the workspace. File
exports should remain contractually separate underneath, but their selector
belongs inside the same distribution surface as share-link management.

## Goal

Consolidate the grouping and seating toolbar distribution actions into one
stable `Dela` affordance that opens a `Dela och exportera` panel:

- `Länk` owns create/copy/revoke shared-link management.
- `Filer` owns the active workspace's export choices.
- `Grupper` preserves `Excel (.xlsx)` as standard and `PDF (A4 stående)`.
- `Sittplatser` preserves `Affisch (A3)` as standard, `Affisch (A4)`, and
  `Excel (.xlsx)`.
- Existing share and export flows stay reusable and independently testable.

## Non-goals

- No backend, API, export-job, share-artifact, preview, revocation, or PDF
  renderer contract changes.
- No change to generated file formats, export defaults, download behavior, or
  Vault/Mina filer artifact semantics.
- No change to share-link token, owner, TTL, revoke, public route, or
  noindex/crawler contracts.
- No redesign of public share pages or shared-link PDF download bodies.
- No new global design-system primitive unless local extraction proves the
  pattern is needed beyond this planner surface.
- No JavaScript-owned persistent toolbar geometry or breakpoint sizing.

## Implementation Plan

1. Add a small typed action model for planner distribution actions, for example
   `plannerShareExportActions.ts`, so grouping/seating file-option lists no
   longer import types from a visual export component.
2. Replace the paired toolbar composition in
   `PlannerGroupingWorkspaceToolbar.vue` and `PlannerSeatingWorkspaceToolbar.vue`
   with one combined `PlannerShareExportPanel.vue` surface.
3. Preserve `classroomPlannerExportFlow.ts` and `classroomPlannerShareFlow.ts`
   as separate orchestration seams. The new component emits export and share
   intents back to the existing shell flows instead of merging state machines.
4. Reuse the existing dense action/button/spinner primitives from `PR-0281`.
   The toolbar trigger should stay width-stable while share/export operations
   are busy.
5. Extract panel lifecycle behavior only if needed, for example to
   `useDensePopoverSheet.ts`, rather than overloading `useDenseMenuSurface.ts`
   with dialog/list behavior. The combined surface is a dialog/popover sheet,
   not a `role=\"menu\"` list.
6. Move the current share-link panel body into the combined panel's `Länk`
   section with the same desktop popover and mobile bottom-sheet expectations
   established by `PR-0275`.
7. Add a `Filer` section that renders the active workspace's file actions using
   dense controls, local busy/error feedback, and the same option ordering and
   default semantics as the current split export control.
8. Update data-test selectors deliberately so tests express the new model:
   one `Dela` trigger plus file-action rows inside `Dela och exportera`.
9. Add visual/browser proof against the approved mockup bundle at
   `docs/mockups/st-29-11-share-export-affordance/`.
10. During implementation closeout, update this PR, `ST-29-11`, `ST-26-06`,
    and `.codex/handoff.md` with exact verification commands and artifacts.

## Current Frontend Entry Points

- Toolbar secondary-zone composition:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- Toolbar secondary-zone composition:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- Current export split wrapper:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
- Current share panel:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerShareLinksPanel.vue`
- Shared dense split/action primitives:
  `frontend/apps/skriptoteket/src/components/ui/UiDenseSplitButton.vue`
  and `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue`
- Existing export flow:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts`
- Existing share flow:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerShareFlow.ts`
- Authenticated planner shell passthrough:
  `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Guest/public planner shell passthrough:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
- Live proof script:
  `scripts/playwright_pr_0286_share_export_affordance.py`

## Implementation Summary

Implemented in the frontend action surface only:

- `PlannerShareExportPanel.vue` is the combined `Dela och exportera` dialog /
  popover sheet for both planner modes.
- `plannerShareExportActions.ts` owns the typed file-option model so workspace
  toolbars do not import types from the legacy visual export split component.
- `PlannerGroupingWorkspaceToolbar.vue` and `PlannerSeatingWorkspaceToolbar.vue`
  now render one `Dela` trigger in the secondary action row and pass the
  existing share/export intents into the combined panel.
- `PlannerExportActionGroup.vue` remains as a reusable/legacy split export
  component, but the grouping and seating workspaces no longer compose it
  beside `Dela`.
- `classroomPlannerExportFlow.ts` and `classroomPlannerShareFlow.ts` were not
  changed; export and share orchestration remain separate state machines.

## Verification

- `pdm run fe-test -- --run PlannerShareExportPanel PlannerGroupingWorkspacePane.export PlannerSeatingWorkspacePane.export PlannerWorkspaceShell PlannerExportActionGroup PlannerShareLinksPanel`
  passed: 7 files / 56 tests.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run python -m scripts.playwright_pr_0286_share_export_affordance --start-backend --start-vite`
  passed and wrote screenshots for grouping and seating at `390x844`,
  `1366x768`, and `1440x900` under
  `.artifacts/playwright-pr-0286-share-export-affordance/`.

## Test Plan

- `pdm run fe-test -- --run PlannerShareExportPanel PlannerGroupingWorkspacePane.export PlannerSeatingWorkspacePane.export PlannerWorkspaceShell`
- `pdm run fe-test -- --run PlannerShareLinksPanel PlannerExportActionGroup`
  only if those components remain as extracted/reused units after the refactor.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Live/browser proof at `390x844`, `1366x768`, and `1440x900` covering:
  - `Grupper` toolbar with one `Dela` affordance
  - `Grupper` open `Dela och exportera` panel with `Länk` and `Filer`
  - `Sittplatser` open `Dela och exportera` panel with seating file choices
  - export/share busy state without secondary-row sibling churn

## Rollback Plan

Restore the previous paired toolbar composition:

- `PlannerExportActionGroup` renders as the separate `Exportera` split control.
- `PlannerShareLinksPanel` renders as the separate `Dela` affordance.
- Existing share/export flows and API contracts remain untouched.

Rollback should not require database, API, renderer, or migration changes
because this slice is a frontend action-surface consolidation only.

## References

- Parent primitive story:
  [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Share-link lane:
  [ST-26-06](../stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md)
- Prior share popover/bottom-sheet slice:
  [PR-0275](pr-0275-st-26-06-share-link-popover-and-bottom-sheet-management.md)
- Prior dense busy-feedback slice:
  [PR-0281](pr-0281-st-29-11-toolbar-processing-spinner-and-status-pill-removal.md)
- Approved mockup:
  [ST-29-11 share/export affordance consolidation](../../mockups/st-29-11-share-export-affordance/README.md)
