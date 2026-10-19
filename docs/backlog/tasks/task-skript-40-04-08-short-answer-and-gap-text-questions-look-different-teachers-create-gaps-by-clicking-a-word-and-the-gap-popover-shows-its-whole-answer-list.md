---
type: task
id: TASK-SKRIPT-40-04-08
title: Short-answer and gap-text questions look different, teachers create gaps by clicking a word, and the gap popover shows its whole answer list
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A teacher tells a short-answer question from a gap-text question at a glance, creates any number of gaps by clicking a word in existing text or inserting a gap, and edits one to a hundred accepted answers in a gap popover that is fully visible above the surrounding editor
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user walked the redesigned exam workspace editor on 2026-10-19 and found three defects in how teachers author short-answer and gap-text (Lucktext) questions. This task fixes all three. It is proposed: a fresh lead plans it through `agent-planning`, maps the current editor code, closes the decision ledger with the user, and then decomposes it.

1. A short-answer question and a gap-text question with one gap look identical in the editor, so a teacher cannot tell what they are creating. A short-answer question shows exactly what it is: a question text field and an answer-key field, and nothing else. A gap-text question shows its text with its gaps visibly marked in place (U1).
2. A teacher cannot add a second gap, so every gap-text question a teacher creates has only one gap. Creating gaps must take no effort: the teacher either inserts a gap at the cursor, or clicks a word in existing text and then confirms "make this a gap" (U2). Any number of gaps per question.
3. Clicking a gap opens its popover for accepted answers, but the popover renders inside the question's field and behind the surrounding editor, so only a sliver of it is visible and answers cannot be entered. The popover must be fully visible above the editor and hold from one to a hundred accepted answers, with an obvious way to add, edit and remove each (U3). The current "kommaseparerade" single input is replaced by one row per accepted answer.

## Contract Inputs

- User walk 2026-10-19 with a screenshot of the clipped popover ("Lucka 1 – godkända svar (kommaseparerade)" under "Fråga 3, Lucktext").
- TASK-SKRIPT-40-04-03 (the redesigned workspace editor, terms W2 and W14).
- TASK-SKRIPT-40-04-04 (`in_progress`): it extends the same `ExamWorkspaceGapPopover.vue` with dropdown options. The lead coordinates with that lane so that U3 and the dropdown option list share one popover design and do not edit the same files concurrently.
- `huleedu-ui-design` for presentation, click economy and Swedish copy; `integrated-frontend-stack` for the SPA code.

## Core Vertical And Performance

### Resume here

