---
type: adr
id: ADR-0074
title: "Klassrumskartan Smart Assignment V1 Controls, Checkpoints, and Solver Boundaries"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-25
links: ["PRD-group-seating-studio-v0.3", "ADR-0069", "ADR-0071", "ADR-0072", "EPIC-26", "EPIC-27", "REV-EPIC-27", "REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25"]
---

## Context

Klassrumskartan fundamentals are now in place:

- class-first workspace
- separate grouping and seating draft kinds
- bounded autosave plus undo/redo
- explicit seating export artifacts

At the same time, the old solver-first classroom-planner surface was intentionally pruned from the
active codebase because it exposed the wrong teacher-facing contract. We now need to reintroduce
smart assignment through a new, deliberately narrow V1 shape that:

- preserves the fundamentals-first workflow
- keeps smart logic secondary and teacher-readable
- uses explicit checkpoints instead of draft history
- avoids reviving the removed multi-slider / suggestion-panel surface
- deletes the old visible metadata semantics instead of trying to map them forward

## Decision

### 1. The main action stays `Slumpa`, with one small persisted `Smart` toggle per mode

Each planner mode keeps its main `Slumpa` action:

- `Grupper`
- `Sittplatser`

Each mode gains its own small `Smart` toggle beside that action.

- New drafts default `Smart` to `off`.
- Toggle state persists per draft.
- `Smart` is independent per mode, so the teacher may use smart seating while keeping grouping
  random, or the reverse.

This preserves a low-button surface while keeping the difference between random and smart behavior
explicit.

### 2. The visible smart model stays intentionally small

The common teacher-facing smart controls for V1 are exactly:

- `Support seat`
- `Keep apart`
- `Keep near`
- `Use history`

No visible weight sliders, planning profiles, or rule-engine jargon are exposed in the default V1
surface.

Smart grouping may additionally expose one explicit mode-specific toggle:

- `Ska hur nära de sitter räknas?`

This replaces a more abstract "classroom-aware" explanation with a clearer teacher question.

### 3. Old visible metadata semantics are deleted without migration

The visible planner semantics for:

- notes
- teacher proximity
- stability preference

are removed from the smart-assignment lane and not migrated forward. There are no real users yet,
so the repo should take the cleaner reset:

- hard-delete old visible semantics
- remove corresponding runtime compatibility paths
- introduce the new smart-assignment model fresh

### 4. History comes only from explicit export-backed checkpoints

Algorithmic history input must never read:

- autosave state
- undo/redo stacks
- raw drafts
- abandoned drafts

V1 history sources are explicit export-backed checkpoints only.

- Seating exports with changed assignments create seating checkpoints.
- Identical repeated exports do not create duplicate checkpoints.
- Seating checkpoint dedupe uses a canonical seating assignment hash:
  - deterministic placed student-to-seat assignments
  - unplaced students
  - normalized ordering only
  - no export layout, print styling, or artifact metadata
- Grouping remains mode-specific when grouping exports exist later, and grouping checkpoints then
  become the primary grouping-history source.
- Smart grouping may additionally read seating checkpoints as a secondary source for:
  - relation carry-over
  - optional seating-distance signals
- When `Use history` is enabled but no eligible checkpoints exist for the requested run, the system
  must not silently degrade to no-history behavior; it blocks the history-enabled run with a short
  teacher-facing message.

### 5. Persistence is relational and normalized

The smart-assignment persistence model uses dedicated relational persistence rather than ad hoc
JSON blobs. The exact table names may vary during implementation, but the normalized shape should
cover:

- per-student smart preferences (including `support_seat`)
- `keep_near` pairs
- `keep_apart` sets and set membership
- export-backed checkpoints with assignment-hash deduplication
- per-draft smart toggle state
- grouping seating-distance toggle state

Grouping should use its own later mode-specific assignment hash once grouping export checkpoints
exist, rather than sharing the seating hash shape.

Teacher-facing `keep apart` sets may still compile into weighted pairwise repel relations at solve
time; the pairwise graph is an internal representation, not the visible authoring model.

### 6. The backend remains authoritative for smart scoring and search

The authoritative smart-assignment logic lives server-side in Python.

- Domain layer owns pure scoring and search logic.
- Application layer loads drafts, checkpoints, room context, and smart rules.
- Web/API exposes bespoke smart-assignment endpoints.
- Frontend renders results, toggle state, and short explanations.

The client may keep cheap local hints, but it must not duplicate the full solver.

### 7. Smart grouping uses `Support seat` only when seating distance is enabled

`Support seat` is always meaningful in seating.

For grouping, it only influences the solver when:

- the seating-distance signal is enabled
- usable seating context exists

Otherwise it is ignored in grouping to avoid fake semantics.

### 8. Explanations stay short and teacher-facing

The UI may show:

- one concise result summary
- a short list of teacher-language reasons
- one low-emphasis follow-up action such as `En smart variant till`

If `En smart variant till` cannot produce a materially different assignment, the UI should show a
short no-further-variant message instead of repeating the same result as though it were new.

The UI must not show:

- score vectors
- raw solver breakdowns
- internal weights
- optimization jargon

## Consequences

### Benefits

- Smart assignment re-enters the product through a clean, explicitly approved contract.
- The teacher-facing model stays small and understandable.
- Export-backed checkpoints align with the current PRD and ADR direction.
- The repo avoids a spaghetti-style bridge between old visible metadata and the new smart model.
- Grouping can benefit from seating context through an explicit, understandable toggle instead of a
  vague "classroom-aware" label.

### Tradeoffs / Risks

- `Slumpa` semantics become mode + toggle dependent, so the UI copy must be especially clear.
- Grouping history remains partially dependent on seating checkpoints until grouping checkpoints
  exist later through explicit grouping export artifacts.
- Hard deletion of old semantics is cleaner, but it removes any fallback path for recovering those
  values later.
- The backend/API surface must be reintroduced carefully so it does not drift back toward the
  superseded solver-first shell.
