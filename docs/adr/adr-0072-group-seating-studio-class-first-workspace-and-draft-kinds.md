---
type: adr
id: ADR-0072
title: "Klassrumskartan Class-First Workspace and Draft-Kind Model"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-21
links: ["PRD-group-seating-studio-v0.3", "ADR-0069", "ADR-0071", "EPIC-24", "REV-EPIC-24"]
---

## Context

ADR-0071 reset Klassrumskartan toward a fundamentals-first workflow, but the product still needed
one more structural clarification: the teacher does not primarily think in terms of choosing one
class and one classroom as equal launch objects.

The teacher primarily thinks in terms of **a class**:

- continue active work for that class
- start new seating work for that class
- start new grouping work for that class
- review saved history for that class

The classroom remains important, but mainly as reusable context for room-bound planning.

## Decision

### 1. `Class` is the primary workspace anchor

The main teacher-facing navigation is class-first.

The app should emphasize:

- classes
- active work for a class
- saved history for a class

The app should de-emphasize classrooms as equal first-step launch objects.

### 2. `Classroom` is a secondary reusable context asset

Classrooms remain first-class managed assets, but they are secondary in the teacher workflow.

Teachers may still create, edit, and maintain classrooms centrally, but classroom selection happens
after class selection when the current task actually needs room context.

### 3. Grouping and seating use separate draft kinds

The teacher-facing working model uses separate draft kinds:

- `GroupingDraft`
- `SeatingDraft`

They are not one blended “planner draft” by default, even if the persistence model reuses shared
domain structures under the hood.

### 4. One active draft exists per class per draft kind

The lifecycle invariant is:

- at most one active grouping draft per class
- at most one active seating draft per class

When the teacher creates a new draft of the same kind for the same class, the previous active draft
of that kind is demoted to history automatically. The teacher should not need to micromanage which
draft is active.

### 5. Classroom requirements differ by draft kind

- `SeatingDraft` is class-scoped and classroom-bound.
- `GroupingDraft` is class-scoped and may be:
  - classroom-agnostic
  - classroom-aware

This distinction must be clear in both the UI and the API contract.

### 6. Exit, resume, discard, and save are different actions

The product must distinguish clearly between:

- leaving the planner while keeping active work resumable
- explicitly discarding a draft
- saving a teacher-approved grouping
- saving a teacher-approved seating arrangement

Leaving the planner does not discard by default. Discard is explicit.

### 7. History belongs to the class

The class owns its visible history:

- saved groupings
- saved seating arrangements
- prior drafts/history for the same class and draft kind

History must be accessible, but secondary to active work.

### 8. Future smart placement should prefer teacher-approved seating history

For future smart placement and rotation features, the preferred historical input is:

- saved seating history
- class context
- teacher-authored placement metadata

Saved grouping history remains useful, but is more secondary. Abandoned drafts are not the
preferred source for future algorithmic decisions.

## Consequences

### Benefits

- The visible app now matches the teacher's actual planning hierarchy.
- Grouping and seating stop implying that they are always one blended activity.
- Classroom selection becomes conditional and more intuitive.
- The future historical data model becomes cleaner because saved class-owned artifacts are
  distinguishable from ephemeral drafts.

### Tradeoffs / Risks

- Existing generic planner-draft assumptions need to be revisited in the API, UI, and persistence
  contracts.
- Some of the current ST-24-01 implementation is now explicitly transitional rather than final.
- Developers must resist reintroducing equal-weight class/classroom selection or blended draft
  semantics in later slices.
