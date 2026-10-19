---
type: task
id: TASK-SKRIPT-40-04-14
title: The question editor toolbar has its own Ångra and Gör om, and every question
  edit autosaves after a short pause
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Every edit is saved to the exam file in Mina filer after a 900 ms pause, or at once
  for structural edits, with no Spara button; Ångra and Gör om move the saved file
  with them; an edit made in another tab is never lost silently; the question toolbar
  can run the one workspace history
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user tested the exam workspace on staging on 2026-10-19 and asked for two things (U1, U2). The user answered the lead's questions Q1-Q6 on 2026-10-19 and accepted the plan. Status `ready` by `agent-planning:user-closure-gate` (user answers 2026-10-19, relayed by orchestrator 944b5a5a). Lead decisions D1-D6 settle what the user handed to the lead under Q3.

Behaviour:

1. One save model: autosave is Spara (Q3). Every stored history step also overwrites the exam file in Mina filer in the same server transaction (D1). Typing is stored after a 900 ms pause, and structural edits are stored at once (Q2). The Spara button and the menu's Spara item are removed. Spara som … stays in the menu and first stores any pending edit.
2. The pause store extends to gap popover answer rows and dropdown option text, and adding a criterion becomes a structural step (Q2).
3. Ångra and Gör om move between stored steps and store nothing new; a new edit after an undo drops the redo steps (Q4). Each undo or redo also moves the server's position and writes that step's document to the file, without a new step, so the file always holds what the teacher sees (D2).
4. The server keeps 50 steps after the baseline instead of 10, behind one named limit (Q6).
5. One shared history (Q1): the top-bar pair, Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z, and the future question-toolbar pair all run it. This task gives the toolbar session `canUndo` and `canRedo` with the provided `undo` and `redo` (D6).
6. Save status (D3) is one computed value the header shows:
   - `Sparar …` while an edit is pending or being stored;
   - `Sparat HH:MM` after a store;
   - `Inte sparat` when a store failed or was refused, with the reason in the tooltip. The refusal reason is the save rule's existing Swedish copy.
   After a network or server failure the pending edit stays and the store is retried every 5 s and on the next edit. Ctrl/Cmd+S stores a pending edit at once. An export first stores a pending edit, where it ran Spara before. Osparat is gone.
7. Cross-tab conflicts (D4). When a store or a position move meets 409 because another tab moved the history, the workspace reads the newest server state and keeps the teacher's pending edit. It then stores that edit as a new step after the other tab's newest step, and shows a notice that the exam was changed in another tab, that the teacher's edits were saved on top, and that Ångra shows the other tab's version. With no pending edit, the workspace reloads and shows that the exam was changed in another tab. A 409 that arrives while an operation is busy waits for the operation to end and is then handled the same way; today such a 409 skips the reload. This replaces the 409 reload that 40-04-09 R9 kept (review aeb140ef F1).
8. Guests (D5): a guest has no Mina filer. The guest draft replica (`examWorkspaceGuestDraft.ts`) follows the same model in IndexedDB: a stored step updates the saved draft, undo and redo move it, it keeps 50 steps, and the status reads `Sparat i webbläsaren HH:MM`. Copy goes to `ui-copy-reviewer`.
9. During a conversion of the open exam, a step that changes a placeholder still being converted is refused by the existing guard (`refuse_placeholder_changes`), which already applies to steps and Spara alike. The status shows `Inte sparat` with that reason.

Scope split (orchestrator 2026-10-19): the Mac toolbar session owns where the toolbar Ångra and Gör om sit (Q5: first, before B I U) and how they look, and the look of the header status slot. This task builds the behaviour and exposes `canUndo`, `canRedo`, `undo`, `redo` and the save status for that session to place and style. It removes the Spara button, because removing it is behaviour.

Non-goals: toolbar and header layout and look; a merge of two tabs' edits inside one document; changes to export or print output.

## Contract Inputs

