---
type: pr
id: PR-0086
title: "Klassrumskartan: class workspace summary contract"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-02"
tags: ["backend", "api", "persistence"]
acceptance_criteria:
  - "The backend exposes a class-scoped workspace summary that separates active grouping work, active seating work, grouping history, and seating history for one class."
  - "The class-workspace summary does not inline full room-template catalogs or other bulky launch data that belong to task-entry flows."
  - "The contract makes task-entry rules explicit, including that seating requires a classroom and grouping is classroom-agnostic by default with optional classroom awareness."
  - "Backend tests cover class-scoped summary loading, task-specific history separation, and top-level resumable-draft behavior remaining outside the class-workspace query."
---

## Problem

`ST-24-05` cleaned the draft lifecycle and removed superseded solver-first contracts, but the
active API surface is still landing-page oriented. It can resolve a draft and fetch one latest
resumable draft, but it cannot answer the class-first question:

- for this class, what active grouping work exists?
- what active seating work exists?
- what history exists for each task?

Without a dedicated class-workspace query, the frontend would have to guess, overfetch, or stitch
together the teacher-facing workspace from unrelated endpoints.

## Goal

Add the backend/API contract that a class-first workspace actually needs, while keeping the query
focused and easy to reason about:

- one class-scoped workspace summary
- separate active summaries for `Grupper` and `Sittplatser`
- separate task-specific history summaries
- explicit task-entry rules through a lightweight `TaskEntryOption` shape rather than through
  frontend inference or bloated summary payloads

## Non-goals

- Full saved-grouping or saved-seating artifact persistence from `ST-24-03` / `ST-24-04`.
- Frontend class-workspace UI implementation.
- Planner leave/return semantics in the SPA.
- Replacing the top-level `GET /drafts/resumable` fast-resume affordance.

## Checklist

- [x] Add a class-scoped workspace summary query and DTOs.
- [x] Return active grouping and active seating summaries separately for one class.
- [x] Return grouping history and seating history separately for one class.
- [x] Keep task-entry rules explicit through a lightweight `TaskEntryOption` contract so the
      summary body does not need to carry full template catalogs later.
- [x] Keep top-level `GET /drafts/resumable` as the cross-class quick-resume surface rather than
      merging that concern into the class-workspace summary.
- [x] Add repository/query support for task-specific class history without reviving owner-global
      draft semantics.
- [x] Add backend tests for summary loading, task separation, and history ordering.

## Implementation plan

- Add a class-workspace read model rooted in `roster_id` that includes:
  - roster/class identity
  - active grouping draft summary or `null`
  - active seating draft summary or `null`
  - grouping history summaries
  - seating history summaries
  - `TaskEntryOption[]` describing task-entry rules without embedding template lists
- Extend the planner repository protocol and SQLAlchemy repository with class-scoped summary/history
  queries that align with the existing `draft_kind` invariant.
- Expose a bespoke curated-app endpoint for class workspace summary loading.
- Keep the DTOs summary-oriented and intentionally smaller than full draft workspace payloads.

## Test plan

- Backend:
  - class workspace summary returns separate active grouping and active seating entries
  - history for grouping and seating stays separated
  - summary for one class does not leak drafts from another class
  - `GET /drafts/resumable` still returns the latest cross-class quick-resume candidate
- Manual:
  - hit the new class summary endpoint for a class with both active draft kinds and confirm the
    response is class-scoped, task-separated, and compact

## Rollback plan

- Revert the class-workspace summary endpoint and repository query additions if they produce
  unstable or misleading class-scoped results; keep the cleaned `draft_kind` lifecycle from
  `PR-0085` intact.

## Follow-up direction

- `PR-0087` consumes this summary contract in the SPA and replaces the symmetric launcher with a
  class-first state machine.
- `PR-0088` uses the task-entry rules to wire grouping and seating start flows without frontend
  guesswork.
