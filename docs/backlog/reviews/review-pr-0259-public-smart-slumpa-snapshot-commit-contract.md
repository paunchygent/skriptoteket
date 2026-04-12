---
type: review
id: REV-PR-0259
title: "Review: PR-0259 public Smart Slumpa snapshot commit contract"
status: approved
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
reviewer: "lead-developer"
prs:
  - PR-0259
links:
  - EPIC-32
  - ST-32-06
  - PR-0231
  - PR-0232
  - PR-0234
  - ADR-0079
  - ADR-0080
---

## TL;DR

`PR-0259` is approved as the right corrective follow-up for the public
Klassrumskartan warnings `Varning: Draft revision mismatch. Expected 3, got 2.`
and `Varning: Draft revision mismatch. Expected 2, got 1.` The fix must keep
the backend conflict guard strict, make public Smart `Slumpa` commit both the
pre-run visible workspace and the accepted solver workspace directly to the
browser-owned guest snapshot before success is surfaced, and stop leaking raw
revision-conflict diagnostics into teacher-facing toasts.

## Problem Statement

Public guest Smart seating and grouping can currently apply a solver result in
memory while failing to write that accepted workspace into the guest snapshot.
The next Smart `Slumpa` sends a newer `expected_revision` with an older
snapshot draft revision, so the backend returns `409 CONFLICT`.

The review needs to decide whether the proposed direct guest snapshot commit
contract is the correct boundary, or whether the fix should instead adjust the
autosave lane. The decision matters because guest mode is browser-owned by
design; hiding the mismatch by weakening backend validation would preserve a
state-loss bug.

The review also covers the feedback bug: `Draft revision mismatch...` is
internal diagnostic text. It should remain visible to tests/logs, but not to
teachers as a warning toast.

## Proposed Solution

Approve a small frontend-led PR slice that:

- commits current visible guest workspace state directly to the browser
  snapshot before public Smart helper calls
- derives `expected_revision` from that committed snapshot
- commits accepted public Smart helper results directly to the browser snapshot
  before applying success state
- applies the same contract to public Smart grouping and seating
- preserves strict backend revision mismatch checks
- maps public Smart revision-conflict feedback to teacher-facing recovery copy
- leaves Smart-off local random `Slumpa` behavior unchanged

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0259-st-32-06-public-smart-slumpa-accepted-workspace-snapshot-commit-contract.md` | Scope, acceptance criteria, and proof obligations | 12 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftSession.ts` | Current failing orchestration and planned commit injection point | 8 min |
| `frontend/apps/skriptoteket/src/views/apps/usePublicSmartSeatingRun.ts` | Seating public Smart flow and success/rollback behavior | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/usePublicSmartGroupingRun.ts` | Grouping parity and shared risk surface | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/useDraftPersistenceLane.ts` | Busy-gated autosave behavior and direct-commit acknowledgement needs | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftWorkspace.ts` | Existing guest snapshot mutation seam to reuse | 6 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_smart_seating.py` | Backend revision guard that should remain intact | 4 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_smart_grouping.py` | Grouping revision guard parity | 4 min |
| `docs/backlog/reviews/review-pr-0231-guest-smart-parity-and-local-continuity-boundary.md` | Prior approved guest Smart boundary and regression context | 6 min |

**Total estimated time:** ~58 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Fix the public guest snapshot commit path rather than backend revision validation | The backend is correctly detecting drift between `expected_revision` and submitted snapshot truth | [x] |
| Commit accepted Smart workspaces directly to guest storage before applying success | Success should mean the browser-owned snapshot can survive the next run or reload | [x] |
| Apply the contract to both public seating and grouping | Both public Smart composables share the same persistence shape even though seating surfaced the bug | [x] |
| Keep Smart-off `Slumpa` on existing local random autosave semantics | The regression is specific to accepted public Smart helper results | [x] |
| Add two-consecutive-run proof as the main regression test | One successful run is insufficient; the bug appears on the next `Slumpa` | [x] |
| Sanitize public Smart revision-conflict toasts | Raw revision diagnostics are internal and not actionable teacher copy | [x] |

## Review Checklist

- [x] Scope is bounded to public guest Smart accepted-result persistence
- [x] The task does not weaken backend conflict semantics
- [x] Acceptance criteria prove the exact `Expected 3, got 2` drift class
- [x] The design covers both `Sittplatser` and `Grupper`
- [x] The plan handles persistence failure without false success
- [x] Test plan includes two consecutive Smart `Slumpa` runs
- [x] Test plan requires sanitized feedback when a public Smart `409` still occurs
- [x] Live proof obligations include Docker web logs and the public dev route
- [x] Implementation was blocked until this retained review approved the slice

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-12`
**Verdict:** `approved`

### Required Changes

None. The proposed boundary is the correct one: keep the backend `409 CONFLICT`
revision guard strict and repair the browser-owned public guest snapshot commit
path.

Implementation must preserve these proof obligations:

1. Directly commit the visible pre-run workspace to the guest snapshot before
   each public Smart helper request and derive `expected_revision` from that
   committed snapshot.
2. Directly commit `result.workspace` to the guest snapshot before applying
   success feedback or replacing the visible planner state.
3. Clear or acknowledge bypassed draft-lane pending state after direct commits
   so delayed autosave cannot replay older assignments.
4. Prove the same two-run revision invariant for `Sittplatser` and `Grupper`.
5. Keep intentional mismatch tests proving the backend still rejects stale or
   contradictory public Smart payloads.
6. Map public Smart revision-conflict responses to teacher-facing recovery copy
   before they reach shell toast state. Raw text such as
   `Draft revision mismatch. Expected 2, got 1.` must not appear in the UI.

### Suggestions (Optional)

- Prefer an explicit return value from the direct commit helper, such as the
  committed snapshot, so the public Smart request cannot accidentally use a
  separately loaded stale snapshot after the pre-run commit.
- Add one reload-style assertion if the session harness can do it cheaply:
  after the first accepted Smart run, reload or hydrate from stored guest
  snapshot and verify the draft revision is already `N+1`.
- Keep the public Smart composable interface honest by naming the operation as a
  snapshot commit, not as generic draft persistence; the current bug came from
  treating those as interchangeable.
- Place the conflict-copy mapping close to the public Smart run orchestration so
  authenticated draft/save conflict messages keep their current semantics.

### Decision Approvals

- [x] Fix the public guest snapshot commit path rather than backend revision validation
- [x] Commit accepted Smart workspaces directly to guest storage before applying success
- [x] Apply the contract to both public seating and grouping
- [x] Keep Smart-off `Slumpa` on existing local random autosave semantics
- [x] Add two-consecutive-run proof as the main regression test
- [x] Sanitize public Smart revision-conflict toasts

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0259` | Created a detailed follow-up implementation slice for public Smart `Slumpa` accepted-workspace guest snapshot commits. |
| 2 | `REV-PR-0259` | Approved the direct public guest snapshot commit contract and recorded the required implementation proof obligations. |
| 3 | `PR-0259` / `REV-PR-0259` | Clarified that the same root cause covers grouping and that raw `Draft revision mismatch` diagnostics must not surface in user toasts. |
