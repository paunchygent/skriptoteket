---
type: review
id: REV-PR-0403
title: "Review: PR-0403 Document Converter preview touch-pinch ownership"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-28
reviewer: "codex"
prs:
  - "PR-0403"
links:
  - "ST-37-04"
  - "PR-0398"
  - "PR-0313"
---

## TL;DR

`approved`. The blocker from the earlier rereview is fixed: the PNPM workspace
now uses the valid `allowBuilds.esbuild: true` configuration, the required
frontend gates are green again, and the remaining PR-0403 touch/pinch proof
still holds.

## Findings

No findings.

## Decision

`approved`

## Problem Statement

The current preview pinch handler is not winning browser gesture arbitration on
touch screens. The app must prevent global page/browser pinch for recognized
preview gestures while preserving one-finger preview panning.

## Proposed Solution

Use the `PR-0313` classroom-map pattern: native non-passive target binding,
platform `gesture*` support, visible zoom-state proof, and anchored zoom around
the gesture midpoint.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0403-st-37-04-document-converter-preview-touch-pinch-ownership.md` | Governing scope and acceptance criteria | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/` | Preview gesture and zoom implementation | 12 min |
| `scripts/authenticated_home_work_apps.py` and helpers | Retained browser proof | 6 min |
| `docs/backlog/prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md` | Prior working reference pattern | 4 min |

**Total estimated time:** ~25 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Preview pinch ownership must be native target-bound | Vue handler proof is insufficient for real browser gesture arbitration | [x] |
| Platform `gesture*` events belong in the preview gesture owner | iPhone/Safari may route pinch through platform gesture events | [x] |
| Zoom must anchor around the gesture midpoint | Top-left scaling makes touch zoom feel broken even when scale changes | [x] |

## Review Checklist

- [x] Governing docs preserve the `PR-0313` lesson and do not accept shallow
      synthetic event proof as sufficient.
- [x] Implementation keeps Document Converter domain-neutral and does not
      import room/classroom semantics.
- [x] One-finger panning remains available.
- [x] Platform gesture and native non-passive target binding are covered by
      focused tests.
- [x] Retained proof reports visible preview zoom-state change and gesture
      ownership evidence.
- [x] Required frontend verification gates are green in the current worktree.

## Review Feedback

**Reviewer:** @codex
**Date:** 2026-06-28
**Verdict:** approved

### Required Changes

None.

### Verification

- Reviewed governing authority in `AGENTS.md`, `docs/index.md`,
  `docs/backlog/prs/pr-0403-st-37-04-document-converter-preview-touch-pinch-ownership.md`,
  `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md`,
  `.codex/handoff.md`, `PR-0313`, and this retained review artifact.
- Inspected the implementation in
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.vue`,
  `useAnchoredDocumentPreviewZoom.ts`,
  `useDocumentPreviewTouchGestures.ts`,
  `useDocumentPreviewZoom.ts`,
  `documentConverterPreview.css`, and
  `DocumentConverterView.vue`.
- Inspected the focused behavioral specs in
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  and
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`.
- Inspected the retained proof helper in `scripts/_document_converter_proof.py`
  and retained artifacts at
  `.artifacts/authenticated-home-work-apps/20260627T232025Z/manifest.redacted.json`
  and
  `.artifacts/authenticated-home-work-apps/20260627T231319Z/document-converter-preview-response.json`.
- Confirmed the blocker fix in `frontend/pnpm-workspace.yaml` now uses
  `allowBuilds: esbuild: true`.
- Ran
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
  and it passed with `5` files and `29` tests.
- Ran `pdm run fe-type-check`; it passed.
- Ran `pdm run fe-lint`; it passed.
- Ran `pdm run fe-build`; it passed. The build emitted existing large-chunk
  warnings, but no PR-0403-specific build failure.

### Findings Summary

- No additional Document Converter-specific behavioral regressions were found
  in the inspected implementation. The earlier PNPM workspace blocker is now
  resolved and the required frontend verification is green.

### Suggestions (Optional)

- Residual non-blocking risk: the retained platform-gesture proof remains a
  synthetic DOM `gesture*` dispatch because Chromium cannot exercise Safari's
  native WebKit gesture path directly. The native-listener CDP inspection,
  browser-level touch pinch, and visible zoom-label assertions are strong, but
  a later Safari device sanity check would still be valuable.

### Decision Approvals

- [x] Preview pinch ownership must be native target-bound
- [x] Platform `gesture*` events belong in the preview gesture owner
- [x] Zoom must anchor around the gesture midpoint

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0403` | Created governed preview touch-pinch ownership slice |
| 2 | `REV-PR-0403` | Recorded the earlier `changes_requested` verdict when the invalid PNPM workspace placeholder blocked frontend proof gates |
| 3 | `REV-PR-0403` | Re-reviewed after the PNPM config fix, reran the frontend gates, and approved the current PR-0403 working tree |
