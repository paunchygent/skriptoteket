---
type: task
id: TASK-SKRIPT-40-04-21
title: A signed-in teacher starts a blank exam from Tomt prov
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-21'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A signed-in teacher can start an empty exam from the same Tomt prov control guests
  use, and it opens in the workspace as an editable saved exam
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

User request 2026-10-21 (relayed by the Mac orchestrator): a signed-in teacher can start an empty exam. Today only guests can: the Öppna drawer shows "Tomt prov" under "Importera prov" only when `isGuest` (`ExamWorkspaceOpenDrawer.vue:181-189`), and it calls the public `POST /api/v1/public/apps/documents.conversion_hub/exam-converter/workspace/blank` (`public_apps_exam_workspace_commands.py:145-159`, domain `native_exam_blank.py:56`). A signed-in teacher can only import a file or open a saved exam; the signed-in API has no blank-create route (`apps_conversion_hub_exam_workspace.py`).

Proposed shape, pending the user's UI confirmation: the same "Tomt prov" button, same place and style, is shown to signed-in teachers too. A new signed-in route creates the blank native exam through the existing `native_exam_blank` domain builder and saves it as the teacher's exam, and the workspace opens it like a saved exam. The guest path stays as it is.

## Contract Inputs

- TASK-SKRIPT-41-02-02 F3b (`9de1523d`): guest blank start and `ExamWorkspaceGuestMode.intake.spec.ts`.
- Signed-in empty state: `ExamWorkspaceEditorPane.vue:97-113` ("Inget prov öppet", "Importera ett prov från Word eller DigiExam, eller öppna ett sparat prov.", button "Öppna"); header Öppna/Importera (`ExamWorkspaceHeader.vue:186-228`).
- TASK-SKRIPT-40-04-05: a blank title saves and autosaves; only export refuses it.
- Explorer maps 2026-10-21 in retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`.

## Core Vertical And Performance

One click on "Tomt prov" as a signed-in teacher: a POST creates and saves one blank native document, and the workspace opens it. No performance concern.

## Validation

- Backend: focused tests for the new route (creates one saved blank document owned by the teacher; refuses a guest) and the handler.
- Frontend: focused Vitest for the drawer showing "Tomt prov" to a signed-in teacher and opening the created exam; the guest specs still pass.
- Behaviour: a staging walk by the Mac orchestrator.

## Stop Conditions

Stop and report if the blank document cannot reuse `native_exam_blank` without changing the guest path, or if creating it needs a decision the questions below do not settle.

## Open Questions For The User

| ID | Question | Proposed answer |
| --- | --- | --- |
| U1 | Wording and placement | Reuse the guest button exactly: "Tomt prov", first under "Importera prov" in the Öppna drawer, plain workspace button style. |
| U2 | Empty-state text for a signed-in teacher | "Importera ett prov från Word eller DigiExam, öppna ett sparat prov eller börja med ett tomt prov." |
| U3 | When the blank exam is saved | Saved at once, so it appears in the saved list with a blank title until the teacher names it. |
| U4 | Course | The drawer's "Kurs (valfritt)" choice, when set, is applied to the blank exam as it is to an import. |

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| B1  | The guest blank path and its public route are unchanged. |