Implementation by a fresh 40-04-08 lead from 2026-10-19 (retained root `01a152b4-0314-7471-91ad-340323c3f2c1`, plan `evidence/planning/TASK-SKRIPT-40-04-08/plan.md`, ledger L1-L13 closed; the user decided L2 option A on 2026-10-19; work orders, proof logs and screenshots under `evidence/implementation/TASK-SKRIPT-40-04-08/`). Status: `in_progress`, every unit committed. Wave 1: J1 popover anchoring (15264da8, a4e8a727), J2 answer rows (97484861), J3 new-gap edit (66ba2fbb). Wave 2: J4 editor gap command with repair J4r (bb54335a), J5 popover rows (81193429), J7 Kort svar model (ed4ce465), J6 gap wiring (25a5e98f). Wave 3: J8a Kort svar field (1fc7c9f2), J8b editor and head wiring plus walking-skeleton migration (931bbcea); R1 structural repairs (13bd6d6f). Frontend domain run at 13bd6d6f green 2026-10-19 (fe-test 3059 passed, 0 failed; type-check, lint, build rc 0). L12 copy review from headless component screenshots: ui-copy-reviewer 0d391833 approved; the user applied all five recommendations 2026-10-19 (ledger L12), committed as C1 (e68f8e16) with focused Vitest 113 passed, fe-type-check and fe-lint rc 0. Code review 9633a403 at dee9449d: changes_requested (F1, F2 high; F3-F6 medium; report evidence/reviews/9633a403-2ef7-4088-a447-d51564a73dc2.md). Repairs by fresh juniors, one commit per finding: F1 seeded gap keys the item, empty insertion keeps the origin, gap edits split (1bebd2af); F2 one textblock word resolver for caret and click, make-gap composable (a7b3a0a7); F3 answer-list echo keeps rows and focus (ac8bedaf); F4 vertical viewport clamp (90d9c763); F6 casts narrowed (1fecdee2); F5 walking-skeleton split (f4854333). Focused proof: 117 exam-workspace and walking-skeleton spec files, 1061 tests passed; fe-type-check and fe-lint rc 0. Full frontend run at 3f498eda green (443 files, 3084 passed). Rereview 9633a403 at 3f498eda cleared F1 and F2 and approved the copy; F3-F6 admitted on focused proof. Merged origin/main 06985163 (40-04-07 writing lines) in 3ba69e98, then fixture repair 2df576c9 and the points-field split f8fe97b4; focused proof 125 files, 1110 passed, fe-type-check and fe-lint rc 0. Full run at a9592369 green (453 files, 3134 passed). Merged origin/main 92373773 (41-02-02 guest access, 39-04-19) in b10b9178; the makeGap pane spec now passes the store and the workspace providers. Focused proof: 143 exam-workspace, walking-skeleton and guest spec files, 1244 passed; fe-type-check and fe-lint rc 0. Next action: one full frontend run at the merged head (orchestrator slot), then the Mac staging walk of the merged head.

### Root causes (ledger L1)

- U1: Kort svar is stored as `gap_fill` (`examWorkspaceItemEdits.ts:423`) and a new Lucktext gets the same one-gap-only body (`:445-447`), so the two render identically.
- U2: no gap-creation path exists. No toolbar, keyboard or editor command inserts an `examGap` node, and `withBody` (`examWorkspaceItemEdits.ts:61-65`) only drops unplaced gap records.
- U3: the popover is `position: absolute` inside `.xw-rich`, which sets `overflow: hidden` (`examWorkspace.css:95-98`); its `z-10` also competes in an ancestor stacking context. Derived from code; the staging walk confirms the fix.

### Design

- Kort svar (L2 option A, decided by the user 2026-10-19; L3): a `gap_fill` whose only gap is the sole segment of its last paragraph shows two fields, Frågetext (the body without that paragraph) and Godkända svar (the accepted-answer rows plus automatic answers). Question-text edits always re-attach the gap paragraph before `withBody`. A new Lucktext starts with empty text and no gap.
- Gap creation (L4-L6): a Lucka glyph button in the mark toolbar turns the selection, or the word at the caret, into a gap, or inserts an empty gap; a click inside a word shows a floating Lucka glyph button (tooltip Gör till lucka) above it. The new gap is seeded from the text (accepted value, or the correct dropdown option), takes the next free `gap_NNN`, and is written by one atomic structural edit `withNewGap`, never through `withBody`. Its popover opens at once.
- Popover (L7-L9): Teleported to `body`, `position: fixed`, z-index 30 as in `ExamWorkspaceMenu`, anchored to the chip, flipped above when the space below is too small, viewport-capped with its own scroll, repositioned on resize and ancestor scroll. Text gaps get one row per accepted answer (add, edit, remove, Enter adds a row, 1-100 rows, editor-only cap, commas allowed); dropdown rows from TASK-SKRIPT-40-04-04 keep their radio and move buttons in the same row layout.
- TASK-SKRIPT-40-04-04 is already on `origin/main` (471f2209 is an ancestor of 0cb1df1a): it landed first and this task builds on it (L8).
- The native exam document, API schema and export rules do not change (L11). No walking-skeleton task: no new system boundary.
- Performance is not material: the row list is capped at 100 inputs and repositioning runs only while a popover is open.

### Units

