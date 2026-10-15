---
type: task
id: TASK-SKRIPT-39-09-07
title: 'Export checklist: the export panel lists what Exam.net loses on import after
  a QTI export'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- After a successful QTI export the export panel lists every Fritext question with criteria, with each criterion's text and points to paste into Exam.net.
- The panel lists every shared-instruction subquestion the export scores all-or-nothing with 2 or more points, because Exam.net gives it 1 point.
- The panel lists every Lucktext whose points do not divide evenly over its gaps, with the rounded value each gap gets.
- Questions that import complete are not listed; an export where nothing is lost shows no checklist, and no checklist file is written.
- The checklist comes from the same QTI items the export builds, and an Exam.net import of a walked export shows exactly the listed losses.
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

After a successful QTI export from the exam workspace, the export panel lists
only what Exam.net loses on import (story Q15). Three cases are listed:

- **Fritext with criteria.** Exam.net imports each criterion point as an
  unlabelled 1-point row, so the teacher pastes the criterion text into the
  row labels or Svarsalternativ. The entry shows the question and each
  criterion's text and points. A Fritext without criteria exports one row
  worth its points, loses nothing and is not listed.
- **All-or-nothing subquestion.** A choice, multiple-response or matching
  child of a shared instruction whose points do not divide evenly over its
  correct answers exports all-or-nothing (Q16). Exam.net gives such a
  subquestion 1 point, so the entry shows the question and the points the
  teacher sets in Exam.net. Listed only at 2 or more points.
- **Lucktext with rounded gap values.** A Lucktext whose points do not divide
  evenly over its gaps gives every gap the points divided by the gaps,
  rounded down to 2 decimals (Q17). The entry shows the question, its points
  and the value each gap gets.

Each entry names the question as the workspace shows it: its number and the
start of its question text. Standalone questions, evenly divided points and
Fritext without criteria are not listed. There is no checklist file.

The checklist is computed on the server from the same QTI items the export
builds, with the predicates the XML writer already uses
(`emits_all_or_nothing`, the gap value split in `examnet_qti_xml.py`), so the
list cannot drift from the package. A JSON route beside the QTI export returns
it for the saved head; the SPA requests it after the QTI download succeeds and
shows it in `ExamWorkspaceExportPanel.vue`. The list is cleared when the
document changes or another export starts. The DigiExam converter lane has no
export panel and gets no checklist.

Out of scope: tiered scoring, Matcha ihop export, any checklist download,
and changing how anything exports.

## Contract Inputs

- Story `ST-SKRIPT-39-09`, decided terms Q15, Q16 and Q17.
- Export route `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`
  (`GET .../documents/{lineage_id}/exports/{target}`) and handler
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_exports.py`.
- Workspace QTI mapping `src/skriptoteket/domain/curated_apps/exam_workspace/examnet_qti_export.py`
  (`native_exam_to_examnet_qti_items`, `_parent_qti_item`).
- Scoring predicates `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_xml.py`
  (`emits_all_or_nothing`, `_equal_choice_point_value`, `_gap_point_values`).
- SPA export flow `frontend/apps/skriptoteket/src/views/apps/exam-workspace/useExamWorkspaceExports.ts`,
  `ExamWorkspaceExportPanel.vue`, and `src/api/examWorkspace.ts`.

## Core Vertical And Performance

A teacher saves an exam holding a Fritext with criteria, a shared-instruction
subquestion with uneven points and a Lucktext with uneven points, exports QTI,
and sees the three entries in the export panel; the Exam.net import of that
package shows exactly those losses. The checklist reuses the export's item
mapping once per request; no material performance concern.

## Validation

- Focused unit tests for the checklist function: each listed case, each
  unlisted neighbour (even points, standalone all-or-nothing, 1-point
  subquestion, Fritext without criteria), and agreement with the predicates
  the XML writer uses on recorded corpus documents.
- A focused web test for the checklist route.
- Focused Vitest for the panel: entries shown after export, nothing shown for
  an empty list, cleared on edit and on a new export.
- Agent-driven staging walk and an Exam.net import of the walked package.

## Stop Conditions

- The checklist needs scoring facts the QTI items do not carry.
- Exam.net imports a listed case without the loss, or loses something the
  checklist does not list.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | The checklist lists only Fritext with criteria, all-or-nothing shared-instruction subquestions with 2 or more points, and Lucktext with rounded gap values (story Q15-Q17). |
| T2  | The server computes the checklist from the export's own QTI items and scoring predicates; a JSON route beside the QTI export returns it. |
| T3  | The export panel shows the checklist after a successful QTI export and clears it when the document changes or another export starts; there is no checklist file. |
| T4  | Only the exam workspace gets a checklist; the DigiExam converter lane is unchanged. |
