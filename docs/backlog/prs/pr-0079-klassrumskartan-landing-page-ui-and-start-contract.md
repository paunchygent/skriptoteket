---
type: pr
id: PR-0079
title: "Klassrumskartan: landing page UI and planner start contract"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-01"
tags: ["frontend"]
acceptance_criteria:
  - "The default landing flow no longer exposes lesson mode as a required teacher-facing choice."
  - "The planner can be opened as soon as one class and one classroom are selected."
  - "The landing page remains the default first screen and reads as class/classroom management plus planner launch, not as a planning dashboard."
  - "Class/classroom edit modals remain usable on normal laptop viewports and support save, cancel, and close cleanly."
  - "Frontend tests cover the landing-page start flow, lesson-mode removal from the default UI, and modal interaction behavior."
---

## Problem

ST-24-01 begins with a visible trust reset. The current landing page is closer to the intended
direction than the earlier Slice 2 UI, but it still leaks lesson-mode mechanics into the default
teacher workflow and still mixes planner bootstrap concerns into the first interaction.

## Goal

Ship the frontend-dominant landing-page cleanup so Klassrumskartan opens as a clean asset library
plus launch point, and the planner start contract is simply:

- select class
- select classroom
- open planner

## Non-goals

- Server-backed resume lifecycle.
- Delete blocking when active drafts depend on a class or classroom.
- Route-level `Grupper` / `Sittplatser` separation from ST-24-02.
- Full planner-store split from PR-0078 follow-up work.

## Checklist

- [x] Remove `lesson mode` from the default teacher-facing landing flow.
- [x] Make planner start depend on `selected class + selected classroom` only.
- [x] Keep the landing page as the default first screen every time the app opens.
- [x] Keep the landing page focused on class/classroom management and planner launch only.
- [x] Preserve back navigation from planner to landing page.
- [x] Keep class/classroom edit modals viewport-bounded, scrollable, cancellable, and closable.
- [x] Tighten the selection gate copy/layout so it reads like an asset library + launch point, not a planning dashboard.
- [x] Update frontend tests for selection/start behavior and modal interaction.

## Implementation plan

- Update the planner root view so the initial UI state is always the landing page unless the user
  explicitly resumes through a later resume affordance.
- Remove default-surface lesson-mode selection from the selection gate while keeping current backend
  compatibility intact for now.
- Keep start-planning wired through the existing draft creation path in this PR; PR-0080 will
  replace that with `resolve`.
- Keep the existing modal usability fixes and align the surrounding layout/copy with the
  fundamentals-first product direction.

## Test plan

- Frontend:
  - planner start enabled only when class + classroom are selected
  - no lesson-mode requirement in the default landing flow
  - back-to-landing behavior
  - class/classroom modal close/cancel/save interaction
- Manual:
  - open the app, select class + classroom, open planner, go back, and verify the landing page
    remains intact and uncluttered

## Rollback plan

- Revert the landing-page UI changes if they regress planner entry, keeping the story split so the
  resume/delete PRs can still land later.

## Follow-up direction

- This shipped slice is now explicitly transitional.
- `ST-24-02` replaces the symmetric class/classroom launch model with a class-first workspace.
- Developers should not treat this PR as the final information architecture for Klassrumskartan.
