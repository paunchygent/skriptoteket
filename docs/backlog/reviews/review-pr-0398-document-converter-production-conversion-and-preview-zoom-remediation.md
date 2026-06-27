---
type: review
id: REV-PR-0398
title: "Review: PR-0398 Document Converter production conversion and preview zoom remediation"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "independent-reviewer-b"
prs:
  - "PR-0398"
links:
  - "EPIC-37"
  - "ST-37-04"
  - "PR-0384"
  - "REV-PR-0384"
  - "PR-0397"
  - "REV-PR-0397"
  - "PR-0399"
---

# Review: PR-0398 Document Converter Production Conversion And Preview Zoom Remediation

## TL;DR

`approved`. The second repair resolves both frontend UX blockers in the current
tree.

- Failed current project refresh now keeps the retained PDF visibly non-current
  with `Visar föregående PDF.`, suppresses ready-state copy, disables
  filename/download/save/artifact actions, and restores the normal
  ready/download/save path after retry succeeds.
- Failed project download/save on an otherwise ready current preview no longer
  trips stale-preview mode. The preview stays current and review-ready,
  filename/download/save remain enabled, artifact selection stays available,
  and the UI shows only the action error copy.

## Findings

No findings.

## Decision

`approved`

## Problem Statement

`PR-0398` needed to make two Document Converter behaviors truthful on the
authenticated route: failed current preview refreshes must not look ready, and
non-preview action failures must not demote a still-current preview into a
stale previous-result state.

## Proposed Solution

The current repair does the right thing by narrowing stale-preview mode to
retryable project-preview failures and keeping ordinary action failures local to
the current ready preview state.

## Artifacts to Review

- Governing docs:
  `AGENTS.md`, `.codex/handoff.md`, `docs/index.md`,
  `docs/backlog/prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md`,
  `docs/backlog/prs/pr-0399-st-37-04-sir-convert-v2-status-vocabulary-contract.md`
  for dependency context only, and this retained review artifact.
- Frontend/proof files:
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`,
  `DocumentConverterView.spec.ts`,
  `DocumentConverterResultPanel.vue`,
  `DocumentConverterResultPanel.spec.ts`,
  `useDocumentPreviewZoom.ts`,
  `documentConverterPreview.css`,
  `useDocumentConverterProjectPreview.ts`,
  `scripts/_document_converter_proof.py`,
  `scripts/authenticated_home_work_apps.py`,
  `.artifacts/authenticated-home-work-apps/20260627T134816Z/manifest.redacted.json`.
- Public surface reviewed:
  authenticated `/apps/document-converter` preview/result behavior and retained
  browser-proof claims for PR-0398 only.
- Explicitly out of scope here:
  PR-0399 as a standalone backend contract review.

## Key Decisions

- Accept the failed-refresh stale-preview repair as behaviorally correct on the
  current tree.
- Accept the narrowed failure predicate as sufficient to keep download/save
  action errors from demoting a ready current preview.
- Keep the previously retained zoom/pinch browser proof as sufficient for this
  re-review because the second repair did not change that surface.

## Review Checklist

- [x] Re-read the updated PR-0398 doc and retained review context.
- [x] Scoped the re-review to PR-0398 frontend/proof behavior only.
- [x] Inspected the `DocumentConverterView.vue` and
  `DocumentConverterView.spec.ts` second-repair diff directly.
- [x] Verified the failed-refresh stale-preview path in the updated focused
  route spec.
- [x] Verified the new failed download/save regression path in the updated
  focused route spec.
- [x] Reran focused frontend proof on the current tree.
- [x] Updated the retained review artifact with the final verdict.

## Evidence Commands Run

- `git diff -- frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts docs/backlog/reviews/review-pr-0398-document-converter-production-conversion-and-preview-zoom-remediation.md`
- `sed -n '150,340p' frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`
- `sed -n '340,520p' frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
- `rg -n "^\\s*it\\(" frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  - Passed: `7 passed`
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts`
  - Passed: `27 passed`

## Residual Risks

- I did not rerun the live authenticated browser proof in this re-review pass.
  That is acceptable because the second repair only narrows the route’s
  failed-preview/action-error state logic; the retained zoom/pinch proof surface
  is unchanged.
- This approval is intentionally limited to PR-0398 frontend/proof behavior.
  PR-0399 backend contract correctness remains owned by the separate review.

## Review Feedback

- Condition 1 verified: failed preview refresh shows the retained PDF as
  previous, disables current actions, and retry success restores the normal
  ready path.
- Condition 2 verified: failed project download/save on a ready current preview
  keeps the preview current/ready, leaves filename/download/save/artifact
  selection available, and shows only the action error.

## Implementation Response Notes

**Responder:** `Harvey`
**Date:** `2026-06-27`

- Narrowed stale-preview mode to retryable project-preview failures instead of
  any `project.errorMessage`.
- Added a focused regression proving download/save failures keep the current
  preview authoritative.
- Kept the failed-refresh stale-preview and retry-recovery regression green.

## Changes Made

- Re-reviewed the second repair with the same PR-0398 frontend/proof-only
  scope.
- Verified both requested behaviors directly in the updated route spec and the
  focused Document Converter suite.
- Updated the retained review verdict to `approved`.
