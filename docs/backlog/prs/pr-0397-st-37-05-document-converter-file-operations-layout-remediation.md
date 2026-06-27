---
type: pr
id: PR-0397
title: "ST-37-05 Document Converter file operations layout remediation"
status: done
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
stories:
  - "ST-37-05"
tags:
  - frontend
  - document-converter
  - exports
  - layout
dependencies:
  - "PR-0396"
acceptance_criteria:
  - "Given the teacher uses HTML/CSS project conversion, when the route renders, then file intake and source lists live in the left column, output and file operations live in the middle column, and the preview column contains preview only."
  - "Given the teacher uses single-file conversion, when the route renders, then the same left/middle/right column contract is used instead of a separate cramped action layout."
  - "Given a result is available, when filename editing, download, or save controls are shown, then those controls are in the central operations column and remain legible with the final extension visible."
  - "Given a result preview or artifact selector is shown, when the teacher scans the preview column, then it contains no save/download buttons, filename input, or raw implementation ids."
---

# PR-0397: ST-37-05 Document Converter File Operations Layout Remediation

## Problem

`PR-0396` adopted the filename protocol, but the filename editor and
download/save actions were placed in the result footer. On narrower preview
widths this compresses source provenance, filename editing, extension display,
and two file-action buttons into a crowded footer that is hard to read.

## Goal

Align Document Converter with a stable three-column workspace contract:

- left column: source intake, file picker/drop area, and selected source files;
- middle column: output settings, create/convert action, generated-output
  selector, editable filename stem, download, save, and retry/status actions;
- right column: preview only.

The same layout contract must apply to both HTML/CSS project conversion and
single-file conversion.

## Non-goals

- No backend filename protocol changes.
- No new conversion route support.
- No shared cross-app primitive extraction in this slice.
- No product copy expansion beyond what is needed to make the existing controls
  understandable in their new locations.

## Implementation Plan

1. Done: project file drop/picker controls now live in the left source column.
2. Done: single-file local picker and saved-file selector now live in the left
   source column while format/output controls remain in the middle column.
3. Done: filename editing and download/save actions moved out of the preview
   footer into a shared middle-column file-operations section.
4. Done: the result panel now renders preview state only; generated-output
   selection is owned by the middle operations column.
5. Done: the layout keeps CSS-owned grid geometry, token-driven styles, and a
   shared action section used by both conversion modes.

## Test Plan

- Focused Document Converter Vitest tests proving both modes use the same
  source/operations/preview column ownership.
- Focused tests proving filename/download/save controls are absent from the
  preview column and present in the operations column.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- Live authenticated Document Converter route proof with the local shared-auth
  stack.
- `pdm run docs-validate`
- `git diff --check`

## Progress

- Added red-first rendered-ownership specs in
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  and
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  for the new source/operations/preview column contract.
- Refactored the route so the left column owns intake and source review, the
  middle column owns conversion settings, generated-output selection, and file
  operations, and the right column owns preview only.
- Introduced a shared local file-operations component to keep filename,
  download, save, retry, and status ownership consistent between
  `HTML/CSS-projekt` and `Filkonvertering`.
- Strengthened
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  so it now creates a succeeded single-file result, hydrates the history-backed
  ready state, and proves the same source/operations/preview ownership after
  success.

## Verification Notes

- Red-first evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  failed before the refactor because
  `[data-testid="document-converter-source-column"]` was missing and the
  filename/download/save controls still rendered inside the preview footer.
- Focused green evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts`
  passed with `22 passed`.
- Retained-review fix evidence: red-first production failure was not feasible
  for the reviewer blocker because the implementation was already present and
  the missing proof was the problem. The pre-edit focused run
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  passed on the current tree, so the slice was resolved by strengthening the
  single-file spec to create a successful result and verify column ownership
  after success.
- Frontend gates:
  `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed
  locally. `fe-build` kept the existing large-chunk warnings.
- Live authenticated browser proof:
  `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90`
  passed with artifact directory
  `.artifacts/authenticated-home-work-apps/20260627T104130Z/`.
  `manifest.redacted.json` records
  `document_converter_forbidden_surfaces_absent=true`, preview enablement after
  auto-render, and refreshed desktop/compact screenshots for
  `/apps/document-converter`.
- Layout screenshot evidence:
  `.artifacts/pr-0397-layout-screenshots/20260627T104912Z/` contains
  viewport and full-page screenshots for empty and active
  `HTML/CSS-projekt` and `Filkonvertering` states at desktop, tablet, and
  compact widths, with generated-output selection asserted outside preview.

## Rollback Plan

Revert this slice to restore the PR-0396 result-footer layout while preserving
backend filename authority.
