---
type: review
id: REV-PR-0248
title: "Review: PR-0248 recovered export silence, rules rail stickiness, and overview copy cleanup"
status: approved
owners: "agents"
created: 2026-04-09
updated: 2026-04-09
reviewer: "lead-developer"
prs:
  - PR-0248
links:
  - EPIC-29
  - ST-29-02
  - ST-29-10
  - PR-0153
  - PR-0155
  - PR-0161
---

## TL;DR

`PR-0248` now aligns with the current restored-export seam. The draft cleanly separates silent
historical-success rediscovery from recovered in-flight completion, keeps the shared export-flow
seam explicit, and requires focused proof in both export-flow specs. The last wording mismatch has
been removed, so the retained review is now `approved`.

## Problem Statement

The review target is deciding whether the planner follow-up is specific enough to protect the
approved transient-feedback doctrine without accidentally regressing the useful recovered export
continuity that still belongs in the product.

## Proposed Solution

Approve `PR-0248` only after it:

- distinguishes silent historical-success rediscovery from recovered in-flight completion
- names the shared export-flow seam instead of treating this as a generic toast cleanup
- requires focused export-flow proof in both grouping and seating specs
- aligns the recovered in-flight completion wording with the current restored-export completion seam
- keeps the `Regler` rail and overview copy cleanup as separate bounded presentation fixes

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0248-st-29-02-recovered-export-silence-rules-rail-stickiness-and-overview-copy-cleanup.md` | Acceptance criteria, proof burden, and scope boundaries | 12 min |
| `docs/backlog/stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md` | Parent story alignment | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts` | Shared recovered-success seam | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.spec.ts` | Grouping proof obligations | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.spec.ts` | Seating proof obligations | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue` | Rules-rail layout seam | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue` | No-class heading seam | 4 min |

**Total estimated time:** ~47 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Silent historical succeeded exports on workspace re-entry | Old success should not replay as fresh action feedback | [x] |
| Preserve one-time success toast for recovered in-flight exports that finish after restore | Recovery continuity is still user-visible truth when completion happens later | [x] |
| Name the shared export-flow seam and spec proof explicitly | Prevents a shallow toast-only implementation | [x] |
| Keep `Regler` rail and overview cleanup in this same bounded planner slice | These are adjacent presentation-truth fixes with shared shell ownership | [x] |

## Review Checklist

- [x] Scope is still bounded and appropriate
- [x] The real export structural risk was checked against the shared flow and existing seating proof
- [x] The draft initially under-specified the recovered-success distinction
- [x] The required proof now needs explicit grouping + seating export spec coverage
- [x] Final re-review confirmed the recovered in-flight wording now matches the current recovered-export completion seam
- [x] The `Regler` rail and overview cleanup remain narrow and reviewable

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-09`
**Verdict:** `approved`

### Required Changes

- None.

### Suggestions (Optional)

- Keep the live browser proof focused on user-visible planner behavior and let the recovered
  in-flight distinction stay primarily owned by the focused export-flow specs.

### Decision Approvals

- [x] Silent historical success rediscovery only
- [x] One-time recovered in-flight completion success aligned to the existing restored-export seam
- [x] Shared export-flow seam explicitly named
- [x] Bounded planner-shell scope retained

## Changes Made

1. Tightened `PR-0248` acceptance criteria to distinguish historical succeeded recovery from
   recovered in-flight completion.
2. Updated the implementation plan to name the shared export-flow seam and prohibit blanket
   recovered-success silencing.
3. Strengthened the test plan around `useGroupingExportFlow.spec.ts` and
   `useSeatingExportFlow.spec.ts`.
4. Re-reviewed the revised draft and kept the record at `changes_requested` because the recovered
   in-flight acceptance wording still over-specifies browser download behavior relative to the
   current shared recovery seam and focused proof surface.
5. Updated `PR-0248` again to remove the implied automatic browser download from the recovered
   in-flight acceptance/proof wording and align that lane back to the current `Mina filer`
   restored-export seam; this record now awaits re-review rather than approval by edit.
6. Completed the final re-review and approved `PR-0248` because the recovered in-flight wording,
   shared export-flow seam, and focused proof burden now match the current implementation truth.
