---
type: task
id: TASK-SKRIPT-40-04-01
title: Opus prototype of the app shell and the exam workspace covering every current and planned workspace control
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: done
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User approved the prototype on 2026-10-17 (user approval 2026-10-17) after settling its 23 open questions in the 2026-10-17 grilling (T6-T28) and the touch hint (T29); screenshots in docs/mockups/app-shell-and-exam-workspace-redesign/screenshots/, walk logs in session 01a149c9-5bc7-7713-ba64-12dee0470bdd evidence/assignments/efba92b2-aa85-44bf-844e-618697d8037e/walk/.
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

## Closeout Evidence

- The user approved the prototype on 2026-10-17
  (`agent-planning:user-closure-gate`, user approval 2026-10-17), after
  settling its 23 open questions (T6–T28) and the touch hint (T29).
- The prototype and its 117 screenshots are in
  `docs/mockups/app-shell-and-exam-workspace-redesign/`; the design rules are
  in REF-SKRIPT-MOCKUP-app-shell-and-exam-workspace-redesign-prototype.
- A headed Chrome walk passed 51 of 51 core-vertical checks at 1440, 834 and
  390 px, and 60 of 60 reserved-Ordning checks (20 per width). The logs are in
  retained session `01a149c9-5bc7-7713-ba64-12dee0470bdd`,
  `evidence/assignments/efba92b2-aa85-44bf-844e-618697d8037e/walk/`.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | The first task of the story is an Opus prototype of the shell and the workspace covering today's workspace plus the planned 39-06, 39-07 and 39-08-04 UI; the user approves it; the approved looks (sizes, colour, type) carry over (user 2026-10-17, G1, G5).                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| T2  | The prototype covers the app shell (top bar, sidebar, page frame) and the exam workspace only (user 2026-10-17, G9).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| T3  | One Opus lead makes the prototype and owns the design rules (user 2026-10-17, G10).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| T4  | The shell and the exam workspace are frozen except for bug fixes while they are prototyped and built (user 2026-10-17, G6).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| T5  | The prototype shows an ordering control only after the user decides from the TASK-SKRIPT-39-06-02 screenshots that ordering is built (user 2026-10-17, G24).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| T6  | The six type names are Fritext, Flerval: ett val, Flerval: flera val, Lucktext, Lucktext med rullista and Kategorisera; Kort svar stays a Lucktext preset with one gap, listed in Ny uppgift, not a seventh type (user 2026-10-17 grilling, Q1).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| T7  | Ny uppgift offers 'Instruktion med deluppgifter' as its last item, set apart from the types; deleting a whole instruction is not offered for now, and if added later it goes in the instruction's ⋮ menu as 'Ta bort instruktionen och deluppgifterna' with one Ångra restoring it (user 2026-10-17 grilling, Q2).                                                                                                                                                                                                                                                                                                                                                                                                                  |
