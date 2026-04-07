---
type: review
id: REV-EPIC-24
title: "Review: Klassrumskartan Slice 2 Planning"
status: approved
owners: "agents"
created: 2026-03-20
updated: 2026-04-06
reviewer: "external-architect"
epic: EPIC-24
adrs:
  - ADR-0069
  - ADR-0070
  - ADR-0071
  - ADR-0072
stories:
  - ST-24-06
  - ST-24-07
  - ST-24-08
---

## TL;DR

The codebase is salvageable because ADR-0069 already established the right normalized core. EPIC-24
should therefore not reset the domain. It should reset the visible UX, draft lifecycle, and
saved-output model so the teacher workflow becomes clear again before more advanced planning logic
is exposed. The later refinement is class-first: classes become the teacher anchor, classrooms
become secondary context, and grouping/seating become separate draft kinds rather than one blended
planner task.

## Scope of this review

This document is intentionally forward-looking. Slice 1 retrospective findings and closure context live in:

- [REV-EPIC-23](review-epic-23-group-seating-studio.md)
- [review-st-23-06-group-seating-studio-draft-persistence.md](review-st-23-06-group-seating-studio-draft-persistence.md)

## Approved architectural guidance

### Preserve current strengths

Approved: the current normalized draft core and most of the backend layering are worth keeping.

- domain rule logic remains pure
- application handlers continue to orchestrate repositories and UoW
- curated-app bespoke endpoints remain the right web boundary
- repositories continue to flush rather than commit

### 0. Fundamentals-first reset

Approved: EPIC-24 is a fundamentals-recovery epic, not a “show the whole solver surface” epic.

- Landing page first
- class first, classroom secondary
- separate grouping and seating modes
- explicit teacher-owned saved outputs
- hidden advanced controls until separately approved

### 0b. Class-first anchor and draft kinds

Approved: the teacher-facing workflow should be class-first, with separate grouping and seating
draft kinds.

- `Class` becomes the primary workspace anchor.
- `Classroom` becomes secondary reusable context.
- Seating remains classroom-bound as an outcome, but the seating draft may open before room
  selection and attach/switch room context inside the seating workspace.
- Grouping may be classroom-aware or classroom-agnostic.
- One active draft exists per class per draft kind.
- Starting a new draft of the same kind demotes the previous one to history automatically.

### 1. Suggestion engine location

Approved with changed priority: authoritative rule evaluation may live server-side in Python, but it is no longer part of the default visible workflow for the fundamentals stories.

- Domain layer owns pure scoring/evaluation logic.
- Application layer loads draft, roster, template, and constraint context.
- Web layer exposes bespoke planner endpoints only.
- Frontend renders results and applies chosen suggestions back into the draft.

### 2. Constraint model

Approved long-term: draft-scoped typed constraint aggregate separated from roster identity and student card presentation.

- `StudentPlanningMeta`
- `PairConstraint`
- `PlanningProfile`

Dedicated persistence remains preferred, but the default teacher UI must not expose these concepts until later approved stories.

### 3. Validation UX

Approved long-term: hybrid.

- Cheap immediate client hints remain acceptable.
- Authoritative backend validation can remain as advanced groundwork.
- Mode-specific save flows must not be blocked by unrelated opposite-axis findings in the fundamentals stories.

### 4. Snapshot finalization

Approved as a separate advanced concern, not as the teacher-facing save model for groupings and seating arrangements.

For EPIC-24 fundamentals, autosave and undo/redo should stay draft-local and bounded, while any
durable teacher-facing artifacts should come later through explicit export rather than ordinary
save semantics.

### 5. Random assignment and future rule toggles

Approved with changed semantics:

- `Slumpa` remains valuable, but it should operate inside the active teacher mode.
- In grouping mode, it randomizes groups.
- In seating mode, it randomizes seats.
- Future sorting rules remain possible, but they belong in separate settings, not in the main view.

### 6. Responsive whiteboard UI

