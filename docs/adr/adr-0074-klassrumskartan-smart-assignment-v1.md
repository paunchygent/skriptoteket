---
type: adr
id: ADR-0074
title: "Klassrumskartan Smart Assignment V1 Controls, Checkpoints, and Solver Boundaries"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-25
links: ["PRD-group-seating-studio-v0.3", "ADR-0069", "ADR-0071", "ADR-0072", "EPIC-26", "EPIC-27", "REV-EPIC-27", "REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25", "ST-27-06"]
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

### 2. The visible smart model stays intentionally small, class-wide, and tool-based

The primary teacher-facing smart authoring surface for V1 is a class-wide visual overview in the
active workspace, not a per-student metadata drawer. Teachers select one rule tool from the active
toolbar and click student tiles in the shared class layout to author or remove rules.

These visible smart rules are class-global and roster-owned even when they are authored from one
active seating or grouping workspace. They are not owned by one draft.

The common teacher-facing smart controls for V1 are exactly:

- `Keep apart`
- `Keep near`
- `Use history`

Smart seating may additionally expose one seating-only rule:

- `Närmare läraren`

Smart grouping may additionally expose one explicit mode-specific toggle:

- `Ska hur nära de sitter räknas?`

This replaces a more abstract "classroom-aware" explanation with a clearer teacher question.

No visible weight sliders, planning profiles, rule-engine jargon, or per-student smart metadata
forms are exposed in the default V1 surface.

The first interaction model is explicitly:

- one active smart tool at a time in the seating/grouping workspace
- switching tools clears any incomplete temporary selection
- `Esc` or `Rensa markering` clears the current temporary selection
- completed rule creation clears the temporary selection but keeps the tool active for repeated use
- active rules must remain visible in a main workspace summary surface rather than being hidden in
  a drawer

The V1 authoring model is also intentionally asymmetric:

- `Närmare läraren` is a unary seating rule authored by clicking one student tile to toggle the
  rule on or off immediately
- `Keep apart` and `Keep near` are relationship-cluster tools authored by selecting two or more
  student tiles and committing one explicit rule from that temporary selection
- relationship clusters must not overlap in V1; one student may belong to at most one visible
  relationship rule at a time

`Närmare läraren` may coexist with one relationship cluster because it is a seating-only unary
rule, not a relationship cluster.

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

Checkpoints are history artifacts only. They may keep source-draft provenance if useful, but they
must not become the authoritative home for class-global smart rules.

When `Use history` is enabled for seating, those same eligible seating checkpoints should also
power a soft fairness objective for teacher-distance over time:

- students without an explicit `Närmare läraren` rule should tend toward a more even mean
  teacher-distance across multiple eligible checkpoints
- students who have recently sat closer to the teacher should become somewhat more likely to be
  seated further away later
- students who have recently sat further away should become somewhat more likely to be seated
  nearer later

This is a balancing goal, not a one-run guarantee.

### 5. Persistence is relational and normalized

The smart-assignment persistence model uses dedicated relational persistence rather than ad hoc
JSON blobs. The exact table names may vary during implementation, but the normalized shape should
separate three ownership lanes:

- roster-global smart rules:
  - seating-only near-teacher preferences
  - `keep_near` sets and set membership
  - `keep_apart` sets and set membership
- draft-local workspace state:
  - per-draft smart toggle state
  - grouping seating-distance toggle state
  - current seating/group arrangement state and bounded draft history
- export-backed checkpoints:
  - roster-scoped seating checkpoints with assignment-hash deduplication
  - room/template context needed for honest teacher-distance history

Smart rules must not remain draft-owned as the end-state model.

Grouping should use its own later mode-specific assignment hash once grouping export checkpoints
exist, rather than sharing the seating hash shape.

Teacher-facing `keep apart` sets and `keep near` sets may still compile into weighted pairwise
relations at solve time; the pairwise graph is an internal representation, not the visible
authoring model.

### 6. The backend remains authoritative for smart scoring and search

The authoritative smart-assignment logic lives server-side in Python.

- Domain layer owns pure scoring and search logic.
- Application layer loads drafts, checkpoints, room context, and roster-scoped smart rules.
- Web/API exposes bespoke smart-assignment endpoints.
- Frontend renders results, toggle state, and short explanations.

The client may keep cheap local hints, but it must not duplicate the full solver.

### 7. `Närmare läraren` is seating-only and must not leak into grouping

`Närmare läraren` is meaningful only in seating.

It acts as an explicit exception to the default teacher-distance fairness balancing.

Grouping must not expose or consume that teacher-distance preference directly. Grouping may still
use seating distance through the explicit seat-distance toggle when:

- the seating-distance signal is enabled
- usable seating context exists

This keeps grouping honest instead of pretending teacher-distance is a shared cross-mode rule.

Teacher-distance is computed from one inferred teaching anchor in the room model.

For V1:

- the UI should recommend placing `Whiteboard` or `Kateder` so the teaching edge is explicit
- if no stronger cue exists, the default assumption is that the teacher stands at the top-middle
  of the room in the standard top-down planner view
