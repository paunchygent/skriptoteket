---
type: task
id: TASK-SKRIPT-41-02-01
title: Teachers and guests import a QTI package into the exam workspace
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A QTI package exported by Skriptoteket or Exam.net imports into a native exam document with its items, points and answer keys, signed-in and as a guest, with no AI
- Unsupported QTI items are skipped with a visible note
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

The workspace exports QTI (`examnet_qti_export.py`, `examnet_qti_leaf_items.py`) but cannot import it. This task adds a deterministic QTI package importer that maps the item kinds the workspace exports (choice, gap fill, inline choice, free text, information items) back to a native exam document, the way `build_native_exam_from_digiexam` maps DigiExam, and offers it as `QTI` in the Öppna drawer for signed-in teachers and as a stateless parse for guests (Q1-Q3).

Non-goals: AI repair of imported items; QTI versions other than the one the export writes and Exam.net's own export.

## Contract Inputs

- ST-SKRIPT-41-02 P1; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- `domain/curated_apps/exam_workspace/digiexam_import.py` (mapper pattern), `examnet_qti_export.py`, `docs/reference/ref-skript-research-exam-net-qti-import-routes-per-question-type-*.md`.
- Mac parent rulings 2026-10-18, relayed by the orchestrator to the implementation lead:
  - Ordering items import, with answer-key origin `teacher_authored`, because the QTI key is the order the teacher wrote. They are not skipped under 39-06-08 D3.
  - These Q2 round-trip losses are accepted because the export cannot carry them. Tests assert each one by name: free-text rubric criterion text (never written), document instructions folded into every item prompt, automatic gap values merged into accepted values, and a parent with one non-gap child flattened to a standalone item.
  - AC1's Exam.net part stays in this task. The Skriptoteket QTI shape is built and proven first. A real Exam.net export, supplied by the Mac parent, becomes a fixture and is proven before review.

## Core Vertical And Performance

The vertical is one pure domain mapper from a parsed QTI package to a `NativeExamDocument`, used by the signed-in import (stored in Mina filer like the DigiExam import) and by a public stateless parse route returning the document. Round trip: export then import gives the same items, points and keys. No performance concern beyond package size limits.

## Validation

- Focused tests: round trip of the omprov fixture export; each supported item kind; skipped unsupported items with notes; malformed packages refused with a Swedish error.
- Vitest for the Öppna QTI entry. Lint and typecheck for touched domains.

## Stop Conditions

Stop and report if Exam.net's own export uses item kinds the export never writes and they need a product decision.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| Q1  | QTI import is deterministic and makes no AI call. |
| Q2  | A Skriptoteket QTI export imported again gives the same items, points and answer keys. |
| Q3  | Unsupported items are skipped with a visible note, as in the DigiExam import. |
