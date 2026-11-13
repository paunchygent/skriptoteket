---
type: adr
id: ADR-SKRIPT-0074-PART-03
title: Klassrumskartan Smart Assignment V1 Controls, Checkpoints, and Solver Boundaries
  — part 03
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: ADR-SKRIPT-0074
part: 3
---

- `Keep apart` in grouping means those students should be spread across different groups whenever
  possible
- `Keep near` in grouping means those students should prefer the same group whenever the rule set
  and current group structure allow it
- when classroom-aware grouping is enabled and usable seating context exists, same-group students
  should also prefer spatially compact local clusters rather than being split across distant parts
  of the room
- classroom-aware grouping is a soft compactness objective, not a brittle hard invalidation
  threshold
- the solver should penalize same-group spread quadratically beyond a local elastic radius rather
  than treating every non-adjacent placement as equally bad
- if there are fewer groups than students in one keep-apart cluster, the solver should maximize
  spread and minimize collisions rather than failing
- if one keep-near cluster cannot fit perfectly because of conflicting rules or current group
  structure, the solver should minimize the split instead of scattering those students broadly
- `Keep apart` in seating means those students should be meaningfully separated, not merely "not in
  direct orthogonal adjacency"
- direct left/right adjacency in the same row is not acceptable when a stronger layout exists
- direct above/below adjacency in the same column is not acceptable when a stronger layout exists
- immediate diagonal neighbors are also not acceptable when the room has clear space for stronger
  separation
- same-row or same-column placements remain acceptable when one full seat buffer stays between the
  students
- greater separation than the minimum should be preferred when the solver has room to do so, and
  the solver should prefer clearer row/column distance or different local seating blocks over tiny
  visual separators alone
- `Keep near` in seating means the selected students should form one immediate local cluster, not
  merely sit somewhere in the same broad area of the room
- direct left/right adjacency in the same row or direct above/below adjacency in the same column is
  the preferred satisfaction for a near-pair
- for a 2-student near-pair, diagonal or one-seat-buffer placements are fallback/tradeoff outcomes
  rather than normal successful pair layouts
- a one-step looser same-row or same-column fallback is acceptable only when the room or other
  rules prevent direct adjacency
- for three or more students, one connected compact cluster is ideal; if that is impossible, the
  solver should keep a connected core and minimize the cluster's diameter rather than scattering the
  students across unrelated rows and columns
- layouts that place near-cluster members in different rows and different columns with no direct
  line relation are not acceptable when a stronger compact placement exists

These are strong objectives, but they remain best-effort when room shape, group count, or other
teacher-authored rules make a perfect result impossible.

### 9. Smart reruns prefer different good candidates when the search space allows it

`Smart` assignment must not collapse into one visibly deterministic answer when several strong
rule-respecting candidates exist.

For V1:

- the primary objective remains smart quality under the teacher-authored rules
- rerun diversity is a secondary objective, not a reason to accept obviously weaker placements
- for smart grouping, rerun diversity sits below explicit relation rules, classroom-aware
  compactness when enabled, and grouping-history anti-repeat memory
- repeated smart runs should prefer a materially different valid assignment from the current draft
  arrangement when multiple good candidates exist
- the backend may achieve this through randomized tie-breaking, multi-start search, or a soft
  diversity penalty against the current assignment hash or another equivalent internal mechanism
- this diversity policy is internal to the smart run and must not become a new teacher-facing
  randomness control

If the valid search space is genuinely narrow because the room, group count, or current rules leave
little room for variation, the smart run may return another near-identical best result.

### 10. Explanations stay short and teacher-facing

The UI may show:

- one concise result summary
- a short list of teacher-language reasons
- one short rerun-related message only when the valid search space is genuinely narrow

The UI must not show:

- score vectors
- raw solver breakdowns
- internal weights
- optimization jargon

### 11. Frontend planner persistence must mirror the split ownership model honestly

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

### Consequences

### Benefits

- Smart assignment re-enters the product through a clean, explicitly approved contract.
- The teacher-facing model stays small and understandable.
- The primary editing flow matches the teacher's class-wide mental model instead of hiding smart
  rules in individual student drawers or bloating the seating/grouping task panes.
- `Planeringskarta` gives teachers one normalized, easy-to-scan rule-authoring view while
  `Sittschema` remains available for teachers who prefer the exact current seating mental model.
- Class-global teacher intentions stay stable across drafts instead of being reauthored per draft.
- Export-backed checkpoints align with the current PRD and ADR direction.
- The repo avoids a spaghetti-style bridge between old visible metadata and the new smart model.
- Grouping can benefit from seating context through one classroom-control-owned compactness lane
  instead of a vague "classroom-aware" label or a hidden history synonym.
- Frontend transition semantics now match the backend ownership boundary instead of re-coupling the
  lanes through one shared save contract.

### Tradeoffs / Risks

- `Slumpa` semantics become mode + toggle dependent, so the UI copy must be especially clear.
- Smart reruns need enough diversity pressure that teachers do not experience the smart path as
  one frozen answer whenever several good alternatives exist.
- The `Regler` workspace adds one more top-level planner mode, so the affordance and labeling must
  stay obvious.
- The visual class-wide rule-authoring surface must stay fast and legible so toolbar state does not
  become confusing and the task panes do not regress into drawer-first editing.
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
