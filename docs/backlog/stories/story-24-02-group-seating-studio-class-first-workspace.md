---
type: story
id: ST-24-02
title: "Klassrumskartan — Class-First Workspace and Draft Entry"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-22
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher opens Klassrumskartan, when the main view loads, then classes are the prominent first-step objects and classrooms are presented as secondary supporting assets."
  - "Given the teacher chooses a class, when the class workspace opens, then the workspace starts neutral with overview selected and a fixed top toggle for `Översikt`, `Grupper`, and `Sittplatser`."
  - "Given the teacher is inside an active grouping draft or seating draft, when they switch to `Översikt` from the top toggle, then they return to the neutral class workspace without discarding the active work by default."
  - "Given the teacher wants to leave the class workspace altogether, when they press `Avsluta`, then they return to the landing page while the latest active draft remains resumable there."
  - "Given the teacher wants to start seating work for a class, when they create or resume a seating draft, then the seating workspace opens directly and classroom selection stays inside that seating workspace."
  - "Given the teacher wants to start grouping work for a class, when they create a new grouping draft, then they can either continue without a classroom or optionally choose a classroom-aware grouping context."
  - "Given the class already has an active seating draft or active grouping draft, when the teacher returns to the landing page, then the latest active work is resumable there without auto-opening the class workspace."
  - "Given the teacher starts a new draft of the same kind for the same class, when the new draft is created, then the previous active draft of that kind is demoted to history automatically."
  - "Given the class has historical drafts or saved arrangements, when the class workspace renders, then that history is accessible but secondary through task-specific drawers rather than dominating the default happy path."
  - "Given the current implementation still carries a symmetric class/classroom launcher from ST-24-01, when this story ships, then the class-first workspace replaces that transitional launch model."
---

## Context
The teacher's real mental model is class-first. They do not normally think in terms of choosing a
class and a classroom as equal launch objects. They think in terms of opening a class, then
continuing or starting seating/grouping work inside that class.

## Notes

- This story starts only after `ST-24-05` has removed superseded solver-first planner contracts from the active codebase.
- This story replaces the transitional symmetric launch model from `ST-24-01`.
- The class workspace should start neutral, keep the top toggle fixed in place, and make active work prominent only after the teacher chooses the task.
- Leaving active work, exiting the class workspace, discarding a draft, and saving a teacher-approved result are different actions and must stay distinct in the UI.
- `GroupingDraft` and `SeatingDraft` are separate units of work even if the persistence layer shares normalized concepts underneath.
- `Sittplatser` is room-contextual, but the seating draft may exist before a room is chosen; seat assignments and saved seating outcomes remain classroom-bound once room context is attached.
- Top-level quick resume belongs on the landing page, not inside the class workspace.
- The next stories (`ST-24-03` and `ST-24-04`) build on this class-first workspace rather than bypassing it.
