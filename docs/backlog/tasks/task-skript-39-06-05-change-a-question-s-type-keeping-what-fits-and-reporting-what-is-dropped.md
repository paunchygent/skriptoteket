---
type: task
id: TASK-SKRIPT-39-06-05
title: Change a question's type, keeping what fits and reporting what is dropped
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
  - Changing a question's type through the workspace API carries over its text and points, drops content the new type cannot hold, returns the names of what was dropped, gives a type that needs structure its minimum empty parts marked as blockers until filled, and one undo step restores the previous question
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

The teacher can change any question to another type (story P14). No route does
this today: item edits are built in the frontend (`examWorkspaceItemEdits.ts`)
and saved through the whole-document PUT, and the editor says a child cannot
be retyped there. This task adds a change-type command to the workspace API.
It is backend and API work; the control and the notice are built by
ST-SKRIPT-40-04 (story P14, P18).

This task delivers:

- A domain operation that changes one question, standalone or a child, to a
  target kind. The question text (`body`) and `points` carry over (story
  P19). Content the target kind cannot hold is dropped, following the kind
  rules in `native_exam_item.py`: choices and their correct choices, gaps and
  their accepted values (including the gap places in the body), match lists,
  pairs and `tick_points`, criteria, and answer-key data the new kind does not
  use.
- A target kind that needs structure the carried text and points cannot supply
  gets its minimum empty parts: two empty choices for single and multiple
  choice, one empty gap for the Lucktext kinds, and one empty pair for
  matching. Each empty part is marked as a blocker until the teacher fills it
  (P6). For matching, the one pair holds all the points, so the points equal
  `tick_points` times the pairs: `tick_points` equals the carried points.
- The operation returns the changed document and the names of the dropped
  content, one name per kind of content, so the workspace can show a notice
  naming it. The Swedish wording of the notice belongs to ST-SKRIPT-40-04's
  prototype.
- One workspace API route under
  `/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/`
  that takes the item id, the target kind and the expected revision, answers a
  stale revision with CONFLICT, saves one new revision and returns the
  document and the dropped names.
- Undo: the saved revision is one autosave, so it is one undo step (story
  P22). One undo step restores the previous question (story P19). The undo
  steps are server-stored autosaves built by TASK-SKRIPT-39-04-08; this task
  depends on them and builds no undo of its own.

Out of scope: the type menu, the notice and the undo shortcut (ST-SKRIPT-40-04);
asking the model to rebuild a question as the chosen type (story P16); the
suggested type (TASK-SKRIPT-39-06-06).

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P14, P16, P18, P19 and P22.
- Kind rules: `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_item.py`
  (`NativeExamItem` fields; `_kind_invariants`, `_answer_key_invariants`,
  `_tick_points_invariants`, `_body_gap_invariants`, `_criteria_invariants`)
  and `native_exam_vocabulary.py:26` (`NativeExamItemKind`).
- Dropdown Lucktext kind from TASK-SKRIPT-39-06-04, a target and a source kind
  once it lands.
- Save path and conflict rule: `SaveExamWorkspaceDocumentHandler` in
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`.
- Undo steps: TASK-SKRIPT-39-04-08 (server-stored autosaves, G13).
- Current frontend item edits: `frontend/apps/skriptoteket/src/views/apps/exam-workspace/examWorkspaceItemEdits.ts`.

## Core Vertical And Performance

The agent changes a saved Lucktext question worth 2 points to free text
through the API. The response holds the document, in which the question keeps
its text and 2 points with no gaps, and names the dropped gaps and accepted
answers. One undo step brings back the Lucktext question with its gaps. The
change is one request and one saved revision.

## Validation

- Focused domain tests on real saved workspace documents: for each pair of
  kinds the model holds, the text and points carry over, the content the
  target cannot hold is dropped, and the returned names list exactly that
  content; a child keeps its parent.
- Focused domain tests for the empty parts: a free-text question changed to
  single choice gets two empty choices, to Lucktext one empty gap, and to
  matching one empty pair whose `tick_points` equals the carried points; each
  empty part is marked as a blocker, and filling it clears the blocker.
- Focused handler tests: a stale revision returns CONFLICT; a valid call saves
  one revision and returns the document and the dropped names.
- Undo proof once TASK-SKRIPT-39-04-08 has landed: one undo step after a
  change restores the previous question.
- Exam.net proof on Hemma staging: a changed question exported and imported
  through the teacher's browser as its new type, with screenshots retained in
  the retained root's `evidence/`.

## Stop Conditions

- TASK-SKRIPT-39-04-08 has not delivered server-stored undo steps when this
  task is implemented: report to the user; the undo proof waits for it.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | The teacher can change any question to another type; this story supplies the command and ST-SKRIPT-40-04's prototype the control (story P14, user 2026-10-17 G2).                                                                                                                     |
| P2  | Changing type carries over the question text and points; content the new type cannot hold is dropped with a visible notice naming it, and one undo step restores it (story P19, user 2026-10-17 G20).                                                                                 |
| P3  | Undo keeps at most 10 steps; each autosave is one step, stored on the server (story P22, user 2026-10-17 G13).                                                                                                                                                                        |
| P4  | Asking the model to rebuild a question as a chosen type waits until walks show it is needed (story P16).                                                                                                                                                                              |
| P5  | This story ships backend, data, API and export only; the current workspace screens are frozen except for bug fixes (story P18, user 2026-10-17 G2).                                                                                                                                   |
| P6  | A change into a type that needs structure carries over the text and points and gives the new type the minimum empty parts (two empty choices, one empty gap, one empty pair), marked as blockers until filled; for matching the one pair holds all the points (user 2026-10-17, G25). |
