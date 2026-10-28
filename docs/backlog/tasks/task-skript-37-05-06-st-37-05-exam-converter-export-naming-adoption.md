---
type: task
id: TASK-SKRIPT-37-05-06
title: ST-37-05 Exam Converter export naming adoption
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: blocked
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-37-05
task_kind: story
acceptance_criteria:
  - Given an Exam Converter export is downloaded or saved, when the output name is generated, then it reflects source exam provenance, canonical output purpose (`Rättat prov`, `Markdown`, or another approved shared label), and correct extension without source-format confusion.
  - Given some Exam Converter outputs are native app state and others may depend on producer replay, when naming is applied, then the adapter declares the authority shape for each output.
  - Given the teacher edits the filename stem, when the export action completes, then extension/content-type truth is preserved and the UI consumes the final sanitized filename returned by the protected API.
dependencies:
  - TASK-SKRIPT-37-05-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Blocked on TASK-SKRIPT-37-05-02 (TASK-SKRIPT-REP-0056 D9). Plan step 4 says "Consume protected API filename authority for each touched save/download action", and acceptance criterion 3 has the UI consume the final sanitized filename the protected API returns; that authority does not exist until TASK-SKRIPT-37-05-02 is done. The dependency is partial: exam workspace downloads already use the server's `Content-Disposition` name, which is `<title>` plus the extension (`handlers/exam_workspace_export_renderer.py:104-157`), and the save name is `<title>.provdokument.zip` (`exam_workspace_file_name.py:31-38`). The labels `Rättat prov` and `Markdown` do not occur in `src/` or `frontend/`.

## Context

Exam Converter exports mix source import, correction, and future native exam
state. Filenames need to identify the intended output without implying the
wrong authority model.

Adopt the shared naming contract for Exam Converter save/export actions.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

Adopt the shared naming contract for Exam Converter save/export actions.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

1. Inventory current Exam Converter save/export actions.
2. Classify each output as app-owned or producer-replay-owned.
3. Apply generated source/purpose names plus editable stems using the canonical
   shared purpose vocabulary.
4. Consume protected API filename authority for each touched save/download
   action.
5. Add tests for naming, extension handling, canonical purpose labels, and
   authority-specific behavior.

## Implementation Steps

1. Inventory current Exam Converter save/export actions.
2. Classify each output as app-owned or producer-replay-owned.
3. Apply generated source/purpose names plus editable stems using the canonical
   shared purpose vocabulary.
4. Consume protected API filename authority for each touched save/download
   action.
5. Add tests for naming, extension handling, canonical purpose labels, and
   authority-specific behavior.

## Proof

- Focused Exam Converter frontend/backend tests for touched actions, including
  canonical purpose vocabulary and protected API filename authority.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Relevant backend gates if API handlers change.
- `pdm run docs-validate`
- `git diff --check`

## Validation

- Focused Exam Converter frontend/backend tests for touched actions, including
  canonical purpose vocabulary and protected API filename authority.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Relevant backend gates if API handlers change.
- `pdm run docs-validate`
- `git diff --check`

## Stop Conditions

Revert Exam Converter naming adoption and keep current file action behavior.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                     |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The task stays `blocked` on TASK-SKRIPT-37-05-02, which is named in `dependencies` (orchestrator decision 2026-10-28, TASK-SKRIPT-REP-0056 D9); the Implementation Contract paragraph gives the evidence. |

## Lessons Learned

No separate material is recorded in the source snapshot.

## Notes

### Problem

Exam Converter exports mix source import, correction, and future native exam
state. Filenames need to identify the intended output without implying the
wrong authority model.

### Goal

Adopt the shared naming contract for Exam Converter save/export actions.

### Non-goals

- No new Exam Converter export formats.
- No correction replay architecture change.
- No question-pool or QTI implementation.

### Implementation Plan

1. Inventory current Exam Converter save/export actions.
2. Classify each output as app-owned or producer-replay-owned.
3. Apply generated source/purpose names plus editable stems using the canonical
   shared purpose vocabulary.
4. Consume protected API filename authority for each touched save/download
   action.
5. Add tests for naming, extension handling, canonical purpose labels, and
   authority-specific behavior.

### Test Plan

- Focused Exam Converter frontend/backend tests for touched actions, including
  canonical purpose vocabulary and protected API filename authority.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Relevant backend gates if API handlers change.
- `pdm run docs-validate`
- `git diff --check`

### Rollback Plan

Revert Exam Converter naming adoption and keep current file action behavior.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
