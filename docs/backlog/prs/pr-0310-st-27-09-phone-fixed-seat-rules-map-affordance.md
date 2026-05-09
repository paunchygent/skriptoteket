---
type: pr
id: PR-0310
title: "ST-27-09: phone fixed-seat rules map affordance"
status: ready
owners: "agents"
created: 2026-05-09
updated: 2026-05-09
stories:
  - "ST-27-09"
  - "ST-29-17"
tags: ["frontend", "ux", "klassrumskartan", "rules-workspace", "fixed-seat", "small-screen"]
dependencies:
  - "PR-0290"
  - "PR-0298"
  - "PR-0304"
acceptance_criteria:
  - "Given `Regler` renders on a phone-sized viewport and the active tool is `Fast plats`, when a classroom template exists, then a classroom-seat map affordance is visible and reachable without leaving the phone rules workspace."
  - "Given the teacher chooses a student and a physical seat on phone, when the pending fixed-seat rule is shown, then both the student and the seat label are visible before `Spara regel` is enabled."
  - "Given the phone fixed-seat map renders, when the classroom has the same template geometry as `Sittplatser`, then seats appear in their classroom-relative positions and saved fixed-seat markers are not detached from the parent classroom template."
  - "Given the phone rules workspace is using relationship tools (`Nära läraren`, `Håll isär`, `Håll nära`), when no physical seat needs to be selected, then the default reduced student-selection flow from `PR-0290` remains intact and is not replaced by the map."
  - "Given no classroom template exists, when the teacher taps `Fast plats`, then the UI explains that a classroom is required and does not present an empty or misleading seat map."
  - "Given tablet, laptop, and desktop widths render, when this slice ships, then the existing desktop `Klassrumsvyn` / `Planeringskarta` rules map behavior from `PR-0298` remains intact."
---

## Problem

`PR-0290` correctly reduced the phone `Regler` workspace so the desktop rail,
map, and inspector were not squeezed into a narrow viewport. That reduction now
breaks the `Fast plats` workflow: phone users can select students, but they do
not have a visible classroom-seat map where they can choose the physical seat
that a fixed-seat rule requires.

This is a major functional gap because `Fast plats` is not a student-only rule.
It binds exactly one roster student to one physical seat in the active
classroom template.

## Goal

Add a phone-appropriate classroom-seat map affordance for fixed-seat rule
authoring while preserving the reduced relationship-rule flow.

The phone map must be a representation of the active classroom template, not a
separate phone-only seating model. It may be visually simplified, but it must
still preserve seat identity, ordering, and classroom-relative geometry well
enough for the teacher to choose the intended physical place.

## Non-goals

- No backend persistence or solver change.
- No new fixed-seat data shape.
- No removal of `Planeringskarta` or the desktop `Klassrumsvyn`.
- No full desktop rail/map/inspector stack on phone.
- No phone-only classroom template fork or independent seat ordering.

## Design Options

### Option A: Reuse The Existing Rules Map In A Focused Phone Surface

Render `PlannerRulesMapPanel` / `PlannerRulesMapCanvas` inside a phone-only
subordinate surface when `Fast plats` is active. The map uses the same template,
seat ids, fixed-seat markers, and `selectFixedSeatRuleSeat` event path as
desktop.

Pros:

- Lowest semantic risk.
- Reuses the proven fixed-seat and classroom-view implementation.
- Preserves geometry exactly.
- Easier to test against existing rules-map specs.

Cons:

- Can feel visually busy on a phone if rendered at the full desktop density.
- Needs careful containment so it does not recreate the squeezed desktop
  workspace.

### Option B: Build A Phone-Specific Seat Picker From The Same Template

Add a compact `PhoneRulesSeatPicker` style component that reads the active
template seats and renders a simplified spatial grid. It would preserve
geometry and seat ids but omit desktop-only map chrome, labels, and secondary
overlays.

Pros:

- Cleaner phone UX.
- Can prioritize touch target size and selected-seat clarity.
- Easier to place above or below the selected-student panel.

Cons:

