---
type: review
id: REV-PR-0398
title: "Review: PR-0398 Document Converter production conversion and preview zoom remediation"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "fixed-review-subagent"
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

`approved`. The implementation response closes the last remaining high finding:
replacement batches that include any unsupported file now fail closed before a
submit payload can be built, and the focused regression proves the exact
supported-plus-unsupported case that previously slipped through.

## Findings

No findings.

## Decision

`approved`

## Problem Statement

This rereview covers the implementation response to the last retained PR-0398
finding only:

- fail-closed handling for supported-plus-unsupported replacement batches in
  `Filkonvertering`
- the new focused frontend regression for that case
- the PR-0398 verification-note update that records the red/green evidence

## Proposed Solution

The response is acceptable because the inference path now rejects any
replacement batch containing even one unsupported file before source-format set
construction, and the focused spec proves the exact replacement flow that had
been missing.

## Artifacts to Review

- Governing docs:
  `AGENTS.md`, `.codex/handoff.md`, `docs/index.md`,
  `docs/backlog/prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md`,
  and this retained review artifact.
- Frontend proof files:
  `useDocumentConverterSingleFile.ts`,
  `DocumentConverterSingleFileView.spec.ts`,
  plus the retained PR doc verification notes.
- Public surface reviewed:
  authenticated `/apps/document-converter` single-file replacement validation
  semantics for supported-plus-unsupported batches.

## Key Decisions

- Accept the `selectLocalUploads()` repair: unsupported filename detection now
  runs before source-format set construction and clears `selectedUploads`
  immediately on any `null` inference.
- Accept the focused regression as truthful proof of the former bug class:
  starting with a valid upload, replacing it with `lektion.html` plus
  `anteckning.txt`, then proving the UI shows `Filformatet stöds inte.`, clears
  the visible list, and blocks submit.
- Keep the earlier compact browser-proof artifact as sufficient for the
  unchanged browser-visible parts of the addendum.

## Review Checklist

- [x] Re-read the updated PR-0398 doc and retained review context.
- [x] Scoped the rereview to the last retained high finding and its proof.
- [x] Inspected the patched inference control flow and the new regression.
- [x] Re-ran the focused single-file spec and adjacent Document Converter
  frontend scope.
- [x] Verified the PR-0398 doc records the red/green evidence for this fix.
- [x] Updated the retained review artifact with the final verdict.

## Evidence Commands Run

- `git status --short`
- `git diff --stat`
- `git diff -- frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterSingleFile.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts docs/backlog/prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md`
- `nl -ba frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterSingleFile.ts | sed -n '228,276p'`
- `nl -ba frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts | sed -n '440,540p'`
- `rg -n "supported-plus-unsupported|support|unsupported|9 passed|red|green|stöds inte" docs/backlog/prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md`
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`

## Residual Risks

No blocking residual risks found in this rereview. The unchanged browser-visible
claims remain covered by the earlier retained authenticated proof artifact at
`.artifacts/authenticated-home-work-apps/20260627T162846Z/manifest.redacted.json`.

## Review Feedback

- The implementation response matches the requested fix shape exactly: any
  unsupported filename now fails the replacement batch before route inference
  can treat the remaining supported file as valid.
- The focused regression is strong proof because it starts from the stale-upload
  state that previously masked the bug and verifies the user-visible error,
  cleared source list, and blocked submit boundary.

## Implementation Response Notes

**Responder:** `current uncommitted addendum`
**Date:** `2026-06-27`

- Added workspace-mode scoping to route-session history.
- Added filename-based local source-format inference and compact single-file
  layout ordering.
- Added focused specs for cross-mode leak checks and basic picker inference.
- Added retained compact browser-proof/docs updates for the single-file slice.
- Added the exact supported-plus-unsupported replacement regression and the
  corresponding fail-closed production repair.

## Changes Made

- Re-reviewed the implementation response to the last retained high finding.
- Replaced the previous `changes_requested` blocker with an `approved` verdict.
