---
type: task
id: TASK-SKRIPT-39-05-09
title: Label-first per-question retry, DOCX pictures as exam assets, field-label gaps
  and the marking-guide rubric
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-14'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-14'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer approved the repair 659973e5 after review of 0beba709 and rereview of c20ce483; merged eafb1487. D44 live replay on low-27 Fråga 6 kept all six given phrases as text. Staging walk at eafb1487: pictures in editor and review items, label-first retry reconverted only the chosen question, QTI export with 4 inline pictures, Exam.net import exam 5331367 kept every picture with SUN inline. Records in Skriptoteket session 01a13798-9df1-75fa-a4c5-bd755b4bfd85 evidence/review/TASK-SKRIPT-39-05-09/ and evidence/walk/TASK-SKRIPT-39-05-09/staging-walk.md.'
task_kind: story
acceptance_criteria:
- A teacher keeps or changes a question's type and reconverts only that question;
  DOCX pictures show in review and converted items and reach the QTI export; low-27
  field-label phrases stay text
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Story item 6, the follow-up to TASK-SKRIPT-39-05-04. Three app changes, one
branch:

- **Label-first retry.** A question's review shows the type the labeler chose
  first. The teacher keeps or changes it and clicks "Konvertera igen"; only
  that question goes to the converter with that type, and the reply replaces
  the item (converted, or review item when it fails again). Today no
  single-question reconversion exists; the only per-item request is answer-key
  suggestions, which no UI calls.
- **Pictures.** DOCX drawings become exam assets at their place in the
  question. Review items and converted items carry them as asset segments; the
  editor shows the picture as an image; the QTI export carries it to Exam.net
  through the existing asset path. Today pictures reach only the labeler
  (`exam_workspace_labeler_block_image.py`), review items drop picture-only
  chunks (`docx_ai_build.py` `review_source_item`), and the workspace shows no
  image at all.
- **D44 (low-27).** A phrase printed after a field label is given material
  unless the question's instruction asks the student for it; it stays text.
  One structural prompt sentence; no new check.

D31 is settled by the 2026-10-14 probe: Exam.net imports a QTI 2.1
`rubricBlock` (scorer and tutor views) as raw HTML inside the student-visible
information block (exam 5326289). The marking guide therefore stays out of the
QTI export; DOCX and PDF answer keys keep it.

## Contract Inputs

- ST-SKRIPT-39-05 item 6; TASK-SKRIPT-39-05-04 D14, D31, D43, D44.
- Retry endpoint and handler beside the DOCX build rounds
  (`exam_workspace_docx_build_rounds.py`, `exam_workspace_docx_build_admission.py`).
- Native assets: `NativeExamAsset`, `NativeAssetSegment` in
  `native_exam_document.py`; QTI image resources in `examnet_qti_export.py`.
- Frontend: `ExamWorkspaceItemEditor.vue`, `ExamWorkspaceItemDrawer.vue`,
  `examWorkspaceBodySegments.ts`.

## Core Vertical And Performance

Teacher opens an imported exam, picks a review item, keeps or changes its
type, clicks "Konvertera igen", and sees the reconverted question; a question
with a picture shows the picture in the editor and in the Exam.net import. A
retry is one converter call for one question; the rest of the document is not
touched.

## Validation

- Focused unit tests for the retry handler, asset extraction and the prompt
  sentence; Vitest for the retry control and image rendering.
- One live replay of the low-27 question showing the field-label phrases as
  text.
- Ruff, mypy, frontend typecheck.
- Parent staging walk: retry on a review item, a DOCX with a picture through
  editor, QTI export and Exam.net import.

## Stop Conditions

- A retry would need to reconvert other questions.
- Exam.net rejects the QTI image resource for a DOCX picture.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Label-first retry: the review shows the labeler's type first; the teacher keeps or changes it and reconverts only that question with that type; the reply replaces the item (user decision 2026-10-14). |
| D2  | DOCX pictures become exam assets at their place in the question: review and converted items carry them, the editor shows them as images, the QTI export carries them (user decision 2026-10-14). |
| D3  | D44 is fixed by one structural prompt sentence (a phrase after a field label is given material unless the instruction asks for it), proven by a live replay of the low-27 question; no new check (user decision 2026-10-14). |
| D4  | The marking guide stays out of the QTI export: the 2026-10-14 probe showed Exam.net puts a QTI rubric block into the student-visible information block (exam 5326289). |
| D5  | One task, one branch, in the shared TASK-SKRIPT-39-05-06 worktree (user decision 2026-10-14). |
