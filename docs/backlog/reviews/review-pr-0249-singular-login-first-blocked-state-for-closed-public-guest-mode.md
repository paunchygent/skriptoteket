---
type: review
id: REV-PR-0249
title: "Review: PR-0249 singular login-first blocked state for closed public guest mode"
status: approved
owners: "agents"
created: 2026-04-09
updated: 2026-04-09
reviewer: "lead-developer"
prs:
  - PR-0249
links:
  - EPIC-32
  - ST-32-05
  - ST-32-06
  - PR-0245
  - PR-0246
---

## TL;DR

`PR-0249` now resolves the original review blockers. The revised draft names both the guest
controller bootstrap seam and the overview-view duplication seam, makes the `/auth/login` and
`/register` action targets explicit, and requires proof in the overview shell, overview view, and
public-host route tests. With those corrections in place, the retained review can approve the
planning package.

## Problem Statement

The review target is deciding whether the closed-public-guest follow-up names the true seams and
proof burden needed to avoid a half-fix that removes one visible block while leaving the other
truth-path or wrong auth target intact.

## Proposed Solution

Approve `PR-0249` only after it:

- names both the guest-controller bootstrap seam and the overview-view duplication seam
- makes `Logga in -> /auth/login` and `Skapa konto -> /register` explicit acceptance criteria
- requires proof in the overview shell, overview view, and public-host route tests
- keeps the backend/browser closure policy unchanged and limits the work to frontend reconciliation

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0249-st-32-05-singular-login-first-blocked-state-for-closed-public-guest-mode.md` | Acceptance criteria, seams, and proof burden | 12 min |
| `docs/backlog/stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md` | Parent story alignment | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts` | Controller bootstrap truth | 8 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestOverviewView.vue` | Duplicate blocked-panel rendering seam | 8 min |
| `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts` | Controller/shell proof | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts` | View/action proof | 6 min |
| `frontend/apps/skriptoteket/src/views/PublicAppHostView.spec.ts` | Public-host route/action proof | 5 min |

**Total estimated time:** ~50 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Reconcile controller + view seams together | Prevents a one-surface cosmetic fix that leaves the other truth-path alive | [ ] |
| Make `/auth/login` and `/register` explicit contract targets | Prevents visually correct but behaviorally wrong auth actions | [ ] |
| Require shell, view, and public-host proof | The route/action contract spans more than one spec surface | [ ] |
| Keep this slice frontend-only and policy-preserving | The one-time browser closure policy is already decided in `PR-0246` | [ ] |

## Review Checklist

- [x] Scope is still bounded and appropriate
- [x] The current duplication was checked against both controller and view seams
- [x] The original draft under-specified proof and action-target requirements
- [x] The corrected proof burden now includes shell/view/public-host coverage
- [x] The backend/policy boundary remains unchanged

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-09`
**Verdict:** `approved`

### Required Changes

None. The revised PR draft closes the original seam and proof gaps.

### Suggestions (Optional)

- Keep the live browser proof focused on one blocked surface plus truthful action destinations; do
  not broaden this into a redesign of the wider signed-out host shell.

### Decision Approvals

- [x] Controller + view seam reconciliation
- [x] Explicit `/auth/login` and `/register` targets
- [x] Shell/view/public-host proof bundle
- [x] Frontend-only policy-preserving scope

## Changes Made

1. Recorded the initial retained review outcome for `PR-0249` as `changes_requested`.
2. Tightened `PR-0249` to name both the controller and view seams involved in the current
   duplication.
3. Added explicit acceptance criteria and proof for `/auth/login` and `/register` action targets.
4. Strengthened the test plan around `useClassroomPlannerGuestOverviewShell.spec.ts`,
   `ClassroomPlannerGuestOverviewView.spec.ts`, and `PublicAppHostView.spec.ts`.
5. Re-reviewed the revised PR draft and marked the retained review `approved`.
