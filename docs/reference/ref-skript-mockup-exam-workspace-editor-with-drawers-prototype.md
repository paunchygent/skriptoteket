---
type: reference
id: REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype
title: Exam workspace editor with drawers prototype
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-13'
status: draft
reference_kind: mockup
summary: Interactive prototype of the exam workspace as one editor with drawers, inline
  import view, instructions and lettered sub-questions
---

## Intent

Decision material for TASK-SKRIPT-39-04-05. The teacher reviews and corrects
an imported exam in one editor: the question list on the left, the selected
question on the right, and Öppna and Exportera as drawers instead of separate
Filer and Redigera modes. It replaces the Filer view and mode selector in the
approved images (REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction);
their other appearance decisions still apply.

## Package Manifest

Files live in `docs/mockups/exam-workspace-editor-drawers/`:

| File | Role |
| --- | --- |
| `prototype.html` | The interactive prototype: markup, static Swedish example data, script and an inline Lucide sprite. |
| `styles.css` | Shared layout styles. |
| `tokens.css` | A copy of the huleedu-integrated 0.1.24 design tokens. |
| `desktop-editor.png` | Desktop preview at 1440 x 900 with question 3 selected. |

Serve `docs/mockups` and open `exam-workspace-editor-drawers/prototype.html`:

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/mockups
```

## Design Interpretation

Desktop is 1100 px and wider, tablet 641-1099 px (drawers float over the
editor), phone 640 px and narrower (drawers and the question list are full
screens with Tillbaka). Binding behaviour to try:

- The header is one row: exam name, then Öppna, Spara and Exportera as one
  group and the Sparkles button that suggests answer keys for every question
  without one. 'Provredigering' sits beside the wordmark in terracotta. Below
  1100 px the brand links show their glyph only; on phone they move into a
  Meny button.
- The up and down arrow keys move between list rows; the editor has no
  previous and next buttons. On phone a question bar has previous, next, a
  picker that opens the list, and the question's Import and review buttons.
- Questions have no titles. The list shows the number and the opening of the
  question text; the editor heading is 'Fråga N' with the type beside it.
- Question 4 is an instruction (an Exam.net parent) with questions 4a-4c
  indented under it. Selecting the instruction edits its text and lists its
  questions with their total; it has no points or answer fields. A question
  under an instruction shows a collapsed 'Instruktion till fråga 4' bar above
  Frågetext that opens to the full text and 'Redigera instruktionen'.
- The editor order is Frågetext, Alternativ, Poäng, densely spaced.
- A suggested key is written in, marked with Sparkles, and puts the question
  in Behöver granskas; marking it reviewed accepts it. Clicking an option
  makes it the key; clicking the Sparkles mark restores the AI's choice.
  Editing an option's wording marks the suggestion out of date with a dot on
  the Alternativ Sparkles button, which suggests a key again.
- A value that blocks export is marked at its own field: question 6 has no
  points, so its Poäng field shows 'Saknas' and its list row 'poäng saknas'.
- Import in the question header opens the question as written in the exam
  file, inline above the fields with a short transition, with any import note
  below it.
- Reviewing questions 3 and 6 shows the all-reviewed toast; its Exportera
  opens the export quick menu. A menu row downloads that format, its folder
  glyph saves it in Mina filer, and Fler val … opens the export drawer.

Illustrative only: the example questions, file names and the export drawer's
options (format, file name and destination; further options are undecided).
Proposals beyond the plan: an `open-files` shared glyph (Lucide FolderOpen)
for Öppna, and the per-format Mina filer glyph in the quick menu.

## Runtime And Proof Boundary

The prototype is static with no backend and proves no runtime behaviour.
Suggestions stored apart from the key (D42), the per-question suggestion
endpoint and saving to Mina filer need backend tasks. Runtime acceptance is
the Hemma staging walk owned by TASK-SKRIPT-39-04-05.

## Governing Links And Follow-Up

- TASK-SKRIPT-39-04-05 implements this; its retained plan holds decisions
  D30-D46 and D59-D61 for this prototype and D47-D58 for blockers and parsing
  issues (Skriptoteket retained session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43`).
- REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction
  holds the approved appearance this prototype builds on.
