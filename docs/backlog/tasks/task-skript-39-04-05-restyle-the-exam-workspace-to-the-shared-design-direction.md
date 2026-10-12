---
type: task
id: TASK-SKRIPT-39-04-05
title: Restyle the exam workspace to the shared design direction
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-12'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The exam workspace is one editor with drawers that meets terms C1-C24 on phone,
  tablet and desktop, matching REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction
  and REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype
- A live staging walk of the core vertical passes at desktop, tablet and phone widths
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The exam workspace becomes one editor with drawers in the shared design
direction, on phone, tablet and desktop. The Filer and Redigera modes go: the
teacher opens, reviews, corrects, saves and exports an exam without leaving
the editor. The visual target is the approved images in
REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction;
the layout, controls and copy follow the prototype in
REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype. Where the two
differ, the prototype and the terms below win.

This task is frontend-only. It does not change conversion, the export gate
or backend storage; those are owned by TASK-SKRIPT-39-05-07,
TASK-SKRIPT-39-04-06 (import trace) and TASK-SKRIPT-39-04-07 (editor
support) (C2).

- **Page and header.** On desktop and tablet, 'Provredigering' sits after
  the Skriptoteket wordmark in the terracotta token. The workspace header is
  one row: the exam name, then a file group (Öppna, Spara, Exportera), a
  divider and the Sparkles action that suggests keys for every question
  without one. Spara is the only filled action. Below 1100 px the brand
  links show their glyph only. No version number is shown.
- **Question list.** Each row shows the number, the opening of the question
  text, the type and the points, the ai-assist glyph for an AI-interpreted
  question and the review glyph. Questions have no titles. An instruction is
  its own row; its questions sit indented under it and are lettered (4, 4a,
  4b, 4c). Clicking a row or pressing up or down selects the next row, also
  an instruction row; the keys do nothing while focus is in a text field.
- **Question editor.** The heading is 'Fråga 4b' at the exam name's level
  with the type small and muted beside it. The Import control and the review
  check sit in the question header. The fields follow in this order:
  question text, alternatives, Poäng, densely spaced. The question text is
  one continuous text surface. A question under an instruction shows a
  collapsed 'Instruktion till fråga 4' bar above the question text.
- **Instruction editor.** Selecting an instruction shows 'Fråga 4' with
  'Instruktion', the editable instruction text, its questions as links and
  their total points. It has no points or answer fields.
- **Review and blockers.** The review check is a square button that is
  filled when the question is reviewed and undoes the review when pressed
  again. A missing value that blocks export is marked at its own field and
  in the list row. A parsing issue sets 'Behöver granskas' and shows as one
  short line in the Import box; it does not block export.
- **Import box.** Import opens, inline above the fields, the question as
  written in the exam file with any parsing-issue line. It opens with a
  short height and opacity transition, the one exception to the layout
  invariant.
- **Answer keys.** An AI suggestion is written in as the key where the
  question has no key or holds the AI's earlier suggestion, carries the
  ai-assist mark and sets the question to needs review. The teacher can pick
  any option; clicking the mark restores the AI's choice; editing an option
  marks the suggestion out of date at the per-question suggest action.
- **Drawers, export and open.** Öppna holds the .docx import, the exams in
  Mina filer with their exam-level import notes, and 'Läs in på nytt'.
  Exportera opens a quick menu (QTI, PDF, DOCX, a Mina filer save per
  format, 'Fler val …' for the export drawer). When every question is
  reviewed and nothing blocks export, a toast offers Exportera. The
  workspace opens the last exam, or the Öppna drawer when there is none.
- **Sizes.** Desktop is 1100 px and wider, tablet 641-1099 px with floating
  drawers, phone 640 px and narrower with full-screen drawers and list. Phone
  keeps the app's mobile brand bar with a Meny button, a toolbar row and one
  question bar (previous, a picker with the review glyph and 'Fråga N', next,
  Import, review check).
- **Stable layout.** No state change moves, resizes or reflows an element;
  controls keep their size and place in every state. Each surface scrolls
  once, in its own region.

## Contract Inputs

- Story: ST-SKRIPT-39-04. Retained plan: Skriptoteket session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43`, decisions D1-D66.
- Visual authority: integrated-frontend-stack and the huleedu-ui-design
  visual system; tokens from huleedu-integrated 0.1.24 or later.
- Mockups: REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction
  and REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype.
- Shared buttons: TASK-SKRIPT-40-01-03.
- Export gate and parsing issues: TASK-SKRIPT-39-05-07.
- Backend: TASK-SKRIPT-39-04-06 (original wording and build steps) and
  TASK-SKRIPT-39-04-07 (per-question suggestion, suggestion stored apart from
  the key, saving the exam and exported files in Mina filer, automatic QTI
  item title), both under ST-SKRIPT-39-04.
- Code: `frontend/apps/skriptoteket/src/views/apps/ExamWorkspaceView.vue`,
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`, and the
  mobile header in `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`.

## Core Vertical And Performance

The core vertical is one teacher session on staging: open the last exam,
move through the list including an instruction and its lettered questions,
open Import on a question, fix a missing Poäng, accept an AI key by marking
the question reviewed, see the all-reviewed toast and export QTI from the
quick menu, on desktop, tablet and phone.

