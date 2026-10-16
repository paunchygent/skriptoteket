---
type: story
id: ST-SKRIPT-39-08
title: Course and tag metadata for saved exams
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-13'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- A teacher can give each saved exam an official Skolverket course (gymnasiet) or
  subject and year band (grundskolan) and tags from its central content, register
  where they teach and their courses in the profile so the dropdown offers those
  first, have the import suggest course and tags, and sort saved exams by course
  and date in the exam app's saved-exam tab
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Teachers save exams in the exam workspace with no course, no tags and a title
and Mina filer name they cannot change. This story gives every saved exam an
official course and correct tags with the least possible teacher effort. The
guiding principle for every task: the teacher finds the intended course and
tags with the fewest clicks, a preselection or suggestion is wrong as seldom as
possible, and the teacher does not dig through entries they do not need.

- Course list: Skolverket's currently valid gymnasiet courses (GY11 and GY25)
  and grundskolan subjects, one entry per subject and year band (åk 1–3, 4–6,
  7–9). Year bands are never grouped together, because their content and
  teaching differ. For gymnasiet the subject follows from the course.
- Course choice: a dropdown that doubles as a search field, in the import panel
  and in a document metadata drawer opened from the exam title. The drawer also
  edits the exam title used in the QTI data and the Mina filer name; a rename
  applies to every saved version of the exam.
- Profile: the teacher registers their school form(s), the grundskolan years
  they teach and their gymnasiet courses. An opened dropdown lists the matching
  entries, which are the default; typing searches the full list.
- Tags: the central content points of the exam's course or of its grundskolan
  subject and year band, picked in a searchable multi-select.
- Suggestions: the import preselects course and tags when they are very likely
  correct; the teacher can change or clear them.
- Saved exams: the exam workspace's saved-exam list becomes the exam tab,
  sorted by course and date. The tab prepares later exam sharing among
  colleagues.
- The exam document stays a durable, shareable format: it carries course and
  tags but no class or other teacher-situational data.

Out of scope: exam sharing among colleagues; a class label (a possible later
optional label linked to classroom planner classes, kept outside the exam
document); the GY11 phase-out after school
year 2026/27, when a later task drops GY11 from the list and moves saved
exams' GY11 courses to their GY25 equivalents; the rename control on the Mina
filer page (TASK-SKRIPT-37-05-04).

## Contract Inputs

- User decisions 2026-10-16 (TASK-SKRIPT-39-05-14 planning): the teacher
  selects a course (gymnasiet) or a subject (grundskolan); for gymnasiet the
  subject follows from the course. Valid courses and subjects come from
  Skolverket's registers. The choice is a simple dropdown that doubles as a
  search field in the import panel, and it can be changed after conversion in
  a metadata panel together with the Mina filer file name and the exam title
  used in the QTI data. This story's first task builds that dropdown, the
  course list and the metadata panel; TASK-SKRIPT-39-05-14 leaves a raw course
  hint from the source document for the dropdown to preselect from. Mina filer
  renaming follows ST-SKRIPT-37-05.
- User decisions 2026-10-16 (ST-SKRIPT-39-08 planning, retained session
  `01a1451f-5c45-71ed-b425-1cda7bf79a02`): D1-D22 below.
- Skolverket Syllabus API (`https://api.skolverket.se/syllabus`): keyless GET
  of courses and subjects; central content is HTML lists without item IDs.
- Mina filer rename rules: TASK-SKRIPT-37-05-04.

## Tasks

1. TASK-SKRIPT-39-08-01: course list, import dropdown and document metadata
   drawer for course, exam title and Mina filer name (ready).
2. Own courses: profile registration of school form, years taught and courses;
   the dropdown default and ordering (to be planned).
3. Tags from central content and import suggestion of course and tags (to be
   planned).
4. Saved-exam tab sorted by course and date (to be planned).

## Verification

Each task closes with a Hemma staging walk in a browser through the teacher's
path it changes. The story closes when a teacher can import an exam with a
preselected course and tags, adjust them in the drawer, find the exam in the
saved-exam tab sorted by course and date, and export it with the
official course name.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Four tasks: course list, import dropdown and metadata drawer; own courses in the profile; tags with import suggestion; saved-exam tab sorted by course and date (user 2026-10-16). |
| D2  | Tags come from Skolverket central content for the exam's course or grundskolan subject and year band, picked in a searchable multi-select (user 2026-10-16). |
| D3  | No class in this story: the exam document is durable and shareable and carries no class; sorting happens by course and date in an exam-focused tab in the exam app listing only exam files from Mina filer; an optional class label linked to classroom planner classes, outside the exam document, and sharing among colleagues are later work (user 2026-10-16). |
| D4  | The course list holds currently valid GY11 and GY25 gymnasiet courses and grundskolan subject-and-year-band entries; no komvux, anpassade skolformer or expired courses (user 2026-10-16). |
| D5  | A chosen course's official name replaces the raw hint in QTI manifest metadata and the PDF and DOCX headers (user 2026-10-16). |
| D6  | An import choice wins; otherwise a uniquely matching hint preselects; otherwise the field stays empty with the hint shown (user 2026-10-16). |
| D7  | The first task builds the Mina filer rename backend under TASK-SKRIPT-37-05-04's rules; the Mina filer page control stays with TASK-SKRIPT-37-05-04 (user 2026-10-16). |
| D8  | The metadata panel is a drawer opened from the exam title (user 2026-10-16). |
| D9  | A rename applies to every saved version of the exam (user 2026-10-16). |
| D10 | The GY11 phase-out after school year 2026/27 is a later task outside this story (user 2026-10-16). |
| D11 | The existing saved-exam list becomes the exam tab sorted by course and date (user 2026-10-16). |
| D12 | An opened dropdown lists the teacher's profile entries; every other entry is reached by typing (user 2026-10-16). |
| D13 | Suggested course and tags arrive preselected and the teacher can change or clear them (user 2026-10-16). |
| D14 | Grundskolan year bands are never grouped; each exam belongs to one band and its tags come only from that band (user 2026-10-16). |
| D20 | A grundskolan choice is one entry per subject and year band (user 2026-10-16). |
| D21 | The profile records school form(s), grundskolan years taught (åk 1–9) and gymnasiet courses; matching entries are the dropdown default (user 2026-10-16). |
| D22 | Minimum clicks and frustration; a preselection or suggestion is made only when very likely correct; teachers do not dig through entries they do not need (user 2026-10-16). |
