---
type: pr
id: PR-0303
title: "ST-26-06 public guest overview share/export state wiring"
status: done
owners: "agents"
created: 2026-05-06
updated: 2026-05-06
stories:
  - "ST-26-06"
  - "ST-29-11"
tags: ["frontend", "klassrumskartan", "public-guest", "share-export"]
acceptance_criteria:
  - "Given a public guest has selected a class list and optional classroom in the Klassrumskartan overview, when they open `Dela och exportera`, then the selected scope prepares the matching browser-owned grouping or seating draft before export/share instead of using stale or missing planner state."
  - "Given a public guest created a grouping or seating link inside the workspace, when they return to the class overview and inspect the matching `Dela och exportera` scope, then the active browser-owned link row is visible with copy and revoke controls."
  - "Given a public guest creates a link from the overview `Dela och exportera` panel, when the helper call succeeds, then the created link appears immediately in the overview link section and uses the same browser-held revoke/supersede metadata as workspace-created links."
  - "Given the public guest overview is mounted before an active draft is loaded, when the relevant draft or snapshot becomes available later, then browser-owned share metadata hydrates for the matching draft kind without requiring a page reload or workspace detour."
  - "Given public guest share/export remediation is implemented, when tests inspect the route and API boundaries, then the fix does not add owner-scoped guest listing APIs, public dashboards, cross-browser sync, authenticated fallback, or automatic guest-share migration."
---

## Problem

The public Klassrumskartan overview renders the shared `PlannerClassWorkspace`
and therefore shows the overview `Dela och exportera` panel, but
`ClassroomPlannerGuestOverviewView.vue` only wires class-list, classroom, and
workspace-entry events. It does not pass the public share/export flow state into
the overview panel and does not handle overview share/export events.

The authenticated app already wires the same component through
`prepareOverviewDistributionScope`, share/export flow state, and copy/revoke
handlers. Public guest mode only passes those flows to
`ClassroomPlannerGuestWorkspaceShell`, so workspace-created links stay invisible
from the overview-created-links section and overview-triggered share/export
actions cannot reliably prepare the selected browser-owned draft.

There is also a late-hydration gap in `classroomPlannerPublicShareFlow.ts`:
browser-owned latest-share metadata is hydrated only once at flow construction
and bails out unless an active draft is already loaded. Overview-first public
sessions can therefore miss the browser-held current link even when localStorage
contains the expected metadata.

## Goal

Make the public guest overview `Dela och exportera` surface operationally match
the authenticated overview for the existing public guest contract:

- prepare the selected browser-owned grouping or seating draft before overview
  share/export actions
- pass public grouping/seating share and export state into `PlannerClassWorkspace`
- route overview create/copy/revoke/export events to the existing public guest
  flow composables
- hydrate browser-owned current-link metadata when the relevant draft/snapshot
  becomes available after mount

## Non-goals

- No backend share-artifact model changes.
- No account-style guest share dashboard or list-all API.
- No public share discovery, cross-browser sync, or organization matching.
- No automatic migration of public guest shares into authenticated accounts.
- No redesign of the `Dela och exportera` rail, typography, or dense-control
  primitives beyond what is necessary to wire the current behavior.
- No change to immutable public token read routes, TTL ceilings, revoke-secret
  authority, or renderer provenance semantics.

## Implementation plan

1. Add a public guest overview distribution preparation path in
   `useClassroomPlannerGuestController.ts` or a small extracted helper.
   - Accept `grouping` or `seating`.
   - Use the selected roster/template from the public overview.
   - Resolve or load the browser-owned draft through `guestPlannerState`.
   - Persist enough snapshot/UI state for export/share to operate on the
     selected scope without forcing the user visibly into the workspace.
   - Preserve the current class-workspace screen unless the user explicitly
     navigates into a workspace.
2. Wire `ClassroomPlannerGuestOverviewView.vue` to pass public share/export flow
   props into `PlannerClassWorkspace`.
   - Mirror the authenticated prop/event shape where possible.
   - Route overview grouping events to `groupingExportFlow` and
     `groupingShareFlow`.
   - Route overview seating events to `seatingExportFlow` and
     `seatingShareFlow`.
3. Harden `classroomPlannerPublicShareFlow.ts` so browser-owned latest-share
   metadata hydrates after the relevant draft/snapshot becomes available.
   - Keep hydration scoped by snapshot plus draft kind.
   - Do not add server-side discovery.
   - Avoid duplicate visible rows when a share was already created in the same
     flow instance.
4. Add focused frontend tests covering:
   - public overview event wiring for grouping and seating share/export
   - overview-created link row appearing immediately after successful share
   - workspace-created link row visible after returning to overview
   - late hydration when the flow is constructed before an active draft exists
   - no authenticated API/client fallback in public share/export calls
5. Add or extend a retained browser proof if the implementation changes visible
   public overview behavior.
   - Exercise `/public/apps/classroom.group-seating-studio`.
   - Create or load a guest roster and classroom.
   - Create a workspace share link, return to overview, and assert the created
     link row appears under the matching scope.
   - Create an overview share link and assert copy/revoke controls are present.

## Test plan

- `pdm run fe-test -- --run ClassroomPlannerGuestOverviewView classroomPlannerPublicShareFlow usePublicGroupingShareFlow usePublicSeatingShareFlow PlannerClassWorkspace PlannerShareExportPanel`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `git diff --check`

Run live browser proof for the public route if the implementation touches the
rendered overview panel or public share/export controls.

## Implementation summary

Implemented on 2026-05-06.

- `ClassroomPlannerGuestOverviewView.vue` now passes public guest share/export
  flow state into `PlannerClassWorkspace` and routes overview grouping/seating
  share, copy, revoke, and export events through the existing public flow
  composables.
- `useClassroomPlannerGuestController.ts` now exposes
  `prepareOverviewDistributionScope`, resolving the selected browser-owned
  grouping/seating draft while preserving the overview screen before
  share/export.
- Guest draft autosave now preserves the current snapshot screen so overview
  share/export preparation does not bounce the public user back into the
  workspace.
- Public share metadata hydration now watches for the relevant draft to appear
  after mount, closing the overview-first late-hydration gap.
- `PlannerOverviewDistributionPanel` now keeps a workspace-created grouping
  link or grouping-only draft as the default overview scope, so the created link
  row remains visible after returning from the workspace.
- Added retained public-route proof
  `scripts/playwright_pr_0303_public_guest_overview_distribution.py`.

## Verification

- `pdm run fe-test -- src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/classroomPlannerPublicShareFlow.spec.ts src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts`
- `pdm run python -m scripts.playwright_pr_0303_public_guest_overview_distribution --start-vite`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the public overview wiring and share-flow hydration changes together.
The existing workspace-level public share/export behavior should remain the
fallback. If the overview preparation path risks widening the public guest
contract, hide or disable overview share/export actions in public guest mode
until a narrower follow-up is approved.
