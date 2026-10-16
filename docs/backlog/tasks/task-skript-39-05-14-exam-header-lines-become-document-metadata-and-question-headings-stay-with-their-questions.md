---
type: task
id: TASK-SKRIPT-39-05-14
title: Exam header lines become document metadata and question headings stay with
  their questions
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-16'
status: done
closeout_review:
  record: inline
  status: not_required
  decided_at: '2026-10-16'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'User closed the task on 2026-10-16 ("close TASK-SKRIPT-39-05-14 and ST-SKRIPT-39-05 as done (user closure)"). Units U2a-U9 passed independent Sol review and rereview before integration (review-*.md, rereview-*.md). Merged to main 7eec5716 and 827c301a. Grouping-only re-record evidence/regroup-2026-10-16c/ (EXIT=0). Staging re-walk at 827c301a: Svenska 2 kursavslutande converted to 24 items, 0 review items, 36 points, judge 24/24 gold, QTI export 200; Exam.net import 5344745 shows three parts, 24 tasks, 36p and no header text. Records in Skriptoteket session 01a144e3-b8c4-7ea5-bee6-6dfc5e242786 evidence/staging-walk-39-05-14b/walk-report.md.'
task_kind: story
acceptance_criteria:
- A converted DOCX exam shows no header line (course line, exam total, part totals)
  as exam text in the editor, PDF, DOCX or Exam.net items; a printed total that differs
  from the item points raises a non-blocking signal; a heading carrying a question
  number or points opens its question or parent; and Svenska 2 kursavslutande imports
  into Exam.net with no repeated header text
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

The grouping prompt sends totals, section headings and points lines to
`other_anchors`, which nothing reads. Those anchors fall through to the nearest
question family, non-title metadata lands in `document.instructions`, and the
QTI adapter prepends the document instructions to every parent item
(`examnet_qti_export.py:169`). The staging walk of 2026-10-16 (Exam.net 5339992)
showed "Svenska 2 / Total: 36 poäng / Poäng: 15 poäng" at the top of each
Exam.net part. A heading that carries a question number and points, such as
"2. Tempus (3 p)", can become a stray review item.

This task changes the conversion and the exports as follows:

- Header anchors replace `other_anchors` in the grouping output: the course
  line, the exam total line and each part total line. Every input anchor lands
  in exactly one of title, header, a question, a shared context or an answer
  key; no anchor is silently lost.
- The native exam document carries the header data: the raw text of the source
  course line as a course hint, and the printed exam and part totals. Header
  lines never enter `document.instructions`, parent instructions or item bodies.
- The printed exam total is compared with the sum of item points, and each
  printed part total with the sum of its parent's item points. A mismatch
  raises a non-blocking signal on the exam or the parent that names the printed
  and computed totals. Export stays allowed.
- Code assigns a heading that carries a question number or printed points to
  the question it opens: the number becomes the label, the printed points
  become the points, and the heading words become body text. A heading over two
  or more questions opens their parent instruction.
- Exports: QTI items carry no header text; the QTI test title is the document
  title; the manifest metadata carries the title and the course hint. PDF and
  DOCX print a generated header with the title, the course hint when present,
  and "Totalt: N poäng" computed from item points.
- A line whose whole content is metadata is a header anchor at its own scope:
  the exam, a part, or one question. A question's own points line, such as
  "Poäng: 3 poäng" under that question, is a question-level header anchor that
  governs that one question. It never enters item text. A question's printed
  points, in its heading or on that line, set its points; criteria and split
  items are redistributed through native scoring. The build's points apply only
  when nothing is printed. Walk of 2026-10-16 (document
  f0ea76bf, revision 18) showed these lines in item bodies of questions 16, 22
  and 24 after the grouping put them into question anchors.
- The editor gets no course control in this task.
- The document format changes in place under a new schema version. Skriptoteket
  is not a live app with users, so no reader, migration or compatibility path
  exists for older documents.

Out of scope: the course list, the course dropdown, the metadata panel and
title or file-name editing (ST-SKRIPT-39-08, with Mina filer renaming under
ST-SKRIPT-37-05), and the remaining corpus misses under ST-SKRIPT-39-05 item 3.

## Contract Inputs

