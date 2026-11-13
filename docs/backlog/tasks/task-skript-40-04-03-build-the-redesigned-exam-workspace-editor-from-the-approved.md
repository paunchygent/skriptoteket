---
type: task
id: TASK-SKRIPT-40-04-03
title: Build the redesigned exam workspace editor from the approved prototype
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
  decided_at: '2026-10-18'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer session 0ff04626 (rereview b5338e7a, f2379108; retained session 01a149c9-5bc7-7713-ba64-12dee0470bdd, evidence/reviews/TASK-SKRIPT-40-04-03/review-1.md..review-3.md): review-3 clears the high R2-F1 saved-position finding and requests only one medium fixture repair (two integration tests seeded malformed container bytes, failing identically on main). That repair landed in 9f3ec452 and, as a medium finding, was admitted by the parent on focused checks without rereview. Merged to main 10eef9fd; affected frontend Vitest 1896 passed, vue-tsc, ESLint, backend lint and typecheck clean. The parent''s staging walk on 10eef9fd on 2026-10-18 passed: fresh Svenska 2 import, edit, Spara, undo/redo, reopen and undo (evidence/staging-walk-10eef9fd/walk.md).'
task_kind: story
acceptance_criteria:
  - A teacher imports, edits, saves, undoes and exports an exam in the one-editor workspace from the approved prototype, with every current workspace feature and the planned controls working against their backends
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

An Opus builder implements the exam workspace editor from the prototype the
user approved in TASK-SKRIPT-40-04-01, in parallel with TASK-SKRIPT-40-04-02.
The workspace keeps every current feature and gains every planned control in
ST-SKRIPT-40-04's list, each wired to its backend as that backend lands. This
task changes no backend; Sol lanes own the backends.

This task delivers:

- The workspace view and its components rebuilt to the approved prototype and
  its design rules, on phone, tablet and desktop, using the shared components
  and buttons from TASK-SKRIPT-40-01-02 and TASK-SKRIPT-40-01-03.
- **Save model.** The editor autosaves shortly after each change, and each
  autosave is one undo step. Spara is a durable overwrite of the open exam;
  one file per exam, with no Spara version history. Spara som asks for a name
  prefilled '<name> (kopia)', copies questions, course and tags, starts its
  own empty undo history and opens the copy. Ctrl+S (Cmd+S on Mac) runs Spara
  instead of the browser's save-page.
- **Undo and redo.** At most 10 steps, with Ctrl+Z and Ctrl+Shift+Z (Cmd on
  Mac). The history is stored on the server, survives reload and reopening,
  continues past a Spara, and drops steps older than the tenth.
- **Öppna drawer.** The exam list grouped by course, newest first, with a sort
  toggle and 'Utan kurs' for exams without a course, on the exam index from
  TASK-SKRIPT-39-08-04.
- **Import box.** The question's original wording plus a few readable steps
  (chosen type, answer-key source, retries) for DOCX and DigiExam imports,
  from TASK-SKRIPT-39-04-06.
- **Question structure and types.** 'Ny uppgift' and '+ Deluppgift', and
  adding, deleting and reordering the questions inside an instruction
  (TASK-SKRIPT-39-06-03); dropdown Lucktext with an own option list per gap
  and one correct option marked as the key (TASK-SKRIPT-39-06-04); change type
  carrying over text and points, with a visible notice naming the dropped
  content and one undo restoring it (TASK-SKRIPT-39-06-05); 'Gör om till
  [type]' for a stored suggested type (TASK-SKRIPT-39-06-06). An ordering
  control only if TASK-SKRIPT-39-06-02 records that ordering is built.
- **DigiExam entry.** The DigiExam import (TASK-SKRIPT-39-07-01), with answer
  keys through the per-question suggestions (TASK-SKRIPT-39-07-02).
- **Course and tags.** 'Lägg till i mina kurser' on a picked course
  (TASK-SKRIPT-39-08-02) and the content tags checklist
  (TASK-SKRIPT-39-08-03).
- **Exports in Mina filer.** One saved file per format per exam, replaced on
  the next save and shown next to the exam (TASK-SKRIPT-39-04-08).
- The Opus lead checks the built workspace screens against the prototype.

TASK-SKRIPT-39-04-05's terms C1-C26 hold only where the approved prototype
keeps them. Three are replaced: C2 (frontend-only with its dependency list)
by this task's dependencies, C3 (visual target) by the approved prototype, and
C25 (each autosave a new version) by the save model above.

## Contract Inputs

- Story: ST-SKRIPT-40-04 and its list of controls. Approved prototype and
  design rules from TASK-SKRIPT-40-04-01.
- Superseded contract: TASK-SKRIPT-39-04-05 (C1-C26).
- Shared components and buttons: TASK-SKRIPT-40-01-02 and
  TASK-SKRIPT-40-01-03.
- Backends, wired as each lands: TASK-SKRIPT-39-04-06, TASK-SKRIPT-39-04-08,
  TASK-SKRIPT-39-06-03 to TASK-SKRIPT-39-06-06, TASK-SKRIPT-39-07-01,
  TASK-SKRIPT-39-07-02 and TASK-SKRIPT-39-08-02 to TASK-SKRIPT-39-08-04.
