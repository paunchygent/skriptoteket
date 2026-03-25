---
type: pr
id: PR-0112
title: "Klassrumskartan: overview design simplification and seamless workspace transitions"
status: done
owners: "agents"
created: 2026-03-23
updated: 2026-03-25
stories:
  - "ST-24-07"
tags: ["frontend", "ux", "design"]
acceptance_criteria:
  - "The overview surface removes duplicated guidance and keeps teacher-facing help text only where it adds new local meaning."
  - "The class workspace top panel, overview shell, and planner shell avoid unnecessary stacked panel separations when the surrounding chrome already communicates the same state."
  - "Entering `Grupper` or `Sittplatser` from `Översikt` does not visually snap the segmented toggle back to `Översikt` before the next workspace renders."
  - "Transitions between `Översikt`, `Grupper`, and `Sittplatser` feel quick and stable, with no avoidable layout jumps caused by duplicated setup chrome or conflicting local toggle state."
  - "Focused browser proof demonstrates the simplified overview/planner chrome and confirms that mode changes feel stable on the live SPA."
---

## Problem

The current `ST-24-07` workspace shape is functionally stronger than before, but the design review
showed three remaining UX problems:

- overview guidance is repeated across the top panel, the overview intro block, and the individual
  class/classroom cards
- the workspace still uses more panel boundaries than the information hierarchy justifies, which
  makes the chrome heavier than the teacher task itself
- the overview toggle path can feel jarring because local overview state resets before the next
  workspace view has visibly taken over

That means the feature is structurally correct but still not yet calm, compact, and seamless enough
for the intended desktop-first teacher workflow.

## Goal

Simplify the overview/planner chrome so the classroom workspace feels more like one coherent tool
surface and less like stacked management panels.

## Non-goals

- Expanding or changing the underlying class/classroom management capability added in `PR-0110`.
- Adding the duplicated resumable CTA from `PR-0111`.
- The final landing cutover and exit-to-origin behavior from `ST-24-08`.
- New planner actions or smart-placement logic.

## Implementation plan

- Overview simplification:
  - remove or collapse overview-level guidance that duplicates what the top panel already says
  - keep card-local help only where it clarifies the class card or classroom card specifically
- Panel rationalization:
  - reduce unnecessary visual segmentation between the top panel, overview shell, and task setup
    panels when the same state is already visible elsewhere
  - preserve the compact desktop-first scan path rather than adding more boxes or status regions
- Seamless mode transitions:
  - remove local overview toggle reset behavior that can snap the segmented control back before the
    requested workspace is on screen
  - keep the planner-shell mode switch visually stable across `Översikt`, `Grupper`, and
    `Sittplatser`
- Proof:
  - add focused component coverage where local mode state or duplicated chrome is simplified
  - extend the live browser proof to explicitly inspect workspace-mode transitions

## Test plan

- Frontend unit/integration:
  - overview no longer renders redundant top-level guidance when the top panel already communicates
    the same instruction
  - class/classroom cards keep their local explanatory text only where it is unique and useful
  - selecting `Grupper` or `Sittplatser` from overview does not force the segmented toggle back to
    `Översikt` before the next screen renders
  - grouping and seating shells keep the stable mode-selection contract after the simplification
- Live/browser:
  - load the class workspace and confirm the overview chrome is lighter and less repetitive
  - move from `Översikt` to `Grupper`, back, and then to `Sittplatser`
  - verify that the segmented toggle and surrounding chrome do not visibly jump or flash through an
    avoidable intermediate state

## Rollback plan

- Revert the design simplification while preserving the overview-first class/classroom management
  capability from `PR-0110`.
