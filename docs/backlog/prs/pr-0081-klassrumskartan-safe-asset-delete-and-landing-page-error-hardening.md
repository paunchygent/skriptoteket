---
type: pr
id: PR-0081
title: "Klassrumskartan: safe asset delete and landing-page error hardening"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-01"
tags: ["backend", "frontend", "api"]
acceptance_criteria:
  - "Roster deletion is blocked safely when an active draft still depends on that roster."
  - "Classroom/template deletion is blocked safely when an active draft still depends on that template."
  - "The API returns a clear application/domain error for dependency-blocked deletes."
  - "The class/classroom edit modals surface teacher-facing delete-blocked messaging without breaking cancel/close behavior."
  - "Backend tests cover blocked and allowed delete cases, and frontend tests cover delete-failure UX."
---

## Problem

ST-24-01 promises that class/classroom deletion either works through the landing page or is blocked
safely when active drafts still depend on the asset. Today that safeguard is not explicit enough,
which risks broken drafts or confusing delete failures.

## Goal

Implement the safe-delete policy for landing-page asset management and make delete failures readable
and recoverable in the edit modals.

## Non-goals

- Soft-delete retain semantics for dependent assets.
- Broader draft cleanup/retention strategy beyond blocking active-draft dependencies.
- Full router/web-layer cleanup beyond what is directly needed for these endpoints.

## Checklist

- [x] Block roster deletion when an active draft still depends on that roster.
- [x] Block classroom/template deletion when an active draft still depends on that template.
- [x] Return a clear domain/application error for “cannot delete because active draft depends on asset”.
- [x] Surface that error in the class/classroom edit modal with teacher-facing copy.
- [x] Keep cancel/close behavior clean after failed delete attempts.
- [x] Add backend tests for blocked delete behavior.
- [x] Add frontend tests for delete-failure messaging and modal usability.
- [x] While touching the planner router module, remove router-layer standards drift only if needed for this story’s endpoints; otherwise leave broader API cleanup to later PRs.

## Implementation plan

- Add application-level dependency checks before deleting a roster or room template.
- Use the chosen ST-24-01 policy: **block delete**, do not silently hard-delete assets that still
  back active drafts.
- Return a clear planner-specific error that the frontend can render directly in the modal surface.
- Keep the modal open after blocked delete so the teacher can read the message and decide what to
  do next.

## Test plan

- Backend:
  - delete roster blocked when active draft depends on it
  - delete template blocked when active draft depends on it
  - delete still succeeds when no active draft depends on the asset
- Frontend:
  - blocked delete error appears in the relevant modal
  - modal remains usable after failed delete
  - cancel/close still works after the error state
- Manual:
  - try deleting a class and a classroom with active-draft dependencies and confirm the blocked
    message is clear and the landing page remains usable

## Rollback plan

- Revert the blocking policy if it causes false positives, but do not replace it with silent hard
  delete; fall back to no-delete plus explicit error until the dependency detection is corrected.

## Follow-up direction

- The delete-blocking policy remains valid under the class-first model.
- Later stories will refine what counts as active class work, but developers should continue to
  protect classes/classrooms from destructive actions while active draft work still depends on
  them.
