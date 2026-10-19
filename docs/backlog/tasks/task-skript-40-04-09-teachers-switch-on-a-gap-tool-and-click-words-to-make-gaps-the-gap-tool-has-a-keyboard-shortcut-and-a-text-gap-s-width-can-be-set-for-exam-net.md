---
type: task
id: TASK-SKRIPT-40-04-09
title: Teachers switch on a gap tool and click words to make gaps, the gap tool has
  a keyboard shortcut, and a text gap's width can be set for Exam.net
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
- With the gap tool on, one click on a word makes it a gap; one shortcut turns the
  tool on and off; the editor's existing formatting shortcuts are named in their tooltips;
  a text gap's width is settled against Exam.net and carried only if Exam.net reads
  it
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user asked for three things on 2026-10-19 in the Hemma orchestrator session. This task is proposed: the lead has mapped the code, settled the facts and opened the questions below; implementation starts after the user answers them and accepts the plan, and after TASK-SKRIPT-40-04-08 merges into main.

1. Gap width (U1). Find out whether a gap's width can be set in QTI and carried into Exam.net, where a teacher sets the width of a gap's text field as a number of characters per gap. The Exam.net probe settled it on 2026-10-19: a per-gap width cannot reach Exam.net (F4). Whether Skriptoteket keeps a width for its own print and preview, or drops width from this task, is user question Q11.
2. A gap tool (U2). The teacher switches the tool on; while it is on, one click on a word makes that word a gap.
3. Keyboard shortcuts (U3). The editor's tools use the common shortcuts (Ctrl/Cmd+B, I, U). One shortcut turns the gap tool on and off; it is the only new shortcut a gap question needs.

What the code already does (facts F1-F3 in the retained plan):

- Every formatting shortcut already works: TipTap's Bold, Italic and Underline bind Ctrl/Cmd+B, I and U, Superscript Ctrl/Cmd+., Subscript Ctrl/Cmd+, and Heading Ctrl/Cmd+Alt+1-3. What is missing is that the toolbar tooltips name them; `aria-keyshortcuts` covers only B, I and U. No unit re-implements a keymap.
- The QTI export already writes `expected-length` on every text gap, derived from the longest accepted answer (8-80 characters, 20 with no answer). QTI defines it as a hint of the expected answer length in characters, not a limit; dropdown (inline choice) gaps have no such attribute. The importer ignores it, the native gap has no width field, and print sizes a gap's blank from the longest answer. A teacher width therefore replaces the derived value; it adds no new QTI attribute.
- Exam.net ignores `expected-length` and has no per-gap width (observed 2026-10-19, exams 5349689 and 5349726). Its only width control is one setting per question under Svarsalternativ, "Hur många tecken ska få plats i en lucka?", with fixed ranges 1-2, 2-4, 4-10, 10-15, 15-20 and 20-30; both imports chose the default 10-15 and every gap rendered at the same width.

## Contract Inputs

- The user's request, 2026-10-19, in the Hemma orchestrator session 944b5a5a.
- TASK-SKRIPT-40-04-08 on `codex/task-skript-40-04-08-remote` (a3405ee1), which this task builds on: gap creation by a word click, the floating Lucka button, the Lucka toolbar button, the gap popover with answer rows (its terms L4-L6, L12).
- QTI: 1EdTech QTI 2.1 information model (stringInteraction `expectedLength`), QTI 3 best-practice guide and shared vocabulary (`expected-length`, `qti-input-width-N`).
- Exam.net gap-width probe and its observed result: `evidence/probes/gap-width/` (`luckbredd-probe.zip`, `README.md`, `result.md`, `shots/`) in retained root `01a1531a-2b8b-7e27-b91b-e774fdfe5052`.
- `huleedu-ui-design` for the tool button, tooltips and Swedish copy; `integrated-frontend-stack` for the SPA; `skriptoteket-backend-dev` for the native model and export if width is carried.

## Core Vertical And Performance

### Resume here

Planning by a fresh 40-04-09 lead on 2026-10-19 (retained root `01a1531a-2b8b-7e27-b91b-e774fdfe5052`, plan `evidence/planning/TASK-SKRIPT-40-04-09/plan.md`, Explorer discovery under `discovery/explorer/`). Status `proposed`. Closed: facts F1-F4 (F4 is the Exam.net probe result of 2026-10-19), lead terms L1-L8; Q7-Q10 withdrawn after F4. Open: user questions Q1-Q6 and Q11, sent to the orchestrator with recommendations. Next action: record the user's answers in the ledger, close it, rewrite Units and Decided Contract Terms from the answers, then ask for `proposed -> ready`. No junior has been launched.

