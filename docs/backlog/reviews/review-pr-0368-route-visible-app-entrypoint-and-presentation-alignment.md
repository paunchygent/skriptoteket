---
type: review
id: REV-PR-0368
title: "Review: PR-0368 route-visible app entrypoint and presentation alignment"
status: approved
owners: "agents"
created: 2026-06-22
updated: 2026-06-22
reviewer: "codex-independent-reviewer"
prs:
  - PR-0368
links:
  - EPIC-37
  - ST-37-04
  - PR-0367
  - PR-0374
  - REF-app-presentation-decomposition-and-naming-plan-v1
  - REF-current-product-lanes-and-sir-convert-boundary-v1
---

## TL;DR

PR-0368 is approved after post-implementation review. The implemented package adds canonical protected `/apps/exam-converter` and `/apps/audio-transcription` identities, keeps public Exam Converter unchanged, leaves Document Converter inert, removes `ConversionHubModeTabs` from normal authenticated flow, retains the old `documents.conversion_hub?mode=...` path only for `PR-0374` cleanup, and preserves the shared HuleEdu/Sir Convert proof lane.

## Problem Statement

The review checks whether `PR-0368` gives an implementation worker a bounded, testable contract for replacing the current tabbed `documents.conversion_hub` presentation with route-visible Exam Converter and Audio Transcription identities without weakening auth, duplicating backend/auth machinery, or preempting later cleanup/MVP slices.

## Proposed Solution

Approved PR-0368 contract:

