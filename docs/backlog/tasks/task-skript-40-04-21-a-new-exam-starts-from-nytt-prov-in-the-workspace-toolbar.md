---
type: task
id: TASK-SKRIPT-40-04-21
title: A new exam starts from Nytt prov in the workspace toolbar
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A "Nytt prov" button is the first action in the exam workspace header toolbar for signed-in teachers and guests, and one click opens a new untitled exam with one empty question, ready to edit
  - A signed-in teacher's new exam is saved at once and appears in the Prov list
  - The import drawer has no new-exam control, and the guest "Tomt prov" button is gone
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

User request 2026-10-21, decided by the user the same day through the Mac orchestrator ("Ja, skicka förslaget till Hemma som det står."): starting a new exam is a file action like Öppna, Spara som and Importera, so it gets its own "Nytt prov" button in the exam workspace header toolbar, for signed-in teachers and guests alike. It replaces the guest-only "Tomt prov" button in the import drawer.

Today only guests can start an empty exam: the Öppna drawer shows "Tomt prov" under "Importera prov" only when `isGuest` (`ExamWorkspaceOpenDrawer.vue:181-189`), and it calls the public `POST /api/v1/public/apps/documents.conversion_hub/exam-converter/workspace/blank` (`public_apps_exam_workspace_commands.py:145-159`). The domain builder `blank_native_exam_document()` (`native_exam_blank.py:56`) already returns a valid exam with an empty title, no course and one empty free-text question. The signed-in API has no blank-create route (`apps_conversion_hub_exam_workspace.py`).

This task adds the toolbar button, adds a signed-in route that creates the blank exam through `blank_native_exam_document()` and saves it as the teacher's exam, points the guest button at the existing public blank route, and removes the guest "Tomt prov" button from the import drawer with no old wording or alias kept.

Non-goals: a confirm dialog for a signed-in teacher when another exam is open (guests get one only under D9); a course or title prompt on creation; any change to the import drawer other than removing "Tomt prov".

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

