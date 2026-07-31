---
type: task
id: TASK-SKRIPT-27-09-02
title: 'ST-27-09: fixed-seat tool and classroom-view-first rules UX'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-27-09
task_kind: story
acceptance_criteria:
- Given a classroom exists, when the teacher opens `Regler`, then `Klassrumsvyn` is
  selected by default and the abstract `Planeringskarta` remains available as a deliberate
  alternate view.
- Given no classroom exists, when the teacher opens `Regler`, then the workspace falls
  back to `Planeringskarta` and explains that classroom-bound tools become available
  after choosing a classroom.
- Given `Planeringskarta` is active, when the teacher clicks `Fast plats`, then an
  anchored contextual prompt says `Fast plats kräver en fysisk plats. Vill du byta
  till klassrumsvyn?` with `Ja`, `Nej`, and close controls.
- Given the prompt is open, when the teacher clicks `Ja`, then the view switches to
  `Klassrumsvyn`, the prompt closes, and the `Fast plats` tool becomes active.
- Given the prompt is open, when the teacher clicks `Nej` or close, then the teacher
  remains on `Planeringskarta` and `Fast plats` does not activate.
- Given `Fast plats` is active in `Klassrumsvyn`, when the teacher selects a student
  and a physical seat, then the pending rule preview makes the student-seat binding
  explicit before save.
- Given fixed-seat rules are saved, when the rules workspace and seating workspace
  render, then fixed seats are visibly marked without hiding normal student labels
  or drag/drop affordances.
- Given Smart seating fails because a fixed-seat rule cannot be honored, when the
  frontend displays the outcome, then it uses short Swedish user-facing recovery copy
  and does not expose solver internals.
---

## Context

The existing rules workspace was designed around student-bound rules and a `Planeringskarta`
default. `Fast plats` introduces a rule that cannot be authored honestly from an abstract planning
map because it needs a concrete physical seat. At the same time, most rules are interpreted through
classroom geometry, so the workspace should nudge teachers toward the classroom view without
removing the abstract planning map.

Update the frontend rules authoring experience:

- make `Klassrumsvyn` the default rules view whenever a classroom exists
- keep `Planeringskarta` available as a deliberate alternate view
- add the `Fast plats` tool
- route `Fast plats` clicks from `Planeringskarta` through the agreed prompt
- support fixed-seat authoring from the classroom view
- show saved fixed-seat markers and teacher-safe failure feedback

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

Update the frontend rules authoring experience:

- make `Klassrumsvyn` the default rules view whenever a classroom exists
- keep `Planeringskarta` available as a deliberate alternate view
- add the `Fast plats` tool
- route `Fast plats` clicks from `Planeringskarta` through the agreed prompt
- support fixed-seat authoring from the classroom view
- show saved fixed-seat markers and teacher-safe failure feedback

## Contract Inputs

No separate material is recorded in the source snapshot.

## Plan

1. Update the rules workspace view model.
   - Select `Klassrumsvyn` by default when a classroom/template exists.
   - Fall back to `Planeringskarta` when no classroom exists.
   - Preserve explicit user switches between views during one rules session.

2. Add `Fast plats` to the tool rail.
   - Use the canonical fixed-seat label.
   - Keep the tool visible from both map views.
   - From `Planeringskarta`, show an anchored prompt instead of a dead disabled state.

3. Implement the prompt interaction.
   - Copy: `Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?`
   - Actions: `Ja`, `Nej`, close.
   - `Ja`: switch to `Klassrumsvyn` and activate `Fast plats`.
   - `Nej` / close: stay on `Planeringskarta` and leave the tool inactive.

4. Implement classroom-view authoring.
   - Let the teacher bind one selected student to one physical seat.
   - Preview pending student-seat binding before save.
   - Support editing/removing existing fixed-seat rules.
   - Render fixed-seat markers without breaking existing seat labels, hover, selection, or drag/drop.

5. Add failure and loading states.
   - Use short Swedish copy for blocked smart runs.
   - Avoid solver jargon, score language, revision language, or internal field names.

## Implementation Steps

1. Update the rules workspace view model.
   - Select `Klassrumsvyn` by default when a classroom/template exists.
   - Fall back to `Planeringskarta` when no classroom exists.
   - Preserve explicit user switches between views during one rules session.

2. Add `Fast plats` to the tool rail.
   - Use the canonical fixed-seat label.
   - Keep the tool visible from both map views.
   - From `Planeringskarta`, show an anchored prompt instead of a dead disabled state.

3. Implement the prompt interaction.
   - Copy: `Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?`
   - Actions: `Ja`, `Nej`, close.
   - `Ja`: switch to `Klassrumsvyn` and activate `Fast plats`.
   - `Nej` / close: stay on `Planeringskarta` and leave the tool inactive.

4. Implement classroom-view authoring.
   - Let the teacher bind one selected student to one physical seat.
   - Preview pending student-seat binding before save.
   - Support editing/removing existing fixed-seat rules.
   - Render fixed-seat markers without breaking existing seat labels, hover, selection, or drag/drop.

5. Add failure and loading states.
   - Use short Swedish copy for blocked smart runs.
   - Avoid solver jargon, score language, revision language, or internal field names.

## Proof