- The user's feedback 2026-10-19 (U1, U2) and answers Q1-Q6 (2026-10-19), relayed through the Hemma orchestrator 944b5a5a.
- TASK-SKRIPT-40-04-03 W5 and W8, TASK-SKRIPT-39-04-08 (the server-stored undo history), TASK-SKRIPT-40-04-06 D2, TASK-SKRIPT-40-04-09 R9 and review aeb140ef F1 (the 409 policy this task replaces).
- Retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`:
  - the plan `evidence/planning/TASK-SKRIPT-40-04-14/plan.md`;
  - the verbatim transcripts `evidence/planning/user-feedback-2026-10-19.md`;
  - Explorer discovery under `discovery/explorer/`: `autosave-map`, `autosave-indicator`, `spara-write`, `save-conflict`, `step-read-position`, `conversion-editing` and `step-cap`.
- The Mac toolbar session (layout and look); `huleedu-ui-design`; `integrated-frontend-stack`; `skriptoteket-backend-dev`.

## Core Vertical And Performance

### Resume here

Ready 2026-10-19 (lead 73032e62, retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`). The ledger is closed. origin/main is merged at 72df15cf. Next action: build wave 1 (K1, K2, K3) with fresh juniors and fail-first tests, after 40-04-13's wave 1, or alongside it where the files are disjoint.

### Units

