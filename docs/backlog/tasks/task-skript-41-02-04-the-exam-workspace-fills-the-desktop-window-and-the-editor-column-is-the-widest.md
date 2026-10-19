---
type: task
id: TASK-SKRIPT-41-02-04
title: The exam workspace fills the desktop window and the editor column is the widest
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
- On desktop (1280 px and wider) the guest exam workspace fills the window width, with no centred page column or side gutters
- At the default widths the editor column is the widest column whenever a drawer or the print preview is open, on the guest and signed-in workspaces, with no horizontal page scroll
- On desktop the user drags any panel border to resize it, collapses and reopens panels, and the widths are remembered per browser
- A panel narrower than its designed minimum keeps its minimum layout and scrolls inside itself; nothing else reflows
- Tablet and phone layouts are unchanged
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

The guest workspace at `/public/apps/documents.conversion_hub/exam-converter` sits inside the
landing page column: `LandingLayout.vue`'s `.landing-frame` sets `max-width: 1040px; margin: 0 auto`, and
`.landing-main` adds side padding. That column causes the empty margins the user reported on
2026-10-19. Inside the workspace, one 380 px drawer track serves every drawer. The 320 px list
and the 380 px drawer come from the 40-04-01 prototype, which gives no functional reason for them.
The editor gets the remainder: 340 px in a 1040 px workspace.

This task changes four things:

1. **Full width (guest).** LandingLayout fills the frame on the public `documents.conversion_hub`
   routes: no max-width and no `.landing-main` padding. The landing top bar stays. The route is
   selected the way AuthLayout already selects full-frame routes, by route name plus appId. Other
   public pages keep the 1040 px column. The signed-in route already fills its frame beside the
   240 px shell sidebar and needs no container change.
2. **One width owner.** `examWorkspace.css` declares the default, minimum and editor-measure tokens
   on `.xw-root`. `ExamWorkspaceView.vue`'s root carries
   `data-side="none|open|export|details|preview"`. One `.ws__body` grid rule per state builds
   `list | minmax(0, 1fr) editor | side`. The `.ws--drawer` and `.ws--preview` classes and the
   `var(--xw-drawer, 380px)` fallbacks are deleted. The tablet floating panels read a named 380 px
   token.
3. **Default widths.** The question list is `clamp(260px, 18%, 340px)` of the workspace width. The
   print preview is `clamp(360px, 34%, 800px)`, with the whole page scaled to fit. The editor
   content cap rises from 860 to 1040 px. The three drawers share one width: 320 px by default, 300 px
   minimum. Exportera's format choice becomes a vertical list so it fits.
4. **Resizable panels (desktop).** A drag handle sits on each panel border, and every panel collapses
   and reopens. Each panel has a designed minimum; below it the panel keeps its minimum layout and
   scrolls internally: list 260, editor 400, drawer 300, preview 300 px. When space runs out, the
   side panel squeezes first, then the list, and the editor last; nothing closes on its own. A drag
   stops at the minimum. The list collapses to a 44 px rail with one expand glyph and a draggable
   edge; a side panel closes with its × and reopens from its header button. Widths and collapse
   state are remembered per browser. The mechanism is in L8-L10.

## Contract Inputs

- User request 2026-10-19 in the Hemma orchestrator session (944b5a5a), relayed in assignment
  bd0f1693, with figures of about 1460 / 450 / 390 / 530 device px, which equal
  1040 / 320 / 380 CSS px at about 1.4x scaling. User answers the same day: Q2, Q3 and Q4 as
  recommended, and Q5 yes, with direction on resizing, collapsing and internal scrolling. Q1 and
  Q6-Q10 answered as recommended the same day; the user saw a mock of the collapsed list rail.
