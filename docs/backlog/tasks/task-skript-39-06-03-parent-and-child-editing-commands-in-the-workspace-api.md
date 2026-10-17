---
type: task
id: TASK-SKRIPT-39-06-03
title: Parent and child editing commands in the workspace API
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The workspace API creates a parent, adds, deletes and reorders its children, and keeps sequence numbers and the parent's summed points consistent
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

The only document write route is the whole-document PUT
(`SaveExamWorkspaceDocumentHandler`, guarded by `expected_revision`). The
editor reads parents and tells the teacher that a child cannot be moved,
removed or retyped there (`examWorkspaceParents.ts`). A client that edits
parents today must rebuild the items and parents itself and keep the document
invariants. This task adds server commands for parent authoring, so the
redesigned workspace (ST-SKRIPT-40-04) calls them instead. It is backend and
API work; it adds no workspace control (story P18).

This task delivers:

- Domain operations on `NativeExamDocument`:
  - create a parent: a new parent with a shared instruction and its first
    child, inserted at a position among the standalone questions;
  - add a child to a parent at a position inside it;
  - delete a child from a parent;
  - reorder the children of one parent.
- Every operation returns a document that holds the existing invariants: item
  sequences run from 1 without gaps, and every parent's children are
  consecutive in sequence order (`validate_parent_structure`).
- The caller supplies a new child's content as an item of any kind the model
  holds (story P4); the server assigns the next free item id and the sequence.
- Deleting a parent's only child is refused with a named error, because a
  parent holds one or more children (`NativeExamParent.item_ids` has
  `min_length=1`).
- The parent has no points of its own; its points remain the sum of its
  children (`parent_points`, story P6).
- One workspace API route per command under
  `/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/`.
  Each takes the expected revision like the PUT route, answers a stale
  revision with CONFLICT, saves one new revision and returns the document.

Out of scope: moving questions between parents or out to standalone (story
P7); turning existing standalone questions into children; ordering, which
does not exist as a kind (if the user decides to build it after
TASK-SKRIPT-39-06-02, that task refuses ordering as a child, story P3); every
workspace control, including "Ny uppgift" and "+ Deluppgift" (story P13,
ST-SKRIPT-40-04).

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P3, P4, P6, P7, P13 and P18.
- Document invariants: `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`
  (`_document_invariants`) and `native_exam_parent.py`
  (`NativeExamParent`, `validate_parent_structure`, `parent_points`).
- Item id rule: `ITEM_ID_PATTERN` in `native_exam_vocabulary.py`.
- Save path and conflict rule: `SaveExamWorkspaceDocumentHandler` in
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`;
  routes in `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- Current read-only parent display: `frontend/apps/skriptoteket/src/views/apps/exam-workspace/examWorkspaceParents.ts`.
- TASK-SKRIPT-39-06-01: the proven parent export path.

## Core Vertical And Performance

On a saved exam with eight standalone questions, a call creates a parent
after question 3 with a shared instruction and one Lucktext child; two calls
add a single-choice and a free-text child; one call moves the free-text child
first; one call deletes the single-choice child. After each call the document
reads back with sequences 1..N and the parent's children consecutive, and the
parent's points equal its children's sum. The exported package imports into
Exam.net with the children in the new order. Each command is one request and
one saved revision.

## Validation

- Focused domain tests on a real saved workspace document with a converted
  parent: each operation keeps sequences contiguous and the parent's children
  consecutive; reorder changes only that parent's children; deleting the only
  child is refused with the named error; the parent's points equal its
  children's sum after each operation.
- Focused handler tests: a stale revision returns CONFLICT; a valid call saves
  one revision and returns the document.
- Exam.net proof on Hemma staging: a document changed through the commands,
  exported and imported through the teacher's browser, with screenshots of
  the task, its children in order and their points retained in the retained
  root's `evidence/`.

## Stop Conditions

- A command cannot keep the invariants without changing the parent model:
  report to the user before changing it.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                      |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | Inside one parent the teacher adds, deletes and reorders children; moving questions between parents or out to standalone is later work (story P7).                         |
| P2  | A question is standalone or a parent with one shared instruction and child questions of any mix of types (story P4).                                                       |
| P3  | Each child has its own points; the parent shows their sum and is not edited directly (story P6).                                                                           |
| P4  | Ordering questions are standalone only and never children of a parent (story P3); this task has no ordering kind to refuse.                                                |
| P5  | "Ny uppgift" and "+ Deluppgift" and their controls are requirements handed to ST-SKRIPT-40-04's prototype; this task supplies the backend (story P13, user 2026-10-17 G2). |
| P6  | This story ships backend, data, API and export only; the current workspace screens are frozen except for bug fixes (story P18, user 2026-10-17 G2).                        |
