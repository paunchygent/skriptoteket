---
type: task
id: TASK-SKRIPT-39-09-05
title: 'Kort svar: Ny fråga creates a one-gap Lucktext after the question text'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A teacher picks Kort svar from Ny fråga, gets a Lucktext with one gap after the
  question text, keys accepted answers, and Exam.net imports
  it as a one-gap Lucktext
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-09 task 5 (story term Q14): the "Ny fråga" control
offers a short answer, Kort svar, that creates a Lucktext with one gap after
the question text.

- **New item.** "Ny fråga" offers Fritext and Kort svar. Kort svar creates a
  `gap_fill` item whose body is the question-text paragraph followed by a
  paragraph holding one gap, with no accepted values and no points, in review
  state like other teacher-created items.
- **Keying.** The gap is keyed through the existing gap popover with accepted
  answers; no new key path is added. Automatic misspellings for
  teacher-keyed gaps are delivered by task 6 (R17).
- **Export.** The item exports through the task 2 Lucktext route; Exam.net
  imports it as a one-gap Lucktext (V99–V104).
- **Out of scope.** A distinct simpleAnswer export (no construction produces
  one); other kinds in "Ny fråga".

## Contract Inputs

- ST-SKRIPT-39-09 term Q14.
- Frontend: `ExamWorkspaceQuestionList.vue:44-51`,
  `ExamWorkspaceView.vue:233-234,452-455`,
  `useExamWorkspaceDocument.ts:437-446` (`addItem`),
  `examWorkspaceItemEdits.ts:331-357` (`newTeacherItem`),
  `ExamWorkspaceGapPopover.vue`.

## Core Vertical And Performance

A teacher picks Kort svar, writes the question, keys "Stockholm", saves and exports; Exam.net imports a one-gap
Lucktext with the accepted answers keyed. No performance concern.

## Validation

- Focused Vitest for the new-item builder and the add control.
- Frontend typecheck and build.
- Staging walk: the item is created, keyed, exported and imported into
  Exam.net in the agent's own tab and read back.

## Stop Conditions

- Exam.net imports the exported one-gap item as anything other than a
  Lucktext with its accepted answers keyed.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | "Ny fråga" offers Kort svar, which creates a Lucktext with one gap after the question text (Q14). |
| T2  | Kort svar is keyed through the existing gap popover with accepted answers; its automatic misspellings come from task 6 (Q14, R17). |
