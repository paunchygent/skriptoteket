---
type: task
id: TASK-SKRIPT-39-08-01
title: Course picker at import and exam metadata drawer for course, title and file
  name
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-16'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A teacher can pick an official Skolverket course (gymnasiet) or subject and year
  band (grundskolan) by typing in a dropdown in the exam workspace import panel, or
  get it preselected from a uniquely matching course hint; change the course, the
  exam title and the Mina filer name afterwards in a document metadata drawer; and
  the chosen course's official name and the title appear in the QTI, PDF and DOCX
  exports, with a rename applied to every saved version of the exam
story: ST-SKRIPT-39-08
backlog_document_profile: contract-derived
---

## Implementation Contract

Skriptoteket has no course or subject list. The editor shows the exam title
read-only (`ExamWorkspaceView.vue:298`), and the Mina filer name of a saved exam
cannot be changed. TASK-SKRIPT-39-05-14 adds header data to the native exam
document holding the raw course line as a course hint. This task gives the
teacher an official course and editable title and file name, guided by the
story's principle: the right course with the fewest clicks, and a preselection
only when it is very likely correct.

This task delivers:

- A course list committed to the repository as a snapshot, produced by a
  generator script from the Skolverket Syllabus API
  (`https://api.skolverket.se/syllabus`, `/v1/courses` and `/v1/subjects`). It
  holds currently valid gymnasiet courses from GY11 and GY25, each with course
  code, name, points, reform and subject code and name, and one entry per
  grundskolan subject and year band with subject code, subject name and band.
  A GY25 entry is named subject plus level ("Engelska nivå 1") because
  Skolverket lists the level alone ("Nivå 1"). The year bands of a grundskolan
  subject are the bands its own syllabus defines (for most subjects åk 1–3,
  4–6 and 7–9). No komvux, anpassade skolformer or expired courses.
  The app makes no runtime call to Skolverket; rerunning the script refreshes
  the snapshot.
- A dropdown in the import panel (`ExamWorkspaceFilesMode.vue`) that doubles as
  a search field: typing matches course name and code, and each entry shows
  name, code and school form (for example "Matematik, åk 7–9"). Picking a
  course is optional and travels with the conversion request.
- Preselection: a course picked at import wins. Otherwise a course hint that
  matches exactly one list entry preselects it: after normalizing case,
  whitespace and dashes, the hint equals one entry's name or code, or contains
  exactly one maximal whole-token entry name or code. With no match or several
  matches the field stays empty and the hint text is shown beside it.
- The chosen course stored in the native document's header data next to the
  course hint, so it is versioned with the document; a course or title change
  is an ordinary document save.
- A document metadata drawer opened from the exam title in the editor, built
  like `ExamWorkspaceItemDrawer.vue`. It edits the course (same dropdown), the
  exam title and the Mina filer name, and shows a gymnasiet course's subject
  read-only. Course and title edits are ordinary document edits saved by the
  toolbar Spara; the rename is a separate immediate drawer action.
- Exports: the chosen course's official name replaces the raw hint in the QTI
  manifest metadata and in the PDF and DOCX headers; the hint is used only when
  no course is chosen. The edited title is the QTI test title and the PDF and
  DOCX header title.
- Mina filer rename backend following TASK-SKRIPT-37-05-04's rules: only the
  record name changes, never bytes, source references or content type; the
  teacher edits the stem and exactly one safe extension is kept; a name already
  used by another record of the same owner is rejected with a named validation
  error; a record that is not the owner's, deleted or missing is rejected as
  not found. A rename from the drawer renames every saved version in the exam's
  lineage, and the collision check ignores that lineage's own records.

Out of scope: own courses in the profile (T2), tags and import suggestion of
course and tags (T3), saved-exam sorting (T4), any class label, a rename
control on the Mina filer page (TASK-SKRIPT-37-05-04), and the GY11 phase-out
after school year 2026/27.

## Contract Inputs

