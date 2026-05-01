---
type: review
id: REV-PR-0276
title: "Review: PR-0276 spatial share-page renderer and grouping polish"
status: changes_requested
owners: "agents"
created: 2026-05-01
updated: 2026-05-01
reviewer: "lead-developer"
prs:
  - PR-0276
links:
  - EPIC-26
  - ST-26-06
  - REV-ST-26-06
  - PR-0277
---

## TL;DR

`PR-0276` is reopened. The data path already coalesces contiguous benches into a
merged poster-scene fixture, but the static share-page HTML/CSS renderer lays the
bench body and `Bänk` label out as flex siblings. The label is therefore pushed
to the right edge instead of centered over the merged bench span. Remediation
belongs in `PR-0276`, not a new slice, because the implementation and missing
visual proof both live in the static share renderer delivered by this PR.

## Problem Statement

This review checks the implemented seating share renderer against the
presentation contract inherited from the poster scene: adjacent benches may be
merged into one labeled visual object, and the label must be centered across the
full merged geometry.

## Proposed Solution

Keep the remediation in `PR-0276`: fix the bench fixture CSS/markup in
`share_scene_renderer.py`, add a renderer-level regression case for a labeled
merged bench fixture, and refresh desktop/mobile visual proof with that fixture
visible.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0276-st-26-06-spatial-share-page-renderer-and-grouping-polish.md` | Remediation scope and proof obligations | 8 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_scene_renderer.py` | Static bench fixture HTML/CSS ownership | 10 min |
| `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py` | Renderer coverage for merged labeled benches | 8 min |
| `.artifacts/pr-0276-spatial-share-renderer/` | Desktop/mobile visual proof coverage | 6 min |

**Total estimated time:** ~32 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Reopen `PR-0276` instead of creating `PR-0278` | The bug is inside the PR-0276 renderer and proof contract | [x] |
| Keep `PR-0277` blocked until PR-0276 is reclosed | Preview thumbnails depend on trustworthy share-renderer output | [x] |
| Require both unit coverage and refreshed visual proof | Current tests passed while the visible contract was broken | [x] |

## Review Checklist

- [x] Data/export coalescing path separated from renderer bug
- [x] Renderer ownership identified
- [x] Test coverage gap identified
- [x] Visual proof gap identified
- [ ] Bench label overlay fix implemented
- [ ] Merged labeled bench renderer test added
- [ ] Desktop/mobile screenshots refreshed with the merged labeled bench visible

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-01`
**Verdict:** `changes_requested`

### Required Changes

1. **P1: Bench label is laid out as a flex sibling, not centered over the bench.**

   The shared-page bench renderer puts `.room-bench-body` and
   `.room-fixture__label` next to each other in the same flex row. Because the
   bench body consumes nearly all available width, the label is pushed to the
   right edge of the visible bench bar instead of being overlaid at the center
   of the merged bench span. The export model already merges the bench geometry
   correctly; the bug is isolated to static share-page HTML/CSS rendering.

   Required fix: make the bench body absolute/inset inside
   `.room-fixture--bench` and position the label as an absolute centered overlay
   for bench fixtures.

2. **P2: Renderer proof does not exercise labeled merged benches.**

   The share renderer test constructs a seating scene with whiteboard and
   teacher desk only, while the export test separately proves merged benches
   have label `Bänk`. No test or saved `PR-0276` visual artifact renders the
   combined contract: one merged bench fixture with a label.

   Required fix: add a renderer-level case using a normalized merged bench
   fixture and assert the generated markup/CSS supports centered overlay
   semantics, plus refresh desktop/mobile visual proof with that fixture
   present.

### Suggestions (Optional)

- Keep this fix renderer-neutral for share pages; do not reopen the export
  coalescing model unless the new renderer test disproves the current
  `poster_scene` fixture shape.

### Decision Approvals

- [x] Reopen `PR-0276` instead of creating `PR-0278`
- [x] Keep `PR-0277` blocked until PR-0276 is reclosed
- [x] Require both unit coverage and refreshed visual proof

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ST-26-06` | Story reopened to `in_progress` with PR-0276 remediation notes. |
| 2 | `PR-0276` | Slice reopened to `in_progress` with bench overlay acceptance and proof obligations. |
| 3 | `docs/index.md` | Review record added to the docs doorway. |
