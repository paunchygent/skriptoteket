---
type: review
id: REV-ST-23-06
title: "Review: ST-23-06 PlanDraft persistence and autosave"
status: approved
owners: ["agents", "external-architect"]
created: 2026-03-20
updated: 2026-04-06
reviewer: "@external-architect"
stories:
  - ST-23-06
  - ST-23-02
links:
  - EPIC-23
  - EPIC-24
---

## TL;DR

`ST-23-06` is a real slice-1 foundation for autosaved PlanDraft persistence, but the retained record must stay honest
about its actual scope. The primary target remains `ST-23-06`; `ST-23-02` is supporting governed scope, and the broader
EPIC-24 fundamentals reset belongs in the EPIC-24 planning review instead of being absorbed here.

## Problem Statement

The slice provides a genuine planner foundation, but the retained decision record must not imply that the autosave/draft
story is complete when reload/hydrate, `StudentPlanningMeta`, group lifecycle, server-side invariants, ownership checks,
CSRF, and revision gating are still unresolved.

## Proposed Solution

Keep the canonical retained review anchored on `ST-23-06`, list `ST-23-02` as supporting governed scope, and route the
broader EPIC-24 fundamentals guidance to the EPIC-24 review/doc set. That keeps the slice-1 record focused while still
documenting the real follow-up surface.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-23-06-group-seating-studio-draft-persistence.md` | Draft persistence and autosave slice | 10 min |
| `docs/backlog/stories/story-23-02-group-seating-studio-manual-planner.md` | Metadata drawer / planning-meta gap | 5 min |
| `docs/backlog/epics/epic-23-group-seating-studio.md` | Slice 1 scope and archived rollout notes | 5 min |
| `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md` | Broader fundamentals follow-up context | 5 min |
| `docs/adr/adr-0069-group-seating-studio-domain-model.md` | Persistence and invariant model | 10 min |
| `src/skriptoteket/application/apps/classroom_planner/*` | Implementation surface | 15 min |

**Total estimated time:** ~50 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| App-specific persistence | A curated app needs its own durable model rather than generic session state | [x] |
| Normalized state | Separate maps for group and seat assignments reduce mutation ambiguity | [x] |
| Separate draft/final lifecycle | Mutable plan drafts and immutable snapshots should not be conflated | [x] |
| Decoupled axes | Seat and group assignment must remain independent projections | [x] |
| Follow-up scope stays separate | `ST-23-02` and EPIC-24 remain discoverable without being misrouted into the primary slice-1 gate | [x] |

## Review Checklist

- [x] Slice 1 is a real implementation foundation, not a mock
- [x] The strongest architectural gaps are named explicitly
- [x] Supporting scope is explicit in `stories:`
- [x] EPIC-24 follow-up context is linked rather than absorbed into the primary record
- [x] Follow-up requirements are scoped as concrete next actions

## Review Feedback

**Reviewer:** @external-architect
**Date:** 2026-03-20
**Verdict:** approved

The initial review identified both record-shape issues and broader follow-up gaps. The retained
record is approved as a truthful slice-1 foundation review once the scope is normalized and the
broader EPIC-24 follow-up surface is linked rather than absorbed here.

### Initial Required Changes (Resolved or Routed)

- Keep `ST-23-06` as the primary target and keep `ST-23-02` as supporting governed scope rather than mixing it into the
  body as a second primary surface.
- Move the broad EPIC-24 architecture memo out of this record; use the EPIC-24 planning review for that material.
- Reconcile the slice with the still-open implementation gaps: JSONB persistence shape vs ADR-0069, missing draft
  hydrate path, missing group lifecycle, weak server-side validation/ownership, missing CSRF on mutations, and absent
  revision checks.

### Suggestions (Optional)

- Keep the frontend and backend roles aligned with the current foundation and resist broadening this record into a
  second planning epic.
- Treat the EPIC-24 material as the next decision surface, not as retrospective justification inside this review.

### Decision Approvals

- [x] App-specific persistence
- [x] Normalized state
- [x] Separate draft/final lifecycle
- [x] Decoupled axes

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Normalized the review into the canonical target-based shape and kept `ST-23-06` as the primary target. |
| 2 | Scope | Added `ST-23-02` as supporting governed scope and linked the broader EPIC-24 planning review instead of folding it into this record. |
