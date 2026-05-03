---
type: pr
id: PR-0281
title: "ST-29-11 toolbar processing spinner and status-pill removal"
status: in_progress
owners: "agents"
created: 2026-05-03
updated: 2026-05-03
stories:
  - "ST-29-11"
  - "ST-26-06"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "toolbar", "sharing"]
dependencies:
  - "PR-0157"
  - "PR-0275"
acceptance_criteria:
  - "Given the teacher starts `Exportera` from the grouping or seating toolbar, when the export is processing, then the toolbar keeps `Dela` and `Exportera` in stable positions and shows progress through an inline spinner inside the existing export control rather than a pop-in status pill."
  - "Given the teacher opens `Dela` and clicks `Skapa länk`, when share creation is processing, then the existing create button shows a spinner while preserving its width and no toolbar-level status pill appears."
  - "Given the teacher revokes an active shared link, when revoke processing is in flight, then the existing revoke button shows an inline spinner while preserving the active-link row geometry."
  - "Given export/share/revoke failures occur, when the operation settles, then error feedback remains attached to the existing local share/export feedback surfaces without adding processing-only toolbar siblings."
  - "Given dense controls need a reusable loading affordance, when this slice ships, then the spinner lives in the shared dense primitive layer rather than as repeated ad hoc `animate-spin` spans in planner toolbar components."
  - "Given the grouping and seating toolbar specs run, when busy and error states are asserted, then tests prove no `*-export-status-pill` is rendered and existing action controls remain available or disabled according to the operation state."
---

## Problem

Klassrumskartan currently renders `UiDenseStatusPill` as a new sibling in the
grouping and seating toolbar secondary zone when export or share work is busy
or fails. That dynamic sibling changes the measured toolbar width and pushes
the `Dela` / `Exportera` controls left during processing.

The current behavior breaks the desktop-first workspace stability contract:
processing feedback becomes a layout event instead of a local state change on
the action that initiated it.

## Goal

Replace processing-only toolbar status pills with inline spinner affordances in
the existing dense controls:

- `Exportera` shows busy state inside the split button.
- `Skapa länk` shows busy state inside the create-link button.
- `Återkalla` shows busy state inside the revoke button.

Keep share/export service contracts untouched. This is a primitive and
composition fix, not a share-artifact or export-flow change.

## Non-goals

- No backend, API, share-artifact, revocation, preview, or export job contract
  changes.
- No redesign of the share management popover/bottom sheet.
- No new persistent status band or helper text.
- No runtime geometry measurement or breakpoint logic.
- No broad replacement of existing non-planner loading indicators outside the
  dense primitive path.

## Implementation plan

1. Add a shared dense spinner primitive in
   `frontend/apps/skriptoteket/src/components/ui/` using the existing
   `lucide-vue-next` icon package and token-owned sizing.
2. Extend `UiDenseActionButton` and `UiDenseSplitButton` so busy actions can
   show an inline spinner without changing outer control geometry.
3. Remove toolbar-level `UiDenseStatusPill` rendering from
   `PlannerGroupingWorkspaceToolbar.vue` and
   `PlannerSeatingWorkspaceToolbar.vue`.
4. Keep error strings available through existing local feedback surfaces, but
   do not render a processing-only toolbar sibling.
5. Update `PlannerShareLinksPanel.vue` so `Skapa länk` and row-level
   `Återkalla` use the shared spinner in-place.
6. Update focused component tests for grouping, seating, export action group,
   and share-link management.

## Test plan

- `pdm run fe-test -- --run PlannerExportActionGroup PlannerShareLinksPanel PlannerGroupingWorkspacePane.export PlannerSeatingWorkspacePane.export`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the previous toolbar status-pill rendering and remove the dense spinner
primitive additions. Share/export service behavior remains unchanged.
