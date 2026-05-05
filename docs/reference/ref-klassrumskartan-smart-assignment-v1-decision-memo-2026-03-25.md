---
type: reference
id: REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25
title: "Klassrumskartan smart assignment v1 decision memo (2026-03-25)"
status: active
owners: "agents"
created: 2026-03-25
updated: 2026-05-05
topic: "smart-assignment"
links: ["PRD-group-seating-studio-v0.3", "ADR-0071", "ADR-0072", "ADR-0074", "EPIC-27", "REV-EPIC-27", "ST-27-06", "ST-27-07", "ST-27-09"]
---

## Summary

This memo locks the first approved product shape for Klassrumskartan smart assignment work after
the fundamentals and export lanes. The goal is to reintroduce smart behavior through a deliberately
small teacher-facing model while keeping the authoritative solver hidden, export-backed history
explicit, and the current class-first workflow intact.

## Locked decisions

- Keep one main `Slumpa` action per mode and add a small persisted `Smart` toggle beside it.
- Persist the `Smart` toggle state per draft, with `off` as the default for new drafts.
- Remove the old visible planner metadata semantics (`notes`, teacher proximity, stability) from
  the planner surface entirely.
- Delete the old smart-adjacent visible semantics and related persistence without migration or
  compatibility work because there are no real users yet.
- Mirror the backend ownership split in the frontend session shape:
  - one session controller owns the active session token plus active draft/roster identity
  - one draft lane owns draft-local persistence and history preparation
  - one smart-rule lane owns roster-global smart-rule hydration/persistence
  - one separate UI bucket owns active tool, temporary selection, and local smart-rule feedback
- Keep one debounce timer per persistence lane; do not keep one planner-wide timer, flush
  contract, or persistence-truth status.
- Keep the primary smart authoring flow class-wide and visual rather than per-student:
  - `Keep apart`
  - `Keep near`
  - `Use history`
- Make `Regler` the dedicated smart-rule authoring workspace in the planner shell.
- Keep `Sittplatser` and `Grupper` calm:
  - they may show compact smart summaries and mode-local smart toggles
  - rule creation/editing routes through a small settings affordance near `Smart` that opens
    `Regler`
  - task-pane drawers or overflow menus must not become full rule editors
- Give `Regler` two map views over the same authoring session:
  - as refined by `ST-27-09`, the classroom-faithful view is the default when a classroom exists
  - `Planeringskarta` remains available as a deliberate abstract planning view and always uses one
    clean alphabetical planning layout that does not inherit classroom geometry or the current
    seating draft
  - `Sittschema` mirrors the current seating draft when it exists; future teacher-facing copy
    should call that destination `Klassrumsvyn` / `klassrumsvyn`
- Add one seating-only rule:
  - `Närmare läraren`
- Add one hard classroom-template-scoped seating rule:
  - `Fast plats`
  - it binds one roster student to one physical seat
  - it can be authored only from the classroom-faithful view
  - from `Planeringskarta`, clicking the tool prompts:
    `Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?`
  - `Ja` switches to the classroom view and activates the tool; `Nej` or close keeps the teacher on
    `Planeringskarta`
- Lock the first interaction model:
  - one active smart tool at a time
  - `Närmare läraren` is a unary click-to-toggle rule
  - `Keep apart` / `Keep near` are 2+ student cluster rules authored through multi-select plus an
    explicit commit action
  - incomplete selections are cleared by `Esc`, `Rensa markering`, or tool changes
  - completed rule creation clears the temporary selection but keeps the tool active
- Block overlapping relationship clusters in V1:
  - one student may belong to at most one `Keep apart` or `Keep near` cluster at a time
  - `Närmare läraren` may coexist because it is not a relationship cluster
- Allow one grouping-only mode-specific toggle for seat-distance input, such as
  `Ska hur nära de sitter räknas?`; it is not a fifth shared control.
- Use export-backed checkpoints only. Autosave, undo/redo, abandoned drafts, and raw draft
  history never count as algorithmic history input.
- When `Use history` is enabled for seating, smart seating should also try to balance
  teacher-distance more fairly over time for students who do not have an explicit
  `Närmare läraren` rule.
- Deduplicate checkpoint creation by assignment hash so repeated identical exports do not create
  extra checkpoint records.
- Ship smart behavior in both `Sittplatser` and `Grupper` from day one, but keep the mode toggles
  independent so the teacher can opt into one and keep the other random.
- Let smart grouping use seating distance only through an explicit teacher-facing toggle such as
  `Ska hur nära de sitter räknas?`, which is easier to reason about than a generic
  "classroom-aware" label.
- Keep `Närmare läraren` as a seating-only rule; grouping must not pretend teacher-distance is a
  shared cross-mode input.
- Keep smart reruns on the same `Slumpa` action; do not introduce a separate alternate-result
  button for rerunning the smart path.
- When several strong rule-respecting candidates exist, repeated smart runs should prefer a
  materially different valid result rather than collapsing onto the current assignment hash.
- The backend may achieve that through randomized tie-breaking, multi-start search, or an internal
  diversity penalty against the current assignment hash or another equivalent mechanism.