- The guest condition (D6 would discard a guest's open exam) triggered on 2026-10-21 and is settled by D9.
- Stop and report if the blank document cannot be created through `blank_native_exam_document()` for both paths.

## Resolved Questions

The proposed answers to U1-U4 were replaced by the user's decision of 2026-10-21; the decided terms below close them.

| ID  | Question                   | Closed by |
| --- | -------------------------- | --------- |
| U1  | Wording and placement      | D1, D2    |
| U2  | Empty-state text           | D7        |
| U3  | When the new exam is saved | D4        |
| U4  | Course                     | D5        |

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | A "Nytt prov" button is the first action in the exam workspace header toolbar, before Öppna: Nytt prov, Öppna, Spara som, Exportera, Importera. It has the same button style as its neighbours and a document-plus icon. The wording is "nytt", not "tomt".                                                                                                                                                                                                                                                                                                                                                      |
| D2  | The import drawer is unchanged apart from D8: it has no new-exam control.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| D3  | A click opens a new untitled exam with one empty question, ready to edit.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| D4  | A signed-in teacher's new exam is saved at once and appears in the Prov list. The existing rule that export needs a title still applies.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| D5  | Course and other details are set in "Uppgifter" as for any other exam. The import drawer's "Kurs (valfritt)" stays tied to imports.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| D6  | If another exam is open, it is saved first, as when switching with Öppna today. There is no confirm dialog.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D7  | The empty-state text when no exam is open is "Skapa ett nytt prov, öppna ett sparat prov eller importera från Word eller DigiExam."                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| D8  | Guests get the same "Nytt prov" toolbar button, backed by the existing public blank route. The guest "Tomt prov" button in the import drawer is removed, with no old wording or alias kept. This replaces the earlier term B1 ("guest path unchanged").                                                                                                                                                                                                                                                                                                                                                          |
| D9  | Guests only: when the open browser draft has content, "Nytt prov" first shows a confirm, "Det öppna provet ersätts av ett nytt. Exportera det först om du vill behålla det.", with Ersätt and Avbryt. Avbryt keeps the draft unchanged. A guest with an empty draft gets no confirm. Signed-in teachers get no dialog; D6 stands for them. User decision 2026-10-21.                                                                                                                                                                                                                                             |
| D10 | The document-plus icon is a new `file-new` glyph meaning (Lucide FilePlus) in the shared design-system glyph set in skill-repository (`resources/frontend-design-system/huleedu-integrated/`), added through that repository's change route as this task's first unit and synced into the Skriptoteket mirror, as TASK-SKRIPT-40-04-17 added its glyphs. Components never import Lucide directly. User decision 2026-10-21.                                                                                                                                                                                      |
| D11 | An untitled exam's file name in Mina filer, and its label in the Prov list while it has no title, is "Namnlöst prov". The title itself stays empty until the teacher sets it in Uppgifter; once it has a title, the title is shown. User decision 2026-10-21.                                                                                                                                                                                                                                                                                                                                                    |
| D12 | The guest sign-in draft move (`exam_workspace_guest_draft_handoff.py`) names a draft with an empty title "Namnlöst prov" under D11. A failing test first proves the current rejection of an empty title, then the fix makes it pass. User decision 2026-10-21.                                                                                                                                                                                                                                                                                                                                                   |
| D13 | For every exam in the workspace, made with "Nytt prov" or imported, every title change renames the exam's Mina filer file to the title. The name follows the export file-name rules, including the TASK-SKRIPT-40-04-05 length cap (`export_file_base_name` in `exam_workspace_exports.py`). An untitled exam is named "Namnlöst prov". Imported exams no longer keep their import-time file name, and no old behaviour is kept. User decision 2026-10-21, relayed by the Mac orchestrator ("my file should always follow the file name that user chooses in the UI, and that is also true for imported files"). |

## Progress

### 2026-10-21 (Hemma orchestrator)

- The user approved the decided terms D1-D8 as written and asked for the feature (relayed by the Mac orchestrator); the task is ready and a lead is assigned.

### 2026-10-21 (implementation lead)

- Stopped before writing code on three gaps, reported to the Hemma orchestrator:
  (1) the guest stop condition holds: a guest has one browser draft slot, and `startBlank` replaces it through `replaceSlotWith` (`examWorkspaceGuestStore.ts:428-446`), and a guest has no saved-exam list to switch with Öppna, so D6 would discard a guest's open exam;
  (2) the document-plus icon needs a new meaning in the shared `uiGlyphs.ts`, a sha-pinned mirror of the skill-repository design-system package (TASK-SKRIPT-40-04-17 T14 route);
  (3) an untitled exam needs a Mina filer file name: `rename_vault_filename` refuses an empty name, and the Prov list shows the file name when the title is empty.

### 2026-10-21 (Hemma orchestrator, decisions)

- The user answered the three gaps through the Mac orchestrator ("Q1-Q2: go with your recommendations", "Q3: Yes, I agree: Namnlöst prov"): D9 settles the guest discard, D10 the glyph route, D11 the untitled name, and D12 adds the guest sign-in draft move with an empty title. The lead resumes.

### 2026-10-21 (implementation lead, delivery)

- D10: skill-repository `TASK-SKILL-REP-0363` added `file-new` (Lucide FilePlus) and released huleedu-integrated 0.1.35 (skill-repository main `4dba3e77`, not pushed); synced here in `b1dff8da`.
- D3, D4, D11, D12 (`9192be9d`): `POST /exam-workspace/blank` saves `blank_native_exam_document()` as the teacher's exam named "Namnlöst prov.provdokument.zip" (201, summary). The guest sign-in draft move names an empty-title draft "Namnlöst prov" and never numbers it; `d12-red.log` proves the old rejection first.
- D1, D2, D5-D9: the "Nytt prov" toolbar button (first file command, `file-new` glyph) for teachers and guests goes through the Öppna gate (`useExamWorkspaceOpenBlocking`), so an unsaved open exam is saved first; a teacher's new exam reloads the Prov list and opens; a guest draft with content gets the D9 confirm (Ersätt, Avbryt); the empty state reads the D7 text; the guest "Tomt prov" button is gone.
- Proof logs: retained root `01a15f95-9eca-7a87-b3b5-4cb77a0761c6` `evidence/u1/`, `evidence/u2/`, `evidence/u3/`, `evidence/lead/`. Owed: independent review and the Mac staging walk (signed in and as a guest).

### 2026-10-21 (implementation lead, review repairs)

- Review `evidence/review-task-skript-40-04-21.md` (changes_requested, F1-F4 admitted) repaired:
  F1 `e379e50b` (Nytt prov is a replacement-coordinator intent; the source settles and the editor locks before any change; the guest slot is replaced only at the cursor the D9 check read; also renames the header button's data-test to `exam-workspace-new-exam`, which collided with Ny fråga),
  F2 `7eabb381` (`isEmptyBody` for question text and instructions),
  F4 `5a6851b9` (`ExamWorkspaceEnrichmentNotice`; the view is 492 lines),
  F3 `e0526e1d` (no assertions in the new specs).
- Proof logs: `evidence/f1/` to `evidence/f4/`, `evidence/lead/repair-*.log`. Owed: F1 independent rereview, D13, the Mac staging walk.

### 2026-10-21 (repair owner, D13 shared-cap repair)

- D13 shared cap is now 238 (`255 - max(len(" Exam.net.pdf"), len(".provdokument.zip"))`, computed from the endings) so the exam's `.provdokument.zip` file fits; trailing-space strip kept. Proof logs: retained root `01a15f95-9eca-7a87-b3b5-4cb77a0761c6` `evidence/d13-cap/`.

### 2026-10-21 (repair owner, round-2 F1: a retired guest creation)

- A guest Nytt prov now replaces the browser slot only under its live authority: the coordinator passes `() => isSelected(entry, token)` to `beginNewExam`, and `startBlank` checks the edit lease, then `replaceIf` evaluates that predicate inside the atomic cursor compare, just before the write. A creation retired by lease handover, pagehide or disposal keeps the retained draft, its history and its pictures. Spec `examWorkspaceGuestNewExam.retiredCreation.spec.ts`; logs in retained root `01a15f95-9eca-7a87-b3b5-4cb77a0761c6` `evidence/f1-retired/`. Guest QTI import (`startFromQti`) has the same replace-before-protection shape outside the coordinator; reported, not changed. Owed: F1 independent rereview.

### 2026-10-21 (repair owner, rereview-3 F1 and F5: the lease decision holds at the slot write)

- Rereview 3 (`evidence/reviews/review-40-04-21-f1-rereview3.md`, changes_requested) repaired: every guest whole-slot replacement (Nytt prov and the guest QTI start) now writes through `replaceSlotIf`, one readwrite IndexedDB transaction over the `drafts` and `edit_lease` stores of the one guest database. It writes only while the D9 expected cursor owns the slot, no other tab holds a live edit lease, and the operation's `isLive` admission is still true. F1: a tab that takes the lease after A's early lease check keeps C even before A sees the loss. F5: the conversion intake passes the import's generation as `isLive` and its lease tab, so a disposed or retired import, or a late parse while another tab holds the lease, never replaces C. Ordinary guest writes and the confirmation UX are unchanged.
- Proof logs: retained root `01a15f95-9eca-7a87-b3b5-4cb77a0761c6` `evidence/f1-lease-f5-qti/` (`before-fix.log` 4 failures on the destructive outcome, then the after logs). Owed: independent rereview of F1 and F5, the Mac staging walk.

### 2026-10-21 (repair owner, rereview-4 F5: a retired gate generation stays retired for the guest QTI write)

- Rereview 4 (`evidence/reviews/review-40-04-21-f1-f5-rereview4.md`, changes_requested; F1 cleared) repaired: `importDocument` captures the sync gate's fence token when a guest QTI import starts, and the `replaceSlotIf` admission now requires that token to be current alongside the import's conversion generation; the in-transaction cursor and lease checks stay. A lost lease or pagehide retires the token, so a late parse refuses even after the lease is released or expires. The signed-in import and ordinary writes are unchanged. `useExamWorkspaceConversion.guestQtiGateRetired.spec.ts` runs the real gate, conversion and guest store: after `leaseLost` or `pageHidden`, with the lease then released, expired or never claimed, C with its history and picture stays and nothing opens; a positive control with current authority replaces the slot and opens the import.
- Proof logs: retained root `01a15f95-9eca-7a87-b3b5-4cb77a0761c6` `evidence/f5-gate-authority/` (`before-fix.log` 4 failures, control passing; `after-fix.log`; suite 342 files / 2554 tests). Owed: independent rereview of F5, the Mac staging walk.
