---
type: story
id: ST-24-01
title: "Klassrumskartan — Landing Page Fundamentals"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
epic: "EPIC-24"
acceptance_criteria:
  - "Given the teacher opens Klassrumskartan, when the landing page loads, then the page focuses on selecting and managing classes and classrooms rather than showing planning-rule panels or strategy controls."
  - "Given the teacher creates or edits a class, when the dialog is used, then the teacher can save, cancel, or close it intuitively, and the dialog remains usable on a normal laptop viewport."
  - "Given the teacher creates or edits a classroom, when the dialog is used, then the teacher can save, cancel, or close it intuitively, and the dialog remains usable on a normal laptop viewport."
  - "Given the teacher no longer wants a class or classroom, when the delete action is used, then the asset is deleted through the same landing-page management flow or blocked safely if an active draft still depends on it."
  - "Given the teacher selects one class and one classroom, when both selections are active, then the planner can be opened immediately."
  - "Given a resumable draft exists, when the teacher opens the landing page, then they see an explicit resume affordance rather than being forced directly into the planner."
  - "Given the teacher is inside the planner, when they choose to go back, then they return to the landing page with access to the same class/classroom management surface."
---

## Context
This story restores trust in Klassrumskartan by making the landing page a clean asset-management and launch surface. It deliberately keeps planning semantics out of the first interaction.

## Notes

- The landing page should feel like a teacher's library plus launch point, not a dashboard for planning logic.
- Modal behavior is part of the story, not a polish extra: viewport-bounded, scrollable, cancellable, and closable.
- Opening the planner must depend on selecting a class and a classroom, not on extra hidden requirements.
- Resume is a server-supported draft-lifecycle concept, but the landing page remains the default first screen.
- This story is now explicitly a recovery step rather than the final information architecture.
- The symmetric class/classroom selection model shipped here is transitional and is replaced by the class-first workspace direction in `ST-24-02`.
