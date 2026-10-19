---
type: task
id: TASK-SKRIPT-40-04-13
title: With the gap tool on, a click on a gap turns it back into its words, any highlighted
  span becomes one gap, and one gap control replaces the Lucka button
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
- With the gap tool on, clicking a gap turns it back into the text it came from in
  one undo step; any highlighted span inside one paragraph becomes one gap with that
  span as its first answer; the toolbar has one gap control
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user tested the gap tool (TASK-SKRIPT-40-04-09) on staging on 2026-10-19 and asked for three things (U1-U3). The main point: with the gap tool on, a click on a gap must turn it back into the word it came from. The two gap controls confuse; making a gap from text the teacher has already written is the primary action, any highlighted span (one word, several words, a sentence) becomes one gap, and an empty gap that is filled later stays a secondary option.

Status `proposed`: the user questions Q1-Q8 in the retained plan are open. The planned behaviour, if the user accepts the lead's recommendations:

1. With the gap tool on, a click on a gap turns it back into text in one undo step: a Lucktext gap becomes its first accepted answer as plain text (reusing `withGapAsText`), a dropdown gap becomes its correct option's text, and a gap without an answer is removed. Its other answers and options go with it; Ångra restores the gap whole.
2. The Luckverktyg toggle is the one gap control. The toolbar Lucka button and the floating Gör till lucka glyph are removed, which reverses the user's earlier 40-04-09 Q5, Q12 and Q13; with the tool off the editor is plain text, and a gap click opens its popover. With the tool on, a word click or any highlighted span in one paragraph makes one gap; Enter on a keyboard selection makes one; Enter or Space on a selected gap opens its popover; the second click of a double click does nothing.
3. A secondary glyph, Tom lucka, inserts an empty gap at the caret and opens its popover with the answer field focused; closing the popover of any gap that has no answer (new, or emptied by the teacher) removes that gap in one undo step, so a keyed question never holds an unanswered gap.

Non-goals: native-format, API, export or print changes; the toolbar Ångra and Gör om and autosave (TASK-SKRIPT-40-04-14).

## Contract Inputs

- The user's feedback 2026-10-19 (U1-U3), relayed by the Mac parent through the Hemma orchestrator 944b5a5a.
- TASK-SKRIPT-40-04-09 and its repairs R9-R10 (main 26f84883; repair 2af07df2 on `codex/task-skript-40-04-gap-toggle-back-remote`).
- The verbatim transcripts: `evidence/planning/user-feedback-2026-10-19.md` in retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`.
- TASK-SKRIPT-40-04-11 (proposed, branch `codex/task-skript-40-04-compact-tools-remote`): boxless glyph tools (T1, T2); the toolbar glyphs here take its look.
- Retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`: plan `evidence/planning/TASK-SKRIPT-40-04-13/plan.md`, Explorer discovery under `discovery/explorer/`, toolbar mock `evidence/planning/mock/toolbar-mock.png`.
- `huleedu-ui-design` (glyph-only tools, names in tooltip and aria-label only); `integrated-frontend-stack`; TipTap 3.31.3 docs through `ctx7`.

## Core Vertical And Performance

### Resume here

Planned 2026-10-19 by lead 73032e62 (retained root `01a1541f-38b9-7a10-a94e-9fd8a0bd1bcc`). Facts F1-F5 and sources U1-U3 closed; user questions Q1-Q8 open, sent to the orchestrator with recommendations and the mock. Next action: record the user's answers in the plan ledger, derive the final units, validate with `--require-closed`, and ask for `ready`.

### Planned units (if the recommendations are accepted)

Paths are under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`; each unit goes to a fresh junior with disjoint files.

| Unit | Files | Behaviour | Focused tests |
| --- | --- | --- | --- |
| H1 revert edit | `examWorkspaceGapEdits.ts` (`withGapAsText` for dropdown gaps and for gaps with no answer), `useExamWorkspaceItemEdits.ts` | Q1, Q2 | `examWorkspaceItemEdits.interpretation.spec.ts` (extended), new `examWorkspaceGapRevert.spec.ts` |
| H2 tool click | `useExamWorkspaceMakeGap.ts`, `ExamWorkspaceRichTextEditor.vue` (`handleClickOn` with the tool on emits a revert; second click of a double click ignored; Enter on a selection converts) | Q3, Q4, Q5 | `ExamWorkspaceRichTextEditor.gapTool.spec.ts`, `ExamWorkspaceRichTextEditor.gapToolSelection.spec.ts` |
| H3 one control | `ExamWorkspaceMarkToolbar.vue` (remove Lucka, add Tom lucka, toggle glyph), removal of the floating button from `useExamWorkspaceMakeGap.ts` and its specs | Q5, Q6, Q8 | `ExamWorkspaceMarkToolbar.gap.spec.ts`; removed `makeGapButton` specs |
| H4 wiring | `ExamWorkspaceBodyEditor.vue` (revert emit to the owner; empty gap opens its popover; empty gap removed on close) | Q6, Q7 | `ExamWorkspaceBodyEditor.gapTool.spec.ts`, `ExamWorkspaceWalkingSkeletonSlice.spec.ts` |

H2 and H3 both touch `useExamWorkspaceMakeGap.ts` and run in separate waves. Performance is not material.

## Validation

- Per unit: its focused spec files, run as `pdm run fe-test -- <spec path>`.
- At the end: `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`, and one exam-workspace frontend domain suite on the orchestrator's go.
- Copy for the toggle, Tom lucka and the tooltips goes to `ui-copy-reviewer`.
- Staging walk on Hemma in a real browser: tool on, click a word, then click the gap and see the word back; Ångra brings the gap back; highlight three words and see one gap; highlight a sentence and see one gap; Tom lucka, close with no answer, see no gap.

## Stop Conditions

Stop and ask the user if a revert needs the gap's original text that its answers do not hold, if any unit needs a native-format, API, export or print change, or if removing the toolbar Lucka leaves a keyboard-only teacher without a way to make a gap.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| U1  | With the gap tool on, clicking a gap turns it back into the word it was made from (user 2026-10-19, staging test) |
| U2  | One clear gap control: making a gap from existing text is the primary action; an empty gap is secondary (user 2026-10-19, staging test) |
| U3  | Any highlighted span (one word, several words, a whole sentence) becomes one gap and is its first accepted answer; creating an empty gap and filling it later stays as a secondary option (user 2026-10-19, staging test) |
| F1  | Today the toolbar Lucka converts the selection or the caret's word, or inserts an empty gap at a caret outside a word; the Luckverktyg toggle (Mod-Alt-G) switches click-to-gap; with the tool off a word click shows the floating Gör till lucka glyph; a gap click opens its popover in both modes |
| F2  | `withGapAsText` already replaces a Lucktext gap with its first accepted answer as plain text and drops its record; only the popover's Visa som text reaches it, not for dropdown gaps |
| F3  | Removing a gap chip drops its record; other gap ids are never renumbered |
| F4  | The only empty-gap path is the toolbar Lucka at a caret outside a word; an unanswered gap in a keyed Lucktext question makes every draft refused until it has an answer (40-04-09 R9) |
| F5  | With the tool on, a drag over several words, a sentence with punctuation, or across a bold mark makes one gap with that text; a selection across two paragraphs makes none; a keyboard selection converts only through Lucka; a double click makes one gap |
