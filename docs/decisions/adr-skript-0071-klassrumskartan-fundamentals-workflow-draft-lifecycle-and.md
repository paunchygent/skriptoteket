---
type: adr
id: ADR-SKRIPT-0071
title: Klassrumskartan Fundamentals Workflow, Draft Lifecycle, and Export Artifacts
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- architect
retired_ids:
- ADR-0071
---

## Context

### Source: Context

ADR-SKRIPT-0069 established the right normalized core: grouping and seating are separate assignment axes over one draft workspace. The later Slice 2 direction added useful backend groundwork, but the visible UX and saved-output model drifted into a solver-first shape that the teacher-facing product has not approved.

We need a contract that preserves the normalized draft core while resetting the teacher workflow around:

- landing page first
- class first, classroom secondary
- explicit grouping versus seating modes
- mode-specific randomize/save semantics
- bounded draft history for undo/redo
- later explicit export artifacts
- server-owned draft lifecycle instead of ad hoc client-only resume

## Decision

### Source: Decision

### 1. The landing page is the default first interaction, but the product is class-first

Klassrumskartan opens to the landing page by default. That page should emphasize classes and
class-owned work. Classrooms remain manageable, but are secondary supporting assets.

The class-first workspace hierarchy is further clarified in ADR-SKRIPT-0072. This ADR establishes the
workflow reset that makes that hierarchy possible.

The landing flow is responsible for:

- selecting or opening a class
- managing classes and classrooms
- offering explicit recovery/resume affordances for active work

The fixed workspace selector for `Översikt`, `Grupper`, and `Sittplatser` belongs inside the
class workspace once the teacher has selected a class.

Resume remains supported, but it is no longer allowed to auto-hijack the teacher directly into the planner on load.

### 2. Grouping and seating are separate teacher-facing modes

The only top-level planner modes in the default workflow are:

- `Grupper`
- `Sittplatser`

Mode separation is not only visual. It must be reflected in:

- routing/navigation
- randomize actions
- save actions
- validation scope
- visible teacher language

The persisted normalized draft may continue to contain both axes internally for now, but the
default UI must teach one task at a time and must not imply that grouping and seating are one
blended teacher task.

The class workspace should start neutral in `Översikt`, with the same top-level toggle remaining in
place as the teacher switches between overview, grouping, and seating.

### 3. `lesson_mode_id` is not a teacher-facing top-level mode

The persisted `lesson_mode_id` may remain internally for now, but it is removed from the default teacher-facing workflow. If it survives long-term, it must be reframed as a separate preset concept rather than competing with `Grupper` / `Sittplatser` as visible top-level modes.

### 4. Drafts are ephemeral working state with explicit lifecycle

Drafts are server-owned working state, not disposable client pointers. Drafts gain explicit lifecycle semantics such as:

- `active`
- `abandoned`
- `superseded`

The server becomes responsible for resolving whether an existing compatible active draft should be
resumed or whether a new draft should be created. This prevents silent accumulation of orphaned
mutable drafts.

ADR-SKRIPT-0072 further constrains that lifecycle by making active work class-scoped and draft-kind
specific.

### 5. Randomize and working controls are mode-specific actions

`Slumpa` is not one global whole-workspace action in the fundamentals workflow.

- In `Grupper`, randomize creates or reshuffles groups only.
- In `Sittplatser`, randomize creates or reshuffles seats only.

Likewise, teacher save actions are mode-specific:

- draft undo/redo in grouping
- draft undo/redo in seating
- later export of the current grouping draft
- later export of the current seating draft

Mode-specific working controls must not be blocked by unrelated findings from the other axis.

### 6. Draft history is bounded working state, not a saved-item archive

Recent draft history exists to support undo and redo inside the active workspace.

The canonical fundamentals model is:

- one active draft per class and draft kind
- autosave of the current draft state
- a bounded recent-history buffer for undo/redo
- configurable history depth, with 10 steps as the current planning target

This recent-history buffer:

- is part of draft working state
- is teacher-accessible through workspace undo/redo controls
- is not a list of separate saved files or named artifacts
- must remain easy to reason about and cheap to tune

### 7. Durable file-vault artifacts come from explicit export, not autosave

Normal draft autosave and undo/redo history must not masquerade as teacher-facing file-vault
artifacts.

When durable artifacts are introduced later, they must come from an explicit export/checkpoint
action on the current draft. The planner domain remains authoritative for draft state. The file
vault may later receive exported projections, but the vault does not become the canonical source
of planner truth.

### 8. Advanced logic remains hidden until separately approved

Constraint logic, pair rules, zone preferences, history rules, suggestion panels, and multi-slider weighting remain valid long-term goals, but they are hidden from the default teacher-facing workflow until explicitly defined and approved one slice at a time.

### 9. The primary workflow is designed desktop-first

The canonical interaction model for Klassrumskartan is the teacher's laptop-sized workspace.

That means:

- full-sized viewports are the primary source for layout, task sequencing, and visual hierarchy
- grouping and seating surfaces may rely on wide working space, layered overlays, and simultaneous
  context where that improves the teacher workflow
- smaller tablet/phone layouts are ports of that desktop workflow and must translate it into a
  workable constrained layout rather than dictating the core design language
- secondary surfaces such as history drawers should prefer overlay behavior on full-sized
  viewports instead of pushing the main workspace down unless a later approved story explicitly
  requires a different pattern

## Non-Decisions

The source does not authorize additional alternatives or scope beyond the decision above.

## Consequences

### Source: Consequences

### Benefits

- The visible app now matches the teacher's actual mental model.
- The app can evolve toward a class-first workspace without undoing the fundamentals reset.
- Resume remains possible without undermining the landing page.
- Grouping and seating stop leaking into each other's save/randomize flows.
- Draft continuity becomes much easier to understand because autosave, undo/redo, and later export
  no longer compete as overlapping save concepts.
- The normalized DDD core from ADR-SKRIPT-0069 is preserved rather than discarded.

### Tradeoffs / Risks

- More backend contract work is required around draft lifecycle and bounded draft-history
  persistence.
- Existing whole-workspace finalize/snapshot concepts may need to be retained only as advanced or audit/export-oriented mechanisms.
- The UI must resist re-exposing hidden advanced semantics until those concepts have their own approved stories.
