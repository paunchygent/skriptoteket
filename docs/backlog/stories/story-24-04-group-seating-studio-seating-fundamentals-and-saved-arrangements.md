---
type: story
id: ST-24-04
title: "Klassrumskartan — Seating Fundamentals and Saved Seating Arrangements"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher is in a class workspace, when they open or create a seating draft, then the seating workflow is clearly tied to that class and the selected classroom."
  - "Given the teacher wants to start seating work, when they create a seating draft, then selecting a classroom is required before the seating planner opens."
  - "Given the teacher is in seating, when the mode is shown, then students can be placed on seats manually without exposing grouping controls in the same workspace."
  - "Given the teacher wants a starting point, when `Slumpa` is used in seating, then the students receive a first seating draft without also re-dividing the current groups."
  - "Given the teacher changes a seating plan, when students are moved, swapped, or removed from seats, then the seating workspace keeps that manual behavior explicit and easy to understand."
  - "Given the class already has an active seating draft, when the teacher returns later, then that seating draft can be resumed as the active seating work for that class."
  - "Given the teacher starts a new seating draft for the same class, when the new draft is created, then the previous active seating draft is demoted to class history automatically."
  - "Given the teacher completes a seating plan, when they save it, then the full seating assignment can be stored as a named seating arrangement attached to that class."
  - "Given the teacher does not provide a seating-arrangement name, when the arrangement is saved, then the default name is the saved date plus time."
  - "Given a saved seating arrangement already exists, when the teacher edits or deletes it later, then the saved arrangement can be updated or removed without changing the current live seating draft by accident."
  - "Given the teacher saves a seating arrangement, when the save succeeds, then the saved seating arrangement and its relevant settings appear in the class history and in the user's saved files / file vault."
  - "Given seating is saved, when the save is validated, then unrelated grouping-only findings do not block the seating save flow."
  - "Given future teacher-authored placement metadata exists, when seating is randomized or adjusted later, then that metadata can influence seating as a separate concern without turning the current seating fundamentals into an abstract tuning surface."
  - "Given future smart placement needs historical input, when the class has saved seating history, then those saved seating arrangements can act as the preferred historical source."
---

## Context
This story defines seating as its own class-scoped, classroom-bound teacher task: place students,
save meaningful arrangements, and keep the workflow readable before adding more intelligence.

## Notes

- This story starts only after `ST-24-05` and `ST-24-02` have removed superseded planner contracts and established the class-first workspace.
- `Saved seating arrangement` is the teacher-facing name for a full seat assignment set.
- Historical reuse and teacher placement metadata are long-term goals, but this story keeps the visible seating workflow simple and implementation-ready.
- Saved seating work should be discoverable from the same vault model as other teacher artifacts so the arrangements feel like owned work rather than hidden app state.
- The review direction for this story is a named saved artifact root plus immutable revisions underneath, not a whole-workspace finalize snapshot.
- Seating save payloads should stay seating-focused: roster snapshot, room/template snapshot, seat assignments, and only the seating-relevant settings that were actually used.
- Static room presentation should follow the design system rather than hard-coded inline styling, while dynamic geometry remains data-driven.
- Saved seating history is strategically more important than grouping history because it is the cleaner long-term source for later smart-placement and rotation logic.
