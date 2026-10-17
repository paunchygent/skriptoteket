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
  - A teacher can give each saved exam an official Skolverket course (gymnasiet) or subject and year band (grundskolan), register where they teach and their courses in the profile so the course list offers those first, and have the import suggest course and central-content tags; the backend stores tags and serves saved exams ordered by course and date, and the tags checklist, the Lägg till i mina kurser action and the course-grouped exam list are built in the exam workspace by ST-SKRIPT-40-04
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
- Saved exams: the saved exams are listed by course and date. The list
  prepares later exam sharing among colleagues.
- UI split (user 2026-10-17, G2/G4): the tasks in this story ship backend,
  data, API and export, plus small UI on pages outside the exam workspace (the
  profile page). Every new control inside the exam workspace (the tags
  multi-select, `Föreslå innehåll`, `Lägg till i mina kurser`, the
  `Mina kurser`/`Alla kurser` dropdown groups and the course-grouped exam list
  in the `Öppna` drawer) is built by ST-SKRIPT-40-04's redesign. The current
  workspace screens are frozen except for bug fixes.
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
   drawer for course, exam title and Mina filer name (done 2026-10-16, main
   `255eef88`, staging walk passed, user closure gate).
2. TASK-SKRIPT-39-08-02: own courses in a `Mina kurser` section on the
   profile page, with its UI, and a course API that returns the registered
   courses first; `Lägg till i mina kurser` in the workspace moves to
   ST-SKRIPT-40-04 (done 2026-10-17, approved review closeout).
3. TASK-SKRIPT-39-08-03: central-content snapshot, content route, Decisions
   classifier at import and the tag-suggestion enrichment job; no model course
   suggestion; the tags checklist and `Föreslå innehåll` in the metadata drawer
   move to ST-SKRIPT-40-04 (done 2026-10-17, approved review closeout).
4. TASK-SKRIPT-39-08-04: exam index backend with one row per exam, the order by
   course and date, the `Utan kurs` group and the saved sort preference; the
   grouped list lives in ST-SKRIPT-40-04's `Öppna` drawer (done 2026-10-17,
   approved review closeout).
5. TASK-SKRIPT-39-08-05: the `Mina kurser` section adds a chosen course at
   once and saves each change at once, with no `+` button, no Spara button and
   no success toast (done 2026-10-17, approved review plus unit tests).

## Verification

Each task closes with focused tests; TASK-SKRIPT-39-08-02 also closes with a
Hemma staging walk in a browser through the profile page, the only UI this
story ships (user 2026-10-17, G2/G4). The story closes when a teacher can
import an exam with a preselected course and stored suggested tags, register
courses in the profile, get saved exams from the API ordered by course and
date, and export an exam with the official course name. The teacher path
through the tags checklist and the course-grouped list is walked under
ST-SKRIPT-40-04.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Four tasks: course list, import dropdown and metadata drawer; own courses in the profile; tags with import suggestion; exam index ordered by course and date (user 2026-10-16; amended user 2026-10-17, G2/G4: the last three ship backend, data and API, plus the profile page UI, and their workspace controls move to ST-SKRIPT-40-04).                                                      |
| D2  | Tags come from Skolverket central content for the exam's course or grundskolan subject and year band, picked in a searchable multi-select (user 2026-10-16).                                                                                                                                                                                                                                    |
| D3  | No class in this story: the exam document is durable and shareable and carries no class; sorting happens by course and date in a list of exam files only, which lives in ST-SKRIPT-40-04's Öppna drawer; an optional class label linked to classroom planner classes, outside the exam document, and sharing among colleagues are later work (user 2026-10-16; amended user 2026-10-17, G2/G4). |
| D4  | The course list holds currently valid GY11 and GY25 gymnasiet courses and grundskolan subject-and-year-band entries; no komvux, anpassade skolformer or expired courses (user 2026-10-16).                                                                                                                                                                                                      |
| D5  | A chosen course's official name replaces the raw hint in QTI manifest metadata and the PDF and DOCX headers (user 2026-10-16).                                                                                                                                                                                                                                                                  |
| D6  | An import choice wins; otherwise a uniquely matching hint preselects; otherwise the field stays empty with the hint shown (user 2026-10-16).                                                                                                                                                                                                                                                    |
| D7  | The first task builds the Mina filer rename backend under TASK-SKRIPT-37-05-04's rules; the Mina filer page control stays with TASK-SKRIPT-37-05-04 (user 2026-10-16).                                                                                                                                                                                                                          |
| D8  | The metadata panel is a drawer opened from the exam title (user 2026-10-16).                                                                                                                                                                                                                                                                                                                    |
| D9  | A rename applies to every saved version of the exam (user 2026-10-16).                                                                                                                                                                                                                                                                                                                          |
| D10 | The GY11 phase-out after school year 2026/27 is a later task outside this story (user 2026-10-16).                                                                                                                                                                                                                                                                                              |
| D11 | Saved exams are ordered by course and date; this story ships the exam index backend and the ordering, and the course-grouped list lives in ST-SKRIPT-40-04's Öppna drawer instead of an exam tab (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                             |
| D12 | An opened dropdown lists the teacher's profile entries; every other entry is reached by typing; this story ships the course API ordering and ST-SKRIPT-40-04 builds the dropdown groups (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                                      |
| D13 | Suggested course and tags arrive preselected and the teacher can change or clear them; the tags checklist that shows and edits them is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                                                              |
| D14 | Grundskolan year bands are never grouped; each exam belongs to one band and its tags come only from that band (user 2026-10-16).                                                                                                                                                                                                                                                                |
| D20 | A grundskolan choice is one entry per subject and year band (user 2026-10-16).                                                                                                                                                                                                                                                                                                                  |
| D21 | The profile records school form(s), grundskolan subject-and-band entries and gymnasiet courses; matching entries are the dropdown default (user 2026-10-16; amended 2026-10-16 by TASK-SKRIPT-39-08-02 P2 from years to subject-and-band entries).                                                                                                                                              |
| D22 | Minimum clicks and frustration; a preselection or suggestion is made only when very likely correct; teachers do not dig through entries they do not need (user 2026-10-16).                                                                                                                                                                                                                     |