- Backend for the server-stored undo history, the Spara overwrite and Spara
  som: TASK-SKRIPT-39-04-08, which owns the save model (G13, G15-G18, G28).
- Code: `frontend/apps/skriptoteket/src/views/apps/ExamWorkspaceView.vue`,
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/` and the
  composables `useExamWorkspaceDocument`, `useExamWorkspaceConversion`,
  `useExamWorkspaceEnrichment` and `useExamWorkspaceExports`. API root
  `/api/v1/apps/documents.conversion_hub/exam-workspace`.
- Visual authority: the huleedu-ui-design skill and the shared
  huleedu-integrated tokens.

## Core Vertical And Performance

One teacher session on Hemma staging at phone, tablet and desktop widths: open
an exam from the Öppna drawer grouped by course, open the Import box on a
question, change its type and see the notice naming the dropped content, undo
it with Ctrl+Z and redo it with Ctrl+Shift+Z, add a '+ Deluppgift', press
Ctrl+S, reload and undo a step from before the reload, run Spara som and see
the copy open with an empty undo history, and save a QTI export to Mina filer.
Each planned control whose backend has landed is walked once.

Performance, carried from TASK-SKRIPT-39-04-05: moving between questions with
the arrow keys and opening the Import box re-render only the affected rows and
the editor, not the whole list.

## Validation

- Focused Vitest specs through `pdm run fe-test` for the changed components
  and composables, written adversarially: the undo history holds at most 10
  steps and drops the oldest, Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z move through it,
  the history continues past a Spara, Ctrl/Cmd+S runs Spara and suppresses the
  browser's save-page, Spara som prefills '<name> (kopia)' and starts an empty
  history, a change of type shows the notice naming the dropped content and
  one undo restores it, and the Öppna drawer groups by course, sorts newest
  first and lists 'Utan kurs'.
- `pdm run fe-type-check` and `pdm run fe-build`.
- A real browser walk of the core vertical on Hemma staging at phone, tablet
  and desktop widths.
- The Opus lead's check of the built screens against the approved prototype.

## Stop Conditions

- The prototype is not approved, or TASK-SKRIPT-40-01-02 or
  TASK-SKRIPT-40-01-03 is not done.
- A control needs a backend change that no listed task owns: report to the
  parent.
- The approved prototype does not settle a control the build needs: report
  to the Opus lead.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                       |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W1  | The workspace is built from the user-approved prototype with the approved looks (sizes, colour, type); TASK-SKRIPT-39-04-05's terms hold only where the approved prototype keeps them (user 2026-10-17, G1).                |
| W2  | This task builds every new workspace control; the Sol lanes ship backend, data, API and export only (user 2026-10-17, G2).                                                                                                  |
| W3  | The Öppna drawer is the exam list with course grouping, newest first, a sort toggle and 'Utan kurs'; TASK-SKRIPT-39-08-04 ships the exam index backend only (user 2026-10-17, G4).                                          |
| W4  | An Opus builder builds the workspace in parallel with the shell build; the Opus lead checks its screens against the prototype (user 2026-10-17, G10).                                                                       |
| W5  | Undo and redo hold at most 10 steps with Ctrl+Z and Ctrl+Shift+Z (Cmd on Mac); each autosave is one step, stored on the server so the history survives reload and reopening; older steps are pruned (user 2026-10-17, G13). |
| W6  | Ctrl+S (Cmd+S on Mac) runs Spara and replaces the browser's save-page (user 2026-10-17, G14).                                                                                                                               |
| W7  | Spara is a durable overwrite of the open exam and Spara som creates a separate copy; one file per exam and no Spara version history (user 2026-10-17, G15).                                                                 |
| W8  | The undo history continues past a Spara (user 2026-10-17, G16).                                                                                                                                                             |
| W9  | Spara som asks for a name prefilled '<name> (kopia)', copies questions, course and tags, starts its own empty undo history and opens the copy (user 2026-10-17, G17).                                                       |
| W10 | Exports saved to Mina filer are one file per format per exam, replaced on the next save and shown next to the exam (user 2026-10-17, G18).                                                                                  |
| W11 | The Import box shows the original wording plus a few readable steps (chosen type, answer-key source, retries) for DOCX and DigiExam imports alike (user 2026-10-17, G19).                                                   |
| W12 | Change type carries over question text and points, drops unfit content with a visible notice naming it, and one undo restores it (user 2026-10-17, G20).                                                                    |
| W13 | DigiExam imports use the workspace's per-question review and AI answer-key suggestions (user 2026-10-17, G21).                                                                                                              |
| W14 | Dropdown Lucktext has its own option list per gap with one correct option marked as the key (user 2026-10-17, G23).                                                                                                         |
| W15 | The ordering control is built only if the user decides so from the TASK-SKRIPT-39-06-02 screenshots; if built it is all-or-nothing with a default of 1 point, editable (user 2026-10-17, G24).                              |
| W16 | 'Ny uppgift' creates a standalone question or an instruction and '+ Deluppgift' adds a question inside it; 'Gör om till [type]' converts a question to its stored suggested type (ST-SKRIPT-39-06 P13, P15).                |
