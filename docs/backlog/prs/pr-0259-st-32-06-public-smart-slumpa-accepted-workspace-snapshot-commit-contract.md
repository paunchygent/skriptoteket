---
type: pr
id: PR-0259
title: "ST-32-06 follow-up: public Smart Slumpa accepted-workspace snapshot commit contract"
status: done
owners: "agents"
created: 2026-04-12
updated: 2026-04-30
stories:
  - "ST-32-06"
tags:
  [
    "frontend",
    "klassrumskartan",
    "public-access",
    "guest-workspace",
    "smart-assignment",
    "regression",
  ]
dependencies:
  - "ADR-0079"
  - "ADR-0080"
  - "PR-0231"
  - "PR-0232"
  - "PR-0234"
acceptance_criteria:
  - "Given a public guest uses `Slumpa` in `Sittplatser` with `Smart` enabled, when the public Smart helper returns an accepted workspace at revision N+1, then the browser-owned guest snapshot is committed to revision N+1 before success is surfaced."
  - "Given a public guest uses `Slumpa` in `Sittplatser` with `Smart` enabled twice in the same workspace, when the second request is sent, then `expected_revision` and `snapshot.seating_draft.revision` match and the request does not fail with `Draft revision mismatch`."
  - "Given a public guest uses `Slumpa` in `Grupper` with `Smart` enabled twice, when the same accepted-workspace persistence path is exercised, then `expected_revision` and `snapshot.grouping_draft.revision` match across both runs."
  - "Given browser snapshot persistence fails after a public Smart helper returns an accepted workspace, when the UI handles the failure, then it rolls back or preserves the previous visible workspace and does not show a success toast for an uncommitted Smart result."
  - "Given public Smart accepted-workspace persistence bypasses draft autosave timing, when `smartGroupingRunInFlight` or `smartSeatingRunInFlight` is true, then the accepted workspace still commits through an explicit guest snapshot mutation rather than `draftLane.markDirty()`."
  - "Given the backend receives a genuinely mismatched public Smart payload, when the public helper compares the submitted `expected_revision` with the materialized snapshot draft revision, then the existing `409 CONFLICT` guard remains intact."
  - "Given any public Smart `Slumpa` request still receives a revision-conflict response, when the guest UI surfaces feedback, then it shows teacher-facing recovery copy and never leaks raw internal text such as `Draft revision mismatch. Expected 2, got 1.` in a toast."
  - "Given `Smart` is disabled, when public guest `Slumpa` runs in grouping or seating, then existing local random behavior and normal draft autosave semantics remain unchanged."
---

## Problem

The public Klassrumskartan guest workspace can drift after solver-backed Smart
`Slumpa` in `Sittplatser` and `Grupper`.

The reproduced warnings are:

```text
Varning: Draft revision mismatch. Expected 3, got 2.
Varning: Draft revision mismatch. Expected 2, got 1.
```

The Docker dev logs confirm the request pattern:

- `POST /api/v1/public/apps/classroom.group-seating-studio/seating/smart-run`
  returned `200` at `2026-04-12T19:59:46Z`.
- A subsequent request to the same route returned `409 CONFLICT` at
  `2026-04-12T20:00:00Z`.
- A second reproduced sequence returned `200` at `20:00:30Z`, then `409` at
  `20:00:38Z` and `20:00:47Z`.

The code-level fault line is in the public Smart accepted-result persistence
path:

- `usePublicSmartSeatingRun.ts` and `usePublicSmartGroupingRun.ts` apply the
  accepted solver workspace and then call `persistAppliedWorkspace`.
- `classroomPlannerGuestDraftSession.ts` implements `persistAppliedWorkspace`
  as `draftLane.markDirty()` plus `draftLane.flushPendingChanges()`.
- The guest draft lane is guarded by `canSchedule: () => !isWorkspaceBusy`.
- During a public Smart run, `smartSeatingRunInFlight` makes
  `isWorkspaceBusy` true, so `markDirty()` returns without setting pending
  changes.
