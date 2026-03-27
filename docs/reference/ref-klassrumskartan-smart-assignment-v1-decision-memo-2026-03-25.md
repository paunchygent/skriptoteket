---
type: reference
id: REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25
title: "Klassrumskartan smart assignment v1 decision memo (2026-03-25)"
status: active
owners: "agents"
created: 2026-03-25
topic: "smart-assignment"
links: ["PRD-group-seating-studio-v0.3", "ADR-0071", "ADR-0072", "ADR-0074", "EPIC-27", "REV-EPIC-27", "ST-27-06"]
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
- Add one seating-only rule:
  - `Närmare läraren`
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
  - `Keep apart` in seating means no direct orthogonal adjacency when possible
  - `Keep near` in seating means same local vicinity rather than exact seat pairing
  - `Keep apart` in grouping should spread cluster members across different groups whenever possible
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
- `PR-0084` correctly removed the old solver-first contract; smart assignment now needs a clean
  re-entry through a new ADR, epic, and stories rather than reusing superseded concepts.

## Backlog translation

The approved planning package for this memo is:

- `ADR-0074`: controls, checkpoints, persistence, and solver boundaries
- `EPIC-27`: smart assignment v1
- `ST-27-01`: contract reset and control model
- `ST-27-02`: export checkpoints for smart history
- `ST-27-03`: smart seating v1
- `ST-27-04`: smart grouping v1
- `ST-27-05`: smart explanations and rerun messaging
- `ST-27-06`: planner session lanes and transition matrix remediation
- `REV-EPIC-27`: required review package before implementation begins
- `PR-0152`: implementation design task for the frontend session-lane remediation
