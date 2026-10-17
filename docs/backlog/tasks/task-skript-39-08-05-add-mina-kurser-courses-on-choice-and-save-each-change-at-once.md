---
type: task
id: TASK-SKRIPT-39-08-05
title: Add Mina kurser courses on choice and save each change at once
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-17'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer cf9ad92d reviewed c1992027 (retained session 01a149c9-5bc7-7713-ba64-12dee0470bdd, evidence/reviews/task-skript-39-08-05-c1992027.md): changes_requested with one medium finding F1 (a profile reload that started before a course save replaced the saved list). F1 was repaired in ab5e7e10 and, as a medium finding, admitted by the parent on focused checks without rereview: profile Vitest 18 passed including the late-reload test (which fails against the old guard), frontend typecheck and ESLint clean. No staging walk, by the user rule that repairs close on approved review plus unit tests. The parent session authorized closure.'
task_kind: story
acceptance_criteria:
  - Choosing a course in the Mina kurser search box adds it to the list at once and clears the box; choosing a course that is already listed changes nothing
  - Adding a course, removing a course or toggling a school form saves at once; a quiet inline Sparat status confirms the save, with no Spara button and no success toast
  - A failed save shows the failure toast and restores the last saved list and school forms; a second change waits for the first save to finish
story: ST-SKRIPT-39-08
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-39-08-02 built the `Mina kurser` section on `/profile`. On staging
(2026-10-17) choosing a course in the search box only staged it; a separate
bare `+` button put it on the list. A teacher who chose a course and pressed
Spara saved the old list, and the toast `Kurserna uppdaterades.` still
reported success. After Spara the search box also showed the text of an
already-listed course. The user called the `+` step "a very stupid thing".

This task changes `ProfileExamCourses.vue` so that every change is one step
and saves itself:

- Choosing a course in the search box appends it to the list and clears the
  box. The `+` button is removed. A course that is already listed is ignored.
- Adding, removing or toggling a school form calls
  `useProfile.updateExamCourses` with the full value at once. Saves run one at
  a time; a change made while a save runs waits for it and is then saved with
  the latest value.
- A quiet inline status in a fixed slot shows `Sparar` while a save runs and
  `Sparat` after it succeeds. The Spara button and the success toast are
  removed.
- A failed save shows `toast.failure` with the existing failure message and
  restores the list and school forms to the last saved value.

## Contract Inputs

- `frontend/apps/skriptoteket/src/components/profile/ProfileExamCourses.vue`
  and its spec.
- `ExamCourseCombobox.vue` is shared with the exam workspace (40-04-03) and
  keeps its behaviour; only the profile's use of it changes.
- `huleedu-ui-design`: toasts only for failures, the layout holds still,
  plain Swedish in sentence case.

## Core Vertical And Performance

One component on the profile page; the backend endpoint and payload are
unchanged.

## Validation

- `ProfileExamCourses.spec.ts`: choosing adds without a second step, a
  duplicate is ignored, a failed save restores the list and toasts, a success
  shows no toast, and saves are serialised.
- Focused Vitest, frontend typecheck and build.
- Independent review. The task closes on an approved review plus unit tests;
  no staging walk (user rule 2026-10-17: walks cover only exam-converter
  changes, relayed by the parent).

## Stop Conditions

- A change that needs `ExamCourseCombobox` to change its shared behaviour
  stops and goes back to the parent.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1 | Choosing a course in the search box adds it to the list at once and clears the box; the `+` button is removed; choosing an already-listed course changes nothing. Source: the user's rejection of the `+` step and the parent's recommendation, 2026-10-17. |
| D2 | Each add, remove and school-form toggle saves at once through `useProfile.updateExamCourses`; the Spara button and the success toast are removed; an inline `Sparat` status confirms the save. Source: parent recommendation, 2026-10-17. |
| D3 | A failed save keeps the failure toast with the existing message and restores the last saved list and school forms. Source: parent recommendation, 2026-10-17. |
| D4 | Saves are serialised: a change made during a save waits and is then saved with the latest value. Source: parent recommendation, 2026-10-17. |
| D5 | `ExamCourseCombobox` keeps its shared behaviour. Source: parent constraint, 2026-10-17. |

## Outcome

`ProfileExamCourses.vue` adds a chosen course at once and clears the search
box; the `+` button, the Spara button and the success toast are gone. Every
change saves at once through one serialised loop, with a `Sparar…`/`Sparat`
status in a fixed slot beside the search box. A failed save restores the last
acknowledged value and shows the failure toast. After its first change the
section keeps its acknowledged value, so a late profile reload cannot replace
it (review F1). The section no longer emits `profileUpdated`.
`ExamCourseCombobox` is unchanged.
