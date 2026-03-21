---
type: reference
id: REF-group-seating-studio-product-direction-2026-03-21
title: "Klassrumskartan product direction (2026-03-21)"
status: active
owners: "agents"
created: 2026-03-21
topic: "group-seating-studio-product-direction"
links: ["PRD-group-seating-studio-v0.3", "ADR-0071", "ADR-0072", "EPIC-24"]
---

## One-sentence direction

Klassrumskartan is a teacher-first, **class-first** planning app where seating and grouping are
separate tasks, classrooms are reusable secondary context, and teacher-approved history stays
attached to the class.

## Mental model

- `Class` is the anchor.
- `Classroom` is a reusable supporting asset.
- `Seating` and `Grouping` are separate units of work.
- Active work is prominent.
- History is available, but secondary.

## Workflow hierarchy

1. Start from a class.
2. Inside that class, continue or start seating/grouping work.
3. Choose a classroom only when the task needs it.
4. Save meaningful arrangements that later become useful history.

## Key product rules

- Seating is classroom-bound.
- Grouping may be classroom-aware or classroom-agnostic.
- One active draft exists per class and draft kind.
- Starting a new draft of the same kind demotes the previous active draft to history.
- Leaving the planner should normally preserve work.
- Discard must be explicit.

## History rules

- Saved seating history is the primary future source for smart placement and rotation.
- Saved grouping history matters, but is more secondary and ephemeral.
- Abandoned drafts are not the preferred future algorithm input.

## UI rules

- Main view: emphasize classes.
- Classrooms remain manageable, but not equally prominent.
- Class workspace: show active seating/grouping work and secondary history.
- Planner: keep manual happy paths clear and avoid solver-first jargon in the default UI.
