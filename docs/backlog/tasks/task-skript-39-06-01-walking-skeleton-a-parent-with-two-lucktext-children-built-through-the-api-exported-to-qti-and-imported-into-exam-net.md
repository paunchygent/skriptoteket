---
type: task
id: TASK-SKRIPT-39-06-01
title: 'Walking skeleton: a parent with two Lucktext children built through the API, exported to QTI and imported into Exam.net'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A parent with a shared instruction and two Lucktext children, each with its own points, created and saved through the workspace API, exports as QTI 3.0 and imports into Exam.net through the teacher's browser with the parent total equal to the children's sum
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

The native document already holds parents: `NativeExamParent` on
`native_exam_document_v4`, checked by `validate_parent_structure` and summed by
`parent_points`. The whole-document PUT saves them, and the QTI export writes
one item per parent with the `SEPARATOR` gap-match before every Lucktext
child. Only conversion has created parents so far. No teacher-created parent
has gone through save, reopen and export into Exam.net. This task proves that
path end to end and repairs whatever blocks it. It is backend, API and export
work; it adds no workspace control (story P18).

This task delivers:

- On Hemma staging, an exam document made by the existing DOCX import route
  gets a saved revision through
  `PUT /api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}`
  that holds one parent with a shared instruction and two Lucktext
  (`gap_fill`) children with `parse_origin` `teacher_created`, each with its
  own points. The API has no route that makes a blank document; this task
  adds none.
- Reopening through the document GET returns the same parent and children,
  and the parent's points are the sum of its children's points
  (`parent_points`).
- The QTI export through `exports/qti` writes the parent as one item: the
  shared instruction as a paragraph, the empty `SEPARATOR` gap-match before
  each child sentence (story P12), one interaction per child with its own
  response and mapping, and SCORE summing the children.
- The package imports into Exam.net through the teacher's browser session as
  one task with children a) and b), each with its own points and the task
  total equal to their sum.
- Every defect found on this path is fixed in this task.

Out of scope: parent and child commands (TASK-SKRIPT-39-06-03), other kinds
as children, and any workspace control (ST-SKRIPT-40-04).

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P4, P6, P8, P12 and P18.
- Parent model: `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_parent.py`
  (`NativeExamParent`, `validate_parent_structure`, `parent_points`) and
  `native_exam_document.py` (`NativeExamDocument.parents`, origin kinds
  `docx_import` and `created`).
- Save route: `SaveExamWorkspaceDocumentHandler` in
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`
  and the PUT route in `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- Parent export: `examnet_qti_export.py` (one item per parent) and
  `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_item_xml.py`
  (`_append_parent_item`, `_append_child_body`, `_separator_identifier`).
- Proven layout: the BF26 English 1 package and the all-types import of
  2026-10-10 (Exam.net exam 5310254), recorded in the story's Contract Inputs.
- Hemma staging and browser proof: the shared `staging-walk` skill.

## Core Vertical And Performance

The agent opens an imported exam on Hemma staging, saves a revision through
the PUT route that adds a parent "Fyll i rätt form av verbet" with two
Lucktext children worth 2 and 3 points, reopens it and sees the parent with 5
points. The agent exports QTI, imports the package into Exam.net through the
teacher's browser and sees one task with a) and b) worth 2 and 3 points and a
total of 5. Save, reopen and export each take one request.

## Validation

- Focused backend test on a real saved workspace document: a revision with a
  teacher-created parent of two `gap_fill` children saves through the save
  handler, reads back unchanged, and its QTI export holds one item with the
  `SEPARATOR` before each child sentence, one response per child and SCORE
  summing the children.
- Exam.net proof on Hemma staging: the saved revision, the exported package
  and screenshots of the Exam.net import showing the task, its children and
  their points, retained in the retained root's `evidence/`.

## Stop Conditions

- The PUT route refuses a teacher-created parent and the fix needs a change to
  the parent model: report to the user before changing it.
- Exam.net imports the children differently from the 2026-10-10 import (merged
  children, lost points, a different type): stop and report with the
  screenshots.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | The walking skeleton is a parent with two Lucktext children built through the workspace API, exported as QTI 3.0 and imported into Exam.net through the teacher's browser; the editor UI comes from ST-SKRIPT-40-04 (story P8). |
| P2  | A parent holds one shared instruction and child questions of any mix of types (story P4).                                                                                                                                       |
| P3  | Each child has its own points; the parent shows their sum and is not edited directly (story P6).                                                                                                                                |
| P4  | Lucktext children export with the empty `SEPARATOR` gap-match before every child sentence, a recorded exception to QTI 3.0 schema validity (story P12).                                                                         |
| P5  | This story ships backend, data, API and export only; the current workspace screens are frozen except for bug fixes (story P18, user 2026-10-17 G2).                                                                             |
