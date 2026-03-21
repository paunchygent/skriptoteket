---
type: adr
id: ADR-0071
title: "Klassrumskartan Fundamentals Workflow, Draft Lifecycle, and Saved Artifacts"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-21
updated: 2026-03-21
links: ["ADR-0059", "ADR-0069", "ADR-0070", "ADR-0072", "PRD-group-seating-studio-v0.3", "EPIC-24", "REV-EPIC-24"]
---

## Context

ADR-0069 established the right normalized core: grouping and seating are separate assignment axes over one draft workspace. The later Slice 2 direction added useful backend groundwork, but the visible UX and saved-output model drifted into a solver-first shape that the teacher-facing product has not approved.

We need a contract that preserves the normalized draft core while resetting the teacher workflow around:

- landing page first
- class first, classroom secondary
- explicit grouping versus seating modes
- mode-specific randomize/save semantics
- named teacher-facing saved outputs
- server-owned draft lifecycle instead of ad hoc client-only resume

## Decision

### 1. The landing page is the default first interaction, but the product is class-first

Klassrumskartan opens to the landing page by default. That page should emphasize classes and
class-owned work. Classrooms remain manageable, but are secondary supporting assets.

The class-first workspace hierarchy is further clarified in ADR-0072. This ADR establishes the
workflow reset that makes that hierarchy possible.

The landing flow is responsible for:

- selecting or opening a class
- managing classes and classrooms
- offering explicit recovery/resume affordances for active work

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

ADR-0072 further constrains that lifecycle by making active work class-scoped and draft-kind
specific.

### 5. Randomize and save are mode-specific actions

`Slumpa` is not one global whole-workspace action in the fundamentals workflow.

- In `Grupper`, randomize creates or reshuffles groups only.
- In `Sittplatser`, randomize creates or reshuffles seats only.

Likewise, teacher save actions are mode-specific:

- save grouping
- save seating arrangement

Mode-specific save flows must not be blocked by unrelated findings from the other axis.

### 6. Saved outputs are named teacher-facing artifacts with immutable revisions

Teacher-facing saved outputs are not modeled as unnamed whole-workspace finalize snapshots.

Instead, the canonical fundamentals model is:

- a named saved artifact root owned by the teacher
- immutable revision records beneath that root

The root owns teacher-facing identity:

- name
- kind (`grouping` or `seating`)
- current revision pointer

The revision owns the frozen payload and source-draft provenance.

Editing a saved grouping or saved seating arrangement creates a new immutable revision and must not mutate the live working draft by accident.

### 7. Vault integration is a projection, not the source of truth

The planner domain remains authoritative for saved groupings and saved seating arrangements. The file vault receives a synchronized teacher-facing projection so the artifacts are discoverable alongside other saved work. The vault does not become the canonical source of planner truth.

### 8. Advanced logic remains hidden until separately approved

Constraint logic, pair rules, zone preferences, history rules, suggestion panels, and multi-slider weighting remain valid long-term goals, but they are hidden from the default teacher-facing workflow until explicitly defined and approved one slice at a time.

## Consequences

### Benefits

- The visible app now matches the teacher's actual mental model.
- The app can evolve toward a class-first workspace without undoing the fundamentals reset.
- Resume remains possible without undermining the landing page.
- Grouping and seating stop leaking into each other's save/randomize flows.
- Saved outputs become meaningful teacher-owned artifacts instead of anonymous technical snapshots.
- The normalized DDD core from ADR-0069 is preserved rather than discarded.

### Tradeoffs / Risks

- More backend contract work is required around draft lifecycle and saved-artifact persistence.
- Existing whole-workspace finalize/snapshot concepts may need to be retained only as advanced or audit/export-oriented mechanisms.
- The UI must resist re-exposing hidden advanced semantics until those concepts have their own approved stories.