Approved: the planner should follow the existing HuleEdu brutalist academic design rules, use responsive breakpoint-aware composition, and render room fixtures that make later PDF/XLSX export stories visually credible. The visible workflow, however, must remain simpler than the earlier Slice 2 shell.

## Requirements for EPIC-24

- Keep the normalized draft core from ADR-0069.
- Preserve the existing domain/application/UoW/repository layering strengths while the workflow contract is reshaped.
- Reassert the landing page as the default first interaction and make resume explicit.
- Split the visible planner into separate grouping and seating modes.
- Add draft lifecycle semantics so old drafts are not silently orphaned.
- Make the class, not the class/classroom pair, the primary teacher entry point.
- Keep the class workspace neutral on entry with a stable top toggle for overview, grouping, and seating.
- Separate grouping drafts from seating drafts in the teacher-facing workflow.
- Split randomize/save flows by teacher mode.
- Keep one active draft per class and task, with bounded in-workspace undo/redo history.
- Attach active work and secondary draft continuity to the class without turning ordinary draft
  state into file-vault artifacts.
- Prefer later explicit seating checkpoints or export artifacts over abandoned drafts as future
  smart-placement input.
- Keep advanced validation/suggestions/finalization hidden from the default fundamentals workflow until later approved stories.
- Carry the remaining implementation-shaping directives through technical backlog items:
  - class-first workspace
  - route-level planner modes
  - workspace/store split by teacher task
  - narrow dirty-slice autosave patches
  - atomic compare-and-swap revision checks
  - mode-specific grouping/seating endpoints
  - deletion safeguards for assets backing active drafts
  - router/web-layer standards cleanup

## Decision approvals

- [x] Suggestion Engine Location
- [x] Constraint Model
- [x] Validation UX
- [x] Snapshot Finalization Contract
- [x] Randomizer + Future Rule Toggles
- [x] Responsive Whiteboard UI Direction

## Review amendment (2026-03-23)

The original review approved EPIC-24 as a fundamentals-recovery epic. The planning package is now
amended because two pieces of that intended outcome were not yet captured strongly enough in the
story list:

- seating still needs task-local `Slumpa`
- `Översikt` must absorb enough compact class/classroom management to replace the separate landing
  page later

The shipped work through `ST-24-04` remains valid. This amendment only reviews the additional
closure slices now drafted for the still-active epic.

## Problem statement

EPIC-24 currently looks more complete than it really is:

- grouping already has task-local `Slumpa`, but seating does not
- the class workspace exists, but `Översikt` is still too thin to become the real dashboard/home
- the landing-page cutover and `Avsluta` exit semantics are now defined product decisions that need
  explicit review before implementation starts

Without this amendment, the implementation could continue from an incomplete planning record and
quietly drift away from the intended desktop-first, compact overview-first UX.

## Proposed solution

Keep EPIC-24 active and finish it through three explicit follow-up stories:

1. `ST-24-06`: seating `Slumpa` fundamentals
2. `ST-24-07`: overview-first workspace management
3. `ST-24-08`: landing-page cutover and exit-to-origin flow

The implementation order is intentionally staged:

- first complete seating `Slumpa`
- then make overview fully capable while temporarily duplicating the resumable CTA in both landing
  and overview
- then perform the final big-bang landing cutover with no compatibility layer left behind

## Artifacts to review

1. [epic-24-group-seating-studio-slice-2.md](../epics/epic-24-group-seating-studio-slice-2.md)
2. [story-24-06-group-seating-studio-seating-slumpa-fundamentals.md](../stories/story-24-06-group-seating-studio-seating-slumpa-fundamentals.md)
3. [story-24-07-group-seating-studio-overview-first-workspace-management.md](../stories/story-24-07-group-seating-studio-overview-first-workspace-management.md)
4. [story-24-08-group-seating-studio-landing-cutover-and-exit-to-origin.md](../stories/story-24-08-group-seating-studio-landing-cutover-and-exit-to-origin.md)
5. [pr-0109-klassrumskartan-seating-slumpa-fundamentals.md](../prs/pr-0109-klassrumskartan-seating-slumpa-fundamentals.md)
6. [pr-0110-klassrumskartan-overview-compact-class-and-classroom-management.md](../prs/pr-0110-klassrumskartan-overview-compact-class-and-classroom-management.md)
7. [pr-0111-klassrumskartan-overview-resumable-cta-and-workspace-entry-polish.md](../prs/pr-0111-klassrumskartan-overview-resumable-cta-and-workspace-entry-polish.md)

