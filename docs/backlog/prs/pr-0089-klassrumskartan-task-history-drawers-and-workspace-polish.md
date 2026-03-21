---
type: pr
id: PR-0089
title: "Klassrumskartan: task history drawers and workspace polish"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-02"
tags: ["frontend"]
acceptance_criteria:
  - "Grouping history and seating history are accessible separately from the class workspace and are not visually intermixed."
  - "History stays secondary to active work and is hidden behind drawers, dropdowns, or similarly stowed-away controls rather than expanded default grids."
  - "The class workspace keeps attention on the current task choice and active work instead of presenting all task and history surfaces at once."
  - "Live browser checks cover the class-first workspace flow using the reusable Klassrumskartan Playwright baseline."
---

## Problem

The class-first workspace can still feel cluttered or conceptually muddy if it exposes too much at
once. `ST-24-02` explicitly requires that history be accessible but secondary, and that grouping
and seating remain clearly separate in the UI.

## Goal

Add the secondary workspace affordances and polish that make the class workspace feel calm and
teacher-readable:

- separate history access for grouping and seating
- hidden-by-default history surfaces
- no large always-open history grids
- no visual blending of both task histories into one planner dashboard

## Non-goals

- Implementing saved grouping / saved seating artifact persistence.
- Reworking the whiteboard/planner internals beyond what is needed to support calm class-workspace
  navigation.
- Introducing novel presentation patterns when standard drawers/dropdowns/lists are sufficient.

## Checklist

- [ ] Add separate grouping-history and seating-history access points in the class workspace.
- [ ] Keep history hidden by default and secondary to active work.
- [ ] Avoid always-open grids or dashboard-style history expansion.
- [ ] Keep the class workspace focused on one chosen task at a time.
- [ ] Add or extend browser automation coverage using the reusable Klassrumskartan smoke as the
      setup baseline.
- [ ] Add frontend tests for history-surface visibility and task separation.

## Implementation plan

- Introduce task-specific secondary surfaces, preferably drawer/dropdown/list based, for grouping
  history and seating history.
- Keep only lightweight summaries visible in the main class workspace until the teacher requests
  more detail.
- Reuse the app-specific Playwright baseline to avoid inventing another bespoke Klassrumskartan
  setup flow just for this story.
- Tighten copy/layout only as needed to support the class-first mental model; do not pre-build UI
  shells for later saved-artifact stories.

## Test plan

- Frontend:
  - grouping history and seating history are visually and behaviorally separate
  - history stays hidden until requested
  - opening history does not auto-expand unrelated task surfaces
- Manual / browser:
  - verify class selection, task choice, and history access in the live app using the reusable
    Klassrumskartan Playwright smoke plus a story-specific extension

## Rollback plan

- Revert the secondary history-surface changes if they make the workspace noisier or less clear,
  keeping the class-first state machine and task-entry semantics from `PR-0087` / `PR-0088`
  intact.

## Follow-up direction

- `ST-24-03` and `ST-24-04` can later replace draft-history-only summaries with richer saved
  grouping and saved seating artifact flows without overturning the class-first workspace shape.
