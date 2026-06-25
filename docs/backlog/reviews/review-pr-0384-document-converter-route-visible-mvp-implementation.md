---
type: review
id: REV-PR-0384
title: "Review: PR-0384 Document Converter route-visible MVP implementation"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
reviewer: "codex-independent-reviewer"
prs:
  - PR-0384
links:
  - ST-37-04
  - EPIC-37
  - PR-0382
  - REV-PR-0382
  - PR-0383
---

# Review: PR-0384 Document Converter Route-Visible MVP Implementation

## TL;DR

Independent re-review completed for the PR-0384 repair pass. The four prior
findings are resolved: the route no longer presents fake preview-navigation
controls, failed refresh preserves the last successful preview as stale/retryable
state, local file intake replaces by declared filename and rejects unsupported
or over-cap selections before submission, and the duplicate inner
`SKRIPTOTEKET` branding is gone. The route remains honest about this MVP’s
scope by presenting artifact/result-oriented preview state instead of pretending
to render interactive PDF pages.

## Problem Statement

`PR-0384` is the first authenticated route-visible Document Converter slice.
That makes truthfulness more important than mockup parity alone: the route must
consume Skriptoteket-owned preview/save/download endpoints, keep copy and icon
contracts locked, present only real teacher-facing affordances, and reuse
shared UI patterns without creating immediate cross-app drift.

## Proposed Solution

