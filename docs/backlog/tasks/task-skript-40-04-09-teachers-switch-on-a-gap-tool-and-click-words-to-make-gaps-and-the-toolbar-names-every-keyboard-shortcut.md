---
type: task
id: TASK-SKRIPT-40-04-09
title: Teachers switch on a gap tool and click words to make gaps, and the toolbar
  names every keyboard shortcut
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
- With the gap tool on, one click on a word makes it a gap with no popover; Ctrl+Alt+G
  (Cmd+Option+G on macOS) turns the tool on and off; every formatting and tool button's
  tooltip names its shortcut
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user asked for three things on 2026-10-19 in the Hemma orchestrator session; the user answered the planning questions the same day ("Accept all", width "Drop it"). This task is `proposed` until the user accepts the plan, and the build starts after TASK-SKRIPT-40-04-08 merges into main.

1. A gap tool (U2). Each Lucktext and dropdown-Lucktext question gets a gap-tool toggle next to the Lucka button. While the tool is on, one click in a word makes that word a gap at once, with no popover; a drag selection inside one paragraph becomes one gap on release; a click on an existing gap opens its popover; typing works as usual.
2. Keyboard shortcuts (U3). Ctrl+Alt+G (Cmd+Option+G on macOS) turns the gap tool on and off. The formatting shortcuts already work through TipTap (Ctrl/Cmd+B, I, U, Ctrl/Cmd+. superscript, Ctrl/Cmd+, subscript, Ctrl/Cmd+Alt+1-3 headings; F3); every mark, heading and tool button's tooltip and `aria-keyshortcuts` now name its shortcut. No unit re-implements a formatting keymap.
3. Gap width (U1). Settled and dropped: Exam.net ignores `expected-length` and has no per-gap width (F4), so this task adds no width field or control, and export, print and preview keep sizing each gap from its longest accepted answer (Q11).

Non-goals: new formatting marks or shortcuts; any native-format, API-schema, export or print change (TASK-SKRIPT-40-04-08 L11 stays in force); the Kort svar field and other text fields get no gap tool.

## Contract Inputs

- The user's request and decisions, 2026-10-19, Hemma orchestrator session 944b5a5a (decisions answered on the Mac and relayed).
- TASK-SKRIPT-40-04-08 on `codex/task-skript-40-04-08-remote` (a3405ee1), which this task builds on: gap creation by a word click, the floating Lucka button, the Lucka toolbar button and the gap popover (its terms L4-L6, L12).
- Exam.net gap-width probe and result: `evidence/probes/gap-width/` (`luckbredd-probe.zip`, `README.md`, `result.md`, `shots/`) in retained root `01a1531a-2b8b-7e27-b91b-e774fdfe5052`; exams 5349689 and 5349726.
- QTI 2.1 information model and QTI 3 best-practice guide (`expected-length` on text entry only).
- `huleedu-ui-design` for the toggle button and tooltip copy; `integrated-frontend-stack` for the SPA; TipTap 3.31.3 docs through `ctx7`.

## Core Vertical And Performance

### Resume here

Planning by a fresh 40-04-09 lead on 2026-10-19 (retained root `01a1531a-2b8b-7e27-b91b-e774fdfe5052`, plan `evidence/planning/TASK-SKRIPT-40-04-09/plan.md`, Explorer discovery under `discovery/explorer/`). Ledger closed and validated with `--require-closed`: F1-F4, L1-L8, user decisions Q1-Q6 and Q11 (2026-10-19); Q7-Q10 withdrawn after F4. Status `proposed`. Next action: the orchestrator relays the user's plan acceptance and applies `proposed -> ready`; after TASK-SKRIPT-40-04-08 merges into main, merge main into this branch and launch wave 1. No junior has been launched.

### TASK-SKRIPT-40-04-08 files this task depends on

