---
type: story
id: ST-SKRIPT-40-04
title: Redesign the app shell and the exam workspace from a fresh Opus prototype
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-28'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user decided on 2026-10-28 (TASK-SKRIPT-REP-0055 D7) to close this story once all its tasks are closed: every child task is terminal. The Closeout section records the evidence.'
epic: EPIC-SKRIPT-40
acceptance_criteria:
  - Teachers use a redesigned app shell and one exam workspace editor built from a user-approved Opus prototype that covers every current workspace feature plus the planned 39-06, 39-07 and 39-08 controls, the Spara/Spara som save model, 100-step undo/redo and keyboard shortcuts
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

This story replaces TASK-SKRIPT-39-04-05. An Opus lead makes a fresh
prototype of the shared app shell (top bar, sidebar, page frame) and the exam
workspace. The user approves it, and Opus builders then implement it. The
greenfield redesign covers only the shell and the exam workspace; every other
screen keeps its layout and gets the shared-token refresh in ST-SKRIPT-40-03.

- **Prototype first.** The prototype covers everything the workspace has
  today plus the planned controls listed below. The approved looks from the
  2026-10-12 images (sizes, colour, type) carry over. The user approves the
  prototype before any build starts.
- **Staffing.** One Opus lead makes the prototype and owns the design rules.
  After approval two Opus builders work in parallel, one on the shell and one
  on the workspace, and the lead checks their screens against the prototype.
  The visible UI design and its implementation are Opus-owned; Sol agents do
  only non-visual work.
- **UI split.** Sol lanes for ST-SKRIPT-39-06, ST-SKRIPT-39-07 and
  ST-SKRIPT-39-08 ship backend, data, API and export only. This story builds
  every new workspace control. The current workspace screens are frozen
  except for bug fixes.
- **Rolling freeze.** Only the area being prototyped or built is frozen, and
  only for bug fixes: the shell and the exam workspace from the start of
  TASK-SKRIPT-40-04-01 until their build lands. Other areas keep shipping UI.

Controls the prototype must show:

- Everything the workspace has today, including the controls missing from the
  earlier prototype: the estimated-points hint and unbuilt-question blocker,
  the exam and part total mismatch signal (`ExamWorkspaceTotalSignal`), the
  course hint, per-question 'Konvertera igen', pictures in questions, undo of
  an AI-interpreted key with the original facit text, 'automatisk'
  misspellings and the 'Visa som text' gap popover, the mark toolbar (bold,
  italic, underline, subscript, superscript, heading), the Kategorisera grid
  with tick points, Fritext criteria, Kort svar under Ny fråga, the export
  checklist after QTI export, the metadata drawer opened from the exam title,
  the course picker at import, the file picker disabled while edits are
  unsaved, and a pending suggestion resumed after reload.
- The Öppna drawer as the exam list: exams grouped by course, newest first, a
  sort toggle, and 'Utan kurs' for exams without a course.
- Spara as a durable overwrite of the open exam and Spara som, which asks for
  a name prefilled '<name> (kopia)', copies questions, course and tags, starts
  its own empty undo history and opens the copy.
- Undo and redo of at most 100 steps with Ctrl+Z and Ctrl+Shift+Z (Cmd on Mac);
  each autosave is one step; the history continues past a Spara.
- Ctrl+S (Cmd+S on Mac) runs Spara instead of the browser's save-page.
- The Import box: the question's original wording plus a few readable steps
  (chosen type, answer-key source, retries), for DOCX and DigiExam imports.
- Change type: question text and points carry over, and a visible notice
  names the content that was dropped; one undo restores it. 'Gör om till
  [type]' for a question with a stored suggested type.
- 'Ny uppgift' and '+ Deluppgift', and adding, deleting and reordering the
  questions inside an instruction.
- Dropdown Lucktext: an own option list per gap with one correct option
  marked as the key.
- The DigiExam import entry.
- The content tags checklist from TASK-SKRIPT-39-08-03.
- 'Lägg till i mina kurser' on a picked course.
- Saving exports to Mina filer: one file per format per exam, replaced on the
  next save and shown next to the exam.
- An ordering question control, only if TASK-SKRIPT-39-06-02 records that
  ordering is built. Until then the workspace offers six question types.

G9 narrows G5: areas outside the shell and the exam workspace keep their
layout and need no prototype.

Out of scope: the layout of every screen other than the shell and the exam
workspace (ST-SKRIPT-40-03), and the backends of the planned controls, which
their own tasks own.

## Contract Inputs

- User decisions 2026-10-17 G1-G24 and lead decision L6, retained session
  `01a1495e-8398-75be-b2da-f0b08ba11afa`, `evidence/planning/decisions-2026-10-17.md`;
  discovery facts in `evidence/discovery/planning-facts-2026-10-17.md`.
- Superseded contract: TASK-SKRIPT-39-04-05 (C1-C26).
- Approved looks:
  REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction
  (`docs/mockups/exam-workspace-shared-direction/approved/`). Earlier
  prototype: REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype
  (`docs/mockups/exam-workspace-editor-drawers/`).