## Key Decisions

| Decision | Rationale | Approve? |
| --- | --- | --- |
| Preserve current strengths | Keep the normalized draft core and backend layering that already work | [x] |
| Fundamentals-first reset | Recover the visible workflow before exposing more advanced planner logic | [x] |
| Class-first anchor and draft kinds | Classes stay the teacher anchor, with grouping and seating as separate draft kinds | [x] |
| Suggestion engine location | Authoritative evaluation may live server-side without entering the default workflow yet | [x] |
| Constraint model | Draft-scoped typed constraints stay separate from roster identity and student-card presentation | [x] |
| Validation UX | Cheap client hints remain acceptable, with authoritative backend validation for harder cases | [x] |

## Review Checklist

| Decision | Proposed direction |
| --- | --- |
| Seating randomizer semantics | Seating `Slumpa` reshuffles the full active seating draft and remains fully random for now. |
| Grouping/classroom relationship | Grouping remains classroom-agnostic by default even if overview shows a selected classroom; classroom-aware grouping remains an explicit opt-in. |
| Overview transition model | Duplicate resumable CTA in both landing and overview during `ST-24-07`, then remove the landing-only copy in `ST-24-08`. |
| Desktop-first overview | `Översikt` becomes a compact desktop-first dashboard using compact panels, selectors, previews, and short action rows rather than long management lists. |
| Final cutover posture | `ST-24-08` is a big-bang landing removal with no compatibility layer left behind. |
| `Avsluta` semantics | After cutover, `Avsluta` leaves Klassrumskartan and returns the teacher to the page they entered from. |

## Review Feedback

**Reviewer:** GPT-5.4 High planning review lane
**Date:** 2026-03-23
**Verdict:** approved

Initial amendment review opened with `changes_requested`; the re-review approval below closed those
planning changes.

### Initial Required changes (Resolved)

1. Keep the amendment in a real review state rather than pre-marking it approved.
2. Return `ST-24-06` and `PR-0109` to `ready` until the amendment clears review.
3. Define class-switch semantics in `ST-24-07` / `PR-0110` when active work exists for the
   current class.
4. Define the `Avsluta` fallback destination in `ST-24-08` when entry-origin state is missing.

## Changes Made

- Returned the review doc to an actual review lifecycle state after the planning review requested
  changes.
- Returned `ST-24-06` and `PR-0109` to `ready` until re-review clears the amendment.
- Clarified `ST-24-07` and `PR-0110` so class switching happens only from a neutral overview state,
  waits for any in-flight transition to finish, and keeps active drafts resumable rather than
  stranding them.
- Clarified `ST-24-08` so `Avsluta` falls back to the catalog when no recorded entry origin exists,
  including refresh or deep-link entry.

## Re-review approval

**Reviewer:** GPT-5.4 High planning review lane
**Date:** 2026-03-23
**Verdict:** approved

### Approved decisions

- [x] Seating `Slumpa` ships first as a full-draft reshuffle with no smart-placement settings.
- [x] Overview-first management is separated from the later landing-page cutover.
- [x] Grouping remains classroom-agnostic by default even when overview shows a classroom.
- [x] Resumable CTA is duplicated during transition before the final cutover removes the
      landing-only copy.
- [x] `Avsluta` becomes an exit-to-origin action only in the final cutover story, with catalog as
      the fallback when entry-origin state is missing.