- Treat relation rules as strong best-effort objectives rather than brittle hard requirements:
  - `Keep apart` in seating means no immediate orthogonal or diagonal adjacency when possible,
    while same-row or same-column placements with one full seat buffer remain acceptable
  - `Keep near` in seating means one local vicinity overall, but a 2-student pair should prefer
    direct left/right or above/below adjacency over diagonal placement
  - `Keep apart` in grouping should spread cluster members across different groups whenever possible
- Treat `Fast plats` as a hard seating invariant rather than a scored preference:
  - fixed placements must be validated before solving
  - fixed students and fixed seats are removed from the remaining search problem
  - all candidate scoring must see the merged fixed + candidate mapping
  - an impossible or conflicting fixed placement fails the smart seating run without saving a
    partial result
- Compute teacher-distance from room-owned teaching cues:
  - recommend that the teacher places `Whiteboard` or `Kateder`
  - if no stronger cue exists, assume the teaching position is the top-middle of the room
  - if those cues are on another wall, that wall becomes the teaching/front edge
- Keep explanations short, teacher-facing, and trust-building. Do not expose score panels, weight
  tuning, or solver jargon.
- Make workspace loading draft-first and fail-safe:
  - clear old smart rules immediately on session change
  - keep the draft usable if smart-rule hydration fails
  - disable smart-rule authoring and offer retry until the current roster rules are ready
- Make `undo` / `redo` draft-lane-only transitions; dirty/conflicted smart rules must neither
  persist nor block those history actions.
- Make `abandonDraft` flush the smart-rule lane first, discard pending draft-local edits
  explicitly, and use explicit teacher wording if continuing would also discard unsaved class-wide
  smart-rule edits.
- Make exit/teardown semantics explicit:
  - `exitPlanner` timeout returns confirm-discard
  - `confirmExitWithoutWaiting` discards both lanes and ignores late responses
  - `clearWorkspace` remains teardown-only and ignores late responses
- Reset smart-rule UI state when the planner screen is left successfully; save/load
  acknowledgements must not decide tool/selection resets.
- Land the frontend split as dedicated session-controller, lane, UI-state, and transition-policy
  modules with `useClassroomState.ts` reduced to a thin composition surface rather than another
  monolithic-store rewrite.

## Checkpoint policy

- A successful seating export with changed assignments creates a seating checkpoint.
- A repeated seating export with the same canonical seating assignment hash does not create a
  second checkpoint.
- The canonical seating assignment hash should be based on normalized placed student-to-seat
  assignments plus unplaced students, excluding export presentation details.
- Those same seating checkpoints are also the only eligible source for teacher-distance fairness
  over time.
- Grouping remains mode-specific when grouping exports exist later, and grouping checkpoints then
  become the primary grouping-history source. Smart grouping may also consume seating checkpoints
  as a secondary source for:
  - relation carry-over
  - optional seating-distance signals
- Raw drafts, draft history, and reopened drafts are never treated as checkpoints.
- If `Use history` is enabled but no eligible checkpoints exist, the history-enabled smart run is
  blocked with a short teacher-facing explanation rather than silently downgraded.

## Resolved conflicts with current repo state

- The current `ST-24-06` contract says seating `Slumpa` is fully random. Smart behavior therefore
  needs a new approved story package rather than an informal behavior change.
- The current planner metadata drawer may remain for advanced notes/history, but it should not be
  extended into the primary smart-rule editing surface.
- The current seating-embedded smart-rule surface is transitional and should not be extended into
  grouping or a drawer-first editing model; the dedicated `Regler` workspace is the approved
  end-state.
- `PR-0084` correctly removed the old solver-first contract; smart assignment now needs a clean
  re-entry through a new ADR, epic, and stories rather than reusing superseded concepts.

## Backlog translation

The approved planning package for this memo is:

- `ADR-0074`: controls, checkpoints, persistence, and solver boundaries
- `EPIC-27`: smart assignment v1
- `ST-27-01`: contract reset and control model
- `ST-27-02`: export checkpoints for smart history
- `ST-27-03`: smart seating v1
- `ST-27-07`: dedicated rules workspace and dual-map authoring
- `ST-27-04`: smart grouping v1
- `ST-27-05`: smart explanations and rerun messaging
- `ST-27-06`: planner session lanes and transition matrix remediation
- `ST-27-09`: fixed-seat rules and classroom-view-first rule authoring
- `REV-EPIC-27`: required review package before implementation begins
- `PR-0152`: implementation design task for the frontend session-lane remediation
- `PR-0155`: implementation design task for the dedicated rules workspace and task-pane summary
  cut-over
- `PR-0297`: backend fixed-seat persistence and score-aware solver seeding
- `PR-0298`: frontend fixed-seat tool and classroom-view-first rules UX

## 2026-05-05 refinement

The original V1 memo made `Planeringskarta` the default rules view. `ST-27-09` refines that default
after the fixed-seat design discussion:

- when a classroom exists, the classroom-faithful view is the default rules surface
- `Planeringskarta` remains available and must stay a stable abstract alphabetical planning map
- geometry-evaluated student rules can still be authored from either view, but the UI should nudge
  teachers toward classroom geometry
- `Fast plats` is geometry-targeted and therefore must be authored from the classroom view
