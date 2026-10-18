---
type: task
id: TASK-SKRIPT-41-02-02
title: Guests open, edit and export exams in the workspace without login
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- At the guest converter's URL a guest starts from QTI or blank, edits, and exports QTI, print PDF, DOCX and the fallback Exam.net PDF without login, with the exam kept in the browser
- Guest imports and exports pass per-caller and pooled hourly limits in the database
- After sign-in the draft is saved to Mina filer and opens there
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Open the exam workspace to guests at the guest converter's URL under ST-SKRIPT-41-02 P1-P5. Guest edits, undo and autosave live in the browser; imports and exports go to public stateless routes that take the document in the request and return the result, under database-backed per-caller and pooled hourly limits that replace the in-memory per-IP throttle for these routes. AI-triggering controls and DigiExam/Word import show a sign-in prompt instead of calling. Sign-in moves the draft into Mina filer.

Non-goals: public AI; changing the signed-in workspace beyond what the shared editor needs.

## Contract Inputs

- ST-SKRIPT-41-02 P1-P5; TASK-SKRIPT-41-02-01 (QTI parse); User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- `infrastructure/security/public_helper_request_throttle.py`, `web/request_metadata.py`, `web/api/v1/public_apps*.py`, the exam workspace views and stores, `exam_workspace_exports.py`.

## Core Vertical And Performance

The vertical is the shared workspace editor running on a browser document store for guests and the server store for signed-in teachers, behind one store interface; the public export and QTI routes are stateless and limited by one database-backed limiter (per caller and pooled per hour). Performance: export rendering cost bounds the pooled limit.

## Validation

- Focused tests: public export and parse routes with no auth, refused past per-caller and pooled limits regardless of user-agent, surviving a restart; no AI client reachable from any public route (extend the REP-0044 guard); sign-in handoff saves the draft once.
- Vitest for the guest store, sign-in prompts and handoff. Lint and typecheck for touched domains.
- Staging walk per ST-SKRIPT-41-02.

## Stop Conditions

Stop and report if the shared editor cannot run on a browser store without forking the workspace, or before merge with the proposed limit defaults for the user to confirm.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| G1  | ST-SKRIPT-41-02 P1-P5 apply as written. |
| G2  | The guest and signed-in workspace are one editor behind one document store interface; no forked workspace. |
| G3  | Limit numbers are settings; the lead proposes defaults and the user confirms them before merge. |
| G4  | Sign-in prompts read "Logga in för att importera från DigiExam eller Word." and "Logga in för att få AI-hjälp." |
