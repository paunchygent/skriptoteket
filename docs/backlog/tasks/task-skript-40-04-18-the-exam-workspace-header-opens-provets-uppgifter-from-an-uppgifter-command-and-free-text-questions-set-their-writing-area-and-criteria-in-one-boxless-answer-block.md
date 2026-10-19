---
type: task
id: TASK-SKRIPT-40-04-18
title: The exam workspace header opens Provets uppgifter from an Uppgifter command
  and free-text questions set their writing area and criteria in one boxless answer
  block
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-20'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The exam workspace header shows an Uppgifter command (info glyph and the word) first in the toolbar, before a separator and Öppna; it opens and closes the Provets uppgifter drawer, shows aria-expanded, and the course and points line under the title is plain text
- A free-text question shows Skrivyta and Bedömningskriterier as rows of one bordered answer block with a shared label column; the stepper, trash and add controls have no box, the line count sits in a fixed-width slot, and no row leaves a wide empty space at its right
- Alla fritextfrågor opens a popover that names how many free-text questions get the count and which ones have another count today, with Avbryt and Använd N rader; when every free-text question already has the count, the popover says so and offers Stäng; nothing in the row moves or changes size between the two states
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

On 2026-10-19 the user saw two problems in the exam workspace on staging (main 54e9c5db). The Provets uppgifter drawer has no visible entry: only the course and points line under the title opens it. The free-text controls put a box around every glyph button, leave a wide empty space to the right of the Skrivyta row, show "Använd för alla fritextfrågor" as a grey disabled button, and let the Bedömningskriterier label collide with the row above. The user asked for mockups, and on 2026-10-20 approved the mockup `docs/mockups/exam-workspace-details-and-writing-area/` (prototype.html, desktop-1440.png) and chose the recommended answer to each question (Q1-Q4, `agent-planning:user-closure-gate`).

1. Uppgifter command (Q1). `ExamWorkspaceHeader.vue` gains a header command in the `.xw-cmd` look from TASK-SKRIPT-40-04-17: the info glyph and the word "Uppgifter", first in the toolbar, then a separator, then Öppna, Spara som, Exportera, Importera, a separator, PDF, AI and the autosave status. Its tooltip and accessible name are "Provets uppgifter"; it carries aria-expanded and emits the existing `toggleDetails`. The `.ws-meta` line under the title stays as plain text and stops being a button.
2. Answer block (Q3). For a free-text question, `ExamWorkspaceQuestionEditor.vue` renders `ExamWorkspaceWritingLinesField` and `ExamWorkspaceCriteriaField` as rows of one bordered block with an 11rem label column ("Skrivyta", "Bedömningskriterier"), so the labels align and no longer collide with the row above.
3. Skrivyta row. Boxless − and + in the `.xw-tool` look, the count "N rader" in a fixed 5.5rem slot sized for "40 rader", a separator, and an "Alla fritextfrågor" word tool with the copy glyph. The row ends after that tool; it does not stretch.
4. Apply-to-all popover (Q2). "Alla fritextfrågor" opens a popover anchored to it: "Samma skrivyta för alla fritextfrågor", "Alla N fritextfrågor får M rader.", and, when some differ, "1a, 1b och 3a har i dag en annan skrivyta.", with Avbryt and the primary "Använd M rader", which emits the existing `applyToAll`. When every free-text question already has the count, the popover shows a check, "Alla N fritextfrågor har redan M rader." and Stäng. The tool is never disabled for that reason, so it stops looking grey. Escape and Avbryt close the popover and return focus to the tool. The field needs the free-text question labels and their counts from `ExamWorkspaceEditorPane.vue` in place of the boolean `allFreeTextMatch`.
5. Criteria rows. Each criterion has its text field, a points field with a "p" suffix and a boxless trash tool; below the rows sits a boxless "+ Kriterium". The mockup's "X av Y p" line is left out (L1).

Units, each for one implementer, in order. Every glyph is already in the shared catalogue (`info`, `copy`, `decrement`, `add`, `delete`, `completed`), so no shared-package change is needed.

