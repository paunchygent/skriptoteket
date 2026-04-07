---
type: review
id: REV-PR-0226
title: "Review: PR-0226 shared planner shell parity and grouping viewport-height stabilization"
status: approved
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
reviewer: "lead-developer"
prs:
  - PR-0226
links:
  - EPIC-29
  - ST-29-11
---

## TL;DR

`PR-0226` is an approved bounded `ST-29-11` hardening slice. It freezes one shared planner-shell
parity contract across guest and authenticated mode, plus one explicit grouping-height contract that
keeps the grouping board and student-pool lanes stable at desktop/laptop widths.

## Problem Statement

Guest and authenticated planner shells had started to drift by wrapper, especially around sticky
toolbar behavior. Grouping also still collapsed vertically when only a few groups existed, making
the workspace feel more content-driven and more cramped than seating.

## Proposed Solution

Treat the issue as shared shell/parity hardening, not a reopened workspace redesign. Freeze the
sticky toolbar as one shared viewport-relative contract, freeze the grouping board lane and
student-pool lane at `480px`, freeze taller group-bucket floors, and require focused proof for
those values.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md` | Slice scope and frozen decisions | 5 min |
| `docs/backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md` | Parent story scope | 4 min |
| `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md` | Epic boundary | 3 min |

**Total estimated time:** ~12 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `PR-0226` under `ST-29-11` | This is shared primitive/parity hardening, not a layout redesign restart | [x] |
| Freeze one shared sticky toolbar contract | Guest/auth shells should not diverge by wrapper | [x] |
| Freeze grouping lane floors at `480px` | Grouping should match the current seating baseline and stop collapsing to content | [x] |
| Freeze group-card floors at `56px` / `112px` | Bucket sizing must be explicit and reviewable | [x] |
| Require focused proof beyond screenshots | The contract should be testable at component/spec level | [x] |

## Review Checklist

- [x] Scope stays inside `ST-29-11`
- [x] Sticky toolbar behavior is defined as one shared shell contract
- [x] Grouping-height stabilization is bounded and reviewable
- [x] Group-bucket floors are explicit and testable
- [x] The slice is approved as the next implementation follow-up

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-06`
**Verdict:** `approved`

### Required Review Outputs

1. Confirm the slice really belongs under `ST-29-11` shared primitive/parity tightening rather
   than reopening core workspace redesign scope.
2. Confirm sticky toolbar behavior is specified as one shared viewport-relative shell contract,
   not as a guest-only patch or a page-height/wrapper-dependent offset.
3. Confirm the grouping-height stabilization contract is bounded and reviewable:
   - grouping board lane floor is explicitly frozen at `480px`
   - unassigned-student pool floor is explicitly frozen at `480px`
   - both floors are tied to the current seating `RoomCanvas` viewport baseline
   - no content-count collapse is allowed when only a few groups exist
4. Confirm the proposed taller group buckets are frozen as explicit `56px` assigned-row floors
   and `112px` empty drop-target floors, and that the proof plan requires direct component/spec
   assertions for those values instead of shell-only or screenshot-only evidence.
5. Approve or reject whether `PR-0226` may proceed as the next implementation slice.

### Review Resolution

The previously requested review tightening is resolved. `PR-0226` now freezes the shared `480px`
grouping-floor contract, the `56px` / `112px` group-card floors, and the fresh grouping-draft seed
count at `4`, with focused component/spec and draft-lifecycle proof added before implementation
close-out.

### Suggestions (Optional)

- Keep the current shared-shell framing. The guest/authenticated sticky-toolbar drift is a valid
  `ST-29-11` follow-up because the bug is still wrapper/parity hardening, not a new workflow
  redesign. The grouping-height portion just needs a tighter review contract so it stays a bounded
  stabilization slice.

### Decision Approvals

- [x] `PR-0226` is the right bounded follow-up slice for the reported guest/authenticated shell
      parity drift.
- [x] The sticky toolbar contract should be shared and viewport-relative across guest and
      authenticated shells.
- [x] Grouping should keep a shared explicit `480px` minimum-height floor for both the board lane
      and student-pool lane instead of shrinking to current content.
- [x] Group cards and empty drop targets should use the explicit `56px` / `112px` minimum-height
      floors and prove them through focused component/spec assertions.
- [x] `PR-0226` may proceed to implementation once this review clears.

### Reviewer Notes

- This follow-up review used to live as a supplemental section inside `REV-EPIC-29`. It is now its
  own retained review record under the target-based review workflow.

## Changes Made

1. `PR-0226` now freezes the grouping-height contract against the current seating baseline:
   `480px` for both the grouping board lane and the unassigned-student pool.
2. `PR-0226` now freezes the taller group-bucket contract as explicit `56px` assigned-row floors
   and `112px` empty drop-target floors instead of the earlier "about 25 percent taller"
   phrasing.
3. `PR-0226` now requires focused component/spec proof through `GroupCard.spec.ts`,
   `GroupBoard.spec.ts`, and `PlannerGroupingWorkspacePane.smart-rules.spec.ts` in addition to the
   guest/authenticated shell parity checks.
4. `PR-0226` now also freezes fresh grouping drafts to `4` default groups in both guest and
   authenticated mode so the parity contract includes blank-draft seeding behavior.
