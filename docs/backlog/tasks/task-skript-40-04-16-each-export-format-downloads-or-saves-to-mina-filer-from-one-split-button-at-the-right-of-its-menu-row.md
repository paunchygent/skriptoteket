---
type: task
id: TASK-SKRIPT-40-04-16
title: Each export format downloads or saves to Mina filer from one split button at
  the right of its menu row
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Each format row in the exam workspace Exportera menu shows its name on one line and one split button at its right edge; the first part downloads the format and the second saves it to Mina filer (guests see the download part only); nothing sits on the left
- ArrowUp/Down move between rows keeping the part column, ArrowLeft/Right move between the two parts, Enter or Space runs the focused part, and every part has an aria-label and tooltip naming its action and format
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user asked on 2026-10-19 in the Hemma orchestrator session (screenshot `/home/paunchygent/apps/skriptoteket-mockups/export-menu-glyphs-2026-10-19.png`, staging 26f84883) to redesign the Exportera menu: download on the left and save to Mina filer on the right of every row looks messy; each format gets one split button, on the right, cohesive with the split button above the menu (U1). The user answered Q1-Q4 and accepted the plan on 2026-10-19 (A1, `agent-planning:user-closure-gate`).

1. Row anatomy. Each format row shows the format name and its grey suffix on one line (L8), then one split button at the row's right edge: the download part first, then the save-to-Mina-filer part, which writes that export format as a file (Q1, L1, L2, X1). PDF med facit has no suffix (Q3); a click on the name downloads (Q4). The format rows, `Det här tappar Exam.net (N)` and `Fler val …` start their text at the same left edge; no glyph or spacer sits on the left (L7). Guests see the download part alone at the same right edge (L6).
2. Split button. Two parts in the shared T1 tool look from TASK-SKRIPT-40-04-11 (`.xw-tool`: 28px box, 16px glyph, 44px on a coarse pointer, its hover tint and focus ring) inside one outlined container with a hairline divider (Q2, X1). The Spara split is not copied: TASK-SKRIPT-40-04-14 removes it. The running part shows the spinning busy glyph in its own slot and the `Exporterar …` line goes; `useExamWorkspaceExports` keeps the running destination (L3).
3. Accessibility and keyboard. Each row is a labelled group; each part is a menuitem button with an aria-label and tooltip naming its action and format (L4). `ExamWorkspaceMenu` gains group-aware arrow navigation: Up/Down between rows keeping the part column, Left/Right between parts (L5).

Non-goals: no export, API or file-format change; the Exportera trigger and the shared classes belong to TASK-SKRIPT-40-04-11 (X2); no new glyph meaning.

## Contract Inputs