### TASK-SKRIPT-40-04-08 files this task depends on

All under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`: `useExamWorkspaceMakeGap.ts` (`makeGap`, `replaceRangeWithGap`, `handleMakeGapClick`, the floating button), `ExamWorkspaceRichTextEditor.vue` (`handleClickOn` for gap chips runs before `handleClick`; `handleKeyDown` Escape), `ExamWorkspaceMarkToolbar.vue` (Lucka button, `showGap`, `gapDisabledReason`, `MARK_SHORTCUTS`), `ExamWorkspaceBodyEditor.vue` (`handleMakeGap`, `newGapId`, `gapKind`), `examWorkspaceRichTextSchema.ts` (`workspaceHistoryKeys` extension pattern), `examWorkspaceGapWord.ts`, `examWorkspaceRichTextTarget.ts`, `ExamWorkspaceGapPopover.vue`, `examWorkspaceItemEdits.ts`.

### Design (working assumptions until the user answers)

- Gap tool (L1-L5; Q2-Q6). `ExamWorkspaceBodyEditor` owns the tool state per gap question and passes it to the rich-text editor. With the tool on, a click inside a word becomes a gap at once through the existing `replaceRangeWithGap` path (same word resolver, seed, next gap id, one undo step), and the floating Lucka button is not shown. Typing works as usual. Escape closes an open popover first, then turns the tool off. At the `gap_999` cap the tool turns off and its button is disabled. Recommended answers: no popover per click (Q2), a click on an existing gap opens its popover (Q3), the tool ends by its button, its shortcut, Escape or moving to another question (Q4), a separate toggle button next to Lucka (Q5), and a drag selection becomes one gap on release (Q6).
- Shortcut (L6, L7; Q1). The toggle shortcut is a TipTap extension built like `workspaceHistoryKeys`. Recommended key: Ctrl+Alt+G, Cmd+Option+G on macOS (no binding in Chrome, Edge, Safari or macOS; Ctrl/Cmd+G is find-next everywhere). Every mark, heading and tool button's tooltip and `aria-keyshortcuts` name its shortcut per platform.
- Width (Q11). Exam.net cannot receive a per-gap width (F4). Recommended: drop width from this task; the export keeps writing today's derived `expected-length` and print keeps the longest-answer blank. The alternative is an optional per-gap width in characters that sizes only Skriptoteket's printed blank and editor preview.
- Performance is not material: one click handler branch and one keymap entry.

### Planned units

Paths are under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/` unless they start with `src/` or `tests/`. Each unit goes to a fresh junior with disjoint files; a wave starts after the earlier wave is integrated. The table is final once Q1-Q6 and Q11 are closed.

| Unit | Wave | Files | Behaviour | Focused tests |
| --- | --- | --- | --- | --- |
| G1 tool click | 1 | `useExamWorkspaceMakeGap.ts`; `ExamWorkspaceRichTextEditor.vue` (`gapTool` prop, click and drag paths) | L2, L3, Q2, Q3, Q6 | new `ExamWorkspaceRichTextEditor.gapTool.spec.ts` (word click converts with no floating button; space click only moves the caret; gap click opens the popover; drag in one paragraph makes one gap; typing unchanged; each gap one undo step) |
| G2 shortcut key | 1 | `examWorkspaceRichTextSchema.ts` (`gapToolKey` extension, `onToggleGapTool` option) | L6, Q1 | new `examWorkspaceGapToolKey.spec.ts` (Ctrl+Alt+G calls the callback on Windows and Linux; a Ctrl+Alt event that types a character, such as AltGr+2 for `@` on a Swedish Windows keyboard, does not), new `examWorkspaceGapToolKey.mac.spec.ts` (Cmd+Option+G calls it; Ctrl+Option+G does not) |
| G3 toolbar | 1 | `ExamWorkspaceMarkToolbar.vue`; new `examWorkspaceShortcutLabels.ts` | L7, Q5: tool toggle button with pressed state, shortcut text in every tooltip and `aria-keyshortcuts` per platform | `ExamWorkspaceMarkToolbar.gap.spec.ts` (extended), new `examWorkspaceShortcutLabels.spec.ts` |
| G4 wiring | 2 | `ExamWorkspaceBodyEditor.vue`; `ExamWorkspaceRichTextEditor.vue` (pass `onToggleGapTool`) | L1, L4, L5, Q4 end to end | new `ExamWorkspaceBodyEditor.gapTool.spec.ts` (three gaps from three clicks, Escape order, cap, leaving the question ends the tool); `src/views/apps/ExamWorkspaceWalkingSkeletonSlice.spec.ts` gains the tool path |
| W1 native width (only if Q11 B) | 3 | `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_values.py`, `native_exam_item.py` (no width on dropdown gaps), `exam_print_layout.py`; OpenAPI regeneration; the QTI export is unchanged | Q11 B | `tests/unit/domain/curated_apps/exam_workspace/test_native_exam_gap.py`, `test_exam_print_layout.py` (a set width sizes the printed blank, an unset width keeps the longest-answer rule) |
| W2 width field (only if Q11 B) | 4 | `ExamWorkspaceGapPopover.vue` (text section); `examWorkspaceItemEdits.ts` (width edit) | Q11 B | new `ExamWorkspaceGapPopover.width.spec.ts`, new `examWorkspaceItemEdits.gapWidth.spec.ts` |