- Retained plan, evidence and ledger:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a153bf-e25e-7acd-b6b4-551ee64c8708/evidence/planning/TASK-SKRIPT-41-02-04/plan.md`.
- Code: `components/layout/LandingLayout.vue:52-56, 109-126`; `components/layout/AuthLayout.vue:53-78, 249-270, 345-351`;
  `views/apps/ExamWorkspaceView.vue:261-264, 430-456, 481-499`; `views/apps/exam-workspace/examWorkspace.css:16-22, 150-159`;
  `ExamWorkspaceEditorPane.vue:207`; `ExamWorkspaceDrawer.vue:107-117`; `ExamWorkspacePrintPreviewPanel.vue:111-147`;
  `ExamWorkspaceExportDrawer.vue:80-95`; `ExamWorkspaceQuestionList.vue:308-311`; `useExamWorkspaceSideColumns.ts:26, 62-78`;
  `stores/layout.ts:32-41`. Paths are under `frontend/apps/skriptoteket/src/`.

## Core Vertical And Performance

The change is frontend only. JS selects the side state and, while the user drags, writes the
requested width as an inline custom property. Clamping is done in CSS. During a drag the handle
reads the container width once per pointer move; nothing is measured at rest, and no resize
listener is added. No performance concern.

## Validation

- Focused Vitest (jsdom; it computes no grid widths, so it proves state and contract only):
  - `ExamWorkspaceLayoutSlice.spec.ts`: the root's `data-side` is `none`, `open`, `export`,
    `details` and `preview` in each state on desktop. Opening the preview clears the drawer, and
    opening a drawer clears the preview. Tablet and phone keep their drawer variants and render no
    handles.
  - `LandingLayout.spec.ts`: the full-frame switch applies on both public `documents.conversion_hub`
    routes and on no other public route.
  - The column-size composable spec covers:
    - arrow, Shift+arrow, Home and End steps within the minimum and maximum;
    - Enter collapses and restores;
    - Shift+Enter and double-click reset to the default and delete the stored width;
    - `aria-valuenow`, `aria-valuemin` and `aria-valuemax` follow the width;
    - a stored value restores on mount;
    - invalid stored JSON is ignored;
    - a storage that throws on read or write leaves the workspace rendering at defaults.
  - The `stores/layout.ts` spec: a throwing storage leaves focus mode and the sidebar at their
    defaults.
- Frontend `typecheck`, `lint` and `build` through the `integrated-frontend-stack` Skriptoteket
  commands.
- Staging walk (`staging-walk`, exam converter UI) on the guest and signed-in workspaces with an exam
  open:
  - Widths: for each side kind at default widths, read `getBoundingClientRect().width` of the list,
    editor and side tracks at 1280, 1440 and 1920 px windows, and at 2560 px through DevTools device
    emulation, since the Mac display is narrower. Check that the editor is widest and that
    `document.documentElement.scrollWidth === clientWidth`.
  - Screenshots at 1440 and 1920 px: the guest workspace with Öppna open, and the signed-in
    workspace with the print preview open.
  - Resizing: drag each handle out and in; collapse and reopen the list and a side panel; reload and
    find the widths kept; double-click to reset; operate a handle by keyboard.
  - Below the minimum: drag a panel wide enough to squeeze another below its minimum, and take a
    screenshot showing it scroll inside itself while the rest of the layout holds.
  - Confirm by measurement the estimated content minimums (Öppna chip row, editor head row, list row)
    and the Exportera format layout.
  - Evidence goes to the retained root.
- `pdm run docs-validate`.

### Resume here (2026-10-19, planning by lead bd0f1693)

- Branch `codex/task-skript-41-02-workspace-width-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-41-02-workspace-width-remote`, from `origin/main`
  `eba9d0f2`. Never pushed.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a153bf-e25e-7acd-b6b4-551ee64c8708`.
  It holds the plan and the Explorer discoveries.
- Status `proposed`. Every ledger row is closed (user answers 2026-10-19), and the plan passes
  `validate --require-closed`. No code is written. No junior launches until the user accepts the plan.
