---
type: review
id: REV-PR-0228
title: "Review: PR-0228 planner workspace shell, breakpoint, and overflow contract"
status: approved
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
reviewer: "lead-developer"
prs:
  - PR-0228
links:
  - EPIC-29
  - ST-29-03
  - ST-29-05
  - ST-29-11
---

## TL;DR

`PR-0228` closes on a materially better baseline than the earlier rejected bounded-pane approach.
The current implementation is back on a CSS-owned page/workspace scroll model, the retained docs
now match that contract, and the close-out proof boundary is explicit: authenticated real-data live
proof plus focused shared-shell guest/auth parity specs.

## Problem Statement

The planner shell regression lane needed fresh review against the actual shell, breakpoint, and
overflow owners across grouping and seating, not just another “sticky rail” patch. Earlier
measured-pane approaches had already shown that brittle geometry math could make the workspace
contract look stronger in theory than it behaved in practice.

## Proposed Solution

Review `PR-0228` as one structural shell contract:

- stable chrome above the workspace
- one bounded page/workspace scroll path
- a stable student-pool rail with fixed header and scrolling list body
- shared guest/authenticated shell expectations
- explicit breakpoint behavior at `1279x900`, `1366x768`, and `1440x900`

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md` | Current intended contract and frozen decisions | 5 min |
| `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md` | Canonical shared desktop-composition ownership | 4 min |
| `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md` | Shipped grouping/seating composition expectations | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue` | Planner route shell height/frame ownership | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` | Shared authenticated planner shell | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue` | Guest shell parity | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceModeSurface.vue` | Shared pane shell and current measured-height seam | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts` | Breakpoint and overflow contract tokens | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue` | Grouping lane composition | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue` | Seating lane composition | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue` | Rail header/list scroll behavior | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue` | Board-lane interaction with overflow ownership | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue` | Seating canvas overflow expectations | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts` | Grouping layout regression coverage | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts` | Seating layout regression coverage | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` | Shared shell assertions | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` | Guest shared-shell assertions | 4 min |
| `scripts/playwright_pr_0227_group_board_height_contract_check.py` | Current live proof lane and its blind spots | 5 min |

**Total estimated time:** ~76 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `PR-0228` as a bounded `ST-29-11` follow-up | This is shell hardening, not a workspace-redesign restart | [x] |
| Keep the CSS-owned page/workspace scroll model | The earlier measured bounded-pane seam was the wrong baseline | [x] |
| Close the slice after reconciling the retained review/proof obligations | Better implementation baseline is only enough once the proof boundary is explicit | [x] |
| Treat auth-only real-data proof plus focused guest/auth shell specs as sufficient for closure | The shared shell contract is already exercised in focused guest/auth specs even though the retained live browser lane is auth-only | [x] |
| Mark `PR-0228` done now | The retained review and backlog contract are now aligned to the actual proof surface | [x] |

## Review Checklist

- [x] The review identifies the true height and overflow owners at each planner-shell layer
- [x] The breakpoint contract is explicit for `laptop`, `desktop`, and the failing in-between band
- [x] The recommended fix path favors CSS-owned layout over brittle measured-height seams
- [x] Guest and authenticated shells are evaluated as one claimed contract
- [x] Toolbar overflow behavior is reviewed together with the pane-body rendering
- [x] Final closure proof is strong enough to move the slice to `done`

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-06`
**Verdict:** `approved`

### Mandatory Repomix Package (External Review)

- Package: `.agents/repomix_packages/repomix-pr-0228-workspace-contract-review.xml`
- Template: `code-review`
- Included files: `27`

### Goal Shape To Review Against

At the named `laptop` and `desktop` review widths, Klassrumskartan should behave like a bounded
workspace frame rather than ordinary page content:

1. Page header, planner top panel, and toolbar remain stable chrome above the active workspace.
2. The active workspace body becomes one bounded region that owns the visible grouping/seating work
   area.
3. Inside that region, the student-pool rail is a stable side lane with a fixed visible header and
   a scrolling list body.
4. The active right-hand lane owns the deeper grouping-board or seating-canvas scrolling.
5. The toolbar and workspace body must not disappear, collapse, or change overflow behavior merely
   because the browser crosses a breakpoint or is resized through an intermediate width band.
6. Smaller breakpoints may intentionally diverge from the desktop-heavy workspace model, but the
   cutover must be explicit and stable rather than accidental or shell-fragile.

