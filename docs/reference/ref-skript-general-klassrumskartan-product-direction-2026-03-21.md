---
type: reference
id: REF-SKRIPT-GENERAL-klassrumskartan-product-direction-2026-03-21
title: Klassrumskartan product direction (2026-03-21)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-group-seating-studio-product-direction-2026-03-21
summary: Klassrumskartan product direction (2026-03-21)
---

## Overview

### Purpose And Summary

### One-sentence direction

Klassrumskartan is a teacher-first, **class-first** planning app where seating and grouping are
separate tasks, classrooms are reusable secondary context, and working history stays attached to
the active draft while durable artifacts come later through explicit export.

### Mental model

- `Class` is the anchor.
- `Classroom` is a reusable supporting asset.
- `Seating` and `Grouping` are separate units of work.
- Active work is prominent.
- History is available, but secondary.

### Workflow hierarchy

1. Optionally resume the latest work from the landing page.
2. Otherwise start from a class.
3. Inside that class, land in a neutral overview with a fixed toggle.
4. Switch to grouping or seating directly from that toggle.
5. Choose or switch classroom inside seating when the task needs it.
6. Work inside one active draft with autosave and bounded undo/redo.
7. Export durable artifacts later through an explicit action instead of treating autosave as file storage.

### Key product rules

- The class workspace stays neutral until the teacher chooses the task.
- The overview/grouping/seating toggle stays fixed in place while the selected workspace changes below it.
- Seating drafts can open before a classroom is chosen; room selection and room switching happen inside seating.
- Seat assignments remain classroom-bound once room context exists.
- Grouping may be classroom-aware or classroom-agnostic.
- One active draft exists per class and draft kind.
- Starting a new draft of the same kind demotes the previous active draft to history.
- Switching back to overview or leaving the class workspace should normally preserve work.
- Discard must be explicit.

### History rules

- Recent draft history exists for undo/redo inside the active workspace and should not be surfaced
  as a pile of separate saved items.
- Later explicit seating checkpoints or exports are the primary future source for smart placement
  and rotation.
- Grouping history matters, but is more secondary and operational.
- Abandoned drafts are not the preferred future algorithm input.

### UI rules

- Main view: emphasize classes.
- Classrooms remain manageable, but not equally prominent.
- Class workspace: show active seating/grouping work and secondary history.
- Planner: keep manual happy paths clear and avoid solver-first jargon in the default UI.

### Scope And Boundaries

No separate material is recorded in the source snapshot.

### Evidence And Follow-Up

The source snapshot is the governing reference record.

## Facts And Semantics

The migrated source records no separate statement for this section.

## Decisions And Interpretation

The migrated source records no separate statement for this section.
