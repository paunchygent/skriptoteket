---
type: task
id: TASK-SKRIPT-40-04-08
title: Short-answer and gap-text questions look different, teachers create gaps by clicking a word, and the gap popover shows its whole answer list
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

Planned by the lead.

## Validation

Focused Vitest per unit, frontend typecheck and build, and a staging walk in a real browser that creates a short-answer question, creates a gap-text question with three gaps by clicking words, and enters several accepted answers in a fully visible popover.

## Stop Conditions

Stop and ask the user if the planned design changes the native exam document format or the export rules, or if U3 cannot share one popover design with TASK-SKRIPT-40-04-04.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                        |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| U1  | Short-answer and gap-text questions are visibly different; short answer is a question field plus an answer-key field (user 2026-10-19)       |
| U2  | Gaps are created by inserting a gap or by clicking a word in existing text and confirming; any number of gaps per question (user 2026-10-19) |
| U3  | The gap popover is fully visible above the editor and holds one to a hundred accepted answers, one row each (user 2026-10-19)                |
