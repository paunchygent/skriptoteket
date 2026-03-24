---
type: story
id: ST-24-07
title: "Klassrumskartan — Overview-first workspace management"
status: in_progress
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
epic: "EPIC-24"
dependencies:
  - "ST-24-02"
  - "ST-24-04"
acceptance_criteria:
  - "Given the teacher opens the class workspace, when `Översikt` renders, then it behaves as a compact desktop-first dashboard rather than as a sparse placeholder card."
  - "Given the teacher is in `Översikt`, when they need to manage the current class, then they can clearly see the active class, edit it, create a new class, or switch to another class without leaving the workspace flow."
  - "Given the teacher is in `Översikt`, when they inspect the current class, then the class card shows a compact fixed-size preview of the roster in three columns and allows class deletion through the same app-native confirmation pattern as other destructive overview actions."
  - "Given the teacher is in `Översikt`, when they need to manage classroom context, then they can clearly see the current classroom, preview it, switch it with a compact selector, edit it, create a new classroom, or delete it without relying on long expanded lists."
  - "Given the teacher switches class from `Översikt`, when active grouping or seating drafts already exist for the current class, then that switch happens only from the neutral overview state, waits for any in-flight workspace transition to finish, and leaves the earlier class drafts resumable rather than silently discarding them."
  - "Given a resumable draft exists, when the teacher is in `Översikt`, then the workspace can host compact resumable entry surfaces that are ready to replace the superseded landing CTA rather than prolonging a dual-home transition."
  - "Given the teacher wants to continue work, when they use the fixed top toggle, then they can enter `Grupper` or `Sittplatser` from the compact overview without a separate launcher surface."
  - "Given grouping remains classroom-agnostic by default, when the teacher enters `Grupper` from overview, then classroom context is still optional and not silently forced by the overview's current classroom selection."
  - "Given the slice ships, when browser proof is run on the current SPA, then it proves the compact overview class/classroom management flow and leaves the app ready for the immediate landing-page cutover handled in tandem with `ST-24-08`."
---

## Context

`ST-24-02` made the class workspace class-first and introduced the top segmented toggle, but the
current `Översikt` is still too quiet to become the real dashboard surface. The separate landing
page still carries too much of the create/select/resume burden.

This story still builds the replacement surface first, but the product direction is now to avoid a
long duplicate-home transition:

- make `Översikt` fully capable first
- copy only the minimum resumable/home logic that must survive
- then move directly into the landing cutover in tandem with `ST-24-08`

## Problem

The current split between landing and overview creates too many steps and too much duplicated mental
model:

- landing still behaves like the main management surface
- overview is too thin to replace it yet
- class/classroom management is not compactly centralized inside the workspace

That means the app still teaches two different “home” ideas instead of one.

## Decisions

- Desktop and laptop are the canonical design source for this story.
- The overview must stay compact and easy to scan on a full desktop viewport.
- Use drawers, dropdowns, compact previews, and short action rows rather than long expanded
  management lists.
- Keep the top toggle in place as the only mode switch:
  - `Översikt`
  - `Grupper`
  - `Sittplatser`
- Any resumable/home surface added here must be cutover-ready, not a long-lived duplicate that
  requires shared state with the old landing page.
- Do not embed destructive delete actions inside the classroom selector itself; keep delete
  adjacent to the selector as an explicit action.
- Keep the class and classroom cards visually balanced:
  - fixed preview surfaces
  - useful count indicators beside the selected names
  - no decorative metadata cards that do not help teachers act

## Notes

- This story is the capability-building step for the later landing-page cutover.
- `Avsluta` semantics do not change here; the final exit behavior belongs to `ST-24-08`.
- The current classroom shown in overview may inform seating entry, preview, and management, but it
  must not silently make grouping classroom-aware by default.
- Class switching in this story is an overview-level action only:
  - it is unavailable while a planner-to-overview transition is still in flight
  - it must not discard previously active grouping or seating drafts for the class being left
  - those drafts remain resumable through the normal continuity/resume surfaces

## Recommended decomposition

### PR-0110

Focus:

- expand `Översikt` into a compact two-panel dashboard for class and classroom management
- add the classroom selector, compact preview, and create/edit/delete actions
- preserve grouping's classroom-agnostic default while making classroom context clearer for seating
- add focused workspace/component tests

### PR-0111

Focus:

- add the improved compact resumable/home surface to overview/main page
- keep explicit grouping and seating continuation affordances, settings entry, and dismiss `×`
- tighten workspace entry and `Avsluta` so the page is immediately ready for landing removal
- add targeted browser proof for the cutover-ready overview entry flow

### PR-0112

Focus:

- simplify overview and planner chrome after the capability expansion lands
- remove duplicated guidance and unnecessary panel separations that do not add local meaning
- make workspace-mode transitions feel seamless rather than snapping through avoidable intermediate states
