---
type: task
id: TASK-SKRIPT-39-06-07
title: 'Delete an instruction in the workspace API: heading only by default, heading with its questions as a separate command'
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
  - Deleting an instruction removes only its heading and leaves its questions in place as standalone questions; a separate command deletes the heading with all its questions; deleting an instruction's last question also removes the empty heading; every delete is one undoable step
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

Teachers must be able to delete an instruction (a parent item with a shared
instruction and its child questions). TASK-SKRIPT-39-06-03 adds, deletes and
reorders children but has no command that deletes the parent itself, and it
refuses to delete a parent's only child. This task adds the parent deletes and
replaces that refusal. Backend and API only; the workspace controls belong to
TASK-SKRIPT-40-04-03.

This task delivers:

- Domain operations on `NativeExamDocument`:
  - delete an instruction (the default delete): the parent and its shared
    instruction are removed; its children stay at the same positions, in the
    same order, with their points and content, as standalone questions;
  - delete an instruction with all its questions (a separate, explicit
    operation): the parent and every child are removed;
  - deleting a parent's last child removes the child and the now-empty
    parent in the same operation, and the result names that the heading went
    too, so the workspace can say so inline.
- Every operation returns a document that holds the existing invariants:
  item sequences run from 1 without gaps and every remaining parent's
  children are consecutive (`validate_parent_structure`).
- One workspace API route per delete under
  `/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/`,
  with the same newest-undo-step base, concurrency guard and CONFLICT answer
  as the TASK-SKRIPT-39-06-03 commands. The child-delete route keeps its path
  and gains the last-child behaviour.
- Every delete is soft: it stores its result as one new undo step, so undo
  restores the instruction, its questions and their positions exactly. A
  delete never writes the exam file; only `Spara` does.

Out of scope: moving questions between parents; turning standalone questions
into children; every workspace control (TASK-SKRIPT-40-04-03).

## Contract Inputs

- User ruling 2026-10-17 (this task's terms D1-D5).
- TASK-SKRIPT-39-06-03 commands, routes and their concurrency guard.
- Document invariants: `native_exam_document.py` (`_document_invariants`) and
  `native_exam_parent.py` (`NativeExamParent`, `validate_parent_structure`,
  `parent_points`).
- Undo-step write: the TASK-SKRIPT-39-04-08 autosave handler.

## Core Vertical And Performance

On a saved exam with a parent of three children between standalone
questions: deleting the instruction leaves three standalone questions at the
same sequence positions with unchanged points; undo restores the parent with
the same children. Deleting the instruction with its questions removes all
four entries and renumbers the rest; undo restores them. Deleting the last
child of a one-child parent removes both and reports the removed heading.
The exported package imports into Exam.net with the expected structure. Each
delete is one request and one undo step.

## Validation

- Focused domain tests on a real saved document with a converted parent:
  each delete keeps sequences contiguous and remaining parents consecutive;
  heading-only delete keeps every child's content, order and points; the
  cascading delete removes exactly the parent and its children; the last-child
  delete removes the parent and reports it.
- Focused handler tests: a stale request returns CONFLICT; a valid delete
  stores one undo step, leaves the exam file unchanged and returns the
  document; undo returns the document from before the delete.
- Exam.net proof on Hemma staging through the teacher's browser after the
  heading-only delete, with screenshots in the retained root's `evidence/`.

## Stop Conditions

- A delete cannot keep the invariants without changing the parent model:
  report to the user before changing it.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Deleting an instruction is required; the default removes only the heading (user 2026-10-17).                                                                                                            |
| D2  | After a heading-only delete the questions stay in place, in order, with their points, as standalone questions (user 2026-10-17).                                                                        |
| D3  | Deleting the heading with all its questions is a separate, explicit command and never the default (user 2026-10-17).                                                                                    |
| D4  | Every delete is soft and undoable: one new undo step, restored exactly by undo; no toast undo (user 2026-10-17).                                                                                        |
| D5  | Deleting a parent's last question also removes the empty heading in the same undo step, and the result reports it for an inline notice (user 2026-10-17); this replaces TASK-SKRIPT-39-06-03's refusal. |