- The following flush sees no pending changes and reports saved, while the
  browser-owned guest snapshot still has the old draft revision.

The next public Smart `Slumpa` sends `expected_revision` from the in-memory
draft and the stale revision from the browser snapshot. The backend correctly
rejects that mismatch. The same root cause applies to grouping when
`smartGroupingRunInFlight` blocks autosave scheduling during accepted-workspace
persistence. The regression likely surfaced around the public/auth cutover work
because the public guest Smart lane became more actively exercised, but the
failing seam is guest snapshot persistence, not auth or the solver.

A secondary user-facing bug rides on top of the same failure: the raw backend
revision-conflict message is internal diagnostic text and must not be surfaced
as a toast. Teachers should get actionable recovery copy, while logs and tests
can still prove the strict backend conflict guard fired.

## Goal

Make public guest Smart `Slumpa` persistence atomic and explicit:

- accepted public Smart workspaces commit directly to the browser-owned guest
  snapshot
- the UI only surfaces success after the accepted workspace is durably written
  into guest storage
- repeated Smart `Slumpa` runs in both `Sittplatser` and `Grupper` keep
  in-memory draft revision and guest snapshot revision aligned
- backend revision guards stay strict
- public Smart conflict feedback is user-facing copy, not raw revision internals

## Non-goals

- Do not weaken or remove the backend `Draft revision mismatch` guard.
- Do not change authenticated Smart grouping or Smart seating APIs.
- Do not change the solver behavior or scoring strategy.
- Do not introduce server-side persistence for guest drafts.
- Do not reopen guest `Use history`; history-based Smart stays
  authenticated-only.
- Do not redesign the `Slumpa` button, toolbar, or Smart settings drawer.
- Do not change guest upgrade semantics beyond preserving a correct snapshot
  for the existing upgrade path.

## Implementation plan