- The user's request, 2026-10-19, Hemma orchestrator session 944b5a5a, and the screenshot above.
- Retained root `01a15432-7b95-76af-90e5-948f58222bfc`: plan `evidence/planning/TASK-SKRIPT-40-04-16/plan.md`; Explorer discovery under `discovery/explorer/`; before/after mock `evidence/mockups/export-menu-split-button-2026-10-19.png` (source `export-menu-split-button.html`, rendered with the worktree's `examWorkspace.css` and design tokens).
- `huleedu-ui-design` (visual system, layout holds still, glyph-only controls) and `integrated-frontend-stack` for the SPA.

## Core Vertical And Performance

### Resume here

Planning by a fresh 40-04-16 lead on 2026-10-19 on `codex/task-skript-40-04-export-split-button-remote` from origin/main 26f84883; origin/main ffab920a (41-02-04) merged at 0a22ac06. Ledger closed and validated with `--require-closed`: F1-F9, L1-L10, user answers Q1-Q4, acceptance A1, alignment X1-X2 (2026-10-19). Held 2026-10-19 for the toolbar redesign, then released the same day: the user chose "Build behaviour now" (B1). Status `ready`. origin/main be979cd7 merged at f388921e. Wave 1 integrated at 3f0efe36: V1 menu rows (junior b6bb3112; lead fixes: a shorter row lands on its first part, Element-keyed group map for vue-tsc) and V2 running destination (junior 0eba3259); 4 focused spec files 35 passed, fe-type-check and fe-lint rc 0. Work orders under the root's `evidence/implementation/TASK-SKRIPT-40-04-16/`. V3 integrated at 6d2e5031 (junior 940e863e; lead fixes: the menu's close event sets open to false again after V3 made it a toggle, which no spec catches; one download button with a conditional `xw-split` wrapper instead of a guest copy; no casts in the ordering spec); 4 spec files 33 passed. V4 integrated at c3a514b8 (junior a7d491c8): 7 view-level spec files 76 passed; fe-type-check, fe-lint and fe-build rc 0. origin/main eb35dc2c merged at d868c02c. Full frontend suite at d868c02c (plain `pdm run fe-test`, 2026-10-19): 507 files, 3597 passed, 2 todo, rc 0 (log in the root's `evidence/commands/fe-test-d868c02c.log`). Next action: independent review (orchestrator routes it) and the staging walk; the look follows TASK-SKRIPT-40-04-17 and adopts its tokens when they land. The mock omits the saved-date line and the zero-points note, which stay under the name (L8).

### Map

Paths under `frontend/apps/skriptoteket/src/views/apps/exam-workspace/` unless stated.

- `ExamWorkspaceExportMenu.vue`: the trigger (:71-91), format rows as `div role=menuitem` that download on click, Enter and Space (:106-118), the decorative left glyph (:119-123), the nested `.xw-mi__mini` save button shown to signed-in teachers only (:141-158), the checklist row and `Fler val …` (:178-200).
- `ExamWorkspaceMenu.vue`: arrow, Home and End navigation over `[role^="menuitem"]` in DOM order (:38, :85-115); Tab closes (:92-95); Escape restores focus to the trigger (:86-91); no Left/Right handling. The nested save button is unreachable by keyboard today (F3).
- `ExamWorkspaceHeader.vue:230-263` and `examWorkspace.css:63-68`: the Spara split this design matches.
- `examWorkspaceExportFormats.ts:27-32`: names and suffixes; `use` is read only by the menu.
- `useExamWorkspaceExports.ts:169`: `exportingTarget` without destination. `ExamWorkspaceView.vue:295-307` is the only host, shared by the teacher and guest hosts.

### Units

Each unit goes to a fresh `junior-implementation-specialist` with disjoint files. Wave 1 (V1, V2) runs concurrently; wave 2 (V3) starts after wave 1 is integrated (B1); wave 3 (V4) repairs the view-level specs after V3. Each work order tells the junior to map existing code (this repository, related repositories, shared libraries) before writing new code and reuse it, to fetch Vue and Vitest docs through `ctx7`, and to prefix every `agent-harness` command, including its own Explorer launches, with `PATH=$HOME/.local/agent-bin:$HOME/.local/bin:$PATH`.

| Unit | Wave | Files | Behaviour | Focused tests |
| --- | --- | --- | --- | --- |
| V1 menu keyboard | 1 | `ExamWorkspaceMenu.vue` | L5 | new `ExamWorkspaceMenu.keyboard.spec.ts`: Down and Up keep the column across group rows and land on the first part of a standalone item; Right and Left move inside a group and stop at its ends; Home and End; a disabled part is skipped; Tab still closes; Escape returns focus to the anchor |
| V2 running destination | 1 | `useExamWorkspaceExports.ts` | L3 (one `exporting` ref of target and destination; `exportingTarget` computed from it; `exportingDestination` exposed) | `useExamWorkspaceExports.spec.ts` extended: download and save each report their destination while running and clear it after success and failure |
| V3 split rows | 2 | `ExamWorkspaceExportMenu.vue` (two outlined `.xw-btn.xw-btn--compact.xw-btn--icon` parts in today's `.xw-split`; the name line truncates with the `truncate` utility inside `.xw-mi__stack`), `examWorkspace.css` (delete the dead `.xw-mi__mini` rules only), `examWorkspaceExportFormats.ts` and its spec (Q3), `ExamWorkspaceView.vue` (destination prop), `ExamWorkspaceExportMenu.ordering.spec.ts` | L1-L4, L6-L9, Q1-Q4, B1 | new `ExamWorkspaceExportMenu.rows.spec.ts`: per format the download part emits `download` and the save part emits `saveToFiles`; guest has no save part; aria-labels and titles per part including the replace-date title; busy glyph and `aria-busy` on the running part only and every part `aria-disabled` while it runs or while blockers exist, with focus kept on the running part; the saved-date line and the zero-points note render under the one-line name; nothing rendered before the name; the name element carries the one-line class; plus `ExamWorkspaceExportMenu.ordering.spec.ts` updated and green |
| V4 view-spec repairs | 3 | the F9 view-level specs: `ExamWorkspaceGuestMode.saveControls.spec.ts`, `ExamWorkspaceExportsSlice.blockers.spec.ts` (save part asserts `aria-disabled`, not `disabled`), `ExamWorkspaceExportsSlice.download.spec.ts`, `ExamWorkspaceExportsSlice.checklist.spec.ts`, `ExamWorkspaceExportBlockerSuggestAllSlice.spec.ts`, `ExamWorkspaceTotalsSlice.spec.ts`, `exam-workspace/ExamWorkspaceTitleBlocker.spec.ts` | L9 against the new rows; no product code | each listed spec green against V3, with assertions moved from the row to the part they mean |

## Validation

- Per unit: the focused spec files in the Units table, run as `pdm run fe-test -- <spec path>`.
- At the end: `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`, and one exam-workspace frontend domain suite on the orchestrator's go.
- Copy: the parts' aria-labels and tooltips go to `ui-copy-reviewer` before the walk.
- jsdom does not lay out text, so the specs prove the one-line class and structure only; the staging walk proves no wrapping at the menu's 300px width and at phone width.
- Staging walk on Hemma in a real browser (exam converter): open Exportera signed in and as a guest; read every row on one line; download and save one format through the mouse; move with the arrow keys across rows and parts and run each part with Enter; hover and focus each part and see nothing move; watch the running part spin.

## Stop Conditions

Stop and ask the user if a row cannot keep its name on one line at 300px with the answered suffix, if the outlined split cannot be drawn from today's `.xw-split` and `.xw-btn` classes, or if any unit needs an export, API or drawer change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| U1  | Each export format offers download and save to Mina filer as one split button on the right of its menu row; nothing sits on the left; name and suffix sit on one line; the design is cohesive with the split button above the menu and reuses its pattern (user 2026-10-19) |
| F1  | Format rows are `role=menuitem` divs that download on click, Enter and Space; the left glyph is decorative; save is a nested plain button shown to signed-in teachers only |
| F2  | The filled split above the menu is the Spara split (`.xw-split`, 28px second part, 40% white divider); Exportera is a single outlined `.xw-btn`; `UiDenseSplitButton` is a planner primitive not used in the exam workspace |
| F3  | `ExamWorkspaceMenu` cycles `[role^="menuitem"]` entries with Up, Down, Home and End, closes on Tab and Escape, and has no Left/Right; the nested save button has no keyboard path |
| F4  | The menu is 300px wide on desktop and full width minus 12px gutters at phone width; rows are at least 40px high; compact icon buttons are 28px |
| F5  | Format suffixes come from `use` in `examWorkspaceExportFormats.ts`, read in production only by the menu |
| F6  | Guest and signed-in workspaces render the same menu through `ExamWorkspaceView` |
| F7  | Glyphs: `download`, `save-to-files`, `busy`, `open-list`, `export-checklist` exist in the catalogue |
| F8  | The export composable keeps the running target but not its destination |
| F9  | Eight specs read the format rows through `exam-workspace-export-<target>` and `exam-workspace-export-save-<target>` |
| L1  | Rows reuse `.xw-split` with two outlined compact icon `.xw-btn` parts; one shared rule in `examWorkspace.css` draws the outlined divider; `.xw-mi__mini` is deleted; no scoped split CSS |
| L2  | Parts are 28px on a fine pointer and 44px on a coarse pointer (one shared coarse-pointer rule) with 16px glyphs; hover uses the existing `.xw-btn` hover (action-05 background) on the hovered part only; hover, focus, press and busy change no size or text |
| L3  | The running part shows the spinning busy glyph with `aria-busy`; every part is `aria-disabled` (not native `disabled`, so focus stays on the running part) while it runs or while blockers exist; the `Exporterar …` line goes; the composable keeps one `exporting` ref of target and destination |
| L4  | Each row is a labelled `role=group`; each part is a `role=menuitem` button with aria-label and title `Ladda ner {name}` and `Spara {name} i Mina filer`; the save title adds the replaced file's date |
| L5  | `ExamWorkspaceMenu` moves Up/Down between rows keeping the part column, Left/Right between parts without wrapping, Home/End to the first and last row; Tab and Escape keep today's behaviour |
| L6  | Guests see the download part alone at the same right edge |
| L7  | Format rows, the checklist row and `Fler val …` start at one left edge with no left glyph or spacer |
| L8  | Name and suffix stay on one line with ellipsis and the full text in the row title; the saved-date line and the zero-points note stay under the name |
| L9  | `exam-workspace-export-<target>` moves to the download part, `exam-workspace-export-save-<target>` stays on the save part, and the row is `exam-workspace-export-row-<target>` |
| L10 | No walking-skeleton task: frontend-only, no system boundary |
| Q1  | Download is the first part, save to Mina filer the second (user 2026-10-19) |
| Q2  | The split is outlined, with the existing hover tint (user 2026-10-19) |
| Q3  | The grey suffixes stay; PDF med facit has none: QTI Exam.net, PDF utskrift, PDF med facit, DOCX Word, PDF för Exam.net reserv (user 2026-10-19) |
| Q4  | A click on the row's name downloads (user 2026-10-19) |
| A1  | The plan with units V1-V4 and L1-L10 is accepted (user 2026-10-19, `agent-planning:user-closure-gate`) |
| X1  | Amends L1 and L2: the parts use TASK-SKRIPT-40-04-11's T1 tool look (`.xw-tool`, 28px box, 16px glyph, 44px on a coarse pointer, its hover and focus) inside one outlined container with a hairline divider; the Spara split, which TASK-SKRIPT-40-04-14 removes, is not copied; save to Mina filer writes that export format as a file |
| X2  | TASK-SKRIPT-40-04-11 owns the shared classes and tokens in `examWorkspace.css`, including the split container and the 32px menu rows; this task owns `ExamWorkspaceExportMenu.vue`, `ExamWorkspaceExportBlockers.vue` and `ExamWorkspaceExportDrawer.vue`; V3 starts after the shared classes are on main; shared files merge 41-02-04, then 40-04-08, then the rest |
| B1  | Build behaviour now (user 2026-10-19): the decided behaviour is built with today's styles (two outlined compact icon `.xw-btn` parts in `.xw-split`, `truncate` on the name, 28px parts on every pointer for now); the look follows TASK-SKRIPT-40-04-17 and adopts its shared tokens when they land; no new tokens or shared CSS; V3 does not wait; amends X1 and X2 |
