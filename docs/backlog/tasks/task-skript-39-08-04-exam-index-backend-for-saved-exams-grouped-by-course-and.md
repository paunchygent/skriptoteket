---
type: task
id: TASK-SKRIPT-39-08-04
title: Exam index backend for saved exams grouped by course and sorted by date
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-16'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Implementation review approved (review-2, retained 01a149c9-5bc7-7713-ba64-12dee0470bdd evidence/reviews/39-08-04-review-2.md). Closeout review approved with no blocking findings at main bd4d706d (Pi c2153ae4, evidence/reviews/TASK-SKRIPT-39-08-04/closeout-review.md). Focused selection incl. real PostgreSQL index and migration tests rerun at main 44cd0c6b: 15 passed, no skips (retained 01a14b79-b714-7f76-bcba-845884716cae evidence/39-08-04-focused.log). No frontend tests and no staging walk by contract (G2/G4).'
task_kind: story
acceptance_criteria:
  - An exam-owned index keeps one row per exam current through save, conversion publish and rename; the saved-exam list endpoint returns the exams either grouped by course (registered courses first, newest saved first within a course, exams without a course last under Utan kurs) or as one flat list newest first, following the teacher's sort preference saved in the backend so it survives another browser; the grouped list and its sort control live in ST-SKRIPT-40-04's Öppna drawer
story: ST-SKRIPT-39-08
backlog_document_profile: contract-derived
---

## Implementation Contract

The exam workspace's `Filer` mode lists saved exams as a flat Mina filer list
read from vault rows, which carry no course or title. After
TASK-SKRIPT-39-08-01 the course and title live in the versioned document
header, which the list cannot read per request.

This task delivers:

- An exam-owned index: one row per lineage with owner, lineage id, course key
  (nullable), title, saved time and head vault file id, in a new table with an
  Alembic migration whose data step seeds a row for every existing head vault
  record from the vault rows alone (course empty, title from the file stem).
  The document save, the conversion publish and the rename keep the row
  current inside their existing Unit of Work; deleting the lineage removes it.
- The saved-exam list endpoint reads the index joined to the head vault row
  and returns course key, title, saved time, file name and version per exam.
  No course or title column on `user_vault_files`; no container parsing per
  request.
- Grouped order: the teacher's registered courses in profile order, then
  other courses by official name, then `Utan kurs`. Within a group the newest
  saved exam first. Each group carries the course key and official course
  name.
- Two orderings: grouped as above, or one flat list of all exams newest first.
  The chosen ordering is saved through the profile preference handler as the
  teacher's default (a column on `user_profiles` next to the exam-course
  preference from TASK-SKRIPT-39-08-02) and is read with the profile, so it
  persists across browsers. The list endpoint returns the exams in that
  ordering.
- The save, publish and rename responses carry what the list needs to update
  in place.

Out of scope: tag filters, search, archiving, any class label, and every
control inside the exam workspace. Drawers win: there are no `Prov` and
`Redigera` modes. The grouped list, its group headers and entries, the sort
control and the in-place update after a save, publish or rename live in
ST-SKRIPT-40-04's `Öppna` drawer (user 2026-10-17, G2/G4).

## Contract Inputs

- Modes and list: `frontend/apps/skriptoteket/src/views/apps/ExamWorkspaceView.vue`
  (`UiSegmentedToggle` modes), `exam-workspace/ExamWorkspaceFilesMode.vue`,
  `useExamWorkspaceDocument.ts` (`ExamWorkspaceDocumentSummary`, saved list).
- Writers that must maintain the index:
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`
  (save), `exam_workspace_conversion_progress.py` (`_publish`),
  `src/skriptoteket/application/scripting/handlers/rename_vault_file.py`
  (TASK-SKRIPT-39-08-01 unit U2), and the vault document store they call.
- Profile course order from TASK-SKRIPT-39-08-02; official names from the
  catalog.
- Coordination point, save model (user 2026-10-17, G15): TASK-SKRIPT-39-04-08
  (proposed) moves the workspace to one file per exam, where `Spara`
  overwrites the current file and `Spara som` creates a new exam with its own
  file, with no Spara version history. The index's one row per lineage, head
  vault file id and version field are checked against that model with
  whichever of the two tasks lands second.
- Retained plan: session `01a145b6-c404-761f-aeef-39de058ba7ca`,
  `evidence/planning/TASK-SKRIPT-39-08-04/plan.md`.

## Core Vertical And Performance

A teacher with Svenska 2 and Svenska 1 registered has three saved exams in
those courses and one without a course. The list endpoint returns Svenska 1
first (if registered first), then Svenska 2 with its newest exam on top, then
`Utan kurs`. Saving an exam moves it to the top of its group; setting its
course moves it to the new group; renaming updates its file name. The list is
one query over the index and head rows.

## Validation

- Focused backend tests: index row written on first save and publish, updated
  on save (title, course, saved time, head id) and rename, removed on lineage
  delete; migration test for idempotent upgrade and the seed from head vault
  rows; list endpoint returns the joined fields.
- Focused backend tests: grouping and order (registered first in profile
  order, other courses by name, `Utan kurs` last, newest first within a
  group); the flat newest-first order; the list follows the saved sort
  default.
- Focused backend test: the sort-default preference handler stores and
  returns the value.
- No frontend tests and no staging walk: this task ships no UI (user
  2026-10-17, G2/G4).

## Stop Conditions

- Maintaining the index needs an edit in a file owned by TASK-SKRIPT-39-05-14
  before it lands: report to the user instead of editing it.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Drawers win: no Prov and Redigera modes; this task ships the exam index backend with exams grouped by course, registered courses first, newest first within a course and Utan kurs last; the grouped list and the import drop zone live in ST-SKRIPT-40-04's Öppna drawer (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                        |
| R3  | In the grouped order, unregistered courses sit between Mina kurser and Utan kurs ordered by official name; the index migration seeds a row for every existing head vault record from vault rows alone with the file stem as title until the next save (user 2026-10-16).                                                                                                                                                                                            |
| R4  | Two orderings, grouped by course with newest first within a group and a flat list newest first; the chosen ordering is saved in the backend as the teacher's default so it persists across browsers; the sort control that switches it is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                               |
| R2  | An exam-owned index row per lineage (owner, lineage, course key, title, saved time, head file id) is maintained by the document save, the conversion publish and the rename; the list reads the index joined to the head vault row; no exam columns on user_vault_files and no document parsing per request; the row shape is checked against TASK-SKRIPT-39-04-08's one-file-per-exam save model (user 2026-10-16; coordination point added user 2026-10-17, G15). |