1. Add an explicit guest snapshot commit helper for active workspaces.
   - Place it in the existing guest workspace/persistence seam rather than in a
     component:
     - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftWorkspace.ts`
     - or a small extracted helper if this keeps modules under the repository
       size budget.
   - The helper should accept a `DraftWorkspaceResponse` and commit it through
     `options.persistSnapshotMutation` plus `replaceGuestSnapshotDraft`.
   - It must preserve the current guest UI context:
     - selected roster
     - selected template
     - current screen `planner`
     - planner initial view `groups` or `seats`
     - dismissed draft ids from the current snapshot
   - It must not depend on `draftLane.markDirty()` or autosave timers.

2. Commit current visible guest state before public Smart helper calls.
   - Before posting to `/public/.../smart-run`, flush existing draft and
     smart-rule lanes.
   - Then directly commit the current visible workspace to the browser snapshot.
   - Build the public Smart payload from that committed snapshot, not from a
     separately loaded stale snapshot.
   - Derive `expected_revision` from the committed snapshot draft revision.
   - This also repairs already-open sessions whose visible planner state is
     newer than the stored snapshot because of the current bug.

3. Commit accepted public Smart results before applying success.
   - On a public Smart `applied` response, commit `result.workspace` directly
     into the guest snapshot first.
   - Only after that commit succeeds:
     - apply the workspace to the live planner refs
     - capture/replace local undo history
     - show the success message
   - If the commit fails, leave or restore the previous workspace and surface a
     warning/error rather than a success toast.

4. Acknowledge bypassed draft-lane state intentionally.
   - After a direct guest snapshot commit succeeds, clear stale pending draft
     lane state so a delayed autosave cannot replay older assignments.
   - Prefer a narrow lane method with an explicit name such as
     `acknowledgeExternalCommit()` if `discardPendingChanges()` would make the
     status semantics misleading.
   - Keep this lane API frontend-local; do not change backend contracts.

5. Update both public Smart composables.
   - Apply the same commit contract to:
     - `usePublicSmartSeatingRun.ts`
     - `usePublicSmartGroupingRun.ts`
   - Avoid duplicating orchestration by extracting a small shared helper only if
     it reduces real duplication and keeps the public grouping/seating behavior
     easy to read.

6. Keep normal local random `Slumpa` behavior unchanged.
   - When `Smart` is off, grouping/seating still use local random mutation plus
     normal draft autosave.
   - The new direct accepted-workspace commit path is only for public Smart
     helper results.

7. Preserve strict backend conflict semantics.
   - Leave `RunPublicSmartSeatingHandler` and `RunPublicSmartGroupingHandler`
     revision comparison intact.
   - Add coverage that proves the backend still rejects intentionally mismatched
     public payloads.

8. Normalize public Smart revision-conflict feedback.
   - Do not pass backend messages matching the `Draft revision mismatch` class
     through to `ClassroomPlannerGuestWorkspaceShell` toasts.
   - Map public Smart `409 CONFLICT` responses to teacher-facing copy that asks
     the user to try again or reload the public workspace.
   - Keep the raw backend message available only through logs/test assertions,
     not visible UI feedback.

## Test plan

- Focused frontend unit tests:
  - `pdm run fe-test -- --run src/views/apps/usePublicSmartSeatingRun.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts`
  - Add two-run seating coverage:
    - first run commits response revision `3` to the snapshot
    - second run sends `expected_revision: 3`
    - second run sends `snapshot.seating_draft.revision: 3`
  - Add two-run grouping coverage with the same revision invariant.
  - Add persistence-failure coverage:
    - accepted helper response
    - snapshot commit rejects
    - UI does not surface success
    - previous workspace is preserved/restored.
  - Add conflict-feedback coverage:
    - backend/public Smart response contains
      `Draft revision mismatch. Expected 2, got 1.`
    - guest run message/toast uses the sanitized public Smart recovery copy
    - raw `Draft revision mismatch` text is not surfaced.

- Guest-session integration-style frontend tests:
  - Target `classroomPlannerGuestDraftSession` or a narrow harness around it.
  - Prove `smartSeatingRunInFlight` / `smartGroupingRunInFlight` do not block
    accepted workspace snapshot commits.
  - Prove stale pending draft-lane state is cleared after direct accepted
    commits.

- Backend/web regression tests:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py`
  - Keep or add assertions that mismatched `expected_revision` still returns
    `409 CONFLICT`.

- Type and docs checks:
  - `pdm run fe-type-check`
  - `pdm run docs-validate`

- Live dev proof:
  - Use the running Docker dev stack.
  - Open `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`.
  - In `Sittplatser`, enable `Smart` and click `Slumpa` twice.
  - Confirm no toast matching
    `Varning: Draft revision mismatch. Expected 3, got 2.`
  - Confirm no toast matching
    `Varning: Draft revision mismatch. Expected 2, got 1.`
  - Confirm `docker logs skriptoteket_web` shows two successful
    `/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run`
    requests with `200`, not `409`.
  - Repeat in `Grupper` with Smart enabled and confirm two successful
    `/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run`
    requests with `200`, not `409`.
  - Record the verification in `.codex/handoff.md`.

## Rollback plan

- Revert only the public Smart accepted-workspace commit changes if the direct
  commit path introduces a guest snapshot regression.
- Keep backend conflict guards and authenticated Smart APIs untouched.
- If the direct commit helper fails under live browser storage behavior, restore
  the current public Smart rollback behavior and temporarily block success
  messaging when accepted result persistence cannot be proven.

## Review gate

- Retained review gate:
  [REV-PR-0259](../reviews/review-pr-0259-public-smart-slumpa-snapshot-commit-contract.md)

## Status Reconciliation (2026-04-30)

This PR is now marked `done`. The committed public Smart grouping/seating
composables commit the current guest workspace to the browser snapshot before
calling the public helper, derive `expected_revision` from the committed
snapshot, commit accepted helper results before surfacing success, acknowledge
the external draft commit, and map raw `Draft revision mismatch` diagnostics to
teacher-facing recovery copy. Focused `usePublicSmartGroupingRun` and
`usePublicSmartSeatingRun` specs cover the regression shape.