- Junior units after acceptance:
  - `ew-width-owner`: `examWorkspace.css`, `ExamWorkspaceView.vue`, `ExamWorkspaceEditorPane.vue`,
    `ExamWorkspaceDrawer.vue`, `ExamWorkspacePrintPreviewPanel.vue`, `ExamWorkspaceLayoutSlice.spec.ts`.
  - `guest-full-frame`: `LandingLayout.vue`, `LandingLayout.spec.ts`.
  - `ew-column-sizes`: the new column-size composable and its zod-validated storage plus spec;
    `stores/layout.ts` storage wrapping plus its spec.
  - `ew-export-format-list`: `ExamWorkspaceExportDrawer.vue` format choice as a vertical list, plus
    its spec.
  - `ew-splitter-wiring`: the handle component, the list collapse rail and the glyph in
    `ExamWorkspaceQuestionList.vue`, and the wiring into `ExamWorkspaceView.vue`. It runs after
    `ew-width-owner` and `ew-column-sizes`.
  - The first four run in parallel with disjoint files. Then the lead runs the focused checks, asks
    for the domain suite, and requests the staging walk.

## Stop Conditions

Stop and report in any of these cases:

- a fourth side-panel kind appears;
- another public route renders the guest workspace;
- the signed-in shell must change to meet the default editor-widest rule at 1040 px;
- the staging walk shows page-level horizontal scroll, an editor narrower than a side track at default widths, or a measured content minimum above the agreed minimum.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| L1  | The empty margins come from LandingLayout's 1040 px `.landing-frame` and `.landing-main` padding; the workspace sets no width cap. |
| L2  | The column and side-panel widths apply to the guest and signed-in workspaces; the full-width change touches the guest route only; the signed-in 240 px sidebar stays. |
| L3  | LandingLayout fills the frame on the public `documents.conversion_hub` routes, selected by route name plus appId like AuthLayout; the top bar stays; other public pages keep 1040 px. |
| L4  | One width owner: tokens on `.xw-root` and `data-side` on the workspace root; `.ws--drawer`, `.ws--preview` and `var(--xw-drawer, 380px)` fallbacks are deleted. |
| L5  | At the default widths the editor is the widest column with any side panel open at every desktop workspace width from 1040 px, with no horizontal page scroll; a user drag may override this down to the editor's minimum. |
| L6  | Tablet and phone layouts are unchanged and get no resize handles; tablet floating panels read a named 380 px token. |
| L7  | jsdom tests prove state and contract; rendered widths and resizing are proven by the staging walk. |
| L8  | Desktop drag handles on each panel border, pointer-captured; JS writes only the requested width as an inline custom property; CSS clamps; panel content keeps its minimum layout and scrolls internally; the drag is the documented layout-geometry exception. |
| L9  | One zod-validated localStorage key `skriptoteket.exam-workspace.columns` shared by both routes; every read and write wrapped; defaults when missing, invalid or unreadable; no versioned readers; stored widths are clipped by CSS, never rewritten; `stores/layout.ts` storage calls get the same wrapping. |
| L10 | Each handle is a focusable `role="separator"` with aria-valuenow/min/max and a Swedish label; arrows 16 px, Shift+arrows 64 px, Home/End to minimum/maximum, Enter collapses and restores, Shift+Enter and double-click reset to the default. |
| Q2  | The question list is `clamp(260px, 18%, 340px)` of the workspace width. |
| Q3  | The print preview is `clamp(360px, 34%, 800px)` of the workspace width, page scaled to fit; the editor stays widest at default widths. |
| Q4  | The editor content cap is 1040 px, centred in the editor column. |
| Q5  | Panels are resizable with a drag handle, collapsible, have designed minimums with internal scroll below them, and widths are remembered per browser. |
| Q1  | Öppna, Exportera and Provets uppgifter share one drawer width, 320 px default and 300 px minimum; Exportera's format choice is a vertical list; the preview keeps its own width. |
| Q6  | The editor-widest rule applies to the default layout only; a drag may make a side panel wider than the editor, down to the editor's minimum. |
| Q7  | When space runs out the side panel squeezes first, then the list, the editor last; a squeezed panel keeps its minimum layout and scrolls inside itself; nothing closes on its own. |
| Q8  | The list collapses to a 44 px rail with one expand glyph and a draggable edge; a side panel closes with its × and reopens from its header button. |
| Q9  | A drag stops at the panel's minimum; collapse happens only through the glyph or Enter on the handle. |
| Q10 | Minimum widths: question list 260 px, editor 400 px, drawer 300 px, print preview 300 px. |