1. Header (item 1): add the Uppgifter command and its separator in `ExamWorkspaceHeader.vue`; turn `.ws-meta` into plain text and delete its button styles; update `ExamWorkspaceHeader.layout.spec.ts` and the other header specs that click `.ws-meta`.
2. Answer block and criteria (items 2 and 5): in `ExamWorkspaceQuestionEditor.vue`, wrap both free-text fields in one bordered block with the 11rem label column; make the fields render rows for that column in place of their own legends, keeping each row a labelled group for assistive technology; restyle `ExamWorkspaceCriteriaField.vue` (boxless trash and "+ Kriterium", the "p" suffix, the "X av Y p" line); update `ExamWorkspaceQuestionEditor.criteria.spec.ts` and `ExamWorkspaceQuestionEditor.writingLines.spec.ts`.
3. Skrivyta row and popover (items 3 and 4): restyle the stepper and the fixed count slot in `ExamWorkspaceWritingLinesField.vue`; add the "Alla fritextfrågor" tool and its popover with both states. Replace `allFreeTextWritingLines` in `ExamWorkspaceEditorPane.vue` and `allFreeTextWritingLinesMatch` in the question editor with one summary of the free-text questions: how many there are and the numbers (as the question list shows them, for example 1a) of those whose count differs from this question's. The popover closes on Escape, Avbryt, Stäng, an outside click and after Använd, and returns focus to the tool. Update `ExamWorkspaceWritingLinesField.spec.ts`.

Unit 3 starts after unit 2, because both change the free-text branch of `ExamWorkspaceQuestionEditor.vue`. Unit 1 touches other files and can run in parallel with unit 2.

Non-goals: no change to the document format, the stepper bounds (1-40), the criteria data or the drawer's contents; no new glyph meaning.

## Contract Inputs

- The user's report, relayed by the parent session on 2026-10-19 (staging main 54e9c5db), and the user's answers Q1-Q4 on 2026-10-20 in this session.
- Mockup `docs/mockups/exam-workspace-details-and-writing-area/prototype.html` and `desktop-1440.png` (main 05f6f2de): frame A (header and answer block), frame B (drawer open), frame C (popover, both states), and the "Före" strip.
- `huleedu-ui-design` (glyph-first controls, the layout holds still) and `integrated-frontend-stack` for the SPA.

## Core Vertical And Performance

### Resume here

2026-10-20: `in_progress` (user start 2026-10-20) on `codex/task-skript-40-04-18` (worktree `Skriptoteket-task-skript-40-04-18`, from main 25b7352e), retained root `01a15680-e9d9-7d82-83b6-4797464fa46e`. Units 1 and 2 dispatched to juniors in parallel; unit 3 follows unit 2.

### Map

Paths under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`.

- `ExamWorkspaceHeader.vue`: the `.ws-meta` details button (:156-161, styles :288-295) and the toolbar commands.
- `ExamWorkspaceWritingLinesField.vue`: the legend, the bordered stepper and the disabled apply-to-all button (:54-65, :105-106).
- `ExamWorkspaceCriteriaField.vue`: the legend, criteria rows, trash and "+ Kriterium".
- `ExamWorkspaceQuestionEditor.vue:152-154` and :304-318: `allFreeTextWritingLinesMatch` and where both fields render; `ExamWorkspaceEditorPane.vue` supplies `allFreeTextWritingLines`.
- `examWorkspaceWritingLines.ts`: bounds and `applyWritingLinesToAllFreeText`.
- `examWorkspace.css`: `.xw-cmd` and `.xw-tool`.

## Validation

- Focused Vitest specs for the header command, the writing-lines field (both popover states, Escape, focus return) and the criteria rows; `pdm run fe-type-check` and `pdm run fe-lint`.
- A staging walk on the Mac through `staging-walk` at the canonical widths: the Uppgifter command opens and closes the drawer; the answer block matches the mockup; both popover states; nothing moves when the count changes.

## Stop Conditions

- The approved mockup and an existing component or token disagree in a way this contract does not settle.
- A change to the document format or the backend seems necessary.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| Q1  | The details entry is an "Uppgifter" command with the info glyph and the word, first in the header toolbar (user 2026-10-20). |
| Q2  | Applying one writing area to all free-text questions goes through a popover that names the changes and asks for confirmation (user 2026-10-20). |
| Q3  | Skrivyta and Bedömningskriterier sit in one bordered answer block with a label column, as in the mockup (user 2026-10-20). |
| Q4  | The approved mockup becomes this implementation task (user 2026-10-20). |
| L1  | Lead decision 2026-10-20: the criteria row has no "X av Y p" line, because the question's points field already shows the criteria sum (the points always match), and the design system asks for the least text. |
