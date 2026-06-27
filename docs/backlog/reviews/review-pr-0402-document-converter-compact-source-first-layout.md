---
type: review
id: REV-PR-0402
title: "Review: PR-0402 Document Converter compact source-first layout"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "codex"
prs:
  - "PR-0402"
links:
  - "ST-37-04"
  - "PR-0398"
---

## TL;DR

Review the compact `Filkonvertering` layout change that restores source/file
picker first ordering after source-format inference made upload format-agnostic.

## Problem Statement

The compact Document Converter layout still placed conversion controls before
the file picker, matching an older dependency where upload format choices were
teacher-selected first. The current app accepts all supported source extensions
and infers source format from the selected file, so that compact order is now
inverted.

## Proposed Solution

Supersede the old compact-order rule in governed docs, order the source column
before operations on compact single-file layouts, and update the authenticated
compact proof helper so it fails if upload appears below conversion controls.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0402-st-37-04-document-converter-compact-source-first-layout.md` | Governing scope and acceptance criteria | 3 min |
| `docs/backlog/prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md` | Superseded compact ordering | 2 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css` | Compact CSS order | 3 min |
| `scripts/_document_converter_single_file_proof.py` | Live compact geometry proof | 3 min |

**Total estimated time:** ~11 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Source/file picker leads compact `Filkonvertering` | Source inference removes the old need to choose source format before upload | [x] |
| Browser proof owns compact geometry | CSS order is user-visible and jsdom cannot prove rendered vertical order | [x] |

## Review Checklist

- [x] Governing docs match the product decision and do not leave the old
      compact-order rule as active truth.
- [x] Compact CSS orders source, operations, and preview predictably without
      changing desktop/tablet ownership.
- [x] The retained browser proof fails if compact source upload appears below
      conversion controls.
- [x] Focused frontend and docs verification are recorded.

## Review Feedback

**Reviewer:** @codex
**Date:** 2026-06-27
**Verdict:** approved

### Required Changes

None.

### Findings

No findings. The current working tree diff stays inside the governed compact
layout slice: the CSS change only swaps `.dc-rail` and `.dc-controls` order for
stacked single-file workbench layouts, the preview remains third, and the proof
helper now fails on real compact geometry if upload no longer renders above the
conversion controls.

### Verification

- Inspected the governed docs updates in `PR-0402`, the superseded `PR-0398`
  compact-order text, `ST-37-04`, `docs/index.md`, and `.codex/handoff.md` for
  docs-as-code consistency.
- Inspected
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css`
  and confirmed the change is limited to compact single-file order inside the
  existing stacked breakpoint.
- Inspected `scripts/_document_converter_single_file_proof.py` and confirmed
  the retained proof now asserts live compact geometry with
  `source_box["y"] < operations_box["y"]`, plus existing picker acceptance,
  source inference, remove clearing, preview, and mode-local result checks.
- Inspected
  `.artifacts/authenticated-home-work-apps/20260627T172303Z/manifest.redacted.json`
  and confirmed the retained compact proof recorded
  `single_file_compact.compact_source_upload_before_controls: true`.
- Confirmed the recorded focused gates are appropriate for this slice:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`,
  `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`,
  `pdm run handoff-validate`, and `git diff --check`.

### Suggestions (Optional)

- Non-blocking future improvement: retain an additional compact single-file
  screenshot artifact if later layout drift investigations need a visual diff in
  addition to the manifest geometry assertion.

### Decision Approvals

- [x] Source/file picker leads compact `Filkonvertering`
- [x] Browser proof owns compact geometry

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0402` | Created governed compact source-first layout slice |
| 2 | `REV-PR-0402` | Approved the current working tree diff with no findings after CSS, proof, docs, and retained artifact review |