G1 and G4 both touch `ExamWorkspaceRichTextEditor.vue` and run in different waves. Every work order tells the junior to map existing code (this repository, related repositories, shared libraries) before writing new code and to reuse it, to fetch TipTap and Vue docs through `ctx7`, to launch its own Explorers through `agent-harness claude launch` with the `PATH=$HOME/.local/agent-bin:$HOME/.local/bin:$PATH` prefix, and to run only its focused test files.

## Validation

- Per unit: the focused files in the Planned units table, frontend as `pdm run fe-test -- <spec path>`, backend as `pdm run test-sequential <test path>`.
- Walking-skeleton spec: `src/views/apps/ExamWorkspaceWalkingSkeletonSlice.spec.ts` switches the tool on, makes gaps with word clicks, and turns the tool off with the shortcut and with Escape.
- Only if Q11 B: the print-layout test proves a set width sizes the printed blank; `pdm run lint` and `pdm run typecheck` for the backend.
- At the end: `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`, and one domain suite per touched domain on the orchestrator's go.
- Staging walk on Hemma in a real browser: switch the tool on, click three words, see three gaps and no popover between them; toggle with the shortcut; Escape ends the tool; the tooltips name the shortcuts. Only if Q11 B: print a gap with a set width and see the blank follow it.
- Swedish copy (tool button, tooltips, Bredd field) goes to `ui-copy-reviewer`.

## Stop Conditions

Stop and ask the user if the chosen shortcut collides with a browser or system shortcut in the staging walk, or if the tool cannot reuse the TASK-SKRIPT-40-04-08 gap-creation path.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| U1  | Find out whether a gap's width can be set in QTI and carried into Exam.net, where a teacher states a width in characters per gap; if it can, the native format, the editor and the QTI export carry it (user 2026-10-19) |
| U2  | A selectable gap tool: while it is on, clicking a word makes that word a gap (user 2026-10-19) |
| U3  | The editor's tools use the common keyboard shortcuts; one shortcut turns the gap tool on and off (user 2026-10-19) |
| F1  | QTI `expected-length` on a text gap is a hint of the expected answer length in characters, not a limit; dropdown gaps have no such attribute |
| F2  | The export already writes `expected-length` from the longest accepted answer (8-80, 20 with none); the import ignores it; the native gap has no width; print sizes the blank from the longest answer |
| F3  | All formatting shortcuts already work through TipTap's keymaps; the tooltips do not name them and `aria-keyshortcuts` covers only B, I and U |
| F4  | Exam.net ignores `expected-length` and has no per-gap width; its one width setting is per question, in fixed ranges, default 10-15 (observed 2026-10-19, exams 5349689 and 5349726) |
| L1  | The gap tool state lives in `ExamWorkspaceBodyEditor` per question; only Lucktext and dropdown-Lucktext questions show the tool |
| L2  | With the tool on, a click in a word becomes a gap at once through `replaceRangeWithGap` (same resolver, seed, next gap id, one undo step); the floating Lucka button is hidden; a click on a space or punctuation only places the caret |
| L3  | Typing works normally while the tool is on |
| L4  | Escape first closes an open gap popover; with none open, Escape turns the tool off |
| L5  | At the `gap_999` cap the tool turns off and its button is disabled with the Högst 999 luckor tooltip |
| L6  | The toggle shortcut is a TipTap extension built like `workspaceHistoryKeys`; Mac keys are tested in a platform-hoisted spec |
| L7  | Every mark, heading and tool button's tooltip and `aria-keyshortcuts` name its shortcut per platform; copy goes to `ui-copy-reviewer` |
| L8  | No walking-skeleton task; the existing walking-skeleton spec gains the tool path and the Exam.net probe is the width boundary proof |
