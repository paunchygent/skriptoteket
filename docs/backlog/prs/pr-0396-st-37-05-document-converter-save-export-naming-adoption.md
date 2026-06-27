---
type: pr
id: PR-0396
title: "ST-37-05 Document Converter save/export naming adoption"
status: done
owners: "agents"
created: 2026-06-26
updated: 2026-06-27
stories:
  - "ST-37-05"
tags:
  - frontend
  - backend
  - document-converter
  - exports
dependencies:
  - "PR-0385"
  - "PR-0390"
  - "PR-0391"
  - "PR-0392"
acceptance_criteria:
  - "Given Document Converter creates a single-file or project-preview output, when the teacher downloads or saves it, then the default filename derives from source file or project title, canonical output purpose (`Konverterad PDF`, `Word-dokument`, `Markdown`, `Sammanslagen PDF`, or `Separat PDF`), and correct extension."
  - "Given the teacher uses `Mina filer` as a source, when a new output is saved, then source reference and display filename remain distinct and the name does not imply project workspace restoration."
  - "Given separate project preview outputs exist, when saved or downloaded, then each has a predictable distinguished name without raw artifact ids in visible UI."
  - "Given the teacher edits the filename stem before save or download, when the action completes, then the protected API remains the final filename authority and repeated saves create new records with system-disambiguated final filenames."
---

# PR-0396: ST-37-05 Document Converter Save/Export Naming Adoption

## Problem

`PR-0385` gives Document Converter useful saved-file sources and current-session
history. Filename editing and cross-app naming protocol adoption should remain
a separate follow-up so the save/reopen boundary is not overbuilt.

## Goal

Adopt the shared naming contract for Document Converter download and
`Mina filer` save actions.

This slice is explicitly authorized to adopt the approved ST-37-05 protocol
directly for Document Converter while `PR-0391`/`PR-0392` remain open for later
shared backend/UI extraction.

## Non-goals

- No saved project/package model.
- No multi-file HTML/CSS source selection from `Mina filer`.
- No change to PR-0385 current-session history semantics.

## Implementation Plan

1. Map local upload, saved-file source, and project-preview source labels into
   source-derived default names.
2. Add editable stems before download/save using the shared UI primitive.
3. Preserve the PR-0385 rule that reopen means using a saved output as a new
   source where supported, not restoring a project workspace.
4. Map touched PDF, DOCX, Markdown, separate-output, and combined-output paths
   to the canonical shared purpose labels.
5. Consume protected API filename authority for save/download completion.
6. Add tests for single-file PDF/DOCX/Markdown output names, saved-source
   output names, separate/combined project preview output names, and
   repeated-save disambiguation.

## Test Plan

- Focused Document Converter backend/frontend tests, including canonical
  purpose vocabulary for PDF, DOCX, Markdown, separate, and combined outputs;
  protected API filename authority; extension preservation; and repeated-save
  disambiguation.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Implementation Summary

Document Converter now applies backend-owned protocol filenames for
single-file downloads/saves and HTML/CSS project-preview downloads/saves. The
route may submit a teacher-edited filename stem, but the protected backend/API
returns the final filename, extension, and content type. Repeated saves create
new `Mina filer` records with system disambiguation, while saved-source
provenance stays separate from the display filename.

## Verification

- `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/application/curated_apps/handlers/test_document_converter_naming_adoption.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py`
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts`
- `/opt/homebrew/bin/pdm run fe-gen-api-types`
- `/opt/homebrew/bin/pdm run lint`
- `/opt/homebrew/bin/pdm run typecheck`
- `/opt/homebrew/bin/pdm run fe-type-check`
- `/opt/homebrew/bin/pdm run fe-lint`
- `/opt/homebrew/bin/pdm run fe-build`
- `/opt/homebrew/bin/pdm run handoff-validate`
- `/opt/homebrew/bin/pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Revert Document Converter naming adoption and keep the PR-0385 save/export
behavior unchanged.