All under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`: `useExamWorkspaceMakeGap.ts` (`makeGap`, `replaceRangeWithGap`, `handleMakeGapClick`, the floating button), `ExamWorkspaceRichTextEditor.vue` (`handleClickOn` for gap chips runs before `handleClick`; `handleKeyDown` Escape; `createGap` emit), `ExamWorkspaceMarkToolbar.vue` (Lucka button, `showGap`, `gapDisabledReason`, `MARK_SHORTCUTS`), `ExamWorkspaceBodyEditor.vue` (`handleMakeGap`, `newGapId`, `gapKind`, opening the new gap's popover), `examWorkspaceRichTextSchema.ts` (`workspaceHistoryKeys` extension pattern), `examWorkspaceGapWord.ts`, `examWorkspaceRichTextTarget.ts`, `ExamWorkspaceGapPopover.vue`.

### Design

- Tool state (L1, Q4). `ExamWorkspaceBodyEditor` owns one `gapToolOn` flag per question and passes it to its rich-text editor and toolbar. The tool turns off by its toggle button, by the shortcut, by Escape, or when focus moves to another question (a `focusin` outside this body editor's root and outside its open popover). Clicks elsewhere in the same question, including the popover, keep it on.
- Click (L2, L3, Q2, Q3, Q6). With the tool on, `useExamWorkspaceMakeGap` converts the clicked word at once through `replaceRangeWithGap` (same word resolver, seed, next gap id, one `withNewGap` undo step) and shows no floating Lucka button. A click on a space or punctuation only places the caret. A mouseup that leaves a non-empty selection inside one paragraph converts it under `makeGap`'s existing guards. A click on a gap chip keeps `handleClickOn` and opens its popover. The body editor does not open the new gap's popover while the tool is on.
- Escape (L4). Escape closes an open gap popover first; with none open, it turns the tool off.
- Cap (L5). When no next gap id is left (`gap_999`), the tool turns off and its toggle is disabled with the Högst 999 luckor tooltip.
- Shortcut (L6, Q1). A `gapToolKeys` TipTap extension in `examWorkspaceRichTextSchema.ts`, built like `workspaceHistoryKeys`, binds `Mod-Alt-g` to an `onToggleGapTool` option; outside a gap question the callback does nothing. ProseMirror's direct lookup matches Ctrl+Alt+G on Windows (AltGr+G types nothing on a Swedish keyboard) and skips its key-code fallback for Ctrl+Alt there, so AltGr+2 (`@`) never toggles.
- Toolbar (L7, Q5). The Lucka button keeps its TASK-SKRIPT-40-04-08 behaviour. A separate toggle glyph button sits right after it, `aria-pressed` while the tool is on. A new `examWorkspaceShortcutLabels.ts` writes each shortcut per platform (Cmd and Option glyphs on macOS, Ctrl and Alt elsewhere) for the tooltips and the `aria-keyshortcuts` values of the five marks, the three headings and the tool toggle. Working copy for the toggle: tooltip and accessible name Luckverktyg plus its shortcut; the final Swedish copy goes to `ui-copy-reviewer`.
- Width (F4, Q11): no change anywhere.
- No walking-skeleton task (L8): the tool stays inside the SPA; the existing walking-skeleton spec gains the tool path.
- Performance is not material: one click-handler branch, one keymap entry and one `focusin` listener per open tool.

### Units

Paths are under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/`. Each unit goes to a fresh `junior-implementation-specialist` with disjoint files; wave 1 runs concurrently in this worktree, and wave 2 starts after wave 1 is integrated.