- if the whiteboard or teaching cues are placed on another wall, that wall becomes the teaching
  edge instead
- if a teacher desk is offset toward one side, the inferred anchor may shift somewhat toward that
  side while staying near the central teaching position rather than snapping to the desk tile

Left/right remains meaningful in the teacher's normal top-down view of the room in the SPA.

### 8. Relationship-cluster semantics are best-effort, not brittle hard failures

`Keep apart` and `Keep near` are visible teacher-authored cluster rules for two or more students.

For V1:

- `Keep apart` in grouping means those students should be spread across different groups whenever
  possible
- if there are fewer groups than students in one keep-apart cluster, the solver should maximize
  spread and minimize collisions rather than failing
- `Keep apart` in seating means those students should not be seated in direct orthogonal adjacency:
  - not immediately left/right in the same row
  - not immediately above/below in the same column
- diagonal placement with one row and one column of separation is acceptable when needed
- greater spacing than the minimum should be preferred when the solver has room to do so
- `Keep near` in seating means the selected students should be placed in the same local vicinity,
  not necessarily as one exact shoulder-to-shoulder pair
- direct adjacency is ideal for `Keep near`, but a small nearby cluster is still acceptable

These are strong objectives, but they remain best-effort when room shape, group count, or other
teacher-authored rules make a perfect result impossible.

### 9. Explanations stay short and teacher-facing

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

### 10. Frontend planner persistence must mirror the split ownership model honestly

The frontend session shape must not behave like one shared save machine after the backend split to
roster-global smart rules and draft-local arrangement state.

The approved frontend model is:

- one thin session controller as the only source of truth for active session token, draft ID, and
  roster ID
- one draft lane for draft-local arrangement state, draft-local toggles, autosave, undo/redo
  preparation, and draft persistence conflict/error handling
- one roster smart-rule lane for roster-global smart-rule hydration/persistence and its own
  conflict/error handling
- one separate smart-rule authoring UI bucket for active tool, temporary selection, and local
  teacher feedback

The lanes may not share one planner-wide timer, one generic flush operation, or one planner-global
persistence-truth status/message.

The transition semantics are also locked:

- `loadWorkspace` is draft-first and fail-safe:
  - clear old smart rules immediately
  - hydrate the current draft lane first
  - disable smart-rule authoring until the current roster's smart rules hydrate
  - if smart-rule hydration fails, keep the draft usable and offer retry without turning that GET
    failure into a planner-wide save conflict
- `undo` / `redo` flush only the draft lane
- `abandonDraft` flushes the smart-rule lane first, discards pending draft-local edits explicitly,
  and any continue-anyway path must explicitly say class-wide smart-rule edits will be lost if the
  smart-rule lane cannot save
- `clearWorkspace` is pure teardown, must not imply save, and must ignore late responses so
  cleared planner state cannot repopulate afterward
- `exitPlanner` waits on the relevant lanes but returns an explicit confirm-discard state on
  timeout instead of silently leaving or silently dropping pending work
- `confirmExitWithoutWaiting` discards both lanes explicitly and ignores late responses after the
  planner tears down
- overview return and route exit use explicit lane policies rather than one generic flush path
- leaving the planner screen successfully resets the smart-rule UI bucket
- save/load acknowledgements must not decide smart-rule UI resets

Each persistence lane keeps its own debounce timer, dirty state, save state, and conflict/error
state. Smart-rule hydration failure remains distinct from smart-rule persistence conflict/error.
This frontend cut-over should land as dedicated session/lane/UI modules with `useClassroomState.ts`
reduced to a thin composition surface, not as another expansion of one umbrella store.

## Consequences

### Benefits

- Smart assignment re-enters the product through a clean, explicitly approved contract.
- The teacher-facing model stays small and understandable.
- The primary editing flow matches the teacher's class-wide mental model instead of hiding smart
  rules in individual student drawers.
- Class-global teacher intentions stay stable across drafts instead of being reauthored per draft.
- Export-backed checkpoints align with the current PRD and ADR direction.
- The repo avoids a spaghetti-style bridge between old visible metadata and the new smart model.
- Grouping can benefit from seating context through an explicit, understandable toggle instead of a
  vague "classroom-aware" label.
- Frontend transition semantics now match the backend ownership boundary instead of re-coupling the
  lanes through one shared save contract.

### Tradeoffs / Risks

- `Slumpa` semantics become mode + toggle dependent, so the UI copy must be especially clear.
- The visual class-wide rule-authoring surface must stay fast and legible so toolbar state does not
  become confusing.
- Grouping history remains partially dependent on seating checkpoints until grouping checkpoints
  exist later through explicit grouping export artifacts.
- Hard deletion of old semantics is cleaner, but it removes any fallback path for recovering those
  values later.
- The backend/API surface must be reintroduced carefully so it does not drift back toward the
  superseded solver-first shell.
- The frontend cut-over is intentionally larger because the shared planner autosave contract must
  be deleted, not patched with more conditional guards.
- Draft-first fail-safe workspace loading creates a partially available planner state when
  smart-rule hydration fails, so teacher-facing disablement and retry messaging must stay clear.
