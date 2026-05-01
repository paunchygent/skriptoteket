---
type: review
id: REV-PR-0276
title: "Review: PR-0276 spatial share-page renderer and grouping polish"
status: approved
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

`PR-0276` is approved after remediation. The static share-page renderer now
covers both retained defects: merged bench labels render as centered overlays,
and wall fixtures no longer fall back to floor geometry when `wall_side` is
missing. The focused renderer tests and refreshed desktop/mobile artifacts cover
the exact contracts that the previous proof missed.

## Problem Statement

This review checks the implemented seating share renderer against the
presentation contract inherited from the poster scene: adjacent benches may be
merged into one labeled visual object, the label must be centered across the
full merged geometry, and wall fixtures must render in the wall band rather
than consuming classroom floor tiles.

## Proposed Solution

Keep the remediation in `PR-0276`: fix the bench fixture CSS/markup, reject
invalid wall fixtures in `share_scene_renderer.py`, add renderer-level
regressions for the labeled merged bench and top whiteboard geometry, and
refresh desktop/mobile visual proof with both fixtures visible.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0276-st-26-06-spatial-share-page-renderer-and-grouping-polish.md` | Remediation scope and proof obligations | 8 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_scene_renderer.py` | Static bench fixture HTML/CSS ownership | 10 min |
| `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py` | Renderer coverage for merged labeled benches and wall fixtures | 8 min |
| `.artifacts/pr-0276-spatial-share-renderer/` | Desktop/mobile visual proof coverage | 6 min |

**Total estimated time:** ~32 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Reopen `PR-0276` instead of creating `PR-0278` | The bug is inside the PR-0276 renderer and proof contract | [x] |
| Keep `PR-0277` blocked until PR-0276 is reclosed | Preview thumbnails depend on trustworthy share-renderer output | [x] |
| Require both unit coverage and refreshed visual proof | Current tests passed while the visible contract was broken | [x] |
| Fail closed for `placement=WALL` without `wall_side` | Wrong wall geometry is more misleading than rejecting invalid poster-scene input | [x] |

## Review Checklist

- [x] Data/export coalescing path separated from renderer bug
- [x] Renderer ownership identified
- [x] Test coverage gap identified
- [x] Visual proof gap identified
- [x] Bench label overlay fix implemented
- [x] Merged labeled bench renderer test added
- [x] Desktop/mobile screenshots refreshed with the merged labeled bench visible
- [x] Wall fixture without `wall_side` rejects instead of floor-rendering
- [x] Top wall whiteboard proof checks top/height against the floor band

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-01`
**Verdict:** `approved after remediation`

### Required Changes

Closed by the 2026-05-01 remediation. The findings remain below as the audit
trail for what was fixed.

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

3. **P1: Wall fixture without wall_side renders as a floor tile.**

   `_fixture_frame()` silently fell back to floor geometry when
   `fixture.placement` was `WALL` but `wall_side` was missing. The CSS still
   added `room-fixture--wall`, so the whiteboard looked like a wall object while
   starting at the floor top and consuming a full grid-cell row.

   Required fix: make `placement=WALL` without `wall_side` impossible to render
   as floor geometry, add a top-whiteboard renderer regression that proves the
   wall fixture top is above the floor top and its height is wall-band
   thickness, and refresh visual proof with `wall_side=TOP`.

### Suggestions (Optional)

- Keep this fix renderer-neutral for share pages; do not reopen the export
  coalescing model unless the new renderer test disproves the current
  `poster_scene` fixture shape.

### Decision Approvals

- [x] Reopen `PR-0276` instead of creating `PR-0278`
- [x] Keep `PR-0277` blocked until PR-0276 is reclosed
- [x] Require both unit coverage and refreshed visual proof
- [x] Fail closed for `placement=WALL` without `wall_side`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ST-26-06` | Story captured the PR-0276 remediation and returned to `ready` after the fix. |
| 2 | `PR-0276` | Slice reopened with bench overlay proof obligations, then closed as `done`. |
| 3 | `docs/index.md` | Review record added to the docs doorway. |
| 4 | `share_scene_renderer.py` | Bench fixtures now use absolute body and centered label overlay positioning. |
| 5 | `test_share_renderer.py` | Added a renderer regression for a normalized merged bench fixture labeled `Bänk`. |
| 6 | `.artifacts/pr-0276-spatial-share-renderer/` | Refreshed seating sample HTML plus desktop/mobile screenshots with the merged labeled bench visible. |
| 7 | `share_scene_renderer.py` | Wall fixtures missing `wall_side` now fail closed instead of floor-rendering. |
| 8 | `test_share_renderer.py` | Added top-wall whiteboard geometry and missing-`wall_side` regressions. |
| 9 | `.artifacts/pr-0276-spatial-share-renderer/` | Refreshed sample/screenshots with `wall_side=TOP`; proof asserts wall-band geometry. |
