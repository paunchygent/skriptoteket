---
type: review
id: REV-PR-0371
title: "Review: PR-0371 public landing authenticated-app preview implementation"
status: approved
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
reviewer: "codex-independent-reviewer"
prs:
  - PR-0371
links:
  - ST-37-04
  - EPIC-37
  - PR-0370
  - REF-public-landing-copy-lock
  - MOCK-pr-0370-public-landing-authenticated-app-preview
  - MOCK-pr-0370-public-landing-approved-copy
---

# Review: PR-0371 Public Landing Authenticated-App Preview Implementation

## TL;DR

Approved. The re-review resolves the prior mobile-proof blocker without
introducing a new contract or regression issue in scope. The public landing
preview now marks its three proof-critical reused app symbols as eager,
synchronous, and high-priority, the focused spec locks that behavior together
with the shared-symbol assets, and the refreshed retained mobile proof now
shows all three approved symbols.

## Problem Statement

`PR-0371` is the production implementation slice for the approved `PR-0370`
mockup package. Approval requires more than copy parity: the signed-out landing
must keep the public Klassrumskartan hero, replace the repeated showcase with
the approved three-panel authenticated preview, reuse the authenticated-home
app symbols, preserve shared HuleEdu auth continuation behavior, avoid
route/app/backend contract drift, and retain believable browser proof at
desktop and mobile widths.

## Proposed Solution

Reassess only the prior blocker and any regression introduced by its fix:
confirm that the landing preview deterministically renders the three reused
symbols in retained mobile proof, that the production change stays scoped to
the signed-out public preview, and that the updated focused spec remains
meaningful evidence instead of drifting into unrelated implementation-detail
testing.

## Artifacts To Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0371-st-37-04-public-landing-authenticated-app-preview-implementation.md` | Scope, acceptance criteria, proof claims, and stop conditions | 10 min |
| `docs/backlog/prs/pr-0370-st-37-04-public-landing-authenticated-app-preview-mockup-approval.md` | Approved mockup/package boundary | 6 min |
| `docs/mockups/pr-0370-public-landing-authenticated-app-preview/README.md` | Product-owner symbol requirement and rejected marker chrome | 8 min |
| `docs/mockups/pr-0370-public-landing-authenticated-app-preview/approved-copy.md` | Locked Swedish copy | 4 min |
| `docs/reference/ref-public-landing-copy-lock.md` | Copy lock and symbol/auth-link contract | 6 min |
| `frontend/apps/skriptoteket/src/views/HomeView.vue` | Signed-out composition and removed repeated showcase | 8 min |
| `frontend/apps/skriptoteket/src/components/home/LandingAuthenticatedPreview.vue` | Preview copy, symbol reuse, and auth continuation links | 12 min |
| `frontend/apps/skriptoteket/src/views/HomeView.spec.ts` | Behavioral truthfulness of the focused landing tests | 10 min |
| `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-desktop.png` | Desktop production proof | 5 min |
| `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-mobile.png` | Mobile production proof | 5 min |

**Total estimated time:** ~74 minutes.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the existing signed-out Klassrumskartan hero and public CTA behavior. | `PR-0370` approved a minimal landing change, not a hero redesign. | [x] |
| Replace the repeated below-hero Klassrumskartan showcase with the three-panel authenticated preview. | This is the core scope of `PR-0371`. | [x] |
| Reuse authenticated-home app symbols instead of custom SVG diagrams or markers. | The product owner explicitly required shared symbols and rejected alternate diagram chrome. | [x] |
| Preserve shared HuleEdu auth ceremony links through the existing continuation helpers. | Auth continuation is a governed cross-product contract. | [x] |
| Require plausible retained desktop and mobile proof before approval. | `PR-0371` acceptance explicitly includes live browser proof reflecting the production page. | [x] |

## Review Checklist

- [x] Governing docs authority exists and matches the implementation slice.
- [x] No authenticated-home, route, app-id, registry, backend/API, Sir Convert,
  HuleEdu, QTI, DOCX, or Exam.net contract changes were introduced in scope.
- [x] Signed-out hero copy and public CTA behavior remain aligned with the
  approved copy lock.
- [x] The repeated `LandingFeaturedClassroom` showcase is removed from the
  signed-out production composition.
- [x] The `När du loggar in` preview uses the approved copy and avoids Roman
  numerals, numeric markers, `Kräver konto`, `Direkt i appen`, and label chrome.
- [x] The focused landing tests primarily prove user-visible behavior and the
  symbol-reuse requirement.
- [x] Retained mobile browser proof convincingly shows the approved production
  preview with all three reused app symbols.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `approved`

### Findings

No findings.

Re-review pass scope:

- `frontend/apps/skriptoteket/src/components/home/LandingAuthenticatedPreview.vue:89`
  now sets `loading="eager"`, `decoding="sync"`, and `fetchpriority="high"` on
  the three signed-out landing preview symbols only.
- `frontend/apps/skriptoteket/src/views/HomeView.spec.ts:173` now proves the
  shared-symbol assets and the eager/synchronous/high-priority loading contract
  for those three public preview images.
- `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-mobile.png`
  now visibly shows all three approved reused symbols, resolving the prior
  retained-proof blocker.

The prior blocker is resolved, and I did not find a new regression in the
scoped fix surface.

### Verification Reviewed

- Worker-reported red/green evidence from `PR-0371`:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts`
- Worker-reported repo gates:
  `pdm run fe-type-check`
  `pdm run fe-lint`
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`
- Reviewer-inspected artifacts:
  `.artifacts/pr-0370-public-landing-authenticated-app-preview/html-mockup-desktop.png`
  `.artifacts/pr-0370-public-landing-authenticated-app-preview/html-mockup-mobile.png`
  `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-desktop.png`
  `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-mobile.png`

### Residual Risks / Test Gaps

- I did not rerun the frontend test/lint/typecheck suite myself in this
  re-review pass; I relied on the recorded rerun evidence plus direct code and
  refreshed artifact inspection.
- The scoped fix deliberately changes loading behavior only for the three
  signed-out landing preview symbols. Authenticated-home app-card lazy loading
  remains outside this fix and was not touched.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0371` | Created the retained review record and recorded the blocking mobile-proof finding plus re-review proof requirements. |
| 2 | `REV-PR-0371` | Re-reviewed the proof fix, confirmed the mobile symbol blocker is resolved, and updated the retained decision to `approved`. |
