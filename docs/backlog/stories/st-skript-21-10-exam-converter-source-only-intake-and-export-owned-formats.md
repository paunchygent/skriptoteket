---
type: story
id: ST-SKRIPT-21-10
title: Exam Converter source-only intake and export-owned formats
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: canceled
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User confirmed 2026-10-20 the removal of the public guest DigiExam converter line (ST-SKRIPT-41-02 term P6, user grilling 2026-10-18, retained root 01a14ee0-903e-7423-b969-30e3661e9006); P6 closes TASK-SKRIPT-21-10-01 and ST-SKRIPT-21-10 as superseded by TASK-SKRIPT-41-02-03.
epic: EPIC-SKRIPT-21
acceptance_criteria:
  - Given a teacher starts an Exam Converter job, when intake renders or submits, then the active product flow requires only one governed source exam file and no optional marked, graded, result, or supporting exam upload is shown, accepted as current product intent, or included in the job spec unless a future accepted contract reintroduces it.
  - Given the answer-key enrichment stage is available, when the source exam lacks machine-readable facit, then Skriptoteket uses the configured LLM enrichment plus teacher review/editor workflow instead of asking the teacher to supply a marked exam file.
  - Given target files are artifacts of the converted/replayed exam, when the teacher starts conversion, then the product requests the currently supported target artifacts by default and defers the visible choice of download/save format to the `Filer` surface after conversion and review.
  - Given a help or question-mark icon is visible in the intake rail or file surface, when the teacher hovers, focuses, or activates it, then it opens accessible teacher-facing help; orphaned icons without a tooltip/popover are removed.
  - Given DOCX is added later, when the target contract exists, then DOCX appears as another post-conversion file action using the same source-neutral exam state as PDF/QTI, not as a separate early target-selection step.
  - Given the future QTI/editor direction lands, when a converted test is saved, then Skriptoteket treats the source-neutral exam representation as editable, shareable product state that can feed PDF, DOCX, QTI, and later question-pool workflows.
  - Given Conversion Hub remains the heavy conversion boundary, when teachers edit, share, or assemble tests later, then lightweight test editing and question-pool work happens in Skriptoteket while Sir Convert remains responsible for heavy source import, LLM enrichment, OCR/PDF, and model-backed conversions.
retired_ids:
  - ST-21-10
backlog_document_profile: contract-derived
---

## Slice Contract

Superseded by TASK-SKRIPT-41-02-03 (ST-SKRIPT-41-02 P6), user decision
2026-10-20. This story set source-only intake and export-owned formats for
both Exam Converter lanes. The signed-in lane was retired by
TASK-SKRIPT-39-07-03 and the public guest lane is removed by
TASK-SKRIPT-41-02-03. The exam workspace, with DigiExam as one import, is the
exam conversion and editing app, and its exports are chosen after editing.

## Contract Inputs

- ST-SKRIPT-41-02 P6; TASK-SKRIPT-41-02-03; TASK-SKRIPT-39-07-03; ADR-SKRIPT-0085 (superseded by EPIC-SKRIPT-41).
- The pre-migration legacy body of this story is retained at `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15f53-3b1b-7dcd-8cae-f7e114f55406/evidence/legacy-profile-history/st-skript-21-10.pre-migration.md`.

## Tasks

| Task                 | Delivers                                     | Depends on |
| -------------------- | -------------------------------------------- | ---------- |
| TASK-SKRIPT-21-10-01 | Canceled: superseded by TASK-SKRIPT-41-02-03 | None       |

## Verification

None: the story closes without implementation.

## Decided Contract Terms

| ID  | Decided contract term                                                                         |
| --- | --------------------------------------------------------------------------------------------- |
| S1  | The story is canceled as superseded by TASK-SKRIPT-41-02-03; no task under it is implemented. |
