---
type: story
id: ST-24-04
title: "Klassrumskartan — Seating Fundamentals and Draft History"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-22
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher is in a class workspace, when they open or create a seating draft, then the seating workflow is clearly tied to that class and the selected classroom."
  - "Given the teacher wants to start seating work, when they create a seating draft, then the seating planner can open before a classroom is chosen and classroom selection or switching happens inside the seating workspace."
  - "Given the teacher is in seating, when the mode is shown, then students can be placed on seats manually without exposing grouping controls in the same workspace."
  - "Given the teacher wants a starting point, when `Slumpa` is used in seating, then the students receive a first seating draft without also re-dividing the current groups."
  - "Given the teacher changes a seating plan, when students are moved, swapped, or removed from seats, then the seating workspace keeps that manual behavior explicit and easy to understand."
  - "Given the class already has an active seating draft, when the teacher returns later, then that seating draft can be resumed as the active seating work for that class."
  - "Given the teacher starts a new seating draft for the same class, when the new draft is created, then the previous active seating draft is demoted to class history automatically."
  - "Given the teacher changes the current seating draft, when they use undo or redo, then the recent seating history can be stepped backward or forward inside the seating workspace without exposing those steps as separate saved items."
  - "Given the seating draft changes repeatedly, when draft history is retained for undo and redo, then the history depth stays bounded and configurable rather than growing without limit."
  - "Given the teacher leaves seating and returns later, when the draft has been autosaved, then the latest seating state is resumed without requiring a separate teacher-facing save action."
  - "Given future teacher-authored placement metadata exists, when seating is randomized or adjusted later, then that metadata can influence seating as a separate concern without turning the current seating fundamentals into an abstract tuning surface."
  - "Given future smart placement needs historical input, when the class has explicit teacher-approved seating checkpoints later on, then those checkpoints can act as the preferred historical source rather than raw undo or autosave trail."
---

## Context
This story defines seating as its own class-scoped, classroom-bound teacher task: place students,
keep the active seating draft recoverable through autosave and in-workspace undo/redo, and keep
the workflow readable before adding more intelligence.

## Notes

- This story starts only after `ST-24-05` and `ST-24-02` have removed superseded planner contracts and established the class-first workspace.
- Draft autosave keeps live seating work alive, while a bounded recent history supports undo and redo inside the seating workspace.
- The recent-history depth should be configurable and simple to tune; the current planning target is 10 steps.
- Historical reuse and teacher placement metadata are long-term goals, but this story keeps the visible seating workflow simple and implementation-ready.
- Durable file-vault artifacts belong to a later export flow and must not be conflated with draft autosave or undo/redo history.
- Seating draft payloads and draft-history entries should stay seating-focused: roster snapshot/reference, room/template snapshot or context, seat assignments, and only the seating-relevant settings that were actually used.
- Static room presentation should follow the design system rather than hard-coded inline styling, while dynamic geometry remains data-driven.
- Explicit teacher-approved seating checkpoints remain strategically more important than grouping history for later smart-placement and rotation logic, but they belong to a later export/checkpoint flow rather than this fundamentals story.