| Unit | Wave | Files | Behaviour | Focused tests |
| --- | --- | --- | --- | --- |
| G1 tool click | 1 | `useExamWorkspaceMakeGap.ts`; `ExamWorkspaceRichTextEditor.vue` (`gapTool` prop into the composable, the click and mouseup paths) | L2, L3, Q2, Q3, Q6 | new `ExamWorkspaceRichTextEditor.gapTool.spec.ts`: a word click converts with no floating button and one `createGap`; a space click only moves the caret; a gap-chip click emits `activateGap`; a drag in one paragraph makes one gap, a drag across paragraphs or over a gap makes none; typing emits `update` only; with the tool off a word click still shows the floating button |
| G2 shortcut key | 1 | `examWorkspaceRichTextSchema.ts` (`gapToolKeys` extension, `onToggleGapTool` option in `examRichTextExtensions`) | L6, Q1 | new `examWorkspaceGapToolKeys.spec.ts` (Ctrl+Alt+G calls the callback; a Ctrl+Alt event whose key is `@` does not; Ctrl+G does not), new `examWorkspaceGapToolKeys.mac.spec.ts` (Cmd+Option+G calls it, with the platform hoisted as in `ExamWorkspaceRichTextEditor.mac.spec.ts`) |
| G3 toolbar | 1 | `ExamWorkspaceMarkToolbar.vue` (toggle button, `gapToolOn` prop, `toggleGapTool` emit, tooltips); new `examWorkspaceShortcutLabels.ts` | L5, L7, Q5 | `ExamWorkspaceMarkToolbar.gap.spec.ts` (extended: toggle pressed state, disabled with the cap reason, Lucka unchanged), new `examWorkspaceShortcutLabels.spec.ts` (Mac and non-Mac text for every mark, heading and the tool) |
| G4 wiring | 2 | `ExamWorkspaceBodyEditor.vue` (tool state, Escape order, focus-leave, cap, no popover on tool-made gaps); `ExamWorkspaceRichTextEditor.vue` (pass `onToggleGapTool` and Escape to the body editor); `src/views/apps/ExamWorkspaceWalkingSkeletonSlice.spec.ts` | L1, L4, L5, Q4 end to end | new `ExamWorkspaceBodyEditor.gapTool.spec.ts` (three gaps from three word clicks with no popover; Escape closes an open popover first, then the tool; focus into another question ends it; the shortcut toggles it; at the cap it turns off; Kort svar shows no toggle); the walking-skeleton spec switches the tool on, makes two gaps and turns it off |

G1 and G4 both touch `ExamWorkspaceRichTextEditor.vue` and run in different waves. Every work order tells the junior to map existing code (this repository, related repositories, shared libraries) before writing new code and to reuse it, to fetch TipTap and Vue docs through `ctx7`, to launch its own Explorers through `agent-harness claude launch` with the `PATH=$HOME/.local/agent-bin:$HOME/.local/bin:$PATH` prefix, and to run only its focused spec files.

## Validation

- Per unit: the focused spec files in the Units table, run as `pdm run fe-test -- <spec path>`.
- Walking-skeleton spec: `src/views/apps/ExamWorkspaceWalkingSkeletonSlice.spec.ts` with the tool path (G4).
- At the end: `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`, and one frontend domain suite on the orchestrator's go.
- Copy: the toggle's tooltip and accessible name and the shortcut tooltip format go to `ui-copy-reviewer` before the walk.
- Staging walk on Hemma in a real browser: switch the tool on, click three words and see three gaps with no popover between them; drag across two words and see one gap; click a gap and see its popover; toggle the tool with Ctrl+Alt+G (Cmd+Option+G on the Mac); press Escape with and without an open popover; move to another question and see the tool off; hover the buttons and read each shortcut.

## Stop Conditions

Stop and ask the user if Ctrl+Alt+G or Cmd+Option+G turns out to be taken by the browser or the system in the staging walk, if the tool cannot reuse the TASK-SKRIPT-40-04-08 gap-creation path, or if any unit needs a native-format, API, export or print change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| U1  | Find out whether a gap's width can be set in QTI and carried into Exam.net, where a teacher states a width in characters per gap; if it can, carry it (user 2026-10-19) |
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
| L8  | No walking-skeleton task; the existing walking-skeleton spec gains the tool path |
| Q1  | Ctrl+Alt+G on Windows and Linux, Cmd+Option+G on macOS, toggles the gap tool (user 2026-10-19) |
| Q2  | With the tool on, a word click makes a gap at once and no popover opens (user 2026-10-19) |
| Q3  | With the tool on, a click on an existing gap opens its popover (user 2026-10-19) |
| Q4  | The tool ends by its button, its shortcut, Escape, or moving to another question; clicks elsewhere in the same question keep it on (user 2026-10-19) |
| Q5  | A separate toggle button next to the Lucka button; Lucka keeps its 40-04-08 behaviour (user 2026-10-19) |
| Q6  | With the tool on, a drag selection inside one paragraph becomes one gap on release (user 2026-10-19) |
| Q11 | Width is dropped: no native width field or control; export, print and preview keep sizing each gap from its longest answer (user 2026-10-19) |