Performance: moving between questions with the arrow keys and opening the
Import box must not re-render the whole list; selection changes re-render
only the affected rows and the editor.

## Validation

- Focused Vitest specs for the changed components and helpers through
  `pdm run fe-test`, written adversarially: lettered numbering around
  instructions, arrow keys ignored in text fields, AI key written only where
  the key is empty or the AI's own, restore and out-of-date marks, blockers
  at their field, parsing issues not blocking export, no element moving on
  review toggle.
- `pdm run fe-type-check` and `pdm run fe-lint`.
- A live click-through walk of the core vertical on Hemma staging in the
  browser pane at desktop, tablet and phone widths, recorded in `handoff.md`.

## Stop Conditions

- TASK-SKRIPT-40-01-03 and ST-SKRIPT-40-03's first task (the 0.1.24 sync) are
  not done.
- TASK-SKRIPT-39-05-07, TASK-SKRIPT-39-04-06 or TASK-SKRIPT-39-04-07 is not
  done.
- A term needs a backend change, a conversion change or a control the
  terms do not name.
- The approved images and the prototype disagree on something the terms do
  not settle.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| C1  | One editor with drawers replaces the Filer and Redigera modes; the task covers the whole exam workspace on phone, tablet and desktop, but not the old DigiExam converter views (D2, D8, D30). |
| C2  | Frontend-only; it runs after TASK-SKRIPT-40-01-03, ST-SKRIPT-40-03's 0.1.24 sync, TASK-SKRIPT-39-05-07, TASK-SKRIPT-39-04-06 and TASK-SKRIPT-39-04-07 (D1, D3, D8, D53, D62). |
| C3  | Visual target: the approved images with their exclusions; layout, controls and copy follow the editor-drawers prototype (D7, D8). |
| C4  | Spara is the only filled action; the header is one row with a file group (Öppna, Spara, Exportera), a divider and the Sparkles all-keys action, compact 36 px on fine pointers (D6, D43, D44). |
| C5  | 'Provredigering' follows the wordmark in terracotta; brand links show glyph only below 1100 px; on phone a Meny button holds Avsluta fokusläge, Hjälp and Logga ut (D38, D44, D46). |
| C6  | No version number in the header (D12). |
| C7  | No state change moves, resizes or reflows an element; controls never appear or disappear on state change; the Import box transition is the only exception (D11, D27, D41). |
| C8  | Buttons carry a glyph and at most one short word; action wording lives in tooltips and screen-reader names (D28). |
| C9  | The review check is a square button, outlined when the question needs review and filled when reviewed, named 'Markera som granskad' or 'Ångra granskad'; no header status text (D14, D29). |
| C10 | Questions have no titles; list rows show the number and the opening of the question text; the heading is 'Fråga N' with the type small and muted beside it (D59, D64). |
| C11 | An instruction is its own row with its questions indented and lettered (4, 4a, 4b); selecting it edits its text and lists its questions and total, with no points or answer fields; its questions show a collapsed instruction bar; lettering is display only (D24, D60, D61, D66). |
| C12 | No previous and next buttons on desktop and tablet; the list and the up and down keys navigate, ignored in text fields; phone keeps previous and next in its question bar (D39, D46). |
| C13 | Field order: question text, alternatives, Poäng; dense spacing; the question text is one continuous text surface with fixed gap and image chips (D22, D45). |
| C14 | No type hint in the question header, no type caption under the question text and no subtask explanation box (D13, D23, D24). |
| C15 | A missing value that blocks export is marked at its field and in the list row; a parsing issue sets needs review, shows one short line in the Import box and does not block export; 'Frågetypen kan ha tolkats fel.' is the kept-type-conflict line (D40, D56, D57, D58, D65). |
| C16 | Import opens the question as written in the exam file inline above the fields, with missing parts marked 'saknas i frågan' (D21, D41). |
| C17 | AI-interpreted questions show the ai-assist glyph in the list row and phone question bar, named 'AI-tolkad' (D25). |
| C18 | AI key suggestions: written in where the key is empty or the AI's own, ai-assist mark named 'AI-förslag', sets needs review, any option selectable, mark restores the AI's choice, edited options mark the suggestion out of date at the per-question action (D26, D32, D42). |
| C19 | Öppna holds the .docx import, the exams in Mina filer with 'Sparad <datum>' and their exam-level import notes, and 'Läs in på nytt' (D16, D35, D36, D63). |
| C20 | Exportera opens a quick menu with QTI, PDF, DOCX, a Mina filer save per format and 'Fler val …' for the export drawer (D31). |
| C21 | When every question is reviewed and nothing blocks export, a floating toast 'Alla frågor är granskade' offers Exportera (D33). |
| C22 | The workspace opens the last exam, or the Öppna drawer when there is none (D34). |
| C23 | The upload shows a moving indeterminate bar with 'Laddar upp provet …' and 'Läser provet …' before the counted bar (D18). |
| C24 | Desktop ≥ 1100 px, tablet 641-1099 px with floating drawers, phone ≤ 640 px with full-screen drawers and list; phone has one question bar with previous, picker, next, Import and review check (D5, D37, D46). |