- More implementation work.
- Higher drift risk unless it reuses shared room/seat presentation helpers.
- Needs stronger parity tests so phone geometry does not diverge from desktop.

### Option C: Linear Seat List Only

Show a numbered/list-based seat picker while preserving seat order.

Pros:

- Smallest UI surface.
- Simple to implement.

Cons:

- Does not meet the classroom-geometry requirement.
- Teachers cannot reliably map a list item to the physical seat they intend.
- Not recommended.

## Recommendation

Start with Option A and allow a thin phone wrapper around the existing rules map.
If the live phone proof is too busy, refactor only the presentation into Option
B while keeping the same source data and event path.

The minimum acceptable implementation is:

- `Fast plats` active on phone shows a visible classroom-seat map affordance
- the map is backed by the active template's seats
- selecting a seat updates the existing pending fixed-seat rule state
- relationship-rule tools continue to use the current reduced student list flow

## Current Frontend Entry Points

- `PlannerRulesWorkspacePane.vue`: phone rules composition and desktop rules
  map wiring.
- `PlannerRulesMapPanel.vue`: map shell and projection switch.
- `PlannerRulesMapCanvas.vue`: classroom/planning map rendering and seat
  selection.
- `PlannerRulesSeatNode.vue`: fixed-seat marker and seat-level presentation.
- `useSmartRuleUiState.ts` and `useClassroomState.ts`: pending rule state and
  fixed-seat actions.
- `classroomPlannerSmartRulePresentation.ts`: fixed-seat and smart-rule marker
  presentation helpers.
- `klassrumskartan-phone-workspace.css`: phone rules layout and student tray
  containment.

## Implementation Plan

1. Add focused phone tests that currently fail because `Fast plats` on phone has
   no seat-map affordance.
2. In `PlannerRulesWorkspacePane.vue`, keep the existing phone rule rows and
   student selection for relationship tools.
3. When the active phone tool is `fixed_seat` and a classroom template exists,
   render a subordinate classroom-seat map surface.
4. Wire the phone map to the same pending fixed-seat state:
   - selected student: `pendingFixedSeatStudentId`
   - selected seat: `pendingFixedSeatSeatId`
   - commit: `commitPendingFixedSeatRule`
   - existing rules: `activeFixedSeatRules`
5. Show a compact pending summary before save, for example:
   - `Elev: Vilma Ossner`
   - `Plats: Plats 12`
6. Make `Spara regel` available for fixed-seat rules only when both student and
   seat are selected.
7. If no classroom exists, keep `Fast plats` blocked with short Swedish recovery
   copy rather than an empty map.
8. Keep desktop rules workspace untouched except for shared helper extraction if
   needed to keep `PlannerRulesWorkspacePane.vue` below the file-size target.
9. Add browser proof for phone `Fast plats` authoring plus desktop preservation.

## UX Copy Lock

Use short Swedish action/recovery copy:

- `Välj elev och plats.`
- `Välj en plats i klassrummet.`
- `Fast plats kräver ett klassrum. Välj ett klassrum först.`
- `Spara regel`

Avoid internal terms such as `template_id`, `seat_id`, solver, payload, or
hydration in visible copy.

## Test Plan

- `pdm run fe-test -- --run PlannerRulesWorkspacePane PlannerRulesMapCanvas PlannerRulesSeatNode useSmartRuleUiState`
- Add focused assertions for:
  - phone `Fast plats` exposes a map when a classroom exists
  - phone seat selection updates pending fixed-seat seat state
  - phone save is disabled until both student and seat are selected
  - relationship-rule phone flow stays student-list-first
  - desktop `Klassrumsvyn` and `Planeringskarta` remain intact
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof:
  - phone `393x852`: open `Regler`, choose `Fast plats`, select one student,
    select one seat, save rule
  - phone `393x852`: choose `Håll nära` and verify the reduced student-list
    flow still works
  - laptop/desktop: verify the existing desktop map workspace still renders

## Rollback Plan

Remove the phone fixed-seat map wrapper and tests while preserving existing
desktop `PR-0298` fixed-seat behavior and backend fixed-seat rules.