- Grouping prompt and schema:
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_docx_grouping.py`.
- Manifest and labeler source:
  `src/skriptoteket/domain/curated_apps/exam_workspace/docx_manifest.py`.
- Family batching of unclaimed anchors:
  `src/skriptoteket/domain/curated_apps/exam_workspace/docx_batches.py`.
- Heading rules:
  `src/skriptoteket/domain/curated_apps/exam_workspace/docx_instruction_runs.py`.
- Build admission, state and assembly:
  `exam_workspace_docx_build_admission.py`, `exam_workspace_docx_build_state.py`
  and `exam_workspace_docx_assembly.py` under
  `src/skriptoteket/application/curated_apps/handlers/`;
  `src/skriptoteket/domain/curated_apps/exam_workspace/docx_ai_build.py`.
- Document model:
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`.
- Exports: `examnet_qti_export.py` and `examnet_pdf_export.py` under
  `src/skriptoteket/domain/curated_apps/exam_workspace/`;
  `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_manifest.py`;
  `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_writer.py`.
- v14 recordings `tests/fixtures/exam_conversion/docx_key_provenance_v14/` and
  the replay harness
  `tests/unit/application/curated_apps/handlers/docx_pipeline_replay.py`.
- Evidence: retained session `01a141b5-f55d-747d-8515-1e07d2fc0d0f`
  `evidence/staging-walk/` (exam-document.json, exam-qti.zip).

## Core Vertical And Performance

A DOCX upload runs grouping, which returns header anchors; the manifest records
them; the build assembles a native document whose header data holds the course
hint and printed totals and whose instructions hold no header line; the
workspace opens with the totals signal where totals differ; QTI, PDF and DOCX
exports read the header data. The grouping call keeps its single request per
exam and the task adds no model call.

## Validation

- Focused tests: manifest and grouping schema tests
  (`tests/unit/domain/curated_apps/exam_workspace/test_docx_manifest.py`), the
  heading assignment, the totals signal, the native document model, and the QTI,
  PDF and DOCX export tests for header text and the generated header.
- Re-record only the grouping step for the eight corpus exams and replay the
  existing build recordings offline through the replay harness. No full corpus
  rerun.
- After the question-level repair: a fresh grouping-only re-record of the
  corpus exams, then a staging re-walk of Svenska 2 kursavslutande with the
  Exam.net import.
- Hemma staging walk: convert Svenska 2 kursavslutande, check the editor, the
  PDF header and the totals, export QTI and import it into Exam.net with no
  header text in any item.

## Stop Conditions

- A re-recorded grouping changes question families so that the existing build
  recordings no longer replay: report to the user before re-recording any build
  call.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Printed exam and part totals are compared with item points and are not stored as exam text; the course line is kept as document metadata for ST-SKRIPT-39-08; QTI carries the title plus the course in manifest metadata and repeats nothing header-derived in items (user 2026-10-16). |
| D2  | Code assigns a numbered or pointed heading to the question it opens, or to the parent when it heads several questions; header anchors replace the reader-less `other_anchors` bucket (user 2026-10-16). |
| D3  | Validation is focused tests, a grouping-only re-record replayed offline, and one staging walk with an Exam.net import; no full corpus rerun (user 2026-10-16). |
| D6  | The document format changes in place under a new schema version with no reader, migration or compatibility path, because Skriptoteket is not a live app with users (user 2026-10-16). |
| D8  | A totals mismatch is a non-blocking signal; export stays allowed (user 2026-10-16). |
| D9  | This task is the conversion fix; the course dropdown, course list and metadata panel are the first task of ST-SKRIPT-39-08 (user 2026-10-16). |
| D11 | PDF and DOCX print a generated header with the title, the raw course hint and "Totalt: N poäng" computed from item points; the editor gets no course control in this task (user 2026-10-16). |
| D12 | A line whose whole content is metadata is a header anchor at its own scope (exam, part or one question); a question's own points line is a question-level header anchor and never item text (user 2026-10-16). |
| D13 | A question's printed points, in its heading or on its own points line, set that question's points; criteria and split items are redistributed through native scoring; the build's points apply only when nothing is printed, replacing the heading-conflict review (user 2026-10-16). |
| D14 | The question-level repair is validated by focused tests, a fresh grouping-only corpus re-record, and a staging re-walk of Svenska 2 kursavslutande with the Exam.net import (user 2026-10-16). |
