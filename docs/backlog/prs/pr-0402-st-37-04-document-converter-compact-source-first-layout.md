---
type: pr
id: PR-0402
title: "ST-37-04 Document Converter compact source-first layout"
status: done
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
stories:
  - "ST-37-04"
tags:
  - frontend
  - document-converter
  - responsive-layout
dependencies:
  - "PR-0398"
acceptance_criteria:
  - "Given `Filkonvertering` runs at compact width, when the workspace stacks vertically, then the source/file picker panel appears before conversion controls and preview."
  - "Given local upload now accepts all supported source extensions and infers the selected source format from the chosen file, when the source panel appears first, then teachers can choose the file before adjusting the output format."
  - "Given the authenticated compact proof runs, when it inspects the live Document Converter route, then it verifies source-first compact order, picker extension coverage, source inference, remove clearing, HTML-to-PDF preview, and mode-local result state."
---

# PR-0402: ST-37-04 Document Converter Compact Source-First Layout

## Problem

`PR-0398` temporarily placed compact conversion controls before upload because
the old picker depended on the selected source format. That no longer matches
the product behavior: the picker accepts every supported source extension and
the app infers the source format from the selected file.

Keeping the file picker below conversion controls now creates an inverted small
screen flow. Teachers should start by choosing the file, then adjust the
remaining conversion choices, then inspect the result.

## Goal

Restore compact `Filkonvertering` to the same logical order as the desktop
grammar:

1. source and file picker;
2. conversion and file operations;
3. preview.

This slice intentionally supersedes the compact-order criterion in `PR-0398`
that said conversion controls should appear before local file upload.

## Non-goals

- No new controls, labels, eyebrows, or explanatory copy.
- No change to desktop or tablet column ownership.
- No change to the source-format inference contract.
- No production deploy, commit, or push unless separately requested.

## Implementation Plan

1. Update the compact single-file CSS order so `.dc-rail` appears before
   `.dc-controls` and `.dc-preview`.
2. Update the retained authenticated compact proof helper so it fails if source
   upload appears below conversion controls.
3. Run focused frontend and docs verification.
4. Send the current diff through the required review subagent before closing.

## Test Plan

- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
- Authenticated compact Document Converter browser proof through
  `scripts/authenticated_home_work_apps.py`, or record the bounded reason if the
  local shared-auth stack is unavailable.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Progress

- Created this slice after product review approved source-format inference and
  requested the compact file picker return to the top of the small-screen
  layout.
- Red-first proof: after updating
  `scripts/_document_converter_single_file_proof.py` to require source-first
  compact geometry, `pdm run python -m scripts.authenticated_home_work_apps
  --base-url http://localhost:5173 --artifact-root
  .artifacts/authenticated-home-work-apps --timeout-seconds 120` failed with
  `Document Converter compact file upload is not before conversion controls.`
- Implemented the compact CSS order change in
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css`
  so single-file compact layouts order source, operations, then preview.

## Verification Notes

- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
  -> passed, `2` files and `11` tests.
- `pdm run fe-type-check` -> passed.
- `pdm run fe-lint` -> passed.
- `pdm run docs-validate` -> passed after expanding the review artifact to the
  required contract shape.
- `pdm run handoff-validate` -> passed.
- `git diff --check` -> passed.
- Authenticated browser proof:
  `pdm run python -m scripts.authenticated_home_work_apps --base-url
  http://localhost:5173 --artifact-root .artifacts/authenticated-home-work-apps
  --timeout-seconds 120` -> passed with retained artifacts at
  `.artifacts/authenticated-home-work-apps/20260627T172303Z/`. An earlier
  post-fix attempt hit HuleEdu login rate limiting before route inspection; the
  rerun after the rate-limit window passed.
- Approved by `REV-PR-0402` with no findings.
