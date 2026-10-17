---
type: task
id: TASK-SKRIPT-39-06-02
title: Exam.net probe of ordering and dropdown Lucktext in the student view and grading
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Screenshots of one ordering task and one dropdown Lucktext task imported into Exam.net, answered in the student preview and graded, are retained and the user records whether ordering is built
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

Exam.net imports a QTI ordering question as Matcha ihop: the right column holds
the position numbers 1..N and the task has one ALL_CORRECT rule (REF probes
V60-V65; imported once in exam 5310254 on 2026-10-10). Dropdown Lucktext
imported as a parent with children in the same exam, and the HuleEduOS round
11 table records `qti-inline-choice-interaction` as a keyed Lucktext gap with
a selectable list. Neither type's student view nor its grading has been
walked. The user decides from this probe whether ordering is built (story
P21). Dropdown Lucktext is not gated on the probe; TASK-SKRIPT-39-06-04 follows
it in order.

This task delivers:

- One QTI 3.0 package with one standalone ordering task and one dropdown
  Lucktext task, built by the HuleEduOS producer from its proven `order` and
  `inline_choice` constructions. Skriptoteket's QTI writer has neither
  interaction, so this task changes no Skriptoteket code.
- The package imported into Exam.net through the teacher's browser session,
  both tasks opened in the student preview, answered, and their grading
  viewed.
- Screenshots of the import, the student preview, the answer and the grading
  for both tasks, retained in the retained root's `evidence/` and shown to the
  user.
- The user's decision on whether ordering is built, recorded in story
  ST-SKRIPT-39-06.

This is an export probe; it adds no workspace control (story P18).

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P2, P20 and P21.
- `REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type`
  (`docs/reference/ref-skript-research-exam-net-qti-import-routes-per-question-type-exam-net-qti-import-routes-per-question-type.md`):
  ordering as position numbers with one ALL_CORRECT rule (V60-V65); student
  side and marking not observed.
- HuleEduOS `examnet-qti-import` contract
  (`.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`,
  section "Inline choice, matching, ordering and images"): the round 11
  constructions, the producer's `inline_choice` and `order` inputs, the
  fixture `tests/fixtures/examnet_qti/friendly-exam.json` and the generator
  `build/exam/examnet-probes/generators/probe_untried_r11.py`.
- Skriptoteket writer interactions: `ExamNetQtiInteractionType` in
  `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_contracts.py:38`.

## Core Vertical And Performance

The agent builds the two-task package with the HuleEduOS producer, imports it
into a new Exam.net exam in the teacher's browser, opens the student preview,
orders the items and picks an option in each dropdown gap, then opens the
grading view. The user reads the screenshots and says whether ordering is
built.

## Validation

- The retained screenshots show, for the ordering task and the dropdown
  Lucktext task, the import result, the student preview, the given answer
  and the grading.
- The user's ordering decision is recorded in the story.

## Stop Conditions

- Exam.net rejects the package, or imports either task as another type than
  the recorded one: stop and report with the screenshots.
- The HuleEduOS producer cannot build either construction: report to the user
  before building the package another way.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | An Exam.net probe of ordering (import, student preview, answer, grading) comes before any ordering build; the user decides from its screenshots; until then the story plans six types (story P21, user 2026-10-17 G24). |
| P2  | If ordering is built, it is all-or-nothing with a default of 1 point that the teacher can edit (story P21, user 2026-10-17 G24).                                                                                        |
| P3  | The probe also walks dropdown Lucktext's student view and grading; dropdown Lucktext is not gated on it (user 2026-10-17).                                                                                              |
| P4  | Lucktext with dropdown gives each gap its own option list with one correct option marked as the key (story P20, user 2026-10-17 G23).                                                                                   |
