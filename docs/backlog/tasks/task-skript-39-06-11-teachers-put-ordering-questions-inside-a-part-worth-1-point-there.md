---
type: task
id: TASK-SKRIPT-39-06-11
title: Teachers put ordering questions inside a part, worth 1 point there
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-28'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A teacher adds an ordering question inside a part or moves one into a part, and it is saved there worth 1 point
  - Inside a part the ordering question's points read 1 and cannot be changed, with a note that Exam.net gives it 1 point; a standalone ordering question keeps its editable points
  - The exported QTI, PDF and DOCX give the ordering child 1 point, and the exam imports into Exam.net with the part's total matching the workspace total
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

The Exam.net probe TASK-SKRIPT-39-06-09 (exam 5395644) showed that an ordering question inside a part imports and grades as it does standalone: Matcha ihop with position numbers, all-or-nothing, scored apart from its sibling questions. Exam.net always gives that child 1 point, whatever the package says. The user decided on 2026-10-28 to build ordering inside parts at a fixed 1 point. This replaces story term P3 (ordering standalone only) for parts.

- Actors: a teacher editing an exam in the exam workspace.
- Input: a part, and an ordering question added inside it or moved into it with the existing part commands (TASK-SKRIPT-39-06-10).
- Output: the ordering child is saved inside the part worth 1 point. The editor shows its points as 1, locked, with a note that Exam.net gives an ordering question in a part 1 point. QTI writes the child with 1 point inside the part's composite item, through the existing writer path that the probe proved. PDF and DOCX print 1 point, and printed part totals add up.
- Moving: an ordering question moved into a part becomes 1 point, and the change is one undo step. Moved out of a part, it keeps 1 point, which the teacher can then edit.
- Non-goals: any change to standalone ordering, other question types, the Matcha ihop student view in Exam.net, or Exam.net tiered rules.

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P3 and P21; the user decision of 2026-10-28 recorded in TASK-SKRIPT-39-06-09.
- The probe record: Hemma `.artifacts/probe-39-06-09/PROBE.md` and the Mac walk record `~/Repos/Skriptoteket/.artifacts/probe-39-06-09/walk-record.md`. The probe builder is on branch `codex/task-skript-39-06-09` (6fee3cfdd); it is not merged.
- The refusal today: `native_exam_document.py:178-182` and TASK-SKRIPT-39-06-10 G6 (moving into a part is refused for ordering).
- The QTI part writer: `examnet_qti_export.py` `_parent_qti_item`. REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type: an ALL_CORRECT rule takes MAXSCORE, and a child inside a part gets 1 point.

## Core Vertical And Performance

The core vertical is one ordering question inside one part. A teacher moves it into the part, it saves at 1 point with the locked points field, and the exported package imports into Exam.net with a part total that matches the workspace. Performance is not material.

Units, each for one junior:

1. Backend: drop the parent refusal for ordering in the document validators and the part commands. A validator rule fixes an ordering child at 1 point, and a move into a part sets it to 1. QTI, PDF and DOCX export the child at 1 point.
2. Frontend: allow ordering in the part's add-question menu and in the move commands. Lock the points field in a part, with the note; one undo step for a move.
3. Copy: one ui-copy review of the note and its tooltip; the lead applies the accepted wording.

## Validation

- Backend unit tests: an ordering child validates at 1 point and is refused at any other value; a move into a part sets 1 point; the QTI composite item holds the ordering child with the probe's structure and a total that matches the workspace; PDF and DOCX print 1 point.
- Vitest: the add menu inside a part offers ordering; the locked points field with its note; the move and its undo.
- One Mac staging walk: add an ordering question to a part, export, and have the Mac import it into Exam.net itself, checking that the part's total matches.

## Stop Conditions

- The exported part's total in Exam.net differs from the workspace total.
- Allowing ordering in parts would need a change to another question type's export.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Ordering questions can sit inside a part; there they are always worth 1 point and the editor shows the points locked, with a note that Exam.net gives them 1 point; standalone ordering keeps editable points (user decision 2026-10-28 after TASK-SKRIPT-39-06-09). |
| D2  | Moving an ordering question into a part sets it to 1 point as one undo step; moving it out keeps 1 point, which the teacher can edit (orchestrator decision 2026-10-28).                                                                                             |
| D3  | QTI writes the ordering child inside the part's composite item through the existing writer path that the probe proved; PDF and DOCX print 1 point (orchestrator decision 2026-10-28).                                                                                |
| D4  | Proof is focused unit and Vitest tests, one ui-copy review of the note, and one Mac staging walk with the Mac's own Exam.net import; one independent review at most, no rereviews (orchestrator decision 2026-10-28).                                                |

## Progress

### Orchestrator decisions 2026-10-28 (asked by the lead, outside D1-D4)

- Change type inside a part: allowed. Changing a part child's type to ordering sets its points to 1 in the same command, as one undo step (`native_exam_change_type.py` refusal removed).
- QTI import: an ordering child of an Exam.net composite part imports as an ordering child at 1 point, whatever points the package states, with no interaction note (`qti_import.py` `_append_parent`).
- Grouping (`group_items`, TASK-SKRIPT-39-06-10 G10) counts as a move into a part under D2: ordering is allowed and set to 1 point, and the list-row checkbox for an ordering question is enabled.
- Each of the three has a focused test.