- Shared components and buttons: TASK-SKRIPT-40-01-02 and TASK-SKRIPT-40-01-03.
- Backends the workspace build consumes: TASK-SKRIPT-39-04-06 (original
  wording and build steps), TASK-SKRIPT-39-04-08 (the save model: server-stored undo history, Spara,
  Spara som and exports in Mina filer),
  TASK-SKRIPT-39-06-03 to TASK-SKRIPT-39-06-06 (parent and child commands,
  dropdown Lucktext, change type, suggested type), TASK-SKRIPT-39-07-01
  (DigiExam import), TASK-SKRIPT-39-08-02 to TASK-SKRIPT-39-08-04 (own
  courses, content tags, exam index).
- ST-SKRIPT-39-06 terms P13 and P15 for 'Ny uppgift', '+ Deluppgift' and
  'Gör om till [type]'.
- Shell code: `frontend/apps/skriptoteket/src/App.vue` and
  `frontend/apps/skriptoteket/src/components/layout/` (`AuthLayout.vue`,
  `AuthTopBar.vue`, `AuthSidebar.vue`, `LandingLayout.vue`). Workspace code:
  `frontend/apps/skriptoteket/src/views/apps/ExamWorkspaceView.vue` and
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`.

## Tasks

01. TASK-SKRIPT-40-04-01: Opus prototype of the app shell and the exam
    workspace covering every current and planned workspace control. Needs
    nothing to start; the user's approval is the gate for the other two tasks.
02. TASK-SKRIPT-40-04-02: build the redesigned app shell from the approved
    prototype. Needs the approved prototype, TASK-SKRIPT-40-01-02 and
    TASK-SKRIPT-40-01-03.
03. TASK-SKRIPT-40-04-03: build the redesigned exam workspace editor from the
    approved prototype. Needs the approved prototype, TASK-SKRIPT-40-01-02 and
    TASK-SKRIPT-40-01-03, and wires each planned control to its backend as
    that backend lands. TASK-SKRIPT-39-07-03 retires the old exam converter
    after this task offers the DigiExam import.
04. TASK-SKRIPT-40-04-04: teachers edit a dropdown gap's options and mark the
    correct one in the gap popover.
05. TASK-SKRIPT-40-04-05: exported files are named after the exam title
    (in progress: on main, review, walk and closeout owed).
06. TASK-SKRIPT-40-04-06: exam texts edit as one document per field, exam
    instructions are editable and printed totals can be accepted.
07. TASK-SKRIPT-40-04-07: teachers set the writing area of printed DOCX and PDF
    exams and imports drop paper answer lines.
08. TASK-SKRIPT-40-04-16: each export format downloads or saves to Mina filer
    from one split button at the right of its menu row (done).
09. TASK-SKRIPT-40-04-17: the workspace header and toolbars share one compact
    control system with an autosave status, file commands and a gap switch
    (done 2026-10-19: main aac5bdfd and 32460f67, staging walks passed).
10. TASK-SKRIPT-40-04-18: the header opens Provets uppgifter from an Uppgifter
    command, and free-text questions set their writing area and criteria in
    one boxless answer block (done 2026-10-20: main 98cbab6c, staging walk passed).
11. TASK-SKRIPT-40-04-08: short-answer and gap-text questions look different and
    gaps are made by clicking a word (done).
12. TASK-SKRIPT-40-04-09: the gap tool and the toolbar's shortcut names (in
    progress: on main, F1 rereview, R14 Exam.net check and closeout owed).
13. TASK-SKRIPT-40-04-10: a printed-total difference shows in one line (done
    2026-10-20: main 0d928d3a, staging walk passed, user closure).
14. TASK-SKRIPT-40-04-11: one compact three-tier control system (canceled;
    replaced by TASK-SKRIPT-40-04-17).
15. TASK-SKRIPT-40-04-12: printed PDF exams keep each question's text and its
    alternatives on one page (in progress: on main, K11 walk passed, K7 "/"
    check and closeout owed).
16. TASK-SKRIPT-40-04-13: a click on a gap turns it back into its words and one
    gap control replaces Lucka (done).
17. TASK-SKRIPT-40-04-14: the question editor has its own Ångra and Gör om and
    every edit autosaves (done).
18. TASK-SKRIPT-40-04-15: printed PDF exams show each question's points as
    (N p) (done).
19. TASK-SKRIPT-40-04-19: two tabs holding exam locks stop invalidating each
    other's CSRF token (proposed; the user owns proposed to ready).
20. TASK-SKRIPT-40-04-20: printed exams and the editor keep imported text
    formatting (done).
21. TASK-SKRIPT-40-04-21: a new exam starts from Nytt prov in the workspace
    toolbar (done 2026-10-22: staging walks passed at `25c4ac01`, `18f045fc`
    and `ede1ea0d`, user closure).
22. TASK-SKRIPT-40-04-22: signing out shows no saved exam list error (done).
23. TASK-SKRIPT-40-04-23: after an import the question list warns about
    questions whose points differ from the source (done 2026-10-22: main
    `ede1ea0d`, staging walk passed, user closure).

Tasks 2 and 3 run in parallel.

## Verification

The story closes when the user has approved the prototype, both build tasks
pass their focused checks and a real browser walk at phone, tablet and
desktop widths, and the Opus lead has checked the built shell and workspace
screens against the approved prototype.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | A new story replaces TASK-SKRIPT-39-04-05; its first task is an Opus prototype that the user approves before Opus implements it; the approved looks (sizes, colour, type) carry over (user 2026-10-17, G1).                                                                                       |
| R2  | Sol lanes ship backend, data, API and export only; this story builds every new workspace control; the current workspace screens are frozen except for bug fixes (user 2026-10-17, G2).                                                                                                            |
| R3  | The greenfield redesign covers the app shell (top bar, sidebar, page frame) and the exam workspace only; every other screen keeps its layout and gets the ST-SKRIPT-40-03 refresh (user 2026-10-17, G3 narrowed by G9).                                                                           |
| R4  | The Öppna drawer is the exam list, with course grouping, newest first, a sort toggle and 'Utan kurs'; TASK-SKRIPT-39-08-04 ships the exam index backend only (user 2026-10-17, G4).                                                                                                               |
| R5  | The shell and the exam workspace are prototyped together first, approved by the user, then built (user 2026-10-17, G5).                                                                                                                                                                           |
| R6  | The freeze is rolling: only the area being prototyped or built is frozen, for bug fixes only (user 2026-10-17, G6).                                                                                                                                                                               |
| R7  | ST-SKRIPT-39-06 and ST-SKRIPT-39-07 UI requirements go to this story's prototype; their backend tasks go to Sol lanes (user 2026-10-17, G8).                                                                                                                                                      |
| R8  | One Opus lead makes the prototype and owns the design rules; after approval two Opus builders build the shell and the workspace in parallel; the lead checks their screens against the prototype; Sol agents do only non-visual work (user 2026-10-17, G10 and standing decision).                |
| R9  | Undo and redo hold at most 100 steps with Ctrl+Z and Ctrl+Shift+Z (Cmd on Mac); each autosave is one step, stored on the server so the history survives reload and reopening; older steps are pruned (user 2026-10-17, G13; raised from 10 to 100 steps by the user in TASK-SKRIPT-40-04-14, Q6). |
| R10 | Ctrl+S (Cmd+S on Mac) runs Spara and replaces the browser's save-page (user 2026-10-17, G14).                                                                                                                                                                                                     |
| R11 | Spara is a durable overwrite of the open exam; Spara som creates a separate copy edited on its own; one file per exam and no Spara version history (user 2026-10-17, G15).                                                                                                                        |
| R12 | The undo history continues past a Spara (user 2026-10-17, G16).                                                                                                                                                                                                                                   |
| R13 | Spara som asks for a name prefilled '<name> (kopia)', copies questions, course and tags, starts its own empty undo history and opens the copy (user 2026-10-17, G17).                                                                                                                             |
| R14 | Exports saved to Mina filer are one file per format per exam, replaced on the next save and shown next to the exam (user 2026-10-17, G18).                                                                                                                                                        |
| R15 | The Import box shows the original wording plus a few readable steps (chosen type, answer-key source, retries) for DOCX and DigiExam imports alike (user 2026-10-17, G19).                                                                                                                         |
| R16 | Change type carries over question text and points, drops unfit content with a visible notice naming it, and one undo restores it (user 2026-10-17, G20).                                                                                                                                          |
| R17 | Dropdown Lucktext has its own option list per gap with one correct option marked as the key (user 2026-10-17, G23).                                                                                                                                                                               |
| R18 | The ordering control is built only if the user decides so from the TASK-SKRIPT-39-06-02 screenshots; until then the workspace offers six question types; if built it is all-or-nothing with a default of 1 point, editable (user 2026-10-17, G24).                                                |
| R19 | 'Ny uppgift' creates a standalone question or an instruction and '+ Deluppgift' adds a question inside it; 'Gör om till [type]' converts a question to its stored suggested type (ST-SKRIPT-39-06 P13, P15).                                                                                      |
| R20 | G9 narrows G5: areas outside the app shell and the exam workspace keep their layout and need no prototype (lead 2026-10-17, L6).                                                                                                                                                                  |
| D1  | Closed as done on 2026-10-28 because every child task is terminal (user decision, TASK-SKRIPT-REP-0055 D7).                                                                                                                                                                                       |

## Closeout

ST-SKRIPT-40-04 is closed. The app shell and exam workspace were rebuilt from the prototype the user approved on 2026-10-17 (40-04-01, merge 4ab165fc4; builds 40-04-02 and 40-04-03), and 22 follow-up tasks added the gap tool, split export button, three-tier controls, header and toolbars, Spara/Spara som, Ctrl+S and Ctrl+Z; 40-04-11 was canceled. Undo and redo keep 100 steps (`MAX_RETAINED_UNDO_STEPS = 100` in `src/skriptoteket/application/curated_apps/exam_workspace_history.py:32`, user decision Q6 in 40-04-14), so the story criterion now reads "100-step". Browser behaviour rests on the child task walks, not on a walk in this check.
