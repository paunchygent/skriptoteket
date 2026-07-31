---
type: story
id: ST-SKRIPT-27-09
title: 'Klassrumskartan: fixed-seat rules and classroom-view-first rule authoring'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-27
acceptance_criteria:
- Given a classroom exists for the current seating draft, when the teacher opens `Regler`,
  then the physical classroom view is selected by default rather than the abstract
  planning map.
- Given the teacher switches to `Planeringskarta`, when they use ordinary student-bound
  rules such as `Keep near`, `Keep apart`, or `Närmare läraren`, then the app keeps
  the teacher in control while making it clear that Smart will interpret those rules
  through classroom geometry.
- Given the teacher clicks `Fast plats` while `Planeringskarta` is active, when the
  contextual prompt appears, then it says `Fast plats kräver en fysisk plats. Vill
  du byta till klassrumsvyn?` and offers `Ja`, `Nej`, and a close action.
- Given that prompt is open, when the teacher chooses `Ja`, then the app switches
  to the classroom view and activates `Fast plats` without losing the current roster
  or draft context.
- Given that prompt is open, when the teacher chooses `Nej` or closes it, then the
  app stays on `Planeringskarta` and does not activate `Fast plats`.
- Given the teacher authors a fixed-seat rule, when the rule is saved, then it binds
  exactly one roster student to one seat in the selected classroom template.
- Given fixed-seat rules exist, when Smart seating runs, then the solver seeds those
  placements as hard assignments and scores all remaining candidate placements against
  the seeded mapping.
- Given fixed-seat rules conflict with the roster, room template, duplicate students,
  duplicate seats, or the available seat count, when Smart seating runs or rules are
  saved, then the operation fails honestly without persisting a partial seating result.
retired_ids:
- ST-27-09
---

## Context

### Context

Teachers need one strict seating rule that reserves a specific physical seat for a specific student.
Unlike the current relationship and teacher-distance rules, `Fast plats` is not a soft preference.
It is a hard seating invariant: if the requested fixed placement cannot be honored, the smart
seating run must fail rather than quietly produce a compromised arrangement.

This story also refines the `Regler` workspace mental model. Most visible rules are interpreted by
the smart solver through physical classroom geometry, so the classroom-faithful view should be the
default when a classroom exists. `Planeringskarta` remains available as a deliberate abstract
planning view, but the app should nudge teachers toward the classroom view for geometry-dependent
work.

### Notes

- Canonical teacher-facing rule name: `Fast plats`.
- Canonical teacher-facing destination label in the fixed-seat prompt: `klassrumsvyn`.
- Existing docs and code may still use `Sittschema` for the classroom-faithful projection; this
  story defines `Klassrumsvyn` / `klassrumsvyn` as the teacher-facing copy for that destination.
- `Fast plats` is the hard exception to the nudge model:
  - it may be visible from `Planeringskarta`
  - it cannot be authored there because it needs a concrete physical `seat_id`
  - the user receives an anchored contextual prompt with `Ja`, `Nej`, and close controls
- Student-bound geometry-evaluated rules remain authorable from both maps:
  - `Keep near`
  - `Keep apart`
  - `Närmare läraren`
- The persistence scope for V1 is roster + classroom template + student + seat.
- The solver contract is seeded-hard-placement first, best-effort scoring second:
  - validate fixed placements up front
  - remove fixed students and fixed seats from the remaining search space
  - score every candidate using the merged fixed + candidate mapping
  - persist no partial result when hard fixed-placement validation fails
- This story supersedes the older `Planeringskarta`-default behavior from `ST-27-07` only for the
  default selected view. `Planeringskarta` must still remain a stable abstract alphabetical map when
  deliberately selected.

### PR slices

- [PR-0296](../prs/pr-0296-st-27-09-fixed-seat-rule-contract-and-classroom-view-default.md):
  contract, backlog, and decision-memo alignment.
- [PR-0297](../prs/pr-0297-st-27-09-fixed-seat-rule-persistence-and-solver-seeding.md):
  backend fixed-seat persistence, validation, and score-aware solver seeding.
- [PR-0298](../prs/pr-0298-st-27-09-fixed-seat-tool-and-classroom-view-first-rules-ux.md):
  frontend classroom-view default, `Fast plats` tool prompt, markers, and proof.
- [PR-0304](../prs/pr-0304-st-27-09-seating-workspace-fixed-seat-lock-marker.md):
  seating-workspace lock marker remediation for honored fixed-seat placements.
- [PR-0310](../prs/pr-0310-st-27-09-phone-fixed-seat-rules-map-affordance.md):
  phone fixed-seat rule authoring map affordance for selecting physical seats
  (`done` 2026-05-09): phone map implemented with Smart toast diagnostics and
  collision-free symbolic rule markers.
- [PR-0312](../prs/pr-0312-shared-phone-classroom-map-touch-viewport-gestures.md):
  shared phone classroom-map touch viewport gestures (`done` 2026-05-10) for
  pinch zoom on the `Fast plats` phone map without changing the fixed-seat rule
  contract.

### Implementation Notes

- `PR-0310` closes the phone-specific fixed-seat authoring gap by adding a
  compact classroom-template seat map when `Fast plats` is active on phone.
- The phone map is intentionally simplified, but it preserves row/seat geometry
  and seat identity from the selected classroom template rather than creating a
  separate phone-only seating model.
- Public guest transitions now resolve the selected classroom when `Regler`
  opens from an active grouping draft, so `Fast plats` does not falsely report
  that no classroom exists.
- `PR-0310` also clarifies Smart compromise toasts so capacity shortfalls and
  soft-rule compromises use distinct Swedish copy, and map seat markers
  globally use compact symbols with success/warning/error token semantics on
  both rules and seating surfaces instead of text labels that can obscure seats
  or student names.

## Epic Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Live Verification Plan

Verification expectations remain in the retained source material below.

## Non-Goals

The source boundaries and recovery limits remain preserved below.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Story Closeout Review

The source material below remains authoritative for this section.
