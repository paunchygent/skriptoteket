---
type: task
id: TASK-SKRIPT-39-08-02
title: Own courses in the profile and the course dropdown default
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
  - A teacher registers school forms and courses (gymnasiet courses, grundskolan subject-and-band entries) in a Mina kurser section on the profile page, and the exam workspace course API returns the registered courses first so the existing course dropdown in the import panel and the metadata drawer offers them first without new controls; Lägg till i mina kurser and the Mina kurser/Alla kurser dropdown groups are built by ST-SKRIPT-40-04
story: ST-SKRIPT-39-08
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-39-08-01 gives the exam workspace a committed course catalog and a
searchable course dropdown that treats all 2269 entries alike. A teacher who
teaches two courses should not search through the catalog every time. This
task records the teacher's own courses and makes them the dropdown default.

This task delivers:

- A `Mina kurser` section on the `/profile` page. It records the school forms
  taught (gymnasiet, grundskolan) and an ordered list of catalog entries:
  gymnasiet courses and grundskolan subject-and-band entries, the same entries
  the dropdown offers. The teacher adds an entry with the existing course
  dropdown and removes an entry from the list. The section shows each entry as
  the dropdown does (name, code, school form).
- Storage as one JSONB column on `user_profiles` holding the school forms and
  the ordered catalog keys; the catalog key is the only identity and no names
  are copied. A dedicated `PATCH /api/v1/profile/exam-courses` handler
  validates every key against the committed catalog and rejects an unknown key
  with a named field error. The profile read returns the stored value.
- Course API ranking: `GET .../exam-workspace/courses` returns the teacher's
  registered courses first, in profile order, then the rest of the catalog, so
  the existing course dropdown in the import panel and the metadata drawer
  offers them first. A typed query searches the whole catalog with the
  existing search rule and ranks registered matches first. One search rule;
  no second matcher. No new control inside the exam workspace (user
  2026-10-17, G2/G4).
- Dropdown sort: this task changes the sort in `searchCourses`
  (`useExamCourseCatalog.ts`) of the frozen workspace course dropdown so
  registered courses show first. It adds no new control (user 2026-10-17,
  G30).

Out of scope: tags (TASK-SKRIPT-39-08-03), the saved-exam list
(TASK-SKRIPT-39-08-04), any class label, school-level or colleague-shared
course lists, and every new control inside the exam workspace. ST-SKRIPT-40-04
builds the `Mina kurser` and `Alla kurser` dropdown groups, with `Alla kurser`
limited to the recorded school forms, and the `Lägg till i mina kurser`
action (user 2026-10-17, G2/G4).

## Contract Inputs

- Course catalog and dropdown from TASK-SKRIPT-39-08-01:
  `src/skriptoteket/domain/curated_apps/exam_workspace/exam_course_catalog.py`
  (`ExamCourse`, `load_exam_course_catalog`),
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/ExamCourseCombobox.vue`
  and `useExamCourseCatalog.ts` (`searchCourses` ranking).
- Per-user preference pattern: `user_profiles` model, the
  `update_classroom_planner_settings` handler and its
  `PATCH /api/v1/profile/classroom-planner-settings` route, and the profile
  view under `frontend/apps/skriptoteket/src/views/`.
- User decision G30 (2026-10-17), retained in session
  `01a1495e-8398-75be-b2da-f0b08ba11afa`,
  `evidence/planning/decisions-2026-10-17.md`.
- Story terms D21 (amended by this task: grundskolan entries are subject and
  band, not years) and D22.
- Retained plan: session `01a145b6-c404-761f-aeef-39de058ba7ca`,
  `evidence/planning/TASK-SKRIPT-39-08-02/plan.md`.

## Core Vertical And Performance

The teacher opens the profile, registers gymnasiet and the courses Svenska 1
and Svenska 2, opens the exam workspace, and the import dropdown shows those
two first before typing. The dropdown still searches the whole catalog in the
browser; the profile value is loaded once with the catalog and no keystroke
makes a server request.

## Validation

- Focused backend tests: the PATCH handler keeps order, rejects an unknown key
  with the named field error, accepts an empty list, and the profile read
  returns the stored value.
- Focused backend test: the course API returns the registered courses first
  in profile order, then the rest of the catalog.
- Focused frontend tests: profile section add and remove; the dropdown lists
  the registered courses first before typing and ranks a registered match
  first when typing.
- Focused frontend test in `useExamCourseCatalog.spec.ts`: the `searchCourses`
  sort puts registered courses first, before typing and for a typed query.
- Hemma staging walk in a browser on the profile page, the only UI this task
  ships besides the dropdown sort change: register two courses, reload and
  see both in the profile (user 2026-10-17, G2/G4, G30).

## Stop Conditions

- The catalog key shape or `ExamCourse` fields change under
  TASK-SKRIPT-39-08-01 review: report to the user before storing keys.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                               |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | Registration lives in a Mina kurser section on /profile and ships with its UI now; the "Lägg till i mina kurser" action on a picked course in the exam workspace is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                     |
| P2  | The profile records grundskolan subject-and-band entries, the same entries as the dropdown, not years only; amends story D21 (user 2026-10-16).                                                                                                                                                                                                     |
| P3  | The registered courses are one ordered JSONB list of catalog keys with the school forms in a column on user_profiles, read and written through a dedicated PATCH profile handler; the catalog key is the only identity (user 2026-10-16).                                                                                                           |
| P5  | The Alla kurser group is limited to the recorded school forms when at least one is recorded; a typed query still searches the whole catalog; the group is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                               |
| P4  | The course API returns the registered courses first so the existing dropdown offers them first before typing; a typed query searches the whole catalog with the same search rule and ranks registered matches first; the Mina kurser and Alla kurser group headings are built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4). |
| P6  | This task may change the sort of the frozen workspace course dropdown (`searchCourses` in `useExamCourseCatalog.ts`) so registered courses show first; it adds no new control (user 2026-10-17, G30).                                                                                                                                               |
