---
type: task
id: TASK-SKRIPT-39-06-03
title: Parent and child editing commands in the workspace API
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
  approval_evidence: 'Implementation reviews: u2-review-1 requested changes (F1 high), u2-review-2 approved (evidence/reviews/u2-review-2.md; retained 01a149c9-5bc7-7713-ba64-12dee0470bdd); on Hemma evidence/reviews/TASK-SKRIPT-39-06-03/review-4b135859.md approved the U-4 saved-baseline repair bc8c1071e. Focused runs: evidence/u2r-focused.log 74 passed, u1r2-focused.log 41 passed. Exam.net proof of a command-changed exam with parents and children in order: evidence/staging-walk-u2-d9c2b3bb/walk.md (exams 5345126 and 5345127); U-4 re-walk (Spara, export, Exam.net import) at main 1f9e4367: evidence/staging-proof-1f9e4367/proof.md (exam 5345261).'
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
  Each applies to the exam's newest undo step, takes the same concurrency
  guard as the TASK-SKRIPT-39-04-08 autosave route, answers a stale request
  with CONFLICT, stores the result as one new undo step and returns the
  document. A command never writes the exam file; only `Spara` does (lead
  decision L8 from user decisions G13, G15 and G20).

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
- Undo-step write and its concurrency guard: the TASK-SKRIPT-39-04-08
  autosave handler.
- Former save path and conflict rule: `SaveExamWorkspaceDocumentHandler` in
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
one undo step; reopening the exam shows the command's result, and `Spara`
writes it to the exam file.

## Validation

- Focused domain tests on a real saved workspace document with a converted
  parent: each operation keeps sequences contiguous and the parent's children
  consecutive; reorder changes only that parent's children; deleting the only
  child is refused with the named error; the parent's points equal its
  children's sum after each operation.
- Focused handler tests: a stale request returns CONFLICT; a valid call
  stores one undo step, leaves the exam file unchanged and returns the
  document; reopening the exam returns the command's result.
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
| P7  | Each command stores its result as one new undo step and never writes the exam file; `Spara` writes the file (lead 2026-10-17, L8, from user decisions G13, G15 and G20).   |
