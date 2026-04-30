---
type: pr
id: PR-0231
title: "ST-32-06: guest Regler workspace, solver-Smart parity, and expandable Smart settings drawer"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-30
stories:
  - "ST-32-06"
tags:
  [
    "frontend",
    "backend",
    "klassrumskartan",
    "public-access",
    "guest-workspace",
    "smart-assignment",
  ]
dependencies:
  - "ADR-0074"
  - "ADR-0079"
  - "ADR-0080"
  - "ST-32-05"
  - "EPIC-27"
  - "EPIC-29"
  - "PR-0223"
acceptance_criteria:
  - "Given guest Klassrumskartan is the same teacher tool rather than a stripped demo, when the public planner shell renders, then `Regler` is available in guest mode as a first-class workspace while its state stays browser-owned."
  - "Given guest opens Smart settings from `Grupper` or `Sittplatser`, when the drawer expands, then it reuses the authenticated expandable Smart-settings shape for guest-valid controls and summaries without exposing or simulating history-based Smart controls such as `Use history`."
  - "Given guest enables `Smart` and runs `Slumpa` in `Grupper` or `Sittplatser`, when the run executes, then grouping and seating both use dedicated public stateless helper routes under `/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run` and `/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run`, return browser-owned results only, and never fall through to authenticated owner-scoped APIs."
  - "Given guest Smart rules are authored or edited in `Regler`, when the browser snapshot is persisted and later upgraded after authentication, then those rules remain browser-owned until upgrade and import with the existing authenticated guest-upgrade flow."
  - "Given new public Smart helper routes are added for guest parity, when they are reviewed, then they publish rate limits, payload caps, time budgets, validation rules, and cookie-agnostic semantics consistent with `ADR-0079`."
---

## Problem

`PR-0223` now cleanly owns the public browser-workspace baseline through
checkpoints 1-3, but the remaining guest Smart gap is still too broad to leave
as one unnamed follow-on.

The unresolved part is not generic “guest polish.” It is one specific parity
lane:

- guest should have the same `Regler` workspace shape as authenticated users
- guest should have the same expandable Smart settings affordance in task
  workspaces
- guest should be able to use real solver-based Smart runs in both workspaces
- guest should not inherit history-based Smart behavior

Without freezing and implementing that as its own slice, guest mode either
stays artificially weaker than the agreed product shape or drifts back toward
owner-scoped authenticated Smart APIs.

## Goal

Ship the guest Smart-parity slice for Klassrumskartan:

- enable `Regler` in guest mode
- restore the expandable Smart settings drawer shape in guest `Grupper` and
  `Sittplatser`
- keep rule authoring browser-owned and routed through the shared `Regler`
  workspace
- add real solver-based guest Smart runs for both workspaces through explicit
  public helper seams
- keep history-based Smart out of guest mode

## Non-goals

- Guest direct-download export and export-triggered checkpoint capture
- Guest local undo/redo parity and shared shortcut parity follow-through
- Vault / My Files, resumable export jobs, or authenticated recovery/history
  surfaces
- Changing the authenticated `Regler` or Smart-assignment product model from
  `ADR-0074`
- Turning the guest controller into a dual-mode wrapper around authenticated
  route-shell orchestration

## Implementation plan

1. Expand guest workspace routing to include `Regler`.
   - Broaden the guest controller and guest shell mode handling beyond
     `"groups" | "seats"`.
   - Re-enable `show_rules_option` in the guest overview/planner surfaces.
   - Reuse the existing shared `PlannerRulesWorkspacePane.vue` presentation
     path rather than creating a guest-only rules UI.

2. Restore guest Smart settings drawer parity.
   - Re-enable the expandable Smart settings affordance in guest grouping and
     seating toolbars.
   - Keep the drawer aligned with the authenticated structure for guest-valid
     controls and summaries.
   - Route rule authoring into `Regler`; do not create inline guest-only rule
     editors inside task panes.

3. Freeze the guest/account Smart control split from `ADR-0080`.
   - Keep solver-based Smart controls in guest mode.
   - Remove or honestly block history-based Smart controls in guest mode,
     especially `Use history`.
   - Ensure guest Smart settings do not imply authenticated history parity.

4. Add explicit public Smart helper transport.
   - Introduce guest-capable public helper routes at:
     - `/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run`
     - `/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run`
   - Keep those seams cookie-agnostic and non-ambient per `ADR-0079`.
   - Publish the abuse-control contract for both routes:
     - rate limits
     - payload caps
     - request time budgets
     - validation rules
   - Do not fall back to authenticated `/api/v1/apps/.../smart-run` routes.

5. Wire guest `Slumpa` onto the public solver lane.
   - `Smart` off stays local random behavior.
   - `Smart` on uses the explicit public solver seam for both `Grupper` and
     `Sittplatser`.
   - Accepted results persist only into the browser-owned guest snapshot.

6. Keep upgrade semantics unchanged.
   - Guest-authored smart rules and accepted Smart-run results remain
     browser-owned until the first authenticated Klassrumskartan visit offers
     import/discard/postpone through the existing upgrade flow.

## Test plan

- `pdm run fe-test` targeted at:
  - `src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
  - `src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
  - guest controller/state specs covering rules-mode routing and Smart control
    visibility
  - shared planner shell/rules pane specs touched by guest parity
- backend and web unit tests for:
  - the new public grouping Smart route
  - the new public seating Smart route
  - cookie-agnostic public semantics
  - validation failures
  - rate limits, payload caps, and request time budgets
- `pdm run fe-type-check`
- `pdm run docs-validate`
- focused public-route browser proof showing:
  - guest can open `Regler`
  - guest can open the expandable Smart settings drawer from `Grupper` and
    `Sittplatser`
  - guest Smart-on grouping runs succeed through the public helper namespace
  - guest Smart-on seating runs succeed through the public helper namespace
  - guest `Use history` is absent or honestly blocked
  - no owner-scoped authenticated Smart API calls occur

## Rollback plan

- Re-hide guest `Regler` and guest Smart settings affordances if the slice
  introduces an authenticated API leak or an unusable public Smart path.
- Keep authenticated Smart behavior untouched; rollback only the guest/public
  routing and helper wiring if needed.

## Review gate

- Retained review gate:
  [REV-PR-0231](../reviews/review-pr-0231-guest-smart-parity-and-local-continuity-boundary.md)

## Status Reconciliation (2026-04-30)

This PR is now marked `done`. `ST-32-06` and
`ref-development-changelog.md` already record that guest `Regler`, public
Smart grouping/seating helpers, guest Smart drawer parity, and the account-only
history split shipped through this slice. The retained `REV-PR-0231` review is
approved.
