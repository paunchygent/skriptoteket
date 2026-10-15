---
type: task
id: TASK-SKRIPT-39-09-04
title: 'Fritext criteria: a criteria list replaces the marking guide and exports as
  1-point rows'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-15'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer (gpt-6.1-sol) requested changes on 28454af4 (oversized model and test modules) and approved the repair at dddf0d2f (merged a3525650). Staging walk at a3525650: DOCX-converted document a57a952f carries conversion-filled Fritext criteria; the criteria editor set 2+2+2 and 5; QTI export wrote 20 one-point rows, imported into Exam.net as 5337577 with 6, 5, 3 and 6 one-point rules. Records in Skriptoteket session 01a13c92-d70e-765f-ae36-b6583539e201 evidence/reviews/TASK-SKRIPT-39-09-04/ and evidence/walk/TASK-SKRIPT-39-09-04/walk-record.md.'
task_kind: story
acceptance_criteria:
- A teacher's Fritext with criteria exports one 1-point rule row per criterion point
  and Exam.net imports those rows; DOCX conversion fills the criteria list
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-09 task 4 (story terms Q12, Q13; plan row R14): a
Fritext item carries a list of criteria, each with text and whole points, in
place of the marking-guide text, and exports one 1-point rule row per
criterion point.

- **Model.** `NativeExamItem.marking_guide` is deleted. A Fritext item carries
  `criteria`: a list of criteria, each with non-empty text and whole points
  of at least 1. When the list is non-empty the item's points equal the sum
  of the criterion points, and validation rejects any other value. Other
  kinds carry no criteria. No reader, default or migration is kept for saved
  marking-guide text.
- **QTI export, workspace lane.** A Fritext with criteria writes a mapping
  with one entry per criterion point, each worth 1 (probe V126–V128), and
  MAXSCORE equal to the sum. A Fritext without criteria and with points
  writes one entry worth its points. A Fritext without points stays manual
  and unkeyed. Criterion text is not written to the package.
- **PDF, DOCX writer and own instructions.** The answer-key PDF and the DOCX
  writer print the criteria as a list with each criterion's points under the
  existing "Rättningsmall" label; the own-instructions content uses the
  criterion texts.
- **DOCX conversion.** The produced-item schema carries the criteria list and
  the build prompt asks for each criterion the answer key states with its
  points. When the answer key gives a guide without per-criterion points,
  conversion fills one criterion with the guide text and the item's points
  and marks the points estimated (R14). When it gives no points, that one
  criterion has 1 point, estimated. Item points that are not whole, or a
  criteria sum that differs from the stated points, route the item to the
  existing needs-review boundary.
- **Frontend data layer.** The generated API types are regenerated; the item
  edit helpers, save rules, readiness rules and specs move from
  `marking_guide` to `criteria`; `ExamWorkspaceMarkingGuideField.vue` is
  deleted. The criteria editor UI is the parent's unit, done last.
- **Out of scope.** The export-panel listing of criterion text (task 6);
  Kategorisera (task 3); Kort svar (task 5).

## Contract Inputs

- ST-SKRIPT-39-09 terms Q12, Q13; plan row R14.
- REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type, Fritext
  section (V110, V126–V129, V135–V137).
- Model: `native_exam_document.py:236,292`. Conversion:
  `docx_ai_contracts.py:154-156`, `docx_ai_build.py:195-196`, prompt
  `exam_workspace_docx_build_rounds.py:68,101,159,185`.
- Export: `examnet_qti_export.py:261,273-276` (`_free_text_item`),
  `examnet_qti_xml.py:38,64-87` (`FREE_TEXT_CRITERION_MAP_KEY`).
- PDF and writers: `examnet_pdf_export.py:90,212`,
  `exam_conversion/examnet_pdf_item_rendering.py:115-119`,
  `examnet_pdf_item_strategies.py:32,63`, `exam_pdf_item_semantics.py:95`,
  `infrastructure/.../conversion_hub/exam_workspace_docx_writer.py:165-167`,
  `docx_own_instructions.py:109`, `exam_language_labels.py:39,102,120`.
- Frontend: `examWorkspaceItemEdits.ts:28,335`, `ExamWorkspaceItemEditor.vue:382`,
  `ExamWorkspaceMarkingGuideField.vue`, and the specs that build items with
  `marking_guide`.

## Core Vertical And Performance

A teacher's Fritext with two criteria (2p and 1p) exports as QTI; Exam.net
imports it as freeText with 3 points and three 1-point rule rows. A DOCX
answer key with a prose guide converts to one estimated criterion. No
performance concern.

## Validation

- Focused unit tests for the criteria model rules, the Fritext QTI mapping
  (with criteria, without criteria, without points), the PDF and DOCX writer
  criteria list, and the DOCX build (stated criteria, guide without points
  breakdown, no points, needs-review cases).
- Frontend: focused Vitest for the edit helpers and save rules, and the
  frontend typecheck.
- Staging walk: a Fritext with criteria is exported and imported into
  Exam.net in the agent's own tab and read back through
  `/api/exams/automarked/<id>/questions`.

## Stop Conditions

- Exam.net imports a criteria Fritext with other than one 1-point row per
  criterion point.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | Fritext criteria (text, whole points >= 1) replace the marking-guide text; item points are their sum (Q12). |
| T2  | Export writes one 1-point row per criterion point; no criteria means one row worth the points (Q13). |
| T3  | Conversion fills the criteria; a guide without a points breakdown becomes one estimated criterion (Q12, R14). |
| T4  | The criteria editor UI is the parent's last unit. |