- Preserve the current public Exam Converter route/capability as an unchanged compatibility contract.
- Keep Document Converter inert in this slice.
- Produce a retained auth-edge inventory and proof plan as the first artifact before route, host, or navigation edits.
- Add focused route/host/home tests and shared-auth live proof that catch the old tabbed combined-app presentation.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `AGENTS.md` | Repo review, docs-as-code, auth-proof, and validation rules | 5 min |
| `docs/index.md` | Current governed docs doorway and linked authorities | 5 min |
| `.codex/handoff.md` | Volatile PR-0367/0368/0374 sequencing and proof constraints | 10 min |
| `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md` | Primary scope, acceptance criteria, implementation plan, test plan | 25 min |
| `docs/backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md` | Completed dependency and registry-only boundary | 5 min |
| `docs/backlog/reviews/review-pr-0367-curated-app-registry-presentation-alignment.md` | Prior retained approval and follow-up ownership | 5 min |
| `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md` | Cleanup owner for temporary mode-route compatibility | 10 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Story-level sequencing and non-goals | 10 min |
| `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md` | Epic-level product direction | 5 min |
| `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md` | Accepted identity split, auth-edge invariant, stop conditions, proof requirements | 25 min |
| `docs/reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md` | Lane ownership and Document Converter boundary | 10 min |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Current protected/public route shape | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Current combined authenticated host and tabbed presentation | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ConversionHubModeTabs.vue` | Current teacher-facing tab surface to retire from normal flow | 5 min |
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | Shared host registry and public Exam host mapping | 5 min |
| `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts` | Current home-card route-visible entrypoints and inert Document Converter card | 5 min |
| `scripts/playwright_pr_0363_conversion_mode_deeplink.py` | Existing old-mode live proof to extend/replace | 5 min |
| `scripts/_playwright_auth.py` and `scripts/_sir_convert_trust_lane_preflight.py` | Required shared-auth proof helpers | 10 min |

**Total estimated time:** ~155 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Split Exam Converter and Audio Transcription into separate teacher-facing route-visible app identities. | Matches the accepted ST-37-04 direction and removes the misleading combined-app tab presentation. | [x] |
| Reuse shared runtime shell, backend clients, Gateway auth, Sir Convert trust lane, replay, polling, formatter, and artifact machinery. | Prevents duplicate auth-edge handling and protects existing HuleEdu/Sir Convert contracts. | [x] |
| Keep PR-0367 registry metadata and public Exam Converter route/capability stable during PR-0368. | PR-0368 is an authenticated presentation split, not a public contract split. | [x] |
| Keep Document Converter inert until a separately reviewed truthful host/backend MVP exists. | Avoids advertising or activating a fake document-conversion lane through the current compatibility host. | [x] |
| Start with a retained auth-edge inventory/proof-plan artifact before implementation edits. | Makes the high-risk auth boundary reviewable before routes and hosts move. | [x] |
| Leave cutover-only `documents.conversion_hub?mode=...` cleanup to PR-0374. | Keeps the route-visible split and compatibility cleanup in separate governed slices. | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate.
- [x] Acceptance criteria or proof obligations are reviewable.
- [x] Risks and structural fault lines are called out explicitly.
- [x] Verification plan matches the claimed contract.
- [x] Public route and capability contracts are frozen for this slice.
- [x] Document Converter remains strictly inert.
- [x] Auth-edge inventory/proof plan is required as a retained first artifact.

## Review Feedback

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-22
**Verdict:** approved

### Required Changes

None.

### Re-review Pass

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| Public Exam Converter route changes were still permitted. | Resolved. PR-0368 now freezes public Exam Converter route, public capability, and public route contract for this slice. | `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:27`, `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:57`, `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:100` |
| Document Converter activation was still allowed. | Resolved. PR-0368 now forbids Document Converter route, alias, host, runtime link, and proof target. | `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:26`, `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:66`, `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:102` |
| Auth-edge inventory was not required as a retained first artifact. | Resolved. PR-0368 now requires `docs/reference/ref-pr-0368-auth-edge-inventory-and-proof-plan.md` before presentation route or host edits, with minimum required contents and Playwright proof script planning. | `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md:75` |

The retained auth-edge inventory file is not expected to exist before implementation; the approved contract requires the worker to create it as the first PR-0368 implementation artifact before any route, host, or navigation edits.

No new findings remain.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] The direction of splitting Exam Converter and Audio Transcription identities is approved.
- [x] The shared runtime/auth/backend machinery invariant is approved.
- [x] The PR-0374 ownership of post-cutover compatibility cleanup is approved.
- [x] PR-0368 implementation readiness is approved.

## Post-Implementation Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-22
**Verdict:** approved

### Scope Reviewed

| Surface | Evidence |
|---------|----------|
| Canonical protected identities | `frontend/apps/skriptoteket/src/router/routes.ts:44` defines `/apps/exam-converter` and `/apps/audio-transcription` before the generic `/apps/:appId` route, both with `requiresAuth` and explicit `presentationMode` props. |
| Shared authenticated runtime host | `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue:43` keeps one host component and selects presentation by prop or cutover query, while runtime composables and backend clients remain shared. |
| Tabbed combined presentation removal | `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue:403` renders the host frame directly with no `ConversionHubModeTabs` in normal flow. Focused specs assert both tab controls are absent. |
| Home entrypoints and inert Document Converter | `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts:41` and `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts:48` point Exam/Audio cards at canonical routes, while `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts:51` keeps Document Converter without a route. |
| Public Exam route/capability preservation | `frontend/apps/skriptoteket/src/router/routes.ts:150` keeps `/public/apps/:appId/:publicCapabilitySlug`; `frontend/apps/skriptoteket/src/router/routes.spec.ts:43` freezes `/public/apps/documents.conversion_hub/exam-converter`. |
| Auth-edge first artifact | `docs/reference/ref-pr-0368-auth-edge-inventory-and-proof-plan.md` inventories Gateway session/CSRF, `/sir-convert`, server-side key injection, signed identity, route grants, shared runtime clients, and forbidden proof shortcuts. |
| Shared-auth dev command hardening | `pyproject.toml:317` moves `fe-dev-shared-auth` to PDM script env mapping, and `tests/unit/test_docker_dev_shared_auth_contract.py` locks the local Gateway/public-backend split. |
| Retained live proof artifact | `.artifacts/playwright-pr-0368-presentation-identity-split/20260622T215450Z/manifest.redacted.json` records both canonical routes with empty query strings and `status: ok`. |

### Findings

None.

### Reviewer Verification

| Command | Outcome |
|---------|---------|
| `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts` | Passed, 27 tests |
| `pdm run fe-test -- --run src/views/HomeView.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/router/routes.spec.ts` | Passed, 24 tests |
| `pdm run test tests/unit/test_docker_dev_shared_auth_contract.py` | Passed, 6 tests |
| `pdm run test tests/unit/scripts/test_playwright_script_surface.py` | Passed, 3 tests |
| `pdm run docs-validate` | Passed |
| `git diff --check` | Passed |

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0368` | Created retained pre-implementation review artifact with `changes_requested` decision and blocking findings. |
| 2 | `REV-PR-0368` | Re-reviewed amended PR-0368, marked previous findings resolved, and approved implementation readiness. |
| 3 | `REV-PR-0368` | Completed post-implementation review and approved the implemented PR-0368 package. |

## Validation

| Command | Outcome |
|---------|---------|
| `pdm run docs-validate` | Passed |
| `git diff --check` | Passed |
