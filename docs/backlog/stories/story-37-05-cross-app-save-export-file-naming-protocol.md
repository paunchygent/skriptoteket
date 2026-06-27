---
type: story
id: ST-37-05
title: "Cross-app save/export file naming protocol"
status: ready
owners: "agents"
created: 2026-06-26
epic: "EPIC-37"
dependencies:
  - "ST-37-04"
  - "ST-21-08"
  - "ST-14-36"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
acceptance_criteria:
  - "Given curated apps create downloads and `Mina filer` records, when a default filename is generated, then it uses source provenance, teacher-facing output purpose, and a version or timestamp signal without duplicating extensions."
  - "Given a teacher downloads or saves a generated output, when the workflow supports naming, then the teacher can edit the filename stem while the system owns extension and content-type consistency."
  - "Given a teacher has a saved file in `Mina filer`, when they rename it, then the record name changes without mutating bytes, source references, hashes, or content-type truth."
  - "Given some outputs are app-owned and others are producer-replay-owned, when save/export naming is implemented, then shared core contracts stay cohesive while app adapters declare only necessary authority differences."
  - "Given Audio Transcription, Exam Converter, Document Converter, and later curated apps need file actions, when implementation PRs are created, then they reuse shared backend/frontend naming and save primitives rather than duplicating app-specific flows."
ui_impact: "Yes (save/download filename editing, Mina filer rename affordances, app-specific export panels)."
data_impact: "Yes (saved file display names and source-reference metadata contracts)."
---

# ST-37-05: Cross-App Save/Export File Naming Protocol

## Context

Current exported and saved files can be hard for teachers to recognize later.
Some names are redundant, some omit source provenance, and app lanes can drift
into different download/save UX for the same underlying user need.

This story creates a shared protocol for file naming, save, export, edit, and
rename behavior across curated apps. The aim is not decorative consistency; it
is dependable file authority at the smallest useful layer, then app-specific UI
where the underlying authority genuinely differs.

## Scope

- Shared naming rules for generated downloads and `Mina filer` saves.
- Shared validation and extension ownership.
- Editable filename stems before download/save.
- Rename support for `Mina filer` records.
- Clear distinction between application-owned outputs and producer-replay
  outputs.
- App-specific adoption for Audio Transcription, Exam Converter, and Document
  Converter after the shared protocol is reviewed.

## Non-Goals

- No implementation inside `PR-0385` except avoiding obvious naming regressions.
- No forced single artifact model across materially different app workflows.
- No source-workspace/project restoration promise.
- No migration or mass rename of existing saved files in the first slice.

## Planned PR Slices

- [ ] [PR-0390: ST-37-05 file naming/save/export protocol reference](../prs/pr-0390-st-37-05-file-naming-save-export-protocol-reference.md)
- [ ] [PR-0391: ST-37-05 shared save/export naming backend contract](../prs/pr-0391-st-37-05-shared-save-export-naming-backend-contract.md)
- [ ] [PR-0392: ST-37-05 shared filename editing UI primitives](../prs/pr-0392-st-37-05-shared-filename-editing-ui-primitives.md)
- [ ] [PR-0393: ST-37-05 Mina filer rename and extension contract](../prs/pr-0393-st-37-05-mina-filer-rename-and-extension-contract.md)
- [ ] [PR-0394: ST-37-05 Audio Transcription export naming adoption](../prs/pr-0394-st-37-05-audio-transcription-export-naming-adoption.md)
- [ ] [PR-0395: ST-37-05 Exam Converter export naming adoption](../prs/pr-0395-st-37-05-exam-converter-export-naming-adoption.md)
- [x] [PR-0396: ST-37-05 Document Converter save/export naming adoption](../prs/pr-0396-st-37-05-document-converter-save-export-naming-adoption.md)
- [x] [PR-0397: ST-37-05 Document Converter file operations layout remediation](../prs/pr-0397-st-37-05-document-converter-file-operations-layout-remediation.md)

## Notes

- Start at the reference and core contract. App adoption must not invent a new
  filename parser, extension policy, or duplicate-save rule in each route.
- Keep source references separate from display names. Names help teachers;
  source references preserve authority.
- Prefer a simple durable core and thin app adapters over broad generic UI that
  hides materially different producer/app authority.
