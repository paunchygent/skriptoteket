---
type: story
id: ST-24-03
title: "Klassrumskartan — Grouping Fundamentals and Saved Groupings"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
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
  - "Given the teacher completes a grouping, when they save it, then the full group assignment can be stored as a named saved grouping attached to that class."
  - "Given the teacher does not provide a grouping name, when the grouping is saved, then the default name is the saved date plus time."
  - "Given a saved grouping already exists, when the teacher edits or deletes it later, then the saved grouping can be updated or removed without changing the current live grouping by accident."
  - "Given the teacher saves a grouping, when the save succeeds, then the saved grouping and its relevant settings appear in the class history and in the user's saved files / file vault."
  - "Given grouping is saved, when the save is validated, then unrelated seating-only findings do not block the grouping save flow."
---

## Context
This story defines grouping as its own class-scoped teacher task: build groups, name them
meaningfully, save whole groupings, and reuse the results later without implying that seating and
grouping are one combined workflow.

## Notes

- This story starts only after `ST-24-05` and `ST-24-02` have removed superseded planner contracts and established the class-first workspace.
- `Group name` and `saved grouping name` are separate concepts and must stay separate in the UI and persistence model.
- The teacher should be able to move students freely between groups, back to the roster, and into newly created groups without hidden automation overriding the manual move.
- Future “avoid these students together” logic should support the teacher quietly, but it does not belong as a visible main-view control in this story.
- The review direction for this story is a named saved artifact root plus immutable revisions underneath, not a whole-workspace finalize snapshot.
- Grouping save payloads should stay grouping-focused: roster snapshot, groups, group assignments, and only the grouping-relevant settings that were actually used.
- Grouping history belongs to the class, but it is less strategically important than seating history for later smart-placement work.
- A later optional helper may allow classroom-aware grouping to derive natural groups from an active seating arrangement, but that is not the default behavior of this story.
