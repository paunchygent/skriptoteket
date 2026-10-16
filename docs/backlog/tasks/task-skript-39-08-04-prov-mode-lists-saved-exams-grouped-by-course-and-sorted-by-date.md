---
type: task
id: TASK-SKRIPT-39-08-04
title: Prov mode lists saved exams grouped by course and sorted by date
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-16'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The exam workspace's first mode is Prov with the import drop zone at the top and the saved
  exams below, either grouped by course (registered courses first, newest saved first within a
  course, exams without a course last) or as one flat list newest first; the teacher switches
  the ordering with a sort control whose choice is saved in the backend as the default and
  survives another browser; a save, a conversion publish and a rename update the group and
  position without a reload
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
- `Prov` mode replaces `Filer`: the import drop zone with its course dropdown
  at the top, then the exams grouped by course. Group order: the teacher's
  registered courses in profile order, then other courses by official name,
  then `Utan kurs`. Within a group the newest saved exam first. A group header
  shows the official course name; an entry shows title, file name, version and
  saved time with the existing open and delete actions. Modes are `Prov` and
  `Redigera`.
- Two orderings: grouped as above, or one flat list of all exams newest first.
  A sort control in Prov mode switches between them; the chosen ordering is
  saved through the profile preference handler as the teacher's default (a
  column on `user_profiles` next to the exam-course preference from
  TASK-SKRIPT-39-08-02) and is read with the profile, so it persists across
  browsers.
- After a save, publish or rename the list updates in place from the response.

Out of scope: tag filters, search, archiving, and any class label.

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
- Retained plan: session `01a145b6-c404-761f-aeef-39de058ba7ca`,
  `evidence/planning/TASK-SKRIPT-39-08-04/plan.md`.

## Core Vertical And Performance

A teacher with Svenska 2 and Svenska 1 registered has three saved exams in
those courses and one without a course. Prov mode shows Svenska 1 first (if
registered first), then Svenska 2 with its newest exam on top, then
`Utan kurs`. Saving an exam moves it to the top of its group; setting its
course moves it to the new group; renaming updates its file name in place.
The list is one query over the index and head rows.

## Validation

- Focused backend tests: index row written on first save and publish, updated
  on save (title, course, saved time, head id) and rename, removed on lineage
  delete; migration test for idempotent upgrade and the seed from head vault
  rows; list endpoint returns the joined fields.
- Focused frontend tests: grouping and order (registered first in profile
  order, other courses by name, `Utan kurs` last, newest first within a
  group); the flat newest-first order; the sort control saves the default
  and the list follows it; in-place update after save, course change and
  rename.
- Focused backend test: the sort-default preference handler stores and
  returns the value.
- Hemma staging walk: save exams in two courses and one without, check the
  groups and order, set a course on the third and see it move, rename one and
  see the new name.

## Stop Conditions

- Maintaining the index needs an edit in a file owned by TASK-SKRIPT-39-05-14
  before it lands: report to the user instead of editing it.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| R1  | The Filer mode becomes Prov: exams grouped by course, registered courses first, newest first within a course, Utan kurs last, with the import drop zone at the top; the modes are Prov and Redigera (user 2026-10-16). |
| R3  | In the grouped order, unregistered courses sit between Mina kurser and Utan kurs ordered by official name; the index migration seeds a row for every existing head vault record from vault rows alone with the file stem as title until the next save (user 2026-10-16). |
| R4  | Two orderings, grouped by course with newest first within a group and a flat list newest first; a sort control switches and the chosen ordering is saved in the backend as the teacher's default so it persists across browsers (user 2026-10-16). |
| R2  | An exam-owned index row per lineage (owner, lineage, course key, title, saved time, head file id) is maintained by the document save, the conversion publish and the rename; the list reads the index joined to the head vault row; no exam columns on user_vault_files and no document parsing per request (user 2026-10-16). |
