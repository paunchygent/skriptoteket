---
type: review
id: REV-PR-0356
title: "Review: PR-0356 source-only intake and export-owned formats"
status: approved
owners: "agents"
created: 2026-06-15
updated: 2026-06-15
reviewer: "reviewer-pr0356-ruthless"
prs:
  - PR-0356
links:
  - ST-21-10
  - PR-0357
  - EPIC-21
---

## TL;DR

Approved on the second pass. The two prior blockers are resolved: authenticated
browser proof is now retained at both required widths, and invalid replacement
attempts no longer clear a previously selected valid `.dxe`. Focused reruns by
this reviewer passed, including a fresh live proof run with retained artifacts.

## Problem Statement

This review verifies that PR-0356 makes the authenticated Exam Converter intake
source-only without leaving hidden supporting-file state, that PDF/QTI remain
post-conversion file actions, that the public-lane cleanup is governed rather
than half-removed, and that the retained verification evidence is strong enough
to approve a browser-visible product change.

## Proposed Solution

Remove the optional marked/result PDF and visible target toggles from the
authenticated rail, keep default PDF/QTI artifact requests inside the governed
Gateway request, and defer the public one-time lane cleanup to PR-0357 while
preserving readiness-driven file actions after conversion and replay.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0356-st-21-10-exam-converter-source-only-intake-and-export-owned-formats.md` | Scope, acceptance, proof obligations | 10 min |
| `docs/backlog/stories/story-21-10-exam-converter-source-only-intake-and-export-owned-formats.md` | Parent story contract | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterSourceFile.ts` | Source-only intake state and rejection behavior | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Authenticated host wiring and submit/retry path | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterWorkflowRailShell.vue` | Rail UI contract and stale control removal | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterWorkspaceShell.vue` | Drop-zone copy and idle intake guidance | 10 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.ts` | Source-only idempotency/correlation shape | 10 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts` | Multipart field removal | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticated*.spec.ts` | Behavioral proof quality | 15 min |
| `.codex/handoff.md` | Retained verification evidence | 10 min |

**Total estimated time:** ~110 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Authenticated intake is source-only | Matches ST-21-10 and removes stale marked-PDF/target-selection UX. | [x] |
| Default PDF/QTI requests stay producer-owned | Keeps early target choice out of the rail while preserving current artifact support. | [x] |
| Public one-time cleanup is split to PR-0357 | The public lane still has its own governed UI/API/backend contract surface. | [x] |
| Browser-visible closeout needs retained authenticated proof | Repo policy and PR acceptance require it for approval. | [x] |
| Invalid replacement attempts must not destroy a valid selected source file | Source-only rejection should be fail-safe, not state-destructive. | [x] |

## Review Checklist

- [x] Governing docs-as-code authority is present and current.
- [x] Authenticated rail no longer renders optional marked/result upload or early target toggles.
- [x] Authenticated submit/retry omits `graded_result_pdf` and still requests default PDF/QTI artifacts.
- [x] Post-conversion PDF/QTI actions remain readiness-driven.
- [x] Public-lane cleanup is governed by a real follow-up (`PR-0357`), not left as undocumented drift.
- [x] Focused Vitest coverage exercises meaningful user-visible behavior and request-shape outcomes.
- [x] Required authenticated internal-browser proof at compact and desktop widths is retained in `.codex/handoff.md`.
- [x] Invalid `.pdf`/`.docx`/ambiguous replacement attempts preserve the current valid `.dxe` instead of clearing it.

## Review Feedback

**Reviewer:** @reviewer-pr0356-ruthless
**Date:** 2026-06-15
**Verdict:** approved

### Current Review Pass - 2026-06-15 (Second Pass)

Decision: `approved`.

No findings.

The two prior blockers are resolved in the current working tree:

- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterSourceFile.ts`
  now preserves the current valid `.dxe` on invalid picker or drop
  replacement attempts and only replaces it when exactly one governed `.dxe`
  is provided.
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.spec.ts`
  now proves invalid `.pdf`, `.docx`, and ambiguous multi-`.dxe` replacement
  attempts leave the original valid source selected and keep
  `Starta konvertering` enabled.
- `scripts/playwright_pr_0356_source_only_fixture_proof.py` uses the shared
  HuleEdu browser-session helper and captures both required authenticated
  fixture routes at both required widths under the governed artifact lane.
- `.codex/handoff.md` and
  `docs/backlog/prs/pr-0356-st-21-10-exam-converter-source-only-intake-and-export-owned-formats.md`
  now record the sanctioned authenticated proof and retained artifact path.

Fresh reviewer validation rerun:

```bash
pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.spec.ts
pdm run test tests/unit/scripts/test_playwright_script_surface.py
pdm run python -m scripts.playwright_pr_0356_source_only_fixture_proof --base-url http://127.0.0.1:5173 --dotenv .env
pdm run handoff-validate
pdm run docs-validate
git diff --check
```

Results:

- `fe-test`: passed, `1` file / `20` tests.
- `test_playwright_script_surface.py`: passed, `3` tests.
- `playwright_pr_0356_source_only_fixture_proof`: passed and wrote fresh
  retained artifacts under
  `.artifacts/playwright-pr-0356-source-only-fixture-proof/20260614T233142Z/`.
- `handoff-validate`: passed.
- `docs-validate`: passed.
- `git diff --check`: passed.

Spot-check of the fresh proof screenshots from
`.artifacts/playwright-pr-0356-source-only-fixture-proof/20260614T233142Z/`
confirmed the source-only rail visually:

- `complete-qti-ready-desktop.png` shows no optional marked/result upload, no
  target selector, and readiness-driven PDF/QTI file actions.
- `missing-facit-compact.png` shows the source-only rail and the question review
  shell for the missing-facit fixture.

### Historical Review Pass - 2026-06-15 (First Pass)

Decision: `changes_requested`.

Prior findings were the missing retained authenticated browser proof and the
state-destructive invalid replacement behavior. Both are now resolved in the
second-pass reviewed state above.

### Validation Commands And Outcomes

```bash
pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.spec.ts frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedConversionSlice.spec.ts frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/completionContract.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Results:

- `fe-test`: passed, 7 files / 53 tests.
- `fe-type-check`: passed.
- `fe-lint`: passed.
- `fe-build`: passed with the existing Vite dynamic/static import note and large
  chunk warnings.
- `docs-validate`: passed.
- `handoff-validate`: passed.
- `git diff --check`: passed.

### Decision Approvals

- [x] Authenticated intake is source-only
- [x] Default PDF/QTI requests stay producer-owned
- [x] Public cleanup is governed as PR-0357
- [x] Browser-proof evidence is retained
- [x] Invalid replacement attempts are fail-safe

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `docs/backlog/reviews/review-pr-0356-source-only-intake-export-owned-formats.md` | Recorded the independent review, findings, and validation outcomes. |
| 2 | `PR-0356` | Second-pass review approved after rerunning the focused frontend/spec, script-surface, live proof, and docs gates. |
