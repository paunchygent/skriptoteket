---
type: story
id: ST-SKRIPT-39-09
title: QTI 3.0 native export for Exam.net
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: not_required
  decided_at: '2026-10-15'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'All eight tasks done (TASK-SKRIPT-39-09-01..08), each proven by a Hemma staging walk and an Exam.net import read back through /api/exams/automarked; task reviews recorded per task, task 8 review waived by the user 2026-10-15.'
epic: EPIC-SKRIPT-39
acceptance_criteria:
  - The exam workspace exports a QTI 3.0 package that Exam.net imports with the same tasks, keys and points as the workspace shows
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

The exam workspace export and the DigiExam converter, public job included,
write QTI 3.0 packages. Exam.net imports an exported exam with the same tasks,
keys and points as the workspace shows. Today both lanes share one QTI 2.1
writer (`build_examnet_qti_package_plan`, `examnet_qti_package.py:55`), which
Exam.net converts on import.

- **One writer.** The 2.1 writer, its 2.1 code paths and its 2.1 golden files
  are deleted. The golden files are regenerated from the 3.0 writer.
- **Port.** Every existing type keeps its behaviour in 3.0: single and
  multiple choice, Lucktext, Lucktext with dropdown, free text, matching,
  parents with children, and pictures.
- **Shapes.** The writer follows the shapes proven in the HuleEduOS QTI 3.0
  contract. Pictures sit under `items/images/` and are listed as item-resource
  files. Parent children are separated by the empty `SEPARATOR` gap-match.
  Every mapping uses one value for all its entries, because Exam.net reads only
  uniform mappings into rule rows.
- **Kategorisera.** Matching is named Kategorisera and exports only as the
  Exam.net grid; Matcha ihop is not an export target. A row has one or more
  correct columns, and a column may be used by several rows or by none. Each
  correct tick is worth one value, 1 by default, set by the teacher for the
  whole grid; the item's points are that value times the number of ticks.
  DOCX conversion produces many-to-many grids from category-sorting questions.
- **Fritext criteria.** A list of criteria, each with text and whole points,
  replaces the marking-guide text, and the item's points are their sum.
  Conversion fills the list and the editor edits it. The export writes one
  1-point rule row per criterion point; a Fritext without criteria exports one
  row worth its points.
- **Kort svar.** "Ny uppgift" offers a short answer: a Lucktext with one gap
  after the question text, with accepted answers and automatic misspellings.
- **Export checklist.** After a QTI export the export panel lists each Fritext
  question with its criterion text to paste into Exam.net, because Exam.net
  cannot import the criterion wording. Questions that import complete are not
  listed. There is no checklist file.
- **Out of scope.** Tiered scoring (set in Exam.net), Matcha ihop export, and
  the authoring work that stays in ST-SKRIPT-39-06.

## Contract Inputs

- EPIC-SKRIPT-39 story 8 and terms E2, E13 (amended 2026-10-15) and E15.
- HuleEduOS `.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`:
  package layout and the proven item shapes.
- `REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type`: Exam.net
  QTI 3.0 import behaviour per question type (probe rounds 13-18).
- Current code: namespace `imsqti_v2p1` (`examnet_qti_terms.py:15,20`); 13
  `examnet_qti*.py` modules in `domain/curated_apps/exam_conversion/` and
  `domain/curated_apps/exam_workspace/`, writer
  `infrastructure/curated_apps/apps/conversion_hub/examnet_qti_writer.py`;
  `NativeExamItem.marking_guide` (`native_exam_document.py:236`); one-to-one
  matching (`native_exam_document.py:379-395`); export panel
  `ExamWorkspaceExportPanel.vue`.
- Golden fixtures `tests/fixtures/exam_conversion/reference-qti-package.zip`
  and `qti_standalone_item_xml_sha256.json`.

## Tasks

1. Walking skeleton: the workspace on Hemma staging exports one single-choice
   question as a QTI 3.0 package; the agent imports it into Exam.net in its
   own tab and reads back type, key and points.
2. Port: every existing type and both lanes write the proven QTI 3.0 shapes
   (pictures under `items/images/`, equal mapping values, all-or-nothing and
   rounded gap values per Q16 and Q17), and the golden files are regenerated.
3. Kategorisera grid: the teacher-facing name, many-to-many keys with at least
   one correct column per row, one teacher-set value per correct tick (default
   1), grid-only export, and DOCX conversion of category-sorting questions with
   gold examples.
4. Fritext criteria: the criteria list replaces the marking-guide text in the
   model, conversion and editor, and exports as 1-point rows.
