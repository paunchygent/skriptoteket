---
type: review
id: REV-PR-0374
title: "Review: PR-0374 post-cutover Conversion Hub compatibility cleanup"
status: approved
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
reviewer: "codex-independent-reviewer"
prs:
  - PR-0374
links:
  - EPIC-37
  - ST-37-04
  - PR-0368
  - REF-app-presentation-decomposition-and-naming-plan-v1
---

## TL;DR

PR-0374 is approved after post-implementation review. The implementation removes normal `documents.conversion_hub?mode=exam|transcript` presentation selection, keeps canonical protected `/apps/exam-converter` and `/apps/audio-transcription` identities query-free, preserves the shared runtime/auth/backend surface, and keeps Document Converter inert.

## Problem Statement

The review checks whether `PR-0374` is a bounded cleanup slice for removing the temporary `documents.conversion_hub?mode=exam|transcript` presentation compatibility after `PR-0368` proved canonical protected `/apps/exam-converter` and `/apps/audio-transcription` identities.

## Proposed Solution

Approved PR-0374 contract:

- Remove the mode-query compatibility from normal routing, links, active tests, docs, and teacher-facing copy.
- Preserve canonical protected Exam Converter and Audio Transcription routes.
- Preserve shared runtime/auth/backend machinery and HuleEdu Gateway proof.
- Keep public Exam Converter unchanged.
- Keep Document Converter inert.
- Prove behavior through canonical route/user-visible tests rather than tests that only assert removed helpers, components, or files are absent.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `AGENTS.md` | Repo review, docs-as-code, auth-proof, and validation rules | 5 min |
| `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md` | Primary scope, acceptance criteria, plan, proof | 25 min |
| `docs/backlog/reviews/review-pr-0368-route-visible-app-entrypoint-and-presentation-alignment.md` | Approved predecessor and proof trail | 10 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Story-level cleanup requirement | 10 min |
| `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md` | Compatibility cleanup owner, auth invariant, stop conditions | 15 min |
| `.codex/handoff.md` | Current worktree state and PR-0368 proof commands | 10 min |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Current canonical routes and generic compatibility route | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Current fallback query-mode selection | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.ts` | Current mode-query helper | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts` | Current compatibility-preserving tests | 10 min |
| `scripts/playwright_pr_0363_conversion_mode_deeplink.py` | Current live proof now targeting PR-0368 canonical identities | 5 min |

**Total estimated time:** ~115 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Remove `documents.conversion_hub?mode=exam|transcript` as a normal product/presentation path. | `PR-0368` proved canonical protected Exam and Audio identities, so the cutover bridge should not become durable architecture. | [x] |
| Preserve shared runtime/auth/backend machinery. | The cleanup must not split the HuleEdu Gateway/Sir Convert auth edge or duplicate per-app runtime clients. | [x] |
| Keep Document Converter inert. | PR-0374 is cleanup, not a new Document Converter MVP or route slice. | [x] |
| Keep public Exam Converter unchanged. | The public route/capability was frozen by PR-0368 and is outside cleanup scope. | [x] |
| Use behavior-first red/green tests for compatibility removal. | The plan now names the affected specs and requires canonical route behavior plus old-query behavior, rather than component/file absence as the active proof. | [x] |
| Add explicit stop conditions. | The plan now halts on backend/API widening, auth-edge shortcuts, public route changes, Document Converter activation, replacement compatibility, or unprovable shared-auth browser proof. | [x] |

## Review Checklist

- [x] Governing docs-as-code item exists.
- [x] PR-0368 dependency is done and approved.
- [x] Cleanup scope is directionally correct.
- [x] Auth-edge invariant is named.
- [x] Backend/API decomposition is excluded.
- [x] Document Converter implementation is excluded.
- [x] Red/green proof plan is concrete enough for the actual compatibility-bearing surfaces.
- [x] Test plan is framed around user-visible/canonical behavior, not only implementation-detail absence.
- [x] Stop conditions are explicit enough for a worker to halt instead of widening scope.

## Review Feedback

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Required Changes

None.

