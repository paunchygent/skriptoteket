---
type: task
id: TASK-SKRIPT-40-04-01
title: Opus prototype of the app shell and the exam workspace covering every current and planned workspace control
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The user approves an Opus-made prototype of the app shell and the exam workspace that shows every current workspace feature and every planned control listed in ST-SKRIPT-40-04
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The Opus lead makes a fresh interactive prototype of the shared app shell (top
bar, sidebar, page frame) and the exam workspace, and the user approves it.
The approved prototype is the build target for TASK-SKRIPT-40-04-02 and
TASK-SKRIPT-40-04-03.

This task delivers:

- A new mockup folder beside `docs/mockups/exam-workspace-editor-drawers/`,
  holding the interactive prototype with static Swedish example data. It
  starts from the earlier editor-drawers prototype and the approved
  2026-10-12 images; their approved looks (sizes, colour, type) carry over.
- The shell at phone, tablet and desktop widths: top bar, sidebar and page
  frame, with the exam workspace inside it.
- The exam workspace showing every current workspace feature and every
  planned control in ST-SKRIPT-40-04's list, including Spara and Spara som,
  10-step undo and redo with its keyboard shortcuts, Ctrl+S, the Öppna drawer
  exam list and the import box.
- The design rules the two builders follow, owned by the lead. When the
  folder needs a reference doc for the rules and the package manifest, the
  lead creates it with `pdm run new-doc --type reference` as a
  `reference_kind: mockup` doc.

The lead does not change application code in this task.

## Contract Inputs

- Story: ST-SKRIPT-40-04 and its list of controls; user decisions G1-G24 in
  session `01a1495e-8398-75be-b2da-f0b08ba11afa`, `evidence/planning/decisions-2026-10-17.md`.
- Earlier prototype:
  REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype
  (`docs/mockups/exam-workspace-editor-drawers/`: `prototype.html`,
  `styles.css`, `tokens.css`).
- Approved looks:
  REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction
  (`docs/mockups/exam-workspace-shared-direction/approved/`).
- Current workspace components, including those absent from the earlier
  mockups: `ExamWorkspaceCriteriaField`, `ExamWorkspaceKategoriseraGrid`,
  `ExamWorkspaceMarkToolbar`, `ExamWorkspaceGapPopover`,
  `ExamWorkspaceMetadataDrawer`, `ExamCourseCombobox`,
  `ExamWorkspaceTotalSignal` and `useExamWorkspaceItemRetry`, under
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`.
- Current shell: `frontend/apps/skriptoteket/src/components/layout/`
  (`AuthLayout.vue`, `AuthTopBar.vue`, `AuthSidebar.vue`, `LandingLayout.vue`).
- Planned-control contracts: ST-SKRIPT-39-06 (P13, P15), TASK-SKRIPT-39-06-02
  to TASK-SKRIPT-39-06-06, TASK-SKRIPT-39-07-01, TASK-SKRIPT-39-08-02 to
  TASK-SKRIPT-39-08-04, TASK-SKRIPT-39-04-06 and TASK-SKRIPT-39-04-08.
- Visual authority: the huleedu-ui-design skill and the shared
  huleedu-integrated tokens.

## Core Vertical And Performance

The user opens the served prototype and walks one teacher session at phone,
tablet and desktop widths: open an exam from the Öppna drawer grouped by
course, open the Import box on a question, change its type and see the
dropped-content notice, undo it with Ctrl+Z, add a '+ Deluppgift', set a
dropdown Lucktext gap's options, press Ctrl+S, run Spara som, and save a QTI
export to Mina filer.

## Validation

- The lead serves the prototype with
  `python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/mockups` and
  opens it in a real browser at phone, tablet and desktop widths, checking
  that every control in ST-SKRIPT-40-04's list is present.
- The user approves the prototype; the approval and its date are recorded in
  this task.

## Stop Conditions

- A planned control's contract is unsettled in a way the prototype must show
  (for example ordering before TASK-SKRIPT-39-06-02 has a user decision): the
  prototype shows the settled controls and the lead reports the open one to
  the user.
- The approved images and the earlier prototype disagree on something the
  story terms do not settle: report to the user.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                          |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | The first task of the story is an Opus prototype of the shell and the workspace covering today's workspace plus the planned 39-06, 39-07 and 39-08-04 UI; the user approves it; the approved looks (sizes, colour, type) carry over (user 2026-10-17, G1, G5). |
| T2  | The prototype covers the app shell (top bar, sidebar, page frame) and the exam workspace only (user 2026-10-17, G9).                                                                                                                                           |
| T3  | One Opus lead makes the prototype and owns the design rules (user 2026-10-17, G10).                                                                                                                                                                            |
| T4  | The shell and the exam workspace are frozen except for bug fixes while they are prototyped and built (user 2026-10-17, G6).                                                                                                                                    |
| T5  | The prototype shows an ordering control only after the user decides from the TASK-SKRIPT-39-06-02 screenshots that ordering is built (user 2026-10-17, G24).                                                                                                   |