5. Kort svar: "Ny uppgift" creates a one-gap Lucktext after the question text.
6. Structured misspellings: one deterministic producer (attested learner
   errors, hunspell REP reversal, keyboard typos) gives every keyed gap its
   automatic misspellings, replacing the model's spelling candidates.
7. Export checklist: after a QTI export the export panel lists each Fritext
   question with its criterion text and each question Q16 or Q17 flags.
8. Source formatting: TASK-SKRIPT-39-09-08 deterministically copies bold,
   italic, underline, superscript, subscript and heading levels from DOCX
   through the rich native document, teacher editor and Exam.net QTI export.

## Verification

- Each task: an agent-driven browser walk on Hemma staging, then an Exam.net
  import of the exported package in the agent's own tab, read back through
  `/api/exams/automarked/<id>/questions` for type, key, points and rules.
- Task 2: one workspace export holding every existing type and one DigiExam
  conversion each import with the same tasks, keys and points as before the
  port.
- Task 3: the gold-corpus eval runs with the many-to-many grid examples.
- Tests only on real input: real workspace documents, real exports and the
  real corpus.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                 |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q1  | The QTI 2.1 writer is replaced outright; its golden files are regenerated as QTI 3.0 and epic term E13 drops the 2.1 baseline (user decision 2026-10-15).                                                                                             |
| Q2  | The exam workspace export and the DigiExam converter, public job included, both move to QTI 3.0 in this story (user decision 2026-10-15).                                                                                                             |
| Q3  | The story ports the existing types and also delivers the Exam.net import routes moved from ST-SKRIPT-39-06 tasks 7-10 (user decision 2026-10-15).                                                                                                     |
| Q4  | Task 1 is a walking skeleton: one single-choice question exported from staging and read back after an Exam.net import (user decision 2026-10-15).                                                                                                     |
| Q5  | Task order: walking skeleton, port, Kategorisera grid, Fritext criteria, Kort svar, export checklist (user decision 2026-10-15).                                                                                                                      |
| Q6  | Package shapes follow the HuleEduOS QTI 3.0 contract: pictures under `items/images/`, `SEPARATOR` gap-match between parent children, uniform mapping values; each is proved by Exam.net import.                                                       |
| Q7  | Matching exports to Exam.net only as the grid (Kategorisera); Matcha ihop is not an export target while its import lists every entry in both columns (user decision 2026-10-15).                                                                      |
| Q8  | Matching is named Kategorisera to teachers, as in Exam.net (user decision 2026-10-15).                                                                                                                                                                |
| Q9  | A Kategorisera row has one or more correct columns; a column may be used by several rows or by none (user decisions 2026-10-15).                                                                                                                      |
| Q10 | A grid scores one uniform value per correct tick, default 1; the teacher sets it for the whole grid and the item's points are that value times the number of ticks; tiered scoring is not modelled and is set in Exam.net (user decision 2026-10-15). |
| Q11 | DOCX conversion produces many-to-many grids from category-sorting questions and the gold corpus gains examples of them (user decision 2026-10-15).                                                                                                    |
| Q12 | Fritext rubric criteria are a list of criteria with text and whole points that replaces the marking-guide text; the item's points are their sum; conversion fills the list (user decision 2026-10-15).                                                |
| Q13 | Fritext exports one 1-point rule row per criterion point, so an N-point criterion becomes N rows; a Fritext without criteria exports one row worth its points (user decision 2026-10-15).                                                             |
| Q14 | 'Ny uppgift' offers a short answer that creates a Lucktext with one gap after the question text, with accepted answers and automatic misspellings (user decision 2026-10-15).                                                                         |
| Q15 | After a QTI export the export panel lists only what Exam.net loses on import: each Fritext question with its criterion text to paste into the row labels or Svarsalternativ, each shared-instruction subquestion scored all-or-nothing with 2 or more points, and each Lucktext with rounded gap values; there is no checklist file (user decisions 2026-10-15). |
| Q16 | Choice, multiple-response and matching questions whose points do not divide evenly over their correct answers export all-or-nothing: one rule worth the points standalone; Exam.net gives a shared-instruction subquestion 1 point, which Q15 flags (user decisions 2026-10-15, probe r19). |
| Q17 | A Lucktext whose points do not divide evenly over its gaps gives every gap the same value, the points divided by the gaps rounded down to 2 decimals, flagged by Q15 (user decision 2026-10-15, probe r19).                                           |
| Q18 | Automatic misspellings come from one deterministic producer, ranked attested learner errors (DaLAJ; Birkbeck and Wikipedia lists), then hunspell REP reversal, then keyboard typos, within the A10 filter; it replaces the model's candidates in DOCX conversion and serves teacher-keyed gaps (user decision 2026-10-15). |
