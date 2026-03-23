---
type: story
id: ST-24-06
title: "Klassrumskartan — Seating `Slumpa` fundamentals"
status: in_progress
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
epic: "EPIC-24"
dependencies:
  - "ST-24-04"
acceptance_criteria:
  - "Given the teacher is inside `Sittplatser` with a selected classroom, when they click `Slumpa`, then the active seating draft is fully reshuffled across the available seats in that classroom."
  - "Given there are more students than seats, when `Slumpa` runs, then the remaining overflow students stay unplaced rather than causing the action to fail."
  - "Given the teacher uses `Slumpa`, when the reshuffle completes, then the result participates in the existing seating draft autosave and in-draft `Ångra` / `Gör om` history."
  - "Given no classroom is selected, when the teacher is in `Sittplatser`, then `Slumpa` is not exposed as a misleading active action for seat randomization."
  - "Given the current product direction still defers smart placement, when `Slumpa` is introduced for seating, then it remains fully random and does not expose advanced settings, smart toggles, or rule controls."
  - "Given the slice ships, when browser proof is run on the current SPA, then it proves seating `Slumpa` changes the live seating draft and remains compatible with autosave plus undo/redo."
---

## Context

`EPIC-24` already preserved `Slumpa` as an important teacher helper and approved that it should
exist inside both visible teacher modes. Grouping now has that helper, but seating still does not,
which leaves the task split incomplete.

The seating workspace now already has the right surrounding mechanics:

- classroom-aware seating drafts
- seating continuity drawer
- autosave
- bounded in-draft undo/redo

That makes this story intentionally narrow: add the missing seating-side randomizer without opening
the larger smart-placement lane yet.

## Problem

The current `Sittplatser` workspace still forces all seat assignment work to be manual:

- there is no seating-side `Slumpa`
- teachers cannot quickly reshuffle an existing seating draft
- the epic promise that randomization is task-local rather than whole-workspace is only half true

That creates an unnecessary asymmetry between grouping and seating and makes the seating workspace
less practical than the product direction intends.

## Decisions

- `Slumpa` in seating reshuffles the full seating draft, not only currently unseated students.
- The action remains fully random in this story.
- Smart placement, tunable rules, and weighting logic stay out of scope.
- Seating `Slumpa` belongs in the existing seating action row inside `Sittplatser`, not in
  `Översikt`.
- The result must flow through the same autosave and bounded undo/redo model as any manual seating
  change.

## Notes

- This story does not decide how future smart placement should use saved student metadata or room
  context. That is explicitly deferred.
- Grouping remains classroom-agnostic by default even after this story; any classroom-aware
  grouping influence remains an explicit teacher opt-in and belongs to later stories.

## Recommended decomposition

### PR-0109

Focus:

- add seating `Slumpa` to the current seating action row
- extend the planner store with seating-randomization mutations using the existing grouping pattern
- keep the behavior draft-local so autosave and seating undo/redo work without a parallel model
- add focused frontend/backend tests and a dedicated browser proof extension
