---
type: story
id: ST-24-02
title: "Klassrumskartan — Class-First Workspace and Draft Entry"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher opens Klassrumskartan, when the main view loads, then classes are the prominent first-step objects and classrooms are presented as secondary supporting assets."
  - "Given the teacher chooses a class, when the class workspace opens, then the teacher can see active seating work, active grouping work, and secondary class-owned history without being forced straight into one planner surface."
  - "Given the teacher wants to start seating work for a class, when they create a new seating draft, then choosing a classroom is required before the seating planner opens."
  - "Given the teacher wants to start grouping work for a class, when they create a new grouping draft, then they can either continue without a classroom or optionally choose a classroom-aware grouping context."
  - "Given the class already has an active seating draft or active grouping draft, when the teacher returns to the class workspace, then they can continue that active work explicitly instead of losing it or replacing it silently."
  - "Given the teacher starts a new draft of the same kind for the same class, when the new draft is created, then the previous active draft of that kind is demoted to history automatically."
  - "Given the class has historical drafts or saved arrangements, when the class workspace renders, then that history is accessible but secondary rather than dominating the default happy path."
  - "Given the current implementation still carries a symmetric class/classroom launcher from ST-24-01, when this story ships, then the class-first workspace replaces that transitional launch model."
---

## Context
The teacher's real mental model is class-first. They do not normally think in terms of choosing a
class and a classroom as equal launch objects. They think in terms of opening a class, then
continuing or starting seating/grouping work inside that class.

## Notes

- This story starts only after `ST-24-05` has removed superseded solver-first planner contracts from the active codebase.
- This story replaces the transitional symmetric launch model from `ST-24-01`.
- The class workspace should make active work prominent and history secondary.
- `GroupingDraft` and `SeatingDraft` are separate units of work even if the persistence layer shares normalized concepts underneath.
- `Sittplatser` is classroom-bound; `Grupper` may be classroom-aware or classroom-agnostic.
- The next stories (`ST-24-03` and `ST-24-04`) build on this class-first workspace rather than bypassing it.
