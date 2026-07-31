---
type: reference
id: REF-SKRIPT-PRD-curated-app-klassrumskartan-2
title: 'Curated App: Klassrumskartan'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: prd
summary: 'Curated App: Klassrumskartan'
---

## Product Outcome And Users

### Source: Summary

Klassrumskartan is a teacher-first planning app where the **class** is the anchor and the
**classroom** is a secondary reusable context.

The refined v0.3 product direction replaces the earlier symmetric class/classroom launcher with a
class-first workflow:

- the teacher may resume most recent work from the landing page
- the teacher starts from a class
- the teacher enters a neutral class workspace with a fixed mode toggle
- the teacher can continue or start seating/grouping work inside that class
- seating drafts can open before a classroom is chosen, but seat work remains classroom-bound once room context exists
- grouping may use a classroom, but does not have to
- one active draft exists per class and draft kind
- bounded undo/redo history belongs to the active draft inside the workspace
- durable file-vault artifacts belong to a later explicit export flow rather than ordinary save

This keeps the happy path simple while preserving the data needed for later smart placement.

### Source: Goals

- Make `Class` the primary teacher workspace anchor in the product.
- De-emphasize `Classroom` as a supporting asset rather than an equal first-step object.
- Let teachers continue active work per class without being forced to micromanage draft state.
- Separate `Seating` and `Grouping` as distinct units of work, with distinct drafts and
  mode-specific working controls.
- Keep the default workflow simple enough that a teacher can do manual planning without learning
  planning jargon.
- Keep recent draft history available for undo/redo without turning it into a separate saved-item
  model.
- Leave durable export/file-vault artifacts to a later explicit export flow.

### Source: Non-goals

- Treating grouping and seating as one blended working draft by default.
- Making historical drafts or later export artifacts the primary visual focus of the main view.
- Exposing smart-placement weights, solver language, or advanced rule controls in the default
  teacher workflow.
- Finalizing the smart-placement algorithm itself in this PRD version.
- Requiring a classroom to exist before a teacher can create classroom-agnostic groups.

### Source: User Roles

- **Teacher**: creates and maintains classes and classrooms, plans grouping and seating for a
  class, saves arrangements, and later chooses whether smart placement should influence new work.
- **Admin / superuser**: governs app availability and infrastructure, but is not the primary
  workflow owner for this product surface.

## Capability Direction

### Source: Requirements

### 1. Class-first main view

- The default main view emphasizes classes and active class work.
- Classrooms remain manageable from the app, but they are secondary in the visual hierarchy.
- The teacher should normally choose a class first, then decide what kind of work to do.
- The app should not force the teacher to choose a classroom before they know whether they are
  working with seating or grouping.

### 2. Class workspace

- Selecting a class opens a class-focused workspace rather than dropping directly into the planner.
- The class workspace starts neutral in `Översikt`.
- A fixed top toggle lets the teacher switch between:
  - `Översikt`
  - `Grupper`
  - `Sittplatser`
- The toggle stays in the same size and placement while the selected workspace changes below it.
- The landing page, not the class workspace, owns the top-level quick-resume affordance.
- Active work is prominent only after the teacher chooses the task.
- History is accessible but secondary, for example through drawers, dropdowns, or expandable
  sections rather than through a cluttered dashboard.
- The canonical design target is a desktop/laptop full-viewport workspace where overlays, drawers,
  and task surfaces may use the available screen real estate without collapsing into phone-shaped
  layouts by default.

### 2a. Viewport strategy is desktop-first

- Klassrumskartan is designed desktop-first because the core teacher workflows rely on broad,
  simultaneous spatial context such as student lists, group surfaces, seating canvases, and
  secondary overlays.
- Full-sized viewports are the canonical source for interaction design, information hierarchy, and
  workspace layout decisions.
- Tablet and phone experiences are ports of the desktop workflow and must adapt that workflow into
  something workable on smaller screens; they must not dictate the primary interaction model for
  the desktop experience.
- Secondary UI such as history drawers should prefer overlay behavior on full-sized viewports
  rather than pushing the main workspace down or replacing the active task surface unnecessarily.
- Curated-app breakpoints may diverge from generic app defaults when needed to preserve the
  teacher-first desktop workflow.

### 3. Draft kinds and lifecycle

- `SeatingDraft` and `GroupingDraft` are separate draft kinds.
- Each class can have:
  - at most one active seating draft
  - at most one active grouping draft
- When a new draft of the same kind is created for the same class, the previous active draft of
  that kind is demoted to history automatically.
- Switching to `Översikt` should not discard work by default.
- Leaving the class workspace through `Avsluta` should not discard work by default.
- Discard must be explicit and teacher-understandable.

### 4. Classroom usage rules

- Seating work is inherently room-bound once seat assignments begin, but the seating draft may
  exist before a classroom is chosen.
- Classroom selection and classroom switching belong inside the seating workspace.
- Grouping may be created without a classroom.
- Grouping may also optionally use a classroom as context for smarter or calmer group formation.
- The teacher must understand whether grouping is classroom-aware or classroom-agnostic when they
  start that work.

### 5. Grouping workflow

- Grouping is a distinct task from seating.
- Teachers can create classroom-agnostic groups directly from a class roster.
- Teachers can optionally create grouping drafts informed by the current classroom context later.
- Grouping drafts autosave continuously.
- Grouping exposes bounded in-workspace undo/redo history rather than a separate saved-groupings
  archive in this PRD version.

### 6. Seating workflow

- Seating is a distinct task from grouping.
- Seating drafts are class-scoped and room-contextual.
- Seating drafts autosave continuously.
- Seating exposes bounded in-workspace undo/redo history rather than a separate saved-arrangements
  archive in this PRD version.

### 7. Draft continuity, undo/redo, and later export

- The app distinguishes clearly between:
  - active draft
  - discarded draft
  - superseded draft
  - bounded in-workspace draft history
  - later explicit export artifact
- Recent draft history exists to support undo/redo inside the workspace; it is not a list of
  separate saved items.
- Abandoned or half-finished drafts should not be treated as equally valuable historical input for
  future smart placement.
- Later export/checkpoint artifacts can become teacher-approved historical input, but that is not
  the same thing as autosave or undo/redo state.

### 8. Smart placement boundaries

- Teacher-authored placement metadata remains a valid long-term direction.
- Future smart placement should primarily read:
  - later explicit seating checkpoints or export artifacts
  - class context
  - teacher-authored placement metadata
- Smart-placement settings remain secondary to the manual happy path and should stay out of the
  main workflow until explicitly approved.

### 9. Architecture constraints

- Preserve the useful normalized persistence work already established in ADR-SKRIPT-0069.
- Keep curated-app bespoke APIs and the existing domain/application/UoW/repository layering.
- Reshape workflow semantics without falling back into a demo-first, solver-first UI.

## Boundaries And Non-Goals

No separate source material was recorded for this section.

## Success Signals

### Source: Metrics

- A teacher can identify a class as the main entry point without having to think in terms of
  equal class/classroom selectors.
- A teacher can continue active seating work and active grouping work independently for the same
  class.
- A teacher can open seating directly from the class workspace and attach or switch classroom
  context inside the seating workspace.
- A teacher can create grouping work without choosing a classroom when they do not want room-aware
  grouping.
- A teacher can adjust a grouping or seating draft and recover recent steps through undo/redo
  without confusion about separate saved-item semantics.
- The visible workflow remains understandable without exposing advanced planner language.

## Governed Follow-Up

No separate source material was recorded for this section.
