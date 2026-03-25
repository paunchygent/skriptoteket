---
type: reference
id: REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25
title: "Klassrumskartan smart assignment v1 decision memo (2026-03-25)"
status: active
owners: "agents"
created: 2026-03-25
topic: "smart-assignment"
links: ["PRD-group-seating-studio-v0.3", "ADR-0071", "ADR-0072", "ADR-0074", "EPIC-27", "REV-EPIC-27"]
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
- Keep the visible smart model intentionally small:
  - `Support seat`
  - `Keep apart`
  - `Keep near`
  - `Use history`
- Allow one grouping-only mode-specific toggle for seat-distance input, such as
  `Ska hur nära de sitter räknas?`; it is not a fifth shared control.
- Use export-backed checkpoints only. Autosave, undo/redo, abandoned drafts, and raw draft
  history never count as algorithmic history input.
- Deduplicate checkpoint creation by assignment hash so repeated identical exports do not create
  extra checkpoint records.
- Ship smart behavior in both `Sittplatser` and `Grupper` from day one, but keep the mode toggles
  independent so the teacher can opt into one and keep the other random.
- Let smart grouping use seating distance only through an explicit teacher-facing toggle such as
  `Ska hur nära de sitter räknas?`, which is easier to reason about than a generic
  "classroom-aware" label.
- Let `Support seat` influence grouping only when the seating-distance signal is enabled and usable
  seating context exists.
- Keep explanations short, teacher-facing, and trust-building. Do not expose score panels, weight
  tuning, or solver jargon.

## Checkpoint policy

- A successful seating export with changed assignments creates a seating checkpoint.
- A repeated seating export with the same canonical seating assignment hash does not create a
  second checkpoint.
- The canonical seating assignment hash should be based on normalized placed student-to-seat
  assignments plus unplaced students, excluding export presentation details.
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
- The current planner metadata drawer is intentionally anchored in notes/observations. That surface
  should not be extended into a mixed smart-planning panel.
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
- `ST-27-05`: smart explanations and alternate options
- `REV-EPIC-27`: required review package before implementation begins