Frontend paths are under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`, and backend paths start with `src/skriptoteket/`. Waves:
1. K1, K2 and K3. K3 then regenerates the API types with `pdm run fe-gen-api-types`.
2. K4 and K7.
3. K5 and K6.

| Unit | Files | Behaviour | Focused tests |
| --- | --- | --- | --- |
| K1 toolbar history state | `examWorkspaceHistoryKeys.ts` (`canUndo` and `canRedo` with `undo` and `redo`), `ExamWorkspaceView.vue` (the provider) | Item 5; no button | `examWorkspaceHistoryKeys.spec.ts` (new) |
| K2 field cadence | `ExamWorkspaceGapAnswerList.vue`, `ExamWorkspaceGapPopover.vue` (store after the pause), `ExamWorkspaceCriteriaField.vue` and `useExamWorkspaceItemEdits.ts` (criterion add is structural) | Item 2 | `ExamWorkspaceGapAnswerList.spec.ts`, `ExamWorkspaceGapPopover.options.spec.ts`, the criteria field spec |
| K3 backend one save | `src/skriptoteket/application/curated_apps/handlers/`: `exam_workspace_undo_steps.py` (the step store also overwrites the file), `exam_workspace_document_store.py` (shared file write; the step limit), `exam_workspace_documents.py` (a position-move command; remove Spara `_save` and its route in `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py` once no caller is left) | Items 1, 3 and 4 on the server | The undo-step, history-step, save-retention and route tests; a new position-move test |
| K4 frontend history | `useExamWorkspaceHistory.ts` (position move on undo and redo, save status, retry), `src/api/examWorkspace.ts` (the move call), `examWorkspaceStore.ts` | Items 3 and 6 | `useExamWorkspaceHistory.spec.ts`, `useExamWorkspaceEditing.history.spec.ts`, `useExamWorkspaceEditing.typingPause.spec.ts` |
| K5 Spara removal | `useExamWorkspaceSave.ts` (Spara goes; Spara som stores first), `useExamWorkspaceSaveFlow.ts` (status from K4), `ExamWorkspaceHeader.vue` (no Spara button or item; shows the status text), `useExamWorkspaceKeyboard.ts` (Ctrl/Cmd+S stores), `useExamWorkspaceExports.ts` (store before export), the API `saveExamWorkspaceDocument` and its store entries | Items 1 and 6 | The save, save-flow, header, keyboard and export specs |
| K6 cross-tab | `useExamWorkspaceHistory.ts` (409 keeps and re-stores the pending edit), `useExamWorkspaceDocument.ts` (`reloadDocument` never skips while busy; it waits) | Item 7 | `useExamWorkspaceEditing.history.spec.ts` (the 409 cases that 40-04-09 F1 pinned change to the new policy), `useExamWorkspaceEditing.gapUndo.spec.ts` |
| K7 guest replica | `examWorkspaceGuestDraft.ts`, `examWorkspaceGuestStore.ts`, `examWorkspaceGuestStoreCommit.ts` | Item 8 | `examWorkspaceGuestDraft.spec.ts`, `examWorkspaceGuestStore.history.spec.ts` |

K4 and K6 both touch `useExamWorkspaceHistory.ts`, so they run in different waves. Every unit that removes a path also deletes its tests; no dual path stays.

Performance (D1): the step store already parses the stored file and every retained step's asset set, and rebuilds the container on every stored step (`prepare_editor_content`, `conversion-editing` and `spara-write` discovery). Writing the file in the same transaction adds one blob write and one row update per step, at most one per 900 ms pause per teacher. The asset scan grows with the step limit, from 10 to 50 steps. K3 measures a step store with 50 retained steps on a fixture with pictures and reports the time. If it exceeds 300 ms, K3 stops and reports before the limit is raised.

## Validation

- Per unit: its focused spec files, run as `pdm run fe-test -- <spec path>` or `pdm run pytest <test file>`. For K3 also `pdm run lint` and `pdm run typecheck`.
- At the end: `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`, and on the orchestrator's go one domain suite per touched domain (the exam-workspace frontend and backend).
- Copy (the status texts, the guest status and the cross-tab notice) goes to `ui-copy-reviewer`.
- Staging walk on Hemma in a real browser:
  1. Type in a question and wait: the status shows Sparat. Reopen the exam from Mina filer: the text is there.
  2. Ångra, then reopen from Mina filer: the file holds the undone version.
  3. Edit a gap answer, wait, Ångra.
  4. Two tabs: edit in one, then type in the other. The notice shows, and the second tab's typing is stored. Ångra shows the first tab's version.
  5. Guest: type, wait, reload the page: the draft is there.
  6. No Spara button.

## Stop Conditions

Stop and ask the user if a unit needs a toolbar or header layout decision (send it to the orchestrator for the toolbar session), if the 50-step store exceeds the K3 timing limit, or if a caller other than the editor needs the Spara endpoint.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| U1  | The question editor toolbar gets its own Ångra and Gör om for the steps taken in that editing area, text and item edits (user 2026-10-19, staging test) |
| U2  | Continuous autosave in the item editor: every add, remove or change is saved after a debounce, not only on Spara (user 2026-10-19, staging test) |
| F1  | There is no editor-local undo; Ctrl/Cmd+Z in an editor, the window handler outside editables and the top-bar Ångra and Gör om all run the one workspace history |
| F2  | Every edit is stored on the server as an undo step, typing after a 900 ms pause and structural edits at once, at most 10 steps after the import baseline; the guest store writes each command to IndexedDB at once |
| F3  | The header save state reads Osparat until Spara even after steps are stored; the draft wording is only in its tooltip |
| F4  | Gap popover answer rows and dropdown option text are committed only on change or blur; Escape cancels the popover and discards uncommitted typing (main f3c71530, with TASK-SKRIPT-40-04-08 merged); adding a criterion is recorded as typing, not as a structural step |
| Q1  | One shared workspace history for the toolbar pair, the top-bar pair and Ctrl/Cmd+Z (user 2026-10-19) |
| Q2  | 900 ms everywhere: the pause store extends to popover answers and option text; adding a criterion is structural (user 2026-10-19) |
| Q3  | Autosave is Spara: autosave also writes the exam file in Mina filer, the header shows Sparat, the Spara button goes and Spara som stays; one save model; the lead designs the write cadence, the guest case, the status text and the cross-tab policy (user 2026-10-19, changed from the lead's recommendation) |
| Q4  | Undo stores nothing new; a new edit after an undo drops the redo steps (user 2026-10-19) |
| Q5  | Ångra and Gör om come first in the question toolbar, before B I U; the Mac toolbar session places and styles them (user 2026-10-19; scope split by the orchestrator 2026-10-19) |
| Q6  | The server keeps 50 steps (user 2026-10-19) |
| D1  | Every stored step writes the file in the same transaction, because the step store already rebuilds the container, so the write adds one blob write; no separate file cadence (lead design 2026-10-19 from Q3 and `spara-write`, `conversion-editing` discovery) |
| D2  | Undo and redo move the server position and write that step's document to the file without a new step, because the history-step read is read-only today and "Sparat" must be true after an undo (lead design 2026-10-19 from Q3, Q4 and `step-read-position` discovery) |
| D3  | One computed save status: Sparar …, Sparat HH:MM, or Inte sparat with the reason; failures retry every 5 s and on the next edit; Ctrl/Cmd+S and exports store a pending edit first (lead design 2026-10-19 from Q3) |
| D4  | On a cross-tab 409, read the newest server state, keep the pending edit and store it on top, with a notice that names the other tab and Ångra; a busy-time 409 waits instead of skipping the reload. The user may override this; the alternatives were a tab lease (the other tab read-only) and keep-and-ask (two actions) (lead design 2026-10-19 from Q3 and review aeb140ef F1) |
| D5  | Guests follow the same model in the IndexedDB replica, with the status Sparat i webbläsaren HH:MM (lead design 2026-10-19 from Q3) |
| D6  | Scope split: this task exposes `canUndo`, `canRedo`, `undo`, `redo` and the save status; the Mac toolbar session places and styles the toolbar pair and the status slot (orchestrator 2026-10-19) |