### Review Resolution

`PR-0228` is now ready to close.

The previously rejected runtime pane-height seam is now gone from the shared shell path:
`PlannerWorkspaceModeSurface.vue` is back to a thin shared wrapper, planner geometry is named in
`plannerWorkspaceLayout.ts` and authored in shared CSS primitives, and the retained Playwright lane
now proves the authenticated real-data shell at `1279x900`, `1366x768`, and `1440x900` using
`SA24D` / `G20`.

The final close-out decision is now explicit and internally consistent across the docs/review
trail:

- `PR-0228` now documents the corrected page/workspace scroll implementation rather than carrying
  forward language from the rejected bounded-pane/right-lane-scroll model.
- The retained browser proof stays auth-only and real-data-based, which is the strongest live
  proof lane for this bounded slice.
- Guest/auth parity remains part of the contract, but it is now carried explicitly by the shared
  shell implementation and the focused guest/auth shell specs rather than by a second retained live
  browser script.
- `ST-29-11` and `EPIC-29` can now acknowledge this slice as closed while keeping later planner
  follow-ons scoped to their own contracts.

### Structural Fault Lines

1. Earlier versions of `PR-0228` carried forward parts of the rejected bounded-pane/right-lane
   internal-scroll model even after the local implementation moved back to page/workspace scroll
   first. That mismatch has now been removed from the retained PR contract.
2. `scripts/playwright_pr_0227_group_board_height_contract_check.py` now proves the corrected
   authenticated shell on real `SA24D` / `G20` data, including the `1279px` band, and the retained
   close-out decision now treats that as the single live-proof lane for this bounded slice.
3. Guest/auth parity is no longer left implicit in the review text: it is now explicitly grounded
   in the shared shell implementation and the focused guest/auth shell specs instead of an absent
   second live browser script.

### Disproven Assumptions

- The current implementation is **not** still on the rejected runtime-measured pane-shell model.
  The shared shell seam is now CSS-owned again and the page/workspace scroll path is back.
- The remaining blocker was **not** primarily shell geometry authorship anymore. The stronger local
  baseline already existed; the missing piece was an honest close-out decision on the retained
  proof boundary.
- The current retained proof lane is **stronger** than the earlier rejected version because it uses
  real `SA24D` / `G20` data and covers the `1279px` resize band, and it is now matched by an
  explicit docs/review contract instead of an over-broad implied parity-proof claim.

### Fix Directions

1. Keep the corrected CSS-owned page/workspace scroll model as the baseline and align the backlog
   contract to it.
   Pros: preserves the healthier shell implementation already in place and removes stale task/review
   language that still points at the rejected pane model.
   Cons: none remaining for this slice after reconciliation.
2. Close the guest/auth parity decision by grounding live proof and shared-shell specs in different
   but explicit roles.
   Pros: keeps the strongest real-data browser proof lane while avoiding a second retained guest
   script whose main contract is already exercised by shared-shell specs.
   Cons: requires the docs to be precise about what the live proof does and does not claim.
3. Mark `PR-0228` done and move further planner-shell concerns into their own follow-up slices.
   Pros: keeps closure honest without reopening stable shell geometry work.
   Cons: later toolbar/breakpoint work still needs its own review gate under `PR-0229`.

### Decision Approvals

- [x] `PR-0228` remains a valid bounded `ST-29-11` follow-up rather than a full workspace-redesign
      restart.
- [x] The current CSS-owned page/workspace scroll implementation is a healthier baseline than the
      previously rejected bounded-pane model.
- [x] The retained docs/review trail is now aligned enough to mark `PR-0228` done without another
      closure decision.
- [x] The current auth-only real-data proof plus focused guest/auth shell specs are sufficient to
      satisfy the written guest/auth parity expectation for this bounded slice.
- [x] `PR-0228` may move to `done` today.

## Changes Made

1. `PR-0228` explicitly documents the corrected CSS-owned page/workspace scroll baseline and the
   chosen proof boundary for close-out.
2. The retained review now approves the slice on one live-proof lane plus focused guest/auth shell
   specs instead of leaving parity obligations implicit.
3. `ST-29-11`, `EPIC-29`, and `.agents/handoff.md` can now treat `PR-0228` as closed and move the
   remaining planner follow-up work into the separate `PR-0229` lane.
