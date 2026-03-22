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

1. Optionally resume the latest work from the landing page.
2. Otherwise start from a class.
3. Inside that class, land in a neutral overview with a fixed toggle.
4. Switch to grouping or seating directly from that toggle.
5. Choose or switch classroom inside seating when the task needs it.
6. Save meaningful arrangements that later become useful history.

## Key product rules

- The class workspace stays neutral until the teacher chooses the task.
- The overview/grouping/seating toggle stays fixed in place while the selected workspace changes below it.
- Seating drafts can open before a classroom is chosen; room selection and room switching happen inside seating.
- Seat assignments and saved seating outcomes are classroom-bound.
- Grouping may be classroom-aware or classroom-agnostic.
- One active draft exists per class and draft kind.
- Starting a new draft of the same kind demotes the previous active draft to history.
- Switching back to overview or leaving the class workspace should normally preserve work.
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
