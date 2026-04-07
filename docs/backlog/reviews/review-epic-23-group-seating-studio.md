---
type: review
id: REV-EPIC-23
title: "Review of EPIC-23: Klassrumskartan (Slice 1)"
status: approved
owners: "agents"
reviewer: "architect"
epic: "EPIC-23"
created: 2026-03-20
updated: 2026-04-06
---

## TL;DR

Slice 1 is a credible foundation for the new "Klassrumskartan" curated app, but this retained record should stay honest
about what it covers. `ST-23-06` remains the primary target, `ST-23-02` is supporting governed scope, and the broader
EPIC-24 fundamentals reset is now carried by the EPIC-24 planning review instead of being absorbed into this record.

## Problem Statement

The seating planner still needs a truthful retained decision record for Slice 1. The app has real autosave and state
normalization work, but this epic review must not imply a full close-out when reload/hydrate, metadata drawer support,
group lifecycle, server invariants, ownership checks, CSRF, and revision gating are still unresolved.

## Proposed Solution

Keep the canonical retained review anchored on `EPIC-23`, preserve the slice-1 assessment as a story-level historical
record, and route broader fundamentals-recovery guidance to the EPIC-24 review/doc set. That keeps the slice-1 record
focused while still documenting the real follow-up surface.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0069-group-seating-studio-domain-model.md` | Persistence and invariant model | 10 min |
| `docs/backlog/epics/epic-23-group-seating-studio.md` | Slice 1 scope and archived rollout notes | 5 min |
| `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md` | Broader fundamentals follow-up context | 5 min |
| `docs/backlog/stories/story-23-02-group-seating-studio-manual-planner.md` | Metadata drawer / planning meta gap | 5 min |
| `docs/backlog/stories/story-23-06-group-seating-studio-draft-persistence.md` | Draft persistence and autosave slice | 10 min |
| `src/skriptoteket/application/apps/classroom_planner/*` | Implementation surface | 15 min |

**Total estimated time:** ~50 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| App-specific persistence | A curated app needs its own durable model rather than generic session state | [x] |
| Normalized state | Separate maps for group and seat assignments reduce mutation ambiguity | [x] |
| Separate draft/final lifecycle | Mutable plan drafts and immutable snapshots should not be conflated | [x] |
| Decoupled axes | Seat and group assignment must remain independent projections | [x] |
| Follow-up scope stays separate | ST-23-02 and EPIC-24 remain discoverable without being misrouted into the primary slice-1 gate | [x] |

## Review Checklist

- [x] Slice 1 is a real implementation foundation, not a mock
- [x] The strongest architectural gaps are named explicitly
- [x] Supporting scope is explicit in `stories:`
- [x] EPIC-24 follow-up context is linked rather than absorbed into the primary record
- [x] Follow-up requirements are scoped as concrete next actions

## Review Feedback

**Reviewer:** @architect
**Date:** 2026-03-20
**Verdict:** approved

### Required Changes

None, changes have been applied.

### Suggestions (Optional)

Keep the broader fundamentals recovery in the EPIC-24 review trail so this slice-1 record stays focused on the
primary target.

### Decision Approvals

- [x] App-Specific Persistence
- [x] Normalized State
- [x] Separate Draft/Final
- [x] Decoupled Axes
- [x] Follow-up scope stays separate

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Normalized the review into the canonical target-based shape and kept EPIC-23 as the primary target. |
| 2 | Scope | Made ST-23-02 supporting governed scope and linked the broader EPIC-24 follow-up review instead of folding it into this record. |
