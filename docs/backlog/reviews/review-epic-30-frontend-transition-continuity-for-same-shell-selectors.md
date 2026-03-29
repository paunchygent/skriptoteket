---
type: review
id: REV-EPIC-30
title: "Review: Frontend transition continuity for same-shell selectors"
status: approved
owners: "agents"
created: 2026-03-29
reviewer: "lead-developer"
epic: EPIC-30
adrs:
  - ADR-0077
stories:
  - ST-30-01
---

## TL;DR

This review package proposes a new cross-app frontend standard for selector-driven same-shell
transitions. The rule is simple: keep the old surface coherent until the next one is ready, then
hand off with an overlap crossfade instead of an `out-in` blank gap. The planner fix becomes the
baseline reference, and the code editor becomes the first planned adoption target.

## Problem Statement

Dense Skriptoteket workspaces now rely on selectors and mode switches inside one persistent shell.
When those swaps tear down the current surface too early, users see blank fades, fallback copy, and
jump-cut shell updates. The planner bug is fixed locally, but the repo still lacks a shared rule
that prevents the same failure pattern elsewhere.

## Proposed Solution

Adopt `ADR-0077` as the architectural rule for qualifying same-shell transitions, document the
implementation pattern and inventory in `REF-frontend-transition-continuity-v1`, and create a new
cross-app epic that starts with an inventory/adoption-plan story before editor rollout work begins.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0077-same-shell-transition-continuity.md` | Decision quality and scope boundary | 6 min |
| `docs/reference/ref-frontend-transition-continuity-v1.md` | Practical implementation pattern and inventory accuracy | 8 min |
| `docs/backlog/epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md` | Cross-app scope and pacing | 5 min |
| `docs/backlog/stories/story-30-01-frontend-transition-continuity-inventory-and-canonical-adoption-plan.md` | Acceptance criteria and rollout expectations | 4 min |
| `docs/backlog/prs/pr-0165-st-30-01-transition-continuity-decision-inventory-and-adoption-plan.md` | First slice boundaries | 3 min |

**Total estimated time:** ~26 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Same-shell selector continuity becomes a shared frontend standard | Prevent planner/editor drift and repeated blank-gap regressions | [ ] |
| Retained outgoing surface plus overlap crossfade is the canonical technique | This is the only pattern that solved the user-visible planner bug cleanly | [ ] |
| The editor workspace selector is the first adoption target | It is the highest-value remaining stable-shell selector surface | [ ] |
| Smaller selector shells stay behind the editor in rollout priority | Keeps the highest-value UX seam from being delayed by low-risk cleanup | [ ] |

## Review Checklist

- [x] ADR scope is clear and does not overreach into unrelated motion work
- [x] Inventory covers the current known same-shell selector surfaces
- [x] Epic scope is appropriately cross-app and not planner-only
- [x] Story acceptance criteria are testable and sequencing is explicit
- [x] Risks and adoption order are reasonable

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-29
**Verdict:** approved

### Required Changes

- None.

### Suggestions (Optional)

- Keep the first implementation slice anchored to the editor before smaller selector cleanup.

### Decision Approvals

- [x] Same-shell selector continuity becomes a shared frontend standard
- [x] Retained outgoing surface plus overlap crossfade is the canonical technique
- [x] The editor workspace selector is the first adoption target
- [x] Smaller selector shells stay behind the editor in rollout priority

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ADR-0077` | Added the same-shell transition continuity decision and explicit scope boundaries |
| 2 | `REF-frontend-transition-continuity-v1` | Added the canonical pattern, adoption inventory, and rollout order |
| 3 | `EPIC-30`, `ST-30-01`, `PR-0165` | Created the cross-app backlog package for phased adoption |
| 4 | `REV-EPIC-30` | Approved the transition-continuity package so implementation can proceed |
