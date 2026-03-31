---
type: adr
id: ADR-0074
title: "Klassrumskartan Smart Assignment V1 Controls, Checkpoints, and Solver Boundaries"
status: accepted
owners: "agents"
deciders: ["architect"]
created: 2026-03-25
updated: 2026-03-30
links: ["PRD-group-seating-studio-v0.3", "ADR-0069", "ADR-0071", "ADR-0072", "EPIC-26", "EPIC-27", "REV-EPIC-27", "REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25", "ST-27-06", "ST-27-07"]
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

### 2. The visible smart model stays intentionally small, class-wide, and centered on `Regler`

The primary teacher-facing smart authoring surface for V1 is one dedicated `Regler` workspace in
the planner shell, not a per-student metadata drawer and not an always-open panel inside
`Sittplatser` or `Grupper`.

`Sittplatser` and `Grupper` may still show a small smart summary near the main `Smart` toggle, but
their task panes are not the home for rule creation or rule editing.

This means:

- rule creation and rule editing route through `Regler`
- a small settings affordance beside `Smart` opens mode-local Smart settings rather than routing
  directly away from the workspace
- that Smart settings drawer may summarize rules and host secondary mode-local controls such as
  `Historik`, `Klassrum`, and `Sittning`
- that compact drawer must not host inline rule creation or rule editing
- redundant active-rule count pills should not appear in task toolbars when richer rule surfaces
  already communicate the same state
- per-student metadata drawers remain secondary and must not become the primary smart-rule editor

Inside `Regler`, teachers author rules from a class-wide visual overview rather than from list
forms alone. Teachers select one rule tool from the active toolbar and click student tiles in the
shared class layout to author or update rules.

These visible smart rules are class-global and roster-owned even when they are authored from one
active class session. They are not owned by one draft.

The common teacher-facing smart controls for V1 are exactly:

- `Keep apart`
- `Keep near`
- `Use history`

Smart seating may additionally expose one seating-only rule:

- `Närmare läraren`

Smart grouping may additionally expose classroom-aware tuning inside Smart settings:

- classroom-aware grouping must stay separate from `Use history`
- the first-row grouping toolbar may keep one compact class selector, but not a second classroom
  context band or abstract helper labels
- `Klassrum` and `Sittning` belong in Smart settings, not in the command row
- the teacher-facing meaning is that smart grouping may use the selected classroom's seating
  context as a soft compactness lane when usable seating context exists

No visible weight sliders, planning profiles, rule-engine jargon, or per-student smart metadata
forms are exposed in the default V1 surface.

The dedicated `Regler` workspace must offer two map views over the same rule-selection model:

- `Planeringskarta` as the default:
  - keep the real classroom geometry
  - sort seats in simple reading order
  - place students alphabetically on that geometry so the teacher gets a spatial feel without
    inheriting the current draft arrangement
- `Sittschema` as an optional alternative:
  - mirror the current seating draft arrangement when one exists
  - stay unavailable when no current seating arrangement exists yet

These two views are alternative projections of the same authoring session, not separate workflows.

The first interaction model is explicitly:

- one active smart tool at a time in `Regler`
- switching tools clears any incomplete temporary selection
- `Esc` or `Rensa markering` clears the current temporary selection
- completed rule creation clears the temporary selection but keeps the tool active for repeated use
- switching between `Planeringskarta` and `Sittschema` keeps the active tool and current temporary
  selection intact
- active rules must remain visible in the main `Regler` summary/inspector surface rather than
  being hidden in a drawer

The `Regler` workspace should also make tool state and selection state unmistakable:

- tool identity should use clear icon-based affordances rather than text-color-only state
- the active tool should stay obvious through button state, cursor changes, and a short status
  line
- student selection should show clear hover, selected, and ordered multi-select feedback before
  the teacher commits a rule
- existing rules must be editable from the main rule summary surface, not just removable

The V1 authoring model is also intentionally asymmetric:

- `Närmare läraren` is a unary seating rule that teachers may toggle directly from the map and
  later edit or remove from the main `Regler` inspector like other active rules
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
- Grouping history remains mode-specific and label-insensitive:
  - grouping checkpoints are the primary grouping-history source
  - exact and near-repeat grouping memory must compare normalized student partitions and repeated
    student co-memberships rather than raw `group_id` or group-name matches
- Smart grouping may additionally read seating continuity through a separate non-history lane:
  - active seating draft first when classroom-aware grouping is enabled through the classroom
    control
  - eligible seating checkpoints second when no active seating draft exists
  - this classroom-aware lane is not grouping history
  - if no usable seating context exists, the run should fall back honestly instead of pretending
    that classroom-aware grouping was used
- When `Use history` is enabled but no eligible grouping checkpoints exist for the requested run,
  the system must not silently degrade to no-history behavior; it blocks the history-enabled run
  with a short teacher-facing message.

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
  - grouping history toggle state
  - classroom-aware grouping state tied to `Klassrum` + `Sittning` in Smart-inställningar
  - current seating/group arrangement state and bounded draft history
- export-backed checkpoints:
  - roster-scoped seating checkpoints with assignment-hash deduplication
  - roster-scoped grouping checkpoints with normalized grouping-partition identity and similarity
    semantics
  - normalized room-context identity plus stored template provenance for honest teacher-distance
    history
  - identical room geometry stays one checkpoint lane even when template ids differ or copied room
    metadata changes

Smart rules must not remain draft-owned as the end-state model.

Grouping should use its own label-insensitive grouping-partition hash and similarity model rather
than sharing the seating hash shape.

Teacher-facing `keep apart` and `keep near` rules are defined by visible seating geometry, not by
pairwise graph math.

An implementation may still use pairwise or other internal scoring as an optimization, but only if
that internal representation preserves the visible semantics below. Internal scoring must not widen
`Keep near` into broad same-side-of-room proximity or weaken `Keep apart` into merely "not
touching."

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
use seating context through the classroom-aware compactness lane when:

- classroom-aware grouping is enabled through `Klassrum` + `Sittning` in Smart-inställningar
- usable seating context exists
- the current seating draft may be read first as a live compactness input, with eligible seating
  checkpoints as fallback compactness input only
- same-group spread is penalized quadratically beyond a local elastic radius using seat-topology
  distance rather than raw pixels

The exact elastic radius and compactness weight curve should stay intentionally tunable through
simulations and discussion of outcomes versus the desired classroom behavior.

This keeps grouping honest instead of pretending teacher-distance is a shared cross-mode rule.

Teacher-distance is computed from an inferred teaching edge and teaching zone in the room model,
not from one arbitrary point alone.

For V1:

- the UI should recommend placing `Whiteboard` or `Kateder` so the teaching edge is explicit
- `Whiteboard` and `Kateder` together determine which wall is the teaching/front edge
- if no stronger cue exists, the default assumption is still that the teacher stands along the top
  edge in the standard top-down planner view
- if a `Kateder` exists, its lateral position should define the primary teaching zone along that
  front edge
- if only a `Whiteboard` exists, the board span should define the default teaching zone on that
  edge
- `Närmare läraren` in seating means a student should prefer seats that are nearer the teaching
  edge first and nearer the teaching zone second
- extreme corner seats must not repeatedly win solely because they are marginally closer to one
  point-anchor when a more central front-zone seat is equally teacher-near in normal teacher
  practice

Left/right remains meaningful in the teacher's normal top-down view of the room in the SPA.

### 8. Relationship-cluster semantics are best-effort, not brittle hard failures

`Keep apart` and `Keep near` are visible teacher-authored cluster rules for two or more students.

For V1:

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

## Consequences

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
