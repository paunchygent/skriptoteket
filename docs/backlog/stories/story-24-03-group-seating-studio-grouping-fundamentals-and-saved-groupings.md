---
type: story
id: ST-24-03
title: "Klassrumskartan — Grouping Fundamentals and Draft History"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-22
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher is in a class workspace, when they open or create a grouping draft, then the grouping workflow operates on that class without implying that seating work must happen at the same time."
  - "Given the teacher wants classroom-agnostic groups, when they start grouping without selecting a classroom, then students can still be assigned into groups manually from the class roster."
  - "Given the teacher wants classroom-aware grouping, when they choose to use a classroom context, then the grouping draft records that context without turning seating into the same task."
  - "Given the teacher wants a starting point, when `Slumpa` is used in grouping, then the class is divided into groups as a first draft without also randomizing seat assignments."
  - "Given the teacher wants a different group structure, when they add or remove groups, then the grouping workspace updates without losing manual control over student placement."
  - "Given the teacher wants meaningful groups, when they rename a group, then the individual group keeps that teacher-defined name."
  - "Given a group contains more students, when the grouping board renders, then the group panel grows or lays itself out so the group's student cards fit inside the panel rather than clipping the content."
  - "Given the class already has an active grouping draft, when the teacher returns later, then that grouping draft can be resumed as the active grouping work for that class."
  - "Given the teacher starts a new grouping draft for the same class, when the new draft is created, then the previous active grouping draft is demoted to class history automatically."
  - "Given the teacher changes the current grouping draft, when they use undo or redo, then the recent draft history can be stepped backward or forward inside the grouping workspace without exposing those steps as separate saved items."
  - "Given the grouping draft changes repeatedly, when draft history is retained for undo and redo, then the history depth stays bounded and configurable rather than growing without limit."
  - "Given the teacher leaves grouping and returns later, when the draft has been autosaved, then the latest grouping state is resumed without requiring a separate teacher-facing save action."
---

## Context
This story defines grouping as its own class-scoped teacher task: build groups, name them
meaningfully, and keep the active grouping draft recoverable through autosave and in-workspace
undo/redo without implying that seating and grouping are one combined workflow.

## Notes

- This story starts only after `ST-24-05` and `ST-24-02` have removed superseded planner contracts and established the class-first workspace.
- The teacher should be able to move students freely between groups, back to the roster, and into newly created groups without hidden automation overriding the manual move.
- Draft autosave keeps live grouping work alive, while a bounded recent history supports undo and redo inside the grouping workspace.
- The recent-history depth should be configurable and simple to tune; the current planning target is 10 steps.
- Future “avoid these students together” logic should support the teacher quietly, but it does not belong as a visible main-view control in this story.
- Grouping draft payloads and draft-history entries should stay grouping-focused: roster snapshot/reference, groups, group assignments, and only the grouping-relevant settings that were actually used.
- Durable file-vault artifacts belong to a later export flow and must not be conflated with draft autosave or undo/redo history.
- Grouping history belongs to the class, but the active draft and its in-workspace undo/redo history matter more than any separate archive of technical draft items in this story.
- A later optional helper may allow classroom-aware grouping to derive natural groups from an active seating arrangement, but that is not the default behavior of this story.