### Re-review Pass

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| Red/green test plan did not name the current compatibility-bearing surfaces. | Resolved. The PR now names `routes.spec.ts`, `App.spec.ts`, `ExamConverterAuthenticatedView.modeRoute.spec.ts`, `conversionHubModeRoute.spec.ts`, `HomeView.spec.ts`, and `AuthSidebar.spec.ts`, with expected red failures against the current PR-0368 state. | `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md:82` |
| Proof language risked implementation-detail absence tests. | Resolved. The PR now requires canonical Exam/Audio route behavior, empty query strings, no teacher-visible lane switch, canonical home/sidebar/proof links, and documents old mode-query behavior as ignored cutover residue. It assigns helper/component removal checks to code search/review rather than active retained tests. | `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md:59`, `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md:66`, `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md:92`, `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md:101` |
| Stop conditions were not explicit enough. | Resolved. The PR now stops on backend/API or generated-type widening, backend app-id split, public Exam route/capability changes, auth-edge shortcuts/rewrites, duplicated auth handling, Document Converter activation, replacement compatibility surfaces, and inability to prove through shared-auth Docker/HuleEdu helper path. | `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md:115` |

No new findings remain.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Cleanup direction is approved.
- [x] Shared runtime/auth/backend preservation is approved.
- [x] Public Exam Converter preservation is approved.
- [x] Document Converter inertness is approved.
- [x] Implementation readiness is approved.

## Post-Implementation Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope Reviewed

| Surface | Evidence |
|---------|----------|
| Canonical protected identities | `frontend/apps/skriptoteket/src/router/routes.ts:44` defines `/apps/exam-converter` and `/apps/audio-transcription` as explicit authenticated routes with presentation props before the generic app route. |
| Stale mode-query residue | `frontend/apps/skriptoteket/src/router/routes.ts:145` preserves `/apps/:appId` as the backend app route, and `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.spec.ts:21` proves `/apps/documents.conversion_hub?mode=transcript` stays generic instead of selecting a canonical teacher-facing identity. |
| Authenticated host behavior | `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue:45` derives presentation solely from inspection fixture or route props and defaults residue to Exam Converter; no query reader/writer or tab component remains in the host. |
| User-visible regression coverage | `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts:45` proves canonical Audio/Exam identities render without shared mode tabs and that `mode` query residue is ignored without URL canonicalization. |
| Live proof/script surface | `scripts/playwright_pr_0363_conversion_mode_deeplink.py` now proves canonical identity paths with no lane switch, and `scripts/playwright_pr_0349_transcript_parity_live.py:54` uses `/apps/audio-transcription` directly. |
| Retained proof artifact | `.artifacts/playwright-pr-0368-presentation-identity-split/20260622T221450Z/manifest.redacted.json` records `/apps/exam-converter` and `/apps/audio-transcription` with empty query strings. |

### Findings

None.

### Reviewer Verification

| Command / check | Outcome |
|-----------------|---------|
| `rg -n 'mode=exam\|mode=transcript\|documents\.conversion_hub\?mode' scripts` | Passed: no matches. |
| `rg -n 'ConversionHubModeTabs\|from "\./conversionHubModeRoute"\|from "@/views/apps/conversionHubModeRoute"\|conversion-hub-mode-' frontend/apps/skriptoteket/src scripts` | Passed: remaining `conversion-hub-mode-*` references are negative assertions only; no helper/component imports remain. |
| `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/components/layout/AuthSidebar.spec.ts` | Passed: 6 files, 35 tests. |
| `pdm run test tests/unit/scripts/test_playwright_script_surface.py` | Passed: 3 tests. |

The heavy transcript parity proof was not rerun during review; the reviewed change there is the route update to the canonical Audio Transcription path, while the worker reported the existing heavy flow was retained.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0374` | Created retained pre-implementation review artifact with `changes_requested` decision and concrete readiness findings. |
| 2 | `REV-PR-0374` | Re-reviewed amended PR-0374, marked findings resolved, and approved implementation readiness. |
| 3 | `REV-PR-0374` | Added post-implementation review pass and approved the implemented cleanup package. |

## Validation

| Command | Outcome |
|---------|---------|
| `pdm run docs-validate` | Passed |
| `git diff --check` | Passed |
