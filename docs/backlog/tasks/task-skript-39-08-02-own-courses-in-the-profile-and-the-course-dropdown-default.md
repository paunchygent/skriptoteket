---
type: task
id: TASK-SKRIPT-39-08-02
title: Own courses in the profile and the course dropdown default
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
- A teacher registers school forms and courses (gymnasiet courses, grundskolan subject-and-band
  entries) in a Mina kurser section on the profile page, adds a picked course to that list from
  the course dropdown without leaving the exam workspace, and the course dropdown in the import
  panel and the metadata drawer lists the registered courses first before typing and ranks them
  first when typing
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
- Dropdown default: before typing, the dropdown lists the registered courses
  under `Mina kurser`, then the rest of the catalog under `Alla kurser`, the
  latter limited to the recorded school forms when at least one is recorded.
  A typed query searches the whole catalog with the existing search rule and
  ranks registered matches first. One search rule; no second matcher.
- A `Lägg till i mina kurser` action on a picked course that is not yet
  registered, in the import panel and in the metadata drawer. It saves at once
  through the same PATCH handler and confirms with a toast.

Out of scope: tags (TASK-SKRIPT-39-08-03), the saved-exam list
(TASK-SKRIPT-39-08-04), any class label, and school-level or
colleague-shared course lists.

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
- Story terms D21 (amended by this task: grundskolan entries are subject and
  band, not years) and D22.
- Retained plan: session `01a145b6-c404-761f-aeef-39de058ba7ca`,
  `evidence/planning/TASK-SKRIPT-39-08-02/plan.md`.

## Core Vertical And Performance

The teacher opens the profile, registers gymnasiet and the courses Svenska 1
and Svenska 2, opens the exam workspace, and the import dropdown shows those
two first before typing. The teacher picks Svenska 3 for an exam and adds it
from the dropdown; the profile now lists three. The dropdown still searches the
whole catalog in the browser; the profile value is loaded once with the
catalog and no keystroke makes a server request.

## Validation

- Focused backend tests: the PATCH handler keeps order, rejects an unknown key
  with the named field error, accepts an empty list, and the profile read
  returns the stored value.
- Focused frontend tests: profile section add and remove; dropdown shows the
  registered group first before typing and ranks a registered match first when
  typing; `Lägg till i mina kurser` appears only for an unregistered picked
  course and calls the PATCH route.
- Hemma staging walk in a browser: register two courses on the profile, see
  them first in the import dropdown, add a third from the dropdown, reload and
  see all three in the profile.

## Stop Conditions

- The catalog key shape or `ExamCourse` fields change under
  TASK-SKRIPT-39-08-01 review: report to the user before storing keys.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| P1  | Registration lives in a Mina kurser section on /profile; the course dropdown also offers "Lägg till i mina kurser" on any picked course (user 2026-10-16). |
| P2  | The profile records grundskolan subject-and-band entries, the same entries as the dropdown, not years only; amends story D21 (user 2026-10-16). |
| P3  | The registered courses are one ordered JSONB list of catalog keys with the school forms in a column on user_profiles, read and written through a dedicated PATCH profile handler; the catalog key is the only identity (user 2026-10-16). |
| P5  | The Alla kurser group is limited to the recorded school forms when at least one is recorded; a typed query still searches the whole catalog (user 2026-10-16). |
| P4  | Before typing the dropdown lists the registered courses under Mina kurser, then the catalog under Alla kurser; a typed query searches the whole catalog with the same search rule and ranks registered matches first (user 2026-10-16). |
