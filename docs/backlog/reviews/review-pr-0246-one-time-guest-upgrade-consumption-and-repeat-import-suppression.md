---
type: review
id: REV-PR-0246
title: "Review: PR-0246 one-time guest-upgrade consumption and repeat-import suppression"
status: approved
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
reviewer: "codex"
prs:
  - PR-0246
adrs:
  - ADR-0079
links:
  - EPIC-32
  - ST-32-05
  - ST-32-06
  - PR-0221
  - PR-0245
---

## TL;DR

`PR-0246` now resolves the two blocking contradictions from the first review.
The revised write-up keeps backend truth on authenticated seams only, preserves
the `PR-0245` non-consuming all-zero guard, and clearly separates two policy
concepts that had previously been conflated:

- backend-owned import-bridge consumption truth
- browser-owned guest-authoring eligibility in one browser

With that clarification in place, the retained review can approve the planning
direction.

## Problem Statement

The review target is deciding how Skriptoteket should end the current
repeat-import loop after a first authenticated guest-upgrade commit while
preserving the already-approved public/authenticated boundary and the new
zero-effect UI truth guard.

## Proposed Solution

Approve the hybrid option in a narrower form:

- keep one backend-owned canonical consumption fact for authenticated policy,
  debugging, and stale-local cleanup
- keep one browser-owned consumed marker for same-browser public suppression
  and stale snapshot clearing
- do not make the public host depend on backend/user-specific truth
- do not consume the bridge on a structurally suspicious all-zero commit
- keep browser guest-authoring eligibility as a separate browser-owned control
  point so the account-first/guest-later loop can be closed without polluting
  the backend consumption ledger

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0246-st-32-05-one-time-guest-upgrade-consumption-and-repeat-import-suppression.md` | Decision shape, options, and acceptance criteria | 12 min |
| `docs/backlog/stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md` | Parent story alignment | 5 min |
| `docs/adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md` | Public/authenticated boundary and one-time bridge rules | 8 min |
| `docs/backlog/prs/pr-0245-st-32-05-empty-guest-snapshot-and-zero-effect-import-ui-reconciliation.md` | Zero-effect guard that must not be regressed | 6 min |
| `src/skriptoteket/web/api/v1/public_apps.py` | Public bootstrap authority model | 4 min |
| `frontend/apps/skriptoteket/src/views/PublicAppHostView.vue` | Public host data source | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestUpgrade.ts` | Current authenticated consumption/retention semantics | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts` | Public guest snapshot auto-init seam | 5 min |

**Total estimated time:** ~49 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use a dedicated backend consumption fact instead of planner-artifact inference | Product policy should not depend on draft/checkpoint internals | [x] |
| Keep a browser-owned consumed marker in addition to the backend fact | Same-browser public suppression and stale-local cleanup still need a local control point | [x] |
| Keep public hosts off backend/user-specific truth | Preserves the cookie-agnostic public boundary and matches the current public bootstrap seam | [x] |
| Keep all-zero suspicious receipts non-consuming | Preserves the `PR-0245` truthful zero-effect guard | [x] |
| Separate browser guest-authoring eligibility from import consumption | Closes the account-first/guest-later loop without overloading the backend ledger | [x] |

## Review Checklist

- [x] The option matrix is bounded and the hybrid direction is the right base
- [x] The retained ADR boundary was checked before approving the recommended path
- [x] The current auth/public host seams were inspected, not inferred
- [x] The current zero-effect guard from `PR-0245` was checked for regression risk
- [x] The revised doc resolves the earlier auth/public and zero-effect contradictions
- [x] The account-first/guest-later edge case is now reviewable as an explicit policy choice

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-04-08`
**Verdict:** `approved`

### Required Changes

None. The revised PR text resolves the two retained blockers from the first
review.

### Suggestions (Optional)

- Keep Option D, but implement it through the existing guest-upgrade seam
  rather than inventing a second parallel orchestration concept. The cleanest
  path is a tiny additive repository/ledger seam plus frontend guest-storage
  marker support.
- When implementation starts, add one explicit acceptance/proof item for the
  approved account-first/guest-later rule so the stricter browser-closure path
  is verified, not just described in the decision table.
- If the backend ledger is added, store at least `owner_user_id`, `app_id`,
  `consumed_at`, and the consumed `snapshot_id` for operator/debug value
  without coupling the policy to planner-entity inference.

### Decision Approvals

- [x] Dedicated backend consumption ledger over planner-artifact inference
- [x] Hybrid server-truth + browser-marker direction
- [x] Public host remains browser-marker-only
- [x] All-zero suspicious receipts remain non-consuming
- [x] Browser guest-authoring eligibility may close earlier than import consumption

## Changes Made

1. Recorded the initial retained review outcome for `PR-0246` as
   `changes_requested`.
2. Re-reviewed the revised PR/story pair and marked the retained review
   `approved` once the auth/public boundary and zero-effect consumption
   contradictions were resolved.