Each unit goes to a fresh junior with disjoint files. Units in one wave run concurrently in this worktree; a later wave starts after the earlier wave is integrated. Paths are under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`.

| Unit | Wave | Files | Behaviour | Focused Vitest |
| --- | --- | --- | --- | --- |
| J1 popover anchoring | 1 | new `useExamWorkspaceAnchoredPosition.ts`; `ExamWorkspaceGapPopover.vue` (root, positioning props only); `ExamWorkspaceBodyEditor.vue` (`openPopover`, position math); specs `ExamWorkspaceBodyEditor.gaps.spec.ts`, `ExamWorkspaceBodyEditor.gapTransitions.spec.ts`, `ExamWorkspaceGapPopover.*.spec.ts` move to document queries | L7 | new `useExamWorkspaceAnchoredPosition.spec.ts` (below/above flip, edge clamp, height cap, scroll and resize recompute, listener removal) plus the migrated specs |
| J2 answer rows | 1 | new `ExamWorkspaceGapAnswerList.vue` | L9 rows as a standalone component: `values` prop, `commit(values)` emit | new `ExamWorkspaceGapAnswerList.spec.ts` (add, edit, remove, Enter adds and focuses, empty and duplicate rows dropped, comma kept, 100 cap, one row minimum) |
| J3 new-gap edit | 1 | `examWorkspaceItemEdits.ts` (`nextGapId`, `withNewGap`); `useExamWorkspaceItemEdits.ts` (`createItemGap`, structural) | L5, L6 | new `examWorkspaceItemEdits.newGap.spec.ts` (seeding per kind, id after the highest, `null` at `gap_999`, body and record in one edit, existing gaps untouched) |
| J4 editor gap command | 1 | `ExamWorkspaceRichTextEditor.vue`; the `RichTextTarget` type file; `ExamWorkspaceMarkToolbar.vue`; new `examWorkspaceGapWord.ts` | L4: `makeGap` on the target, word-at-caret, floating Gör till lucka button, `createGap(body, gapId, seed)` emit, Lucka toolbar button with disabled state | new `examWorkspaceGapWord.spec.ts`, new `ExamWorkspaceRichTextEditor.makeGap.spec.ts`, existing `ExamWorkspaceMarkToolbar` spec |
| J5 popover rows | 2 | `ExamWorkspaceGapPopover.vue` (text section); `examWorkspaceGapLabels.ts` (delete `parseAcceptedValues`) and its spec; `ExamWorkspaceBodyEditor.gaps.spec.ts` | L9 inside the popover, shared row layout with dropdown options, heading Lucka N – godkända svar | new `ExamWorkspaceGapPopover.acceptedValues.spec.ts`, updated `ExamWorkspaceBodyEditor.gaps.spec.ts`, `examWorkspaceGapLabels.spec.ts`, `ExamWorkspaceGapPopover.options.spec.ts` |
| J6 gap wiring | 2 | `ExamWorkspaceBodyEditor.vue` (toolbar to target, `createGap`, open the new gap's popover); `ExamWorkspaceQuestionEditor.vue` (forward); `ExamWorkspaceEditorPane.vue` (`createItemGap`) | L4, L6 end to end in the component tree | new `ExamWorkspaceBodyEditor.makeGap.spec.ts` (three gaps by word clicks, popover opens on each, undo removes one gap per step) |
| J7 Kort svar model | 2 | new `examWorkspaceShortAnswer.ts` (`isShortAnswer`, question body split and re-attach); `examWorkspaceItemEdits.ts` (`newTeacherItem`: new Lucktext starts empty) and the specs that assume a new Lucktext has a gap | L2 A, L3 | new `examWorkspaceShortAnswer.spec.ts` (adversarial: typing in the question keeps the gap record and its placement; text next to the gap is not a Kort svar), updated `useExamWorkspaceStructure.spec.ts`, `examWorkspaceInlineChoice.spec.ts` |
| J8 Kort svar view | 3 | new `ExamWorkspaceShortAnswerField.vue`; `ExamWorkspaceQuestionEditor.vue` (branch); `ExamWorkspaceQuestionHead.vue` (Kort svar label) | L3 | new `ExamWorkspaceShortAnswerField.spec.ts`, `ExamWorkspaceWalkingSkeletonSlice.spec.ts` (adds a Kort svar) |

J3 and J7 both edit `examWorkspaceItemEdits.ts` and run in different waves. J1, J5 and J6 edit the popover or body editor in different waves. Every work order tells the junior to map existing code before writing new code, to fetch TipTap and Vue docs through `ctx7`, to launch its own Explorers through `agent-harness claude launch` with the `PATH=$HOME/.local/agent-bin:$HOME/.local/bin:$PATH` prefix, and to run only its focused spec files.

## Validation

- Per unit: the focused Vitest files in the Units table, run as `pdm run fe-test -- <spec path>`.
- At the end: `pdm run fe-type-check`, `pdm run fe-build`, and one frontend domain suite on the orchestrator's go.
- Staging walk on Hemma in a real browser: create a Kort svar question and see only Frågetext and Godkända svar; create a Lucktext with three gaps by clicking words; open a gap on the last line of a long question and see the whole popover above the editor; enter several accepted answers including one with a comma, remove one, reload and see them kept.
- Swedish copy from ledger L12 goes to `ui-copy-reviewer`.

## Stop Conditions

Stop and ask the user if the planned design changes the native exam document format or the export rules, or if U3 cannot share one popover design with TASK-SKRIPT-40-04-04.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                        |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| U1  | Short-answer and gap-text questions are visibly different; short answer is a question field plus an answer-key field (user 2026-10-19)       |
| U2  | Gaps are created by inserting a gap or by clicking a word in existing text and confirming; any number of gaps per question (user 2026-10-19) |
| U3  | The gap popover is fully visible above the editor and holds one to a hundred accepted answers, one row each (user 2026-10-19)                |
| L2  | Kort svar is decided by shape: a Lucktext whose only gap stands alone in its last paragraph shows as Kort svar with a Frågetext field and a Godkända svar field; Ny fråga starts an empty Lucktext with no gap; no native-format or export change (user 2026-10-19) |
| L3  | The Kort svar editor shows only Frågetext (body without the gap paragraph, mark toolbar, no gap button) and Godkända svar (accepted-answer rows plus automatic answers); question-text edits re-attach the gap paragraph before `withBody` |
| L4  | A Lucka toolbar glyph converts the selection or the word at the caret into a gap, or inserts an empty gap; a click inside a word shows a floating Lucka glyph button (tooltip Gör till lucka); the new gap's popover opens at once; any number of gaps |
| L5  | A new gap is seeded from the converted text (accepted value, or one correct dropdown option) and takes the next free `gap_NNN`; at `gap_999` the Lucka button is disabled with a tooltip |
| L6  | Gap creation is one atomic structural edit `withNewGap` (body plus record), never through `withBody`, and the written body JSON-equals the editor's emit |
| L7  | The popover is Teleported to `body`, `position: fixed`, z-index 30, anchored to the chip, flipped above when needed, viewport-capped with own scroll, repositioned on resize and ancestor scroll; no positioning library |
| L9  | Accepted answers are one row each with remove glyph, an add glyph (Lägg till svar), Enter adds and focuses a row, at least one row shown, empty and duplicate rows dropped on commit, commas allowed, editor-only cap of 100 |
| L10 | The 40-04-06 removal of the last-gap rule stays: a Lucktext may have zero gaps, reported as `no_gaps` |
| L11 | The native exam document format, API schema and export rules do not change |
| L12 | Copy (user 2026-10-19 after ui-copy-reviewer 0d391833): Lucka glyph buttons with tooltip Gör till lucka; Högst 999 luckor; Kort svar fields Frågetext and Godkända svar; add buttons glyph-only with Lägg till svar / Lägg till alternativ as tooltip and accessible name; no per-chip automatisk tag under Automatiska svar |
