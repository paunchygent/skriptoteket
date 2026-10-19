---
type: story
id: ST-SKRIPT-41-02
title: Guests open, edit and export exams in the workspace without login or AI
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-41
acceptance_criteria:
  - A guest imports a QTI package or starts a blank exam, edits it and exports QTI, print PDF, DOCX and the fallback Exam.net PDF without login, with no AI
  - On sign-in the guest's exam is saved to Mina filer
  - The public guest DigiExam line is removed
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

The public guest converter today converts DigiExam files through its own jobs table, artifacts, answer-key planner, Exam.net PDF builder and QTI adapter, sharing only the parser and the final writers with the workspace. The workspace has no QTI import. This story makes the public offer the workspace itself (P1-P6): QTI import for everyone, the workspace without login at the guest converter's URL with browser-only storage and strict limits, and removal of the guest DigiExam line.

## Contract Inputs

- User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- `web/api/v1/public_apps_exam_converter.py`, `application/curated_apps/public_exam_converter*.py`, `handlers/public_exam_converter_jobs.py`, `infrastructure/security/public_helper_request_throttle.py`, `frontend/apps/skriptoteket/src/views/apps/ExamConverterPublicView.vue`, the exam workspace views.

## Tasks

| Task                 | Delivers                                                                                                                            | Depends on                             |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| TASK-SKRIPT-41-02-01 | QTI package import into a native exam document, signed-in and guest                                                                 | None                                   |
| TASK-SKRIPT-41-02-02 | The public workspace: entry, browser storage, public exports, limits, sign-in handoff                                               | TASK-SKRIPT-41-02-01 for the QTI start |
| TASK-SKRIPT-41-02-03 | Removal of the guest DigiExam line and closure of superseded docs                                                                   | TASK-SKRIPT-41-02-02                   |
| TASK-SKRIPT-41-02-04 | The workspace fills the desktop window; the editor column is the widest; resizable, collapsible panels with one shared drawer width | TASK-SKRIPT-41-02-02                   |
| TASK-SKRIPT-41-02-05 | A guest draft Mina filer rejects for good stops retrying and is offered for download or removal                                     | TASK-SKRIPT-41-02-02                   |

## Progress

- 2026-10-19: TASK-SKRIPT-41-02-01, 41-02-02 and 41-02-04 are `done`; TASK-SKRIPT-41-02-03 is `ready`.
- TASK-SKRIPT-41-02-04 merged to main as `ffab920a` and its walk repair as `67861ab3`. Both
  staging walks passed. The guest workspace fills the desktop window, is held to the window
  height, and the editor is the widest column at default widths. Panels have drag handles, a
  collapsible list rail and widths remembered per browser. W1 and W2 are handed to
  TASK-SKRIPT-40-04-17.

## Verification

Focused tests per task; a staging walk: a guest imports the omprov QTI export, edits, exports all four formats, hits the limit message, signs in and finds the exam in Mina filer.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | The guest converter's URL opens the exam workspace without login; a guest starts from a QTI import or a blank exam; DigiExam and Word import are shown and ask the guest to sign in.                                    |
| P2  | A guest's exam lives only in the browser on that device; the page says clearing the browser loses it.                                                                                                                   |
| P3  | Guests export QTI, print PDF, DOCX and the fallback Exam.net PDF; AI controls ask the guest to sign in and make no call.                                                                                                |
| P4  | Guest imports and exports pass strict per-caller and pooled hourly limits kept in the database, shared by workers, surviving restarts and not keyed on the user-agent; past a limit the page asks the guest to sign in. |
| P5  | After sign-in the browser draft is saved to Mina filer automatically and opens there; the browser copy is cleared.                                                                                                      |
| P6  | The public guest DigiExam line is removed; TASK-SKRIPT-21-10-01 and ST-SKRIPT-21-10 close as superseded.                                                                                                                |