- `pdm run fe-test -- --run PlannerRulesWorkspacePane PlannerRulesMapCanvas PlannerRulesToolRail PlannerSeatingWorkspacePane.smart-rules`
- Add focused Vitest coverage for:
  - classroom-view default when a template exists
  - planning-map fallback without a classroom
  - `Fast plats` prompt copy and `Ja` / `Nej` / close behavior
  - fixed-seat pending preview and saved marker rendering
  - teacher-safe blocked-run copy
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- Live proof on `http://127.0.0.1:5173` covering:
  - open `Regler` with a classroom and verify `Klassrumsvyn` default
  - switch to `Planeringskarta`, click `Fast plats`, choose `Nej`
  - repeat and choose `Ja`, verifying the tool activates in `Klassrumsvyn`
  - create one fixed-seat rule and run Smart seating

## Validation

- `pdm run fe-test -- --run PlannerRulesWorkspacePane PlannerRulesMapCanvas PlannerRulesToolRail PlannerSeatingWorkspacePane.smart-rules`
- Add focused Vitest coverage for:
  - classroom-view default when a template exists
  - planning-map fallback without a classroom
  - `Fast plats` prompt copy and `Ja` / `Nej` / close behavior
  - fixed-seat pending preview and saved marker rendering
  - teacher-safe blocked-run copy
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- Live proof on `http://127.0.0.1:5173` covering:
  - open `Regler` with a classroom and verify `Klassrumsvyn` default
  - switch to `Planeringskarta`, click `Fast plats`, choose `Nej`
  - repeat and choose `Ja`, verifying the tool activates in `Klassrumsvyn`
  - create one fixed-seat rule and run Smart seating

## Stop Conditions

Revert the frontend tool/view changes while preserving the backend contract from `PR-0297`. If the
backend has shipped but frontend authoring is rolled back, hide fixed-seat authoring while still
rendering any existing fixed-seat rules read-only until the frontend is corrected.

## Lessons Learned

No separate material is recorded in the source snapshot.

## Notes

### Problem

The existing rules workspace was designed around student-bound rules and a `Planeringskarta`
default. `Fast plats` introduces a rule that cannot be authored honestly from an abstract planning
map because it needs a concrete physical seat. At the same time, most rules are interpreted through
classroom geometry, so the workspace should nudge teachers toward the classroom view without
removing the abstract planning map.

### Goal

Update the frontend rules authoring experience:

- make `Klassrumsvyn` the default rules view whenever a classroom exists
- keep `Planeringskarta` available as a deliberate alternate view
- add the `Fast plats` tool
- route `Fast plats` clicks from `Planeringskarta` through the agreed prompt
- support fixed-seat authoring from the classroom view
- show saved fixed-seat markers and teacher-safe failure feedback

### Non-goals

- Backend persistence or solver changes; those belong to `PR-0297`.
- Removing `Planeringskarta`.
- Blocking `Keep near`, `Keep apart`, or `Närmare läraren` from `Planeringskarta`.
- Adding a mobile-specific fixed-seat workflow beyond preserving the existing reduced workspace
  behavior.

### Implementation plan

1. Update the rules workspace view model.
   - Select `Klassrumsvyn` by default when a classroom/template exists.
   - Fall back to `Planeringskarta` when no classroom exists.
   - Preserve explicit user switches between views during one rules session.

2. Add `Fast plats` to the tool rail.
   - Use the canonical fixed-seat label.
   - Keep the tool visible from both map views.
   - From `Planeringskarta`, show an anchored prompt instead of a dead disabled state.

3. Implement the prompt interaction.
   - Copy: `Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?`
   - Actions: `Ja`, `Nej`, close.
   - `Ja`: switch to `Klassrumsvyn` and activate `Fast plats`.
   - `Nej` / close: stay on `Planeringskarta` and leave the tool inactive.

4. Implement classroom-view authoring.
   - Let the teacher bind one selected student to one physical seat.
   - Preview pending student-seat binding before save.
   - Support editing/removing existing fixed-seat rules.
   - Render fixed-seat markers without breaking existing seat labels, hover, selection, or drag/drop.

5. Add failure and loading states.
   - Use short Swedish copy for blocked smart runs.
   - Avoid solver jargon, score language, revision language, or internal field names.

### Test plan

- `pdm run fe-test -- --run PlannerRulesWorkspacePane PlannerRulesMapCanvas PlannerRulesToolRail PlannerSeatingWorkspacePane.smart-rules`
- Add focused Vitest coverage for:
  - classroom-view default when a template exists
  - planning-map fallback without a classroom
  - `Fast plats` prompt copy and `Ja` / `Nej` / close behavior
  - fixed-seat pending preview and saved marker rendering
  - teacher-safe blocked-run copy
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- Live proof on `http://127.0.0.1:5173` covering:
  - open `Regler` with a classroom and verify `Klassrumsvyn` default
  - switch to `Planeringskarta`, click `Fast plats`, choose `Nej`
  - repeat and choose `Ja`, verifying the tool activates in `Klassrumsvyn`
  - create one fixed-seat rule and run Smart seating

### Rollback plan

Revert the frontend tool/view changes while preserving the backend contract from `PR-0297`. If the
backend has shipped but frontend authoring is rolled back, hide fixed-seat authoring while still
rendering any existing fixed-seat rules read-only until the frontend is corrected.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
