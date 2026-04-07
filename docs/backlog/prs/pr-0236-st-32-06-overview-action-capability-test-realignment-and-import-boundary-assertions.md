---
type: pr
id: PR-0236
title: "ST-32-06 follow-up: overview action-capability test realignment and import-boundary assertions"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-06"
  - "ST-26-02"
tags:
  ["frontend", "klassrumskartan", "overview", "public-access", "import", "tests"]
dependencies:
  - "PR-0223"
  - "PR-0137"
  - "PR-0175"
acceptance_criteria:
  - "Given the shared overview panels now support public capability gating, when an isolated unit test expects the action footer to be visible, then the fixture passes `showActions: true` explicitly instead of relying on absent-boolean behavior."
  - "Given class-list import remains scoped to the create/edit workflow, when the roster overview panel renders with actions visible, then the assertions still prove there is no separate overview-level `Importera från fil` button."
  - "Given public or other constrained shells may hide overview actions, when `showActions` is false, then focused coverage proves the shared panel omits the footer without implying a product regression."
---

## Problem

`pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts`
fails because the spec mounts
[PlannerRosterOverviewPanel.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue)
without `showActions`, yet still expects the action footer to render.

That expectation became stale when `PR-0223` added overview capability gating:

- [PlannerClassWorkspace.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue)
  now passes `:show-actions="overviewCapabilities?.show_roster_actions !== false"`.
- The shared panel intentionally supports hidden action footers for the public
  guest overview and other constrained shells.

The product contract that class-list import belongs inside the shared
create/edit workflow remains unchanged:

- [PR-0137](pr-0137-klassrumskartan-class-list-import-remediation-example-corpus-and-overview-reconciliation.md)
  moved import into the `Ny klasslista` / `Redigera` workflow.
- [PR-0175](pr-0175-klassrumskartan-class-list-import-dropzone-in-create-edit-modal.md)
  kept the drag/drop import affordance inside that same modal.

This failure is therefore assessed as a stale isolated spec, not a user-facing
regression.

## Goal

Realign the focused roster-overview tests to the explicit capability contract
without reopening the settled import boundary.

## Non-goals

- No product change that moves roster import back onto the overview surface.
- No broad rewrite of overview capability wiring.
- No unrelated UI copy or layout adjustments in the overview panels.

## Implementation plan

1. Keep the capability-gated footer as the shared overview contract.
2. Update the isolated roster-overview spec to pass `showActions: true` when
   asserting visible buttons.
3. Add or refresh a negative assertion proving the action footer disappears
   when `showActions` is false.
4. Keep the import-boundary assertion explicit: visible overview actions still
   must not introduce a separate `Importera från fil` button.
5. Re-run the shared overview-shell coverage so the parent capability contract
   and the isolated panel contract stay aligned.

## Implementation summary (2026-04-07)

- Updated
  [PlannerRosterOverviewPanel.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.spec.ts)
  so the visible-footer assertion passes `showActions: true` explicitly instead
  of relying on the absent-boolean case.
- Added focused negative coverage that proves the shared roster overview panel
  hides its action footer when `showActions` is false.
- Kept the settled import boundary unchanged: the visible overview panel still
  does not expose a separate `Importera från fil` button because import remains
  inside the create/edit roster workflow.

## Test plan

- Current assessment proof:
  - `pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts`
- Required remediation proof:
  - `pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run docs-validate`

## Verification summary (2026-04-07)

- `pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
  (pass)
- `pdm run fe-type-check` (pass)
- `pdm run fe-test` (pass; 145 files, 753 tests)
- `pdm run docs-validate` (pass)

## Rollback plan

- Revert only the stale test realignment if it accidentally changes the
  settled overview/import product contract.
- Do not move import out of the create/edit modal or remove the public
  capability-gating surface as part of this follow-up.
