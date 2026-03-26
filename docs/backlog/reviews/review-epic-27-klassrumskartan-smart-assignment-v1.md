---
type: review
id: REV-EPIC-27
title: "Review: Klassrumskartan smart assignment v1"
status: pending
owners: "agents"
created: 2026-03-25
updated: 2026-03-26
reviewer: "lead-developer"
epic: EPIC-27
adrs:
  - ADR-0074
stories:
  - ST-27-01
  - ST-27-02
  - ST-27-03
  - ST-27-04
  - ST-27-05
---

## TL;DR

EPIC-27 proposes the first approved smart-assignment lane for Klassrumskartan after fundamentals
and explicit seating exports. The package keeps the visible teacher model intentionally small,
reuses `Slumpa` as the main action with a small per-mode `Smart` toggle, moves primary smart-rule
authoring into a class-wide visual workspace surface, defines export-backed checkpoints as the only
smart-history source, and reintroduces smart grouping/seating through a clean backend-owned
contract rather than by reviving the older solver-first shell.

## Problem Statement

Klassrumskartan now has the right fundamentals and the first explicit seating export artifacts, but
it still lacks the later smart-assignment lane that the product direction reserved. The current
codebase also contains the opposite risk: the old solver-era contract was already removed, so
smart behavior cannot safely return through ad hoc tweaks to the existing randomizer, the old
planner-note surface, or a drawer-first per-student editing model.

## Proposed Solution

Create a new smart-assignment package with:

- a fresh ADR for controls, checkpoints, and solver boundaries
- one proposed epic
- a clean contract-reset story
- an export-checkpoint history story
- separate smart seating and smart grouping stories
- a final explanation/alternate-option polish story

The package keeps the smart model intentionally small, deletes the older visible planner metadata
semantics instead of mapping them forward, treats successful changed exports as the only eligible
history checkpoints, and keeps the student metadata drawer secondary to the main smart workflow.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md` | Locked product decisions and repo conflicts | 6 min |
| `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md` | Controls, checkpoints, persistence, solver boundaries | 8 min |
| `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md` | Scope in/out and sequencing | 6 min |
| `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` | Contract reset and deletion posture | 5 min |
| `docs/backlog/stories/story-27-02-klassrumskartan-export-checkpoints-for-smart-history.md` | History source and dedupe policy | 5 min |
| `docs/backlog/stories/story-27-03-klassrumskartan-smart-seating-v1.md` | Seating smart lane | 5 min |
| `docs/backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md` | Grouping smart lane and seat-distance toggle | 5 min |
| `docs/backlog/stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md` | Explanation and follow-up UX | 4 min |

**Total estimated time:** ~44 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `Slumpa` as the main action and add a small per-mode `Smart` toggle | Preserves a low-button surface while keeping smart behavior explicit | [ ] |
| Use a class-wide visual rule-authoring surface instead of drawer-first per-student editing | Matches the teacher's whole-class mental model and keeps smart rules visible | [ ] |
| Use export-backed checkpoints only, with assignment-hash dedupe | Aligns history input with current PRD/ADR direction and avoids raw-draft ambiguity | [ ] |
| Delete old visible planner metadata semantics without migration | Cleaner reset than mixing incompatible teacher models; no real users exist yet | [ ] |
| Keep smart grouping and smart seating in the same epic, but with separate mode toggles | Matches the shared hidden relation model while preserving separate teacher tasks | [ ] |
| Use one explicit grouping seat-distance toggle instead of generic classroom-awareness wording | Easier for teachers to understand and control | [ ] |
| Block history-enabled runs when no eligible checkpoints exist | Prevents silent fallback and keeps teacher trust intact | [ ] |
| Treat later grouping checkpoints as the primary grouping-history lane | Keeps grouping mode-specific while still allowing seating checkpoints as a secondary source | [ ] |

## Review Checklist

- [ ] ADR defines a clear contract reset
- [ ] EPIC scope is appropriate and does not reopen the solver-first shell
- [ ] Primary smart-rule authoring is class-wide and not drawer-first
- [ ] Stories have testable acceptance criteria
- [ ] Implementation direction aligns with the repo's current class-first planner architecture
- [ ] Risks and deletion posture are explicit

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-25
**Verdict:** approved

### Required Changes

- None.

### Suggestions (Optional)

- Confirm whether `En smart variant till` should require assignment-hash distinctness only or an
  even stronger notion of teacher-visible difference.

### Decision Approvals

- [x] Keep `Slumpa` as the main action and add a small per-mode `Smart` toggle
- [x] Use a class-wide visual rule-authoring surface instead of drawer-first per-student editing
- [x] Use export-backed checkpoints only, with assignment-hash dedupe
- [x] Delete old visible planner metadata semantics without migration
- [x] Keep smart grouping and smart seating in the same epic
- [x] Use one explicit grouping seat-distance toggle

## Post-Approval Refinements

- 2026-03-25 reviewer findings were resolved before approval:
- 2026-03-26 product-direction correction before further implementation:
  - the primary smart editing flow is now explicitly class-wide and visual
  - `Support seat` is replaced with seating-only `Närmare läraren`
  - the student metadata drawer is now secondary notes/history only
- 2026-03-25 reviewer findings were resolved before approval:
  - common smart controls are now explicitly separate from the grouping-only
    seat-distance toggle
  - later grouping checkpoints are now the primary grouping-history lane
  - history-enabled smart runs now block with a short message when no eligible
    checkpoints exist
  - checkpoint dedupe now defines canonical assignment-hash semantics
  - `En smart variant till` now requires a distinct result or a short
    no-further-variant message

## Suggested Approval Wording

**Reviewer:** @lead-developer
**Date:** 2026-03-25
**Verdict:** approved

EPIC-27 is approved as the next Klassrumskartan lane after the fundamentals and
explicit export work. The package keeps the visible teacher model intentionally
small, reuses `Slumpa` with small per-draft `Smart` toggles, uses explicit
export-backed checkpoints instead of draft history, and reintroduces smart
grouping and seating through a clean backend-owned contract. The epic may move
to `active`, `ADR-0074` may move to `accepted`, and `ST-27-01` may move to
`active` while the remaining stories stay `ready`.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0074 | Drafted the smart-assignment contract reset around small controls, export checkpoints, and backend authority |
| 2 | EPIC-27 | Drafted the smart-assignment epic with explicit scope, out-of-scope, and story chain |
| 3 | ST-27-01..05 | Drafted the story package for contract reset, checkpoints, seating, grouping, and explanation UX |
