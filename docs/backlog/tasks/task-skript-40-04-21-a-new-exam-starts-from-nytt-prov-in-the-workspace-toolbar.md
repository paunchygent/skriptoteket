---
type: task
id: TASK-SKRIPT-40-04-21
title: A new exam starts from Nytt prov in the workspace toolbar
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
- A "Nytt prov" button is the first action in the exam workspace header toolbar for
  signed-in teachers and guests, and one click opens a new untitled exam with one
  empty question, ready to edit
- A signed-in teacher's new exam is saved at once and appears in the Prov list
- The import drawer has no new-exam control, and the guest "Tomt prov" button is gone
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

User request 2026-10-21, decided by the user the same day through the Mac orchestrator ("Ja, skicka förslaget till Hemma som det står."): starting a new exam is a file action like Öppna, Spara som and Importera, so it gets its own "Nytt prov" button in the exam workspace header toolbar, for signed-in teachers and guests alike. It replaces the guest-only "Tomt prov" button in the import drawer.

Today only guests can start an empty exam: the Öppna drawer shows "Tomt prov" under "Importera prov" only when `isGuest` (`ExamWorkspaceOpenDrawer.vue:181-189`), and it calls the public `POST /api/v1/public/apps/documents.conversion_hub/exam-converter/workspace/blank` (`public_apps_exam_workspace_commands.py:145-159`). The domain builder `blank_native_exam_document()` (`native_exam_blank.py:56`) already returns a valid exam with an empty title, no course and one empty free-text question. The signed-in API has no blank-create route (`apps_conversion_hub_exam_workspace.py`).

This task adds the toolbar button, adds a signed-in route that creates the blank exam through `blank_native_exam_document()` and saves it as the teacher's exam, points the guest button at the existing public blank route, and removes the guest "Tomt prov" button from the import drawer with no old wording or alias kept.

Non-goals: a confirm dialog when another exam is open; a course or title prompt on creation; any change to the import drawer other than removing "Tomt prov".

## Contract Inputs

- Mac mock screenshots of the decided placement: `.artifacts/mock-40-04-21-nytt-prov/` on the Mac (button added in the DOM only, on the staging page).
- Header toolbar: `ExamWorkspaceHeader.vue:186-228` (Öppna, Spara som, Importera; Exportera through the `export` slot).
- Signed-in empty state: `ExamWorkspaceEditorPane.vue:97-113` ("Inget prov öppet", "Importera ett prov från Word eller DigiExam, eller öppna ett sparat prov.", button "Öppna").
- TASK-SKRIPT-41-02-02 F3b (`9de1523d`): guest blank start and `ExamWorkspaceGuestMode.intake.spec.ts`.
- TASK-SKRIPT-40-04-05: a blank title saves and autosaves; only export refuses it.
- Explorer maps 2026-10-21 in retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`.

## Core Vertical And Performance

One click on "Nytt prov" as a signed-in teacher: the open exam, if any, is saved as Öppna saves it before switching; a POST creates and saves one blank native document; the workspace opens it and the Prov list shows it. The guest click takes the same steps against the public blank route. No performance concern.

## Validation

- Backend: focused tests for the new signed-in route (creates one saved blank document owned by the teacher, with one empty question; refuses a request without a signed-in teacher) and its handler.
- Frontend: focused Vitest for the toolbar order and button, the click opening the created exam for a signed-in teacher and for a guest, the open exam being saved first, the new empty-state text, and the import drawer without "Tomt prov"; the guest intake specs are updated to the toolbar button.
- Behaviour: a staging walk by the Mac orchestrator, signed in and as a guest.

## Stop Conditions

- Stop and report if the guest workspace cannot save or keep its open exam before switching the way Öppna does, so that D6 would discard a guest's open exam.
- Stop and report if the blank document cannot be created through `blank_native_exam_document()` for both paths.

## Resolved Questions

The proposed answers to U1-U4 were replaced by the user's decision of 2026-10-21; the decided terms below close them.

| ID | Question | Closed by |
| --- | --- | --- |
| U1 | Wording and placement | D1, D2 |
| U2 | Empty-state text | D7 |
| U3 | When the new exam is saved | D4 |
| U4 | Course | D5 |

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | A "Nytt prov" button is the first action in the exam workspace header toolbar, before Öppna: Nytt prov, Öppna, Spara som, Exportera, Importera. It has the same button style as its neighbours and a document-plus icon. The wording is "nytt", not "tomt". |
| D2  | The import drawer is unchanged apart from D8: it has no new-exam control. |
| D3  | A click opens a new untitled exam with one empty question, ready to edit. |
| D4  | A signed-in teacher's new exam is saved at once and appears in the Prov list. The existing rule that export needs a title still applies. |
| D5  | Course and other details are set in "Uppgifter" as for any other exam. The import drawer's "Kurs (valfritt)" stays tied to imports. |
| D6  | If another exam is open, it is saved first, as when switching with Öppna today. There is no confirm dialog. |
| D7  | The empty-state text when no exam is open is "Skapa ett nytt prov, öppna ett sparat prov eller importera från Word eller DigiExam." |
| D8  | Guests get the same "Nytt prov" toolbar button, backed by the existing public blank route. The guest "Tomt prov" button in the import drawer is removed, with no old wording or alias kept. This replaces the earlier term B1 ("guest path unchanged"). |
