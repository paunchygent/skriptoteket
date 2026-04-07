---
type: review
id: REV-EPIC-34
title: "Review: Docs-as-code tightening and legacy review-record migration"
status: approved
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
reviewer: "lead-developer"
epic: EPIC-34
stories:
  - ST-34-01
  - ST-34-02
links:
  - REF-review-workflow
  - REF-sprint-planning-workflow
---

## TL;DR

`EPIC-34` is the right canonical backlog home for the repo's docs-as-code tightening lane. It
cleanly separates the already-shipped review-workflow cutover and sprint retirement backfill from
the remaining legacy review-record migration work, while keeping `REF-review-workflow` as the
governing retained-review contract.

## Problem Statement

The repo already shifted to a target-based retained review model and retired sprint docs as a live
planning shape, but those changes were not yet closed out through one explicit docs-as-code epic
review. Without that review record, the backlog could still make the governance lane look informal
or incomplete, especially while the remaining duplicate review-id families are still queued for
migration.

## Proposed Solution

Approve `EPIC-34` as the dedicated docs-as-code tightening lane with two explicit story surfaces:

- `ST-34-01` backfills the already-implemented review-workflow cutover and sprint-doc retirement.
- `ST-34-02` owns the remaining migration of legacy duplicate review-id families via `PR-0230`.

Keep [REF-review-workflow](../../reference/ref-review-workflow.md) as the governing retained-review
reference and [REF-sprint-planning-workflow](../../reference/ref-sprint-planning-workflow.md) as
the canonical record of sprint retirement.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-review-workflow.md` | Canonical retained review model and primary-target rules | 8 min |
| `docs/reference/ref-sprint-planning-workflow.md` | Sprint retirement contract | 4 min |
| `docs/backlog/epics/epic-34-docs-as-code-tightening-and-legacy-review-record-migration.md` | Governance scope, risks, and story split | 6 min |
| `docs/backlog/stories/story-34-01-docs-as-code-review-workflow-cutover-and-sprint-retirement-backfill.md` | Backfilled shipped baseline | 5 min |
| `docs/backlog/stories/story-34-02-legacy-review-record-migration-to-the-target-based-model.md` | Remaining migration lane | 5 min |
| `docs/backlog/prs/pr-0230-st-34-02-legacy-review-record-migration-to-the-target-based-model.md` | First bounded execution slice for the archive migration | 5 min |
| `docs/index.md` | Discoverability and canonical backlog routing | 4 min |

**Total estimated time:** ~37 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `EPIC-34` as a dedicated docs-as-code governance lane | Gives the review-workflow cutover and legacy migration one canonical planning home instead of leaving them implicit in handoff notes | [x] |
| Record the already-shipped workflow cutover as a backfill story | Separates historical truth from the still-open migration work and keeps the backlog honest about what is already done | [x] |
| Keep the remaining archive cleanup as a separate ready story and PR slice | Preserves a bounded migration lane instead of mixing shipped governance changes with unfinished legacy cleanup | [x] |
| Govern the epic through `REF-review-workflow` and `REF-sprint-planning-workflow` | Keeps the repo's written review and planning contracts attached directly to the epic and its child stories | [x] |

## Review Checklist

- [x] The epic scope is appropriately limited to docs-as-code governance and historical review migration
- [x] The story split distinguishes the shipped baseline from the remaining migration lane honestly
- [x] The retained review and sprint-retirement references are attached as governing docs
- [x] The migration lane is bounded enough to execute incrementally through `PR-0230`
- [x] The epic is ready to stay active while `ST-34-02` remains the open work surface

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-06`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions (Optional)

- As `PR-0230` progresses, prefer explicit legacy framing over overly aggressive splitting when a
  historical review record cannot be cleanly retargeted without falsifying the decision trail.

### Decision Approvals

- [x] Create `EPIC-34` as a dedicated docs-as-code governance lane
- [x] Record the already-shipped workflow cutover as a backfill story
- [x] Keep the remaining archive cleanup as a separate ready story and PR slice
- [x] Govern the epic through `REF-review-workflow` and `REF-sprint-planning-workflow`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `EPIC-34` | Added the canonical docs-as-code tightening and legacy review migration epic |
| 2 | `ST-34-01` | Backfilled the already-shipped target-based review-workflow cutover and sprint retirement |
| 3 | `ST-34-02`, `PR-0230` | Created the remaining legacy review-record migration lane and first bounded execution slice |
| 4 | `REV-EPIC-34` | Closed out the epic review as approved against the current docs-as-code contract |
