---
type: pr
id: PR-0124
title: "Klassrumskartan: seating export reload recovery and draft-scoped rehydration"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["frontend", "backend", "klassrumskartan", "export", "remediation", "recovery"]
acceptance_criteria:
  - "Given a teacher starts a seating export and reloads the page before completion, when the same seating draft is reopened, then Skriptoteket rehydrates the in-flight export from backend-owned state and resumes teacher-visible recovery without depending only on browser session storage."
  - "Given a seating export already succeeded but the automatic download did not complete, when the same seating draft is reopened later, then the UI exposes a draft-scoped `Ladda ned igen` path for the latest recoverable export job."
  - "Given the teacher opens a different seating draft, when export recovery state exists for another draft, then the UI does not surface the wrong export state or cross-draft recovery affordance."
  - "Given no recoverable export exists for the active seating draft, when the workspace opens, then the export UI stays quiet and does not imply phantom background work."
  - "Given the frontend recovery path runs after reload, when browser session storage is cleared or unavailable, then the teacher can still recover from backend state for the active draft."
---

## Problem

The current export recovery remediation is intentionally session-scoped and
draft-local inside the browser tab. That is a safe stopgap, but it is not a
complete teacher-facing recovery model:

- recovery currently depends on `sessionStorage`
- a hard refresh plus context change can hide a valid export job from the UI
- the export job itself still exists server-side, but the frontend does not yet
  treat backend state as the primary recovery source

This leaves the product in an awkward middle state where exports are durable
enough operationally, but not yet durably discoverable from the teacher
workspace after reload.

## Goal

Promote seating export recovery from a browser-session safeguard to a
draft-scoped product contract owned by backend state and rehydrated when the
teacher reopens the relevant seating draft.

## Non-goals

- Building a cross-draft export inbox, export history page, or generic download
  center.
- Adding notifications outside the existing seating export action group.
- Changing the export artifact contract, poster renderer, or Sir Convert lane.
- Expanding into grouping export recovery.
- Removing the current polling fallback; it remains part of the safety model.

## Locked design decisions

- The active seating draft is the recovery scope. Recovery must be keyed to the
  currently opened seating draft, not to a browser tab and not to a global app
  singleton.
- Backend state is authoritative for reload recovery. Browser storage may still
  exist as a transient optimization, but it must not be the only recovery
  mechanism.
- The recovery surface remains compact and local to the existing seating
  `Export` action group; do not add a separate modal, toast-only recovery, or a
  global banner.
- The frontend must not guess across drafts. If multiple export jobs exist for a
  user, only recover jobs that the backend explicitly reports as recoverable for
  the active draft.
- Recovery should prefer the latest relevant job for the draft:
  - in-flight jobs first
  - otherwise the latest successful downloadable job within the supported
    recovery window
- The UX should remain teacher-safe:
  - if a job is still running, show resumable in-progress state
  - if a job already succeeded, show a clear download-again path
  - if no recoverable job exists, show nothing extra

## Recommended backend contract direction

Add one explicit draft-scoped recovery read surface rather than making the
frontend infer recovery from broad job lists.

Recommended shape:

- `GET /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports/jobs/recover`

Recommended behavior:

- returns `null`/empty when no recoverable job exists for the active user +
  draft
- returns one latest recoverable job DTO when:
  - the latest in-flight export for the draft is still `submitted` or
    `processing`, or
  - the latest successful export for the draft is still within the supported
    recovery/download window
- never returns a job from another draft

If implementation pressure makes a dedicated recovery endpoint undesirable, the
alternative is one narrowly typed "latest export for draft" endpoint with the
same ownership and draft-scoping guarantees. Do not solve this by exposing an
unfiltered generic job list to the frontend.

## Frontend recovery contract

- On seating-draft open, the route-shell/export composable should ask the
  backend for a recoverable export for that draft.
- If the backend reports an in-flight job:
  - restore compact in-progress state
  - resume polling
  - keep the current export action disabled while that job remains active
- If the backend reports a successful recent job:
  - restore compact success/download state
  - show `Ladda ned igen`
  - do not force an automatic browser download on rehydrate
- If no recoverable job exists:
  - clear stale local recovery state for that draft
  - keep the export affordance in its normal idle state

## Implementation plan

- Add a backend draft-scoped recovery handler/repository query for the latest
  recoverable seating export job owned by the active teacher.
- Keep the query deterministic and bounded; do not scan or expose unrelated
  export history.
- Extend the frontend export API helper with a dedicated recovery read call for
  the active draft.
- Update `useSeatingExportFlow` and route-shell wiring so draft open triggers
  backend recovery rehydration before relying on any transient local state.
- Keep `sessionStorage` only as an optional fast-path/cache if it still adds
  value, but ensure the UX remains correct without it.
- Preserve the compact `Export` action group and avoid broader UI sprawl.

## Test plan

- Focused backend tests for:
  - latest in-flight recoverable job lookup by `owner_user_id + draft_id`
  - latest successful downloadable job lookup by `owner_user_id + draft_id`
  - cross-draft isolation
  - no-recoverable-job response
- Focused API tests for the recovery route shape and authorization behavior.
- Focused frontend tests for:
  - rehydrating in-flight export from backend on draft open
  - rehydrating successful latest export with `Ladda ned igen`
  - avoiding cross-draft leakage
  - recovery when `sessionStorage` is empty or unavailable
- Live browser proof:
  - start an export
  - reload or reopen the active seating draft
  - verify the export affordance resumes correctly and preserves a download path

## Rollback plan

- Revert the draft-scoped recovery endpoint and frontend rehydration wiring
  while keeping the existing export lane and the current session-scoped fallback
  intact.
