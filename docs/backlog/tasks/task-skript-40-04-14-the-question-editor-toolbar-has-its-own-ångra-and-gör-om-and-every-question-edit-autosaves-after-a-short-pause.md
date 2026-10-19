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
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The question editor's toolbar shows Ångra and Gör om glyphs that undo and redo the
  steps taken in that editing area; every add, remove or change in the question editor
  is stored after a debounce without pressing Spara
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user tested the exam workspace on staging on 2026-10-19 and asked for two things (U1, U2): the question editor's toolbar gets its own Ångra and Gör om for the steps taken in that editing area, and every edit in the item editor is saved after a debounce, not only on Spara.

Much of U2 exists today (F2): every edit is stored on the server as an undo step, typing after a 900 ms pause and structural edits at once. What the teacher does not see is that state (F3), and some item-editor fields store only on change or blur (F4).

Status `proposed`: the user questions Q1-Q6 in the retained plan are open. The planned behaviour, if the user accepts the lead's recommendations:

1. The question toolbar starts with Ångra and Gör om glyphs. They run the same workspace history as the top bar and Ctrl/Cmd+Z, so text, gap records and item fields undo together; the top-bar pair stays.
2. Popover answer rows and dropdown option text are stored after the same 900 ms typing pause; adding a criterion is a structural step.
3. After a step is stored, the header's save-state slot shows Utkast sparat; Spara keeps overwriting the exam in Mina filer.
4. Undo after an autosave moves to the previous stored step and stores nothing; a new edit after undo drops the redo steps; a refused draft is discarded (40-04-09 R9).
5. The server keeps 50 steps instead of 10.

Non-goals: an editor-local undo stack; changes to Spara som, export or print; the gap control (TASK-SKRIPT-40-04-13).

## Contract Inputs

- The user's feedback 2026-10-19 (U1, U2), relayed by the Mac parent through the Hemma orchestrator 944b5a5a.
- TASK-SKRIPT-40-04-03 W5 and W8 and TASK-SKRIPT-39-04-08 (the server-stored undo history), TASK-SKRIPT-40-04-06 D2 (Ctrl/Cmd+Z in a text field runs the workspace history), TASK-SKRIPT-40-04-09 R9.
- The verbatim transcripts: `evidence/planning/user-feedback-2026-10-19.md` in retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`.
- TASK-SKRIPT-40-04-11 (proposed, branch `codex/task-skript-40-04-compact-tools-remote`): boxless glyph tools (T1, T2); the toolbar glyphs here take its look.
- Retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`: plan `evidence/planning/TASK-SKRIPT-40-04-14/plan.md`, Explorer discovery under `discovery/explorer/`, toolbar mock `evidence/planning/mock/toolbar-mock.png`.
- `huleedu-ui-design` (glyph-only tools; a status that changes sits in a slot sized for its widest state); `integrated-frontend-stack`.

## Core Vertical And Performance

### Resume here

Planned 2026-10-19 by lead 73032e62 (retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`). Facts F1-F4 and sources U1-U2 closed; user questions Q1-Q6 open, sent to the orchestrator with recommendations and the mock. Next action: record the user's answers, derive the final units, validate with `--require-closed`, and ask for `ready`.

### Planned units (if the recommendations are accepted)

Frontend paths are under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`.

| Unit | Files | Behaviour | Focused tests |
| --- | --- | --- | --- |
| K1 toolbar undo | `examWorkspaceHistoryKeys.ts` (provide `canUndo` and `canRedo` with the pair), `ExamWorkspaceView.vue`, `ExamWorkspaceMarkToolbar.vue`, `examWorkspaceShortcutLabels.ts` | Q1, Q5 | `ExamWorkspaceMarkToolbar.undo.spec.ts` (new), `examWorkspaceShortcutLabels.spec.ts` |
| K2 field cadence | `ExamWorkspaceGapAnswerList.vue`, `ExamWorkspaceGapPopover.vue` (store after the typing pause), `ExamWorkspaceCriteriaField.vue` and `useExamWorkspaceItemEdits.ts` (criterion add is structural) | Q2 | `ExamWorkspaceGapAnswerList.spec.ts`, `ExamWorkspaceGapPopover.options.spec.ts`, the criteria field spec |
| K3 draft state | `useExamWorkspaceHistory.ts` (last stored time), `useExamWorkspaceSaveFlow.ts`, `ExamWorkspaceHeader.vue` | Q3, Q4 | `useExamWorkspaceHistory.spec.ts`, the header save-state spec |
| K4 step limit | `src/skriptoteket/application/curated_apps/handlers/exam_workspace_undo_steps.py:93` and `exam_workspace_document_store.py:269` (two literal `[-10:]` slices become one named limit; no migration, the history is one JSON blob per lineage), the frontend history header comment and spec fake | Q6 | the backend undo-step and save-retention handler tests |

Performance: K2 adds one timer per open popover; K4 grows stored steps per lineage fivefold, and stored documents are small JSON.

## Validation

- Per unit: its focused spec files (`pdm run fe-test -- <spec path>`; for K4 `pdm run pytest <test file>`), with `pdm run lint` and `pdm run typecheck` for K4.
- At the end: `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`, and one domain suite per touched domain on the orchestrator's go.
- Copy goes to `ui-copy-reviewer`.
- Staging walk on Hemma in a real browser: type in a question, wait, see Utkast sparat; press the toolbar Ångra and Gör om and see the text return; edit a gap answer, wait, Ångra; reload and Ångra still works.

## Stop Conditions

Stop and ask the user if a per-question history turns out to be needed (Q1 option b), or if a visible draft state cannot share the save-state slot without moving its neighbours.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| U1  | The question editor toolbar gets its own Ångra and Gör om for the steps taken in that editing area, text and item edits (user 2026-10-19, staging test) |
| U2  | Continuous autosave in the item editor: every add, remove or change is saved after a debounce, not only on Spara (user 2026-10-19, staging test) |
| F1  | There is no editor-local undo; Ctrl/Cmd+Z in an editor, the window handler outside editables and the top-bar Ångra and Gör om all run the one workspace history |
| F2  | Every edit is stored on the server as an undo step, typing after a 900 ms pause and structural edits at once, at most 10 steps after the import baseline; the guest store writes each command to IndexedDB at once |
| F3  | The header save state reads Osparat until Spara even after steps are stored; the draft wording is only in its tooltip |
| F4  | Gap popover answer rows and dropdown option text are stored only on change, blur or Escape; adding a criterion is recorded as typing, not as a structural step |