- Depends on TASK-SKRIPT-39-05-14 (header data and course hint in
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`)
  for the units that store or read header data; those start after it lands on
  main and main is merged into the task worktree.
- Import and conversion: `ExamWorkspaceFilesMode.vue`,
  `useExamWorkspaceConversion.ts` and `useExamWorkspaceSourceFile.ts` under
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`;
  `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- Editor and drawer pattern: `ExamWorkspaceView.vue` and
  `ExamWorkspaceItemDrawer.vue` in the same frontend folder.
- Save path: `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`
  (stores `document.title` as sent) and the conversion merges
  `exam_workspace_conversion_merge.py` and `examWorkspaceConversionMerge.ts`
  (keep a teacher-edited title).
- Mina filer records: `src/skriptoteket/domain/scripting/vault.py`,
  `src/skriptoteket/infrastructure/repositories/user_vault_file_repository.py`,
  `src/skriptoteket/web/api/v1/vault.py`; exam versions share
  `document_lineage_id` and the saved-exam list shows the head record's name.
- Rename rules: `docs/backlog/tasks/task-skript-37-05-04-*.md` acceptance
  criteria.
- Exports: `examnet_qti_export.py` and `examnet_pdf_export.py` under
  `src/skriptoteket/domain/curated_apps/exam_workspace/`;
  `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_manifest.py`;
  `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_writer.py`.
- Skolverket Syllabus API OpenAPI spec:
  `https://api.skolverket.se/syllabus/v3/api-docs`.

## Core Vertical And Performance

The teacher opens the import panel, types part of a course name, picks the
course and drops a DOCX; the conversion request carries the course; the built
native document holds it in header data; the editor shows the course and title
in the metadata drawer; the teacher changes the title and the Mina filer name;
the save stores a new revision and the rename updates every version record;
QTI, PDF and DOCX exports carry the official course name and the new title.
The course list is loaded once per page and searched in the browser; a search
keystroke makes no server request.

## Validation

- Focused backend tests: the generator's mapping from recorded Skolverket
  responses to snapshot entries, hint matching (unique match, several matches,
  no match), the document header course field, the rename rules (stem edit,
  extension kept, collision across lineages rejected, own lineage ignored,
  foreign or deleted record rejected, all versions renamed), and the QTI, PDF
  and DOCX exports for course name and title.
- Focused frontend tests: dropdown search by name and code, preselection
  display with the hint beside an empty field, and the metadata drawer saving
  course, title and name.
- Hemma staging walk in a browser: pick a course at import, convert Svenska 2
  kursavslutande, change the title and the Mina filer name in the drawer,
  check Mina filer shows the new name on every version, export QTI and import
  it into Exam.net with the new title.

## Stop Conditions

- The Skolverket API no longer returns the course or subject fields the
  generator needs: report to the user before choosing another source.
- TASK-SKRIPT-39-05-14 has not landed on main: do not start a unit that stores
  or reads header data (the chosen course in the header, hint preselection,
  export header text).

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D4  | The course list holds currently valid gymnasiet courses from GY11 and GY25 plus grundskolan subject-and-year-band entries; no komvux, anpassade skolformer or expired courses (user 2026-10-16). |
| D5  | When a course is chosen, its official name replaces the raw hint in QTI manifest metadata and in the PDF and DOCX headers; the raw hint is used only when no course is chosen (user 2026-10-16). |
| D6  | Picking a course at import is optional and wins; otherwise a hint matching exactly one entry preselects it; with no match the field stays empty and the hint is shown beside it; the teacher can change the value at any time (user 2026-10-16). |
| D7  | This task builds the Mina filer rename backend following TASK-SKRIPT-37-05-04's decided rules and the metadata drawer uses it; a rename control on the Mina filer page stays with TASK-SKRIPT-37-05-04 (user 2026-10-16). |
| D8  | The metadata panel is a document metadata drawer opened from the exam title, matching the item drawer from TASK-SKRIPT-39-04-02 (user 2026-10-16). |
| D9  | A rename applies to every saved version in the exam's lineage; the collision check ignores the exam's own versions (user 2026-10-16). |
| D15 | The course list is a committed snapshot produced by a generator script from the Skolverket Syllabus API; the app makes no runtime call to Skolverket. |
| D16 | The chosen course is stored in the native document's header data next to the course hint and saved through the existing document save. |
| D17 | The dropdown searches course name and code and shows name, code and school form; a gymnasiet course's subject is shown read-only in the drawer. |
| D18 | Header-independent units (course list, dropdown, rename, drawer shell, course pick at import) start now; units that store or read NativeExamHeader start after TASK-SKRIPT-39-05-14 lands on main and main is merged into the task worktree (user 2026-10-16). |
| D20 | A grundskolan choice is one entry per subject and year band; the exam is bound to that band (user 2026-10-16). |
| D22 | A preselection is made only when it is very likely correct; otherwise the field stays empty (user 2026-10-16). |
| D23 | A GY25 entry is named subject plus level ("Engelska nivå 1"), searchable by composed name and code, with the reform in the meta line (user 2026-10-16). |
| D24 | A grundskolan subject gets the year bands its own syllabus defines, labelled as Skolverket does (user 2026-10-16). |
| D25 | A hint preselects when, after normalizing case, whitespace and dashes, it equals exactly one entry's name or code, or contains exactly one maximal whole-token entry name or code; several or none leave the field empty with the hint shown (user 2026-10-16). |
| D26 | Title and course edits are ordinary document edits saved by the toolbar Spara; the Mina filer rename is a separate immediate drawer action applied to every saved version (user 2026-10-16). |
