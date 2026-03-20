---
type: story
id: ST-23-02
title: "Klassrumskartan — Roster/Room Persistence & Lesson Mode"
status: ready
owners: "agents"
created: 2026-03-20
epic: "EPIC-23"
acceptance_criteria:
  - "Given no lesson mode is selected, when the planner view loads, then group and seat assignment controls are disabled."
  - "Given a lesson mode is selected, when the teacher proceeds to the planner, then the draft state stores that lesson mode and the planner becomes interactive."
  - "Given a teacher opens the metadata drawer for a student, when planning factors are edited, then the student card surface remains unchanged."
  - "Given a roster or room template is created, when the page reloads, then it can be reselected from the setup view."
---

## Context
Rosters and Room Templates are durable domain concepts that must be stored in the database, not lost on reload.

## Implementation Plan

### [ ] PR 1: Domain/State Modeling (Backend Endpoints)
- **Intent**: CRUD logic for App-specific durable items.
- **Code Choice**: Implement explicit relational tables (`roster`, `room_template`) in Postgres. Expose standard CRUD routes under the `/api/v1/apps/classroom.group-seating-studio/` prefix.

### [ ] PR 2: Setup Components
- **Intent**: Build the UI for setting up constraints prior to unlocking the canvas.
- **Code Choice**: Build `LessonModePicker.vue` selecting a subset from the `/bootstrap` catalog presets (no CRUD). Build `ConstraintDrawer.vue` managing `StudentPlanningMeta` separately from `StudentCardViewModel`. Disable planner canvas if lesson mode is null.