| T8  | The last deluppgift's delete button is disabled with the tooltip 'En instruktion behöver minst en deluppgift'; no error message after a click (user 2026-10-17 grilling, Q3).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| T9  | A new rullista gap starts with two empty options, the first as the key, marked by a 'Rätt svar' chip; the empty options block export until filled in (G25) (user 2026-10-17 grilling, Q4).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| T10 | The change-type notice is a toast that stays until closed or replaced by another edit, worded 'Bytte till X. Borttaget: …' with Ångra, naming the dropped content in plain Swedish ('4 svarsalternativ och facit', '2 luckor', 'rutnätet') (user 2026-10-17 grilling, Q5).                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| T11 | Marking a question reviewed hides its 'Gör om till X' offer; there is no separate dismiss button (user 2026-10-17 grilling, Q6).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| T12 | One Provfil drop zone names both .docx and .dxe; questions that could not be imported get an info note on the exam's row in the exam list, such as 'Fråga 7 importerades inte: "Put the events …" (sortering).' (user 2026-10-17 grilling, Q7).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| T13 | The Import box is collapsed by default and opened with Import in the question header; its steps are short facts ('Typ: Flerval: ett val', 'Facit: tolkat av AI ur facittexten', 'Skickades om en gång: Fritext → Flerval: ett val'); Konvertera igen sits inside the box with a type select (user 2026-10-17 grilling, Q8).                                                                                                                                                                                                                                                                                                                                                                                                         |
| T14 | Copy: name taken 'Det finns redan ett prov med det namnet i Mina filer.'; export file name is the exam title without punctuation plus the extension; the label 'Spara i Mina filer'; the status texts 'Sparat 17 okt 14:05', 'Osparat' and 'Sparar …'; Spara stays enabled with nothing to save, so Ctrl+S always gives 'Provet är sparat' (user 2026-10-17 grilling, Q9).                                                                                                                                                                                                                                                                                                                                                          |
| T15 | While edits are unsaved, the Öppna drawer's course, drop zone and Välj provfil are disabled with 'Spara det öppna provet innan du importerar eller öppnar ett annat.' (user 2026-10-17 grilling, Q10).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| T16 | 'Läs in på nytt' is dropped; undo with its 10 steps that survive reload replaces it (user 2026-10-17 grilling, Q11).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| T17 | The exam list sorts 'Per kurs' (default) or 'Senaste'; dates read 'Sparad 17 okt 14:05', with the year added only for earlier years (user 2026-10-17 grilling, Q12).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| T18 | Central content is a checklist of the course's items; AI-suggested items are ticked with a Sparkles mark and the questions they rest on ('Fråga 4a, 4b, 4c'); 'Föreslå innehåll' reruns and replaces only the AI-ticked items, never the teacher's own ticks (user 2026-10-17 grilling, Q13).                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| T19 | 'Lägg till i mina kurser' is a link under the picked course in Provets uppgifter; once added it becomes a muted 'I mina kurser' with a check (user 2026-10-17 grilling, Q14).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| T20 | The desktop sidebar toggle collapses the sidebar to the 64 px glyph rail and replaces fokusläge; the workspace does not open in focus mode by default (user 2026-10-17 grilling, Q15).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| T21 | Breakpoints: phone below 768 px, tablet 768–1279 px, desktop 1280 px and wider; the rail is 64 px (user 2026-10-17 grilling, Q16).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| T22 | Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z undo and redo workspace history inside text fields too; a 900 ms typing pause makes one step (user 2026-10-17 grilling, Q17).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| T23 | '+ Alternativ' and the per-option remove button stay; on fine pointers the remove button shows on hover or focus (user 2026-10-17 grilling, Q18).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| T24 | The phone top bar shows the exam title in place of the wordmark, the save status only, Spara and Meny; course and total are shown only in Provets uppgifter (user 2026-10-17 grilling, Q19).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| T25 | Ångra and Gör om sit glyph-only at the right end of the workspace header after a separator; on phone at the right end of the tool row (user 2026-10-17 grilling, Q20).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| T26 | Escape closes the dialog first, then the gap popover, then an open menu, then the drawer (user 2026-10-17 grilling, Q21).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| T27 | The status slot is wide enough for the widest real 'Sparat <date> <time>'; the builders measure the widest real value (long month names such as 'mars' and 'sep') instead of copying the prototype's 11em (user 2026-10-17 grilling, Q22).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| T28 | Ordering gets a reserved place now: a disabled 'Ordning' entry in Byt frågetyp and Ny uppgift that cannot be chosen, is skipped by keyboard navigation, and carries the hint 'Kommer senare' as small muted text beside the entry on every device, linked through aria-describedby, with no tooltip (amended by T29); the entry is removed if the TASK-SKRIPT-39-06-02 decision drops ordering. + Deluppgift, and Byt frågetyp on a deluppgift, omit the entry, because an ordering question is standalone only and never a child of a parent (ST-SKRIPT-39-06 P3, TASK-SKRIPT-39-06-03 P4). This narrows T5: the disabled entry is shown now, a working ordering control only after that decision (user 2026-10-17 grilling, Q23). |
| T29 | The 'Kommer senare' hint on the reserved Ordning entry is small muted text next to the greyed-out entry on every device, linked through aria-describedby; the prototype no longer relies on a tooltip, because touch devices show none (user 2026-10-17, touch hint).                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