Expose `/apps/document-converter` ahead of the generic curated-app host, link
the authenticated home card to it, and ship a dedicated HTML/CSS project
workspace that lets a teacher add supported files, choose template/output/paper
settings, preview the resulting PDF, and explicitly download/save/discard the
selected server-owned artifact through scoped Skriptoteket endpoints.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0384-st-37-04-document-converter-route-visible-mvp-implementation.md` | Scope, stop conditions, claimed proof, copy and route activation contract | 20 min |
| `docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/copy-approval/swedish-copy-v4.md` | Locked Swedish copy, icon, and output-choice constraints | 20 min |
| `frontend/apps/skriptoteket/src/router/routes.ts`, `frontend/apps/skriptoteket/src/router/routes.spec.ts`, `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`, `frontend/apps/skriptoteket/src/views/HomeView.spec.ts` | Route ordering, auth meta, home-card activation | 20 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`, `useDocumentConverterProjectPreview.ts`, `documentConverterProjectPreviewApi.ts`, `documentConverterProjectFiles.ts` | Route-visible workspace truthfulness, preview/download/save/discard behavior, local file-state handling | 60 min |
| `frontend/apps/skriptoteket/src/components/ui/UiSegmentedTileToggle.vue`, `frontend/apps/skriptoteket/src/components/ui/UiSegmentedTileToggle.spec.ts` | Shared control extraction versus drift | 20 min |
| `frontend/apps/skriptoteket/src/components/icons/*.vue`, `frontend/apps/skriptoteket/src/components/icons/index.ts` | Canonical icon-wrapper compliance | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter/browserDownload.ts`, nearby transcript/exam/classroom surfaces | Cross-app reuse and duplication audit | 30 min |
| `scripts/authenticated_home_work_apps.py`, `.artifacts/authenticated-home-work-apps/20260625T190452Z/*` | Retained shared-auth proof truthfulness and layout/copy review | 25 min |

**Total estimated time:** ~3.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the route-specific project-preview API under Skriptoteket-owned `/api/v1/apps/documents.conversion_hub/document-converter/...` endpoints. | Preserves the no-Sir-Convert-from-browser contract and keeps artifact authority server-owned. | [x] |
| Reuse shared UI primitives and icon wrappers before adding app-local styling. | Prevents immediate cross-app segmented-control and icon drift. | [x] |
| Expose only `Enskilda PDF-filer` and `Kombinerad PDF` in the visible UI. | Copy lock explicitly removes visible `both`/`Båda`. | [x] |
| Ship only truthful preview controls and failure recovery. | Route-visible MVP cannot present fake preview/navigation affordances. | [x] |
| Keep the app header scoped to the app, not duplicate product-shell branding. | The surrounding authenticated shell already brands Skriptoteket. | [x] |

## Review Checklist

- [x] The route resolves before generic `/apps/:appId` and keeps auth meta truthful.
- [x] The authenticated home card now links to `/apps/document-converter` and removes `Kommer senare`.
- [x] Visible output choices are limited to `Enskilda PDF-filer` and `Kombinerad PDF`.
- [x] Paper-size controls expose A3/A4/A5.
- [x] New document-converter icons are canonical wrapper components instead of direct Lucide leaks in route code.
- [x] Shared reuse improved for tile-style segmented output choices and browser download triggering.
- [x] The preview pane is now result-oriented and no longer presents fake PDF navigation/zoom controls.
- [x] Failure recovery preserves a usable stale preview when refresh fails.
- [x] Local file-state handling enforces supported manifest constraints before the backend rejects them.
- [x] Route-visible shell copy avoids duplicating `SKRIPTOTEKET` inside the already branded app shell.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-25`
**Verdict:** `approved`

### Implementation Repair Notes

**Repair owner:** `codex-pr-0384-implementation-specialist`
**Repair date:** `2026-06-25`
**Repair status:** `repaired_pending_re_review`

- Finding 1 repaired by removing the inert page-strip, page navigation, zoom
  buttons, and blank PDF canvas from the route-visible result surface. The
  preview pane now shows selected artifact/result state plus download/save and
  discard actions only; full PDF rendering remains out of scope for this MVP.
- Finding 2 repaired in `useDocumentConverterProjectPreview.ts`: failed refresh
  attempts now preserve the last successful preview and selected artifact, mark
  the result stale, and leave the retry path available until success or discard.
- Finding 3 repaired in `useDocumentConverterProjectPreview.ts`: local file
  intake now replaces by declared filename, rejects unsupported file types, and
  enforces the current HTML/CSS/image caps before mutating route state.
- Finding 4 repaired by removing the inner `SKRIPTOTEKET` route header and
  keeping only the app-specific `DOKUMENTKONVERTERARE` title.
- Red repair proof: `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  failed before repair with 6 failing tests covering duplicate shell branding,
  duplicate filename submission, unsupported-file rejection, cap overflow,
  inert preview controls, and failed-refresh preview loss.
- Green repair proof: focused Document Converter spec passed 8/8; focused
  route/home/API/shared-control group passed 28/28; `pdm run fe-type-check`,
  `pdm run fe-lint`, and shared-auth browser proof passed with refreshed
  artifacts in `.artifacts/authenticated-home-work-apps/20260625T192730Z/`.

### Required Changes

None.

### Re-review Outcome

The prior findings are resolved:

1. The fake PDF-navigation/zoom/page surface is gone. The view now presents an
   artifact/result-oriented preview area only, with no inert controls that
   imply page rendering or zoom behavior.
2. Failed refresh now preserves the last successful preview and selected
   artifact while marking the state stale and keeping retry plus artifact
   actions available.
3. Local file intake now replaces by declared filename, rejects unsupported
   files, and enforces the governed HTML/CSS/image caps before state mutation
   and submission.
4. The inner `SKRIPTOTEKET` route branding was removed; the authenticated shell
   remains the only product-level brand surface while the route header now names
   the app as `DOKUMENTKONVERTERARE`.

No remaining blocking findings were identified in the repaired scope.

## Cross-App Reuse Audit

### Extract Now

- `UiSegmentedTileToggle` is the right immediate extraction. The output-mode cards are no longer route-local duplicated segmented styling, and the new control is promoted through the shared UI index.
- Reusing `triggerBrowserDownload()` from
  [browserDownload.ts](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/frontend/apps/skriptoteket/src/views/apps/exam-converter/browserDownload.ts:1)
  is also the right immediate reuse. It avoids another copy of the local Blob-to-download helper and keeps Document Converter aligned with Exam Converter and transcript artifact downloads.
- The new icon files are acceptable because they follow the canonical-wrapper pattern under `src/components/icons/` instead of leaking direct Lucide imports into the route view.

### Acceptable Local Duplication

- The route-local project-preview API client keeps its own URL builder and manifest construction instead of sharing a generic artifact-action client with transcript or Exam Converter. That duplication is acceptable here because the semantics differ materially: Document Converter actions are keyed by `{preview_id, artifact_id}` on Skriptoteket-owned project-preview resources, while transcript uses `{transcriptId, artifactKey}` and authenticated Exam Converter still routes through Sir Convert artifact contracts.
- The Document Converter composable also keeps its own view state instead of reusing the heavier transcript/exam file-action state helpers. That is acceptable because this route owns preview generation plus project-file orchestration, not only artifact action state.

### Follow-Up-Worthy Consolidation

- There is a broader frontend hardening opportunity around owner-scoped artifact action state, success/failure feedback, and runtime response validation across Document Converter, transcript formatter exports, and authenticated/public Exam Converter downloads. That should be its own governed follow-up if the team wants a shared artifact-action library.
- `UiSegmentedTileToggle` currently stops at visual reuse and does not yet inherit the fuller keyboard/focus behavior of `UiSegmentedToggle`. That is worth a shared UI follow-up, but it is not a blocker for this PR now that the route no longer presents fake preview behavior.

## Verification

- Reviewed `AGENTS.md`, `.codex/handoff.md`, `.codex/rules/025-curated-apps.md`,
  `.codex/rules/045-huleedu-design-system.md`, `.codex/rules/070-testing-standards.md`,
  `.codex/rules/075-browser-automation.md`, `.codex/rules/096-review-workflow.md`,
  `docs/index.md`, `docs/backlog/prs/pr-0384-st-37-04-document-converter-route-visible-mvp-implementation.md`,
  `docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/copy-approval/swedish-copy-v4.md`,
  and the routed `ruthless-code-review`, `testing`, `agent-docs-governance`,
  `integrated-frontend-stack`, and `skriptoteket-testing` guidance.
- `git status --short`
  Confirmed a dirty working tree in the expected PR-0384 scope plus unrelated docs work; no unrelated changes were reverted.
- `git diff --stat -- frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterProjectPreview.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterPreview.css frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts docs/backlog/prs/pr-0384-st-37-04-document-converter-route-visible-mvp-implementation.md .codex/handoff.md`
  Confirmed the repair scope is bounded to the expected PR-0384 files.
- `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  Passed: `1` file, `8` tests.
- `pdm run fe-test -- --run src/components/ui/UiSegmentedTileToggle.spec.ts src/router/routes.spec.ts src/views/HomeView.spec.ts src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts`
  Passed: `5` files, `28` tests.
- `pdm run fe-type-check`
  Passed.
- `pdm run fe-lint`
  Passed.
- `pdm run docs-validate`
  Passed.
- Visual review of
  `.artifacts/authenticated-home-work-apps/20260625T192730Z/document-converter-desktop.png`
  and `.artifacts/authenticated-home-work-apps/20260625T192730Z/document-converter-compact.png`
  confirmed the duplicate inner branding is removed and the route no longer
  shows fake page-navigation or zoom controls in the retained proof surface.
- I did not rerun the shared-auth browser script because the review brief only
  required focused checks and the refreshed retained artifacts already captured
  the repaired route state.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0384` | Created the retained independent review record for the route-visible Document Converter MVP implementation. |
| 2 | `REV-PR-0384` | Recorded four findings covering preview truthfulness, refresh recovery, local file-state validation, and duplicated shell branding. |
| 3 | `REV-PR-0384` | Captured the cross-app reuse audit, distinguishing immediate extraction wins from acceptable local duplication and separate follow-up candidates. |
| 4 | `REV-PR-0384` | Added implementation repair notes and focused validation evidence for the accepted findings while leaving the independent verdict pending re-review. |
| 5 | `REV-PR-0384` | Re-reviewed the repair pass, reran focused frontend/docs gates, and approved the slice with no remaining blockers. |
