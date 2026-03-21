---
type: prd
id: PRD-group-seating-studio-v0.3
title: "Curated App: Klassrumskartan"
status: active
product: "skriptoteket"
version: "0.3"
owners: "agents"
created: 2026-03-21
---

## Summary

Klassrumskartan is a teacher-first planning app where the **class** is the anchor and the
**classroom** is a secondary reusable context.

The refined v0.3 product direction replaces the earlier symmetric class/classroom launcher with a
class-first workflow:

- the teacher starts from a class
- the teacher can continue or start seating/grouping work inside that class
- seating is classroom-bound
- grouping may use a classroom, but does not have to
- one active draft exists per class and draft kind
- saved seating and grouping history belongs to the class

This keeps the happy path simple while preserving the data needed for later smart placement.

## Goals

- Make `Class` the primary teacher workspace anchor in the product.
- De-emphasize `Classroom` as a supporting asset rather than an equal first-step object.
- Let teachers continue active work per class without being forced to micromanage draft state.
- Separate `Seating` and `Grouping` as distinct units of work, with distinct drafts, save flows,
  and history.
- Keep the default workflow simple enough that a teacher can do manual planning without learning
  planning jargon.
- Persist meaningful teacher-approved history that can support later smart-placement features.

## Non-goals

- Treating grouping and seating as one blended working draft by default.
- Making historical drafts or saved arrangements the primary visual focus of the main view.
- Exposing smart-placement weights, solver language, or advanced rule controls in the default
  teacher workflow.
- Finalizing the smart-placement algorithm itself in this PRD version.
- Requiring a classroom to exist before a teacher can create classroom-agnostic groups.

## User Roles

- **Teacher**: creates and maintains classes and classrooms, plans grouping and seating for a
  class, saves arrangements, and later chooses whether smart placement should influence new work.
- **Admin / superuser**: governs app availability and infrastructure, but is not the primary
  workflow owner for this product surface.

## Requirements

### 1. Class-first main view

- The default main view emphasizes classes and active class work.
- Classrooms remain manageable from the app, but they are secondary in the visual hierarchy.
- The teacher should normally choose a class first, then decide what kind of work to do.
- The app should not force the teacher to choose a classroom before they know whether they are
  working with seating or grouping.

### 2. Class workspace

- Selecting a class opens a class-focused workspace rather than dropping directly into the planner.
- The class workspace can surface:
  - active seating draft
  - active grouping draft
  - saved seating history
  - saved grouping history
- Active work is prominent.
- History is accessible but secondary, for example through drawers, dropdowns, or expandable
  sections rather than through a cluttered dashboard.

### 3. Draft kinds and lifecycle

- `SeatingDraft` and `GroupingDraft` are separate draft kinds.
- Each class can have:
  - at most one active seating draft
  - at most one active grouping draft
- When a new draft of the same kind is created for the same class, the previous active draft of
  that kind is demoted to history automatically.
- Leaving the planner should not discard work by default.
- Discard must be explicit and teacher-understandable.

### 4. Classroom usage rules

- Seating requires a classroom because seating is inherently room-bound.
- Grouping may be created without a classroom.
- Grouping may also optionally use a classroom as context for smarter or calmer group formation.
- The teacher must understand whether grouping is classroom-aware or classroom-agnostic when they
  start that work.

### 5. Grouping workflow

- Grouping is a distinct task from seating.
- Teachers can create classroom-agnostic groups directly from a class roster.
- Teachers can optionally create grouping drafts informed by the current classroom context later.
- Saved groupings belong to the class.
- Grouping history is useful, but secondary compared with seating history.

### 6. Seating workflow

- Seating is a distinct task from grouping.
- Seating drafts are class-scoped and classroom-bound.
- Saved seating arrangements belong to the class.
- Seating history is the main future historical input for smart placement and student rotation.

### 7. Saved outputs and history

- The app distinguishes clearly between:
  - active draft
  - discarded draft
  - saved grouping
  - saved seating arrangement
- Teacher-approved saved arrangements are the preferred historical source for future smart
  placement.
- Abandoned or half-finished drafts should not be treated as equally valuable historical input.
- Saved arrangements can still be reviewed, revisited, reprinted, and later edited if necessary,
  but history should not dominate the default teacher workflow.

### 8. Smart placement boundaries

- Teacher-authored placement metadata remains a valid long-term direction.
- Future smart placement should primarily read:
  - saved seating history
  - class context
  - teacher-authored placement metadata
- Smart-placement settings remain secondary to the manual happy path and should stay out of the
  main workflow until explicitly approved.

### 9. Architecture constraints

- Preserve the useful normalized persistence work already established in ADR-0069.
- Keep curated-app bespoke APIs and the existing domain/application/UoW/repository layering.
- Reshape workflow semantics without falling back into a demo-first, solver-first UI.

## Metrics

- A teacher can identify a class as the main entry point without having to think in terms of
  equal class/classroom selectors.
- A teacher can continue active seating work and active grouping work independently for the same
  class.
- A teacher can create grouping work without choosing a classroom when they do not want room-aware
  grouping.
- A teacher can save a seating arrangement and later use that saved history as meaningful prior
  context.
- The visible workflow remains understandable without exposing advanced planner language.
