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
- The editor column is the widest column whenever a drawer or the print preview is open, on the guest and signed-in workspaces, with no horizontal page scroll
- Each side-panel kind (Öppna, Exportera, Provets uppgifter, print preview) has its own desktop width, set in one place
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

This task changes three things:

1. **Full width (guest).** LandingLayout fills the frame on the public `documents.conversion_hub`
   routes: no max-width and no `.landing-main` padding. The landing top bar stays. The route is
   selected the way AuthLayout already selects full-frame routes, by route name plus appId. Other
   public pages keep the 1040 px column. The signed-in route already fills its frame beside the
   240 px shell sidebar and needs no container change.
2. **One width owner.** `examWorkspace.css` declares one token per desktop track on `.xw-root`: the
   question list, each drawer kind (`open`, `export`, `details`), the print preview, and the editor
   content measure. `ExamWorkspaceView.vue`'s root carries
   `data-side="none|open|export|details|preview"`. One `.ws__body` grid rule per state builds
   `list | minmax(0, 1fr) editor | side`. The `.ws--drawer` and `.ws--preview` classes and the
   `var(--xw-drawer, 380px)` fallbacks are deleted. The tablet floating panels read a named
   380 px token.
3. **Widths.** The values come from the closed ledger (open rows Q1-Q4 in the retained plan wait for
   the user). Both routes render the same `ExamWorkspaceView.vue`, so the width rule applies to
   both.

## Contract Inputs

- User request 2026-10-19 in the Hemma orchestrator session (944b5a5a), relayed in assignment
  bd0f1693. The screenshot path it names
  (`/home/paunchygent/apps/skriptoteket/.orchestration/guest-workspace-cramped-2026-10-19.png`)
  holds a chat window, not the workspace. The plan uses the brief's description: a cap of about
  1460 device px and columns of about 450 / 390 / 530 device px. These equal 1040 / 320 / 380 CSS px
  at about 1.4x scaling.
- Retained plan, evidence and ledger:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a153bf-e25e-7acd-b6b4-551ee64c8708/evidence/planning/TASK-SKRIPT-41-02-04/plan.md`.
- Code: `components/layout/LandingLayout.vue:52-56, 109-126`; `components/layout/AuthLayout.vue:53-78, 249-270, 345-351`;
  `views/apps/ExamWorkspaceView.vue:261-264, 430-456, 481-499`; `views/apps/exam-workspace/examWorkspace.css:16-22`;
  `ExamWorkspaceEditorPane.vue:207`; `ExamWorkspaceDrawer.vue:111-117`; `ExamWorkspacePrintPreviewPanel.vue:111-147`;
  `useExamWorkspaceSideColumns.ts:26, 62-78`. Paths are under `frontend/apps/skriptoteket/src/`.

## Core Vertical And Performance

The change is CSS plus one semantic attribute; there is no backend change. JS selects only the side
state (`drawer`, `previewOpen`). It measures no geometry and adds no resize listener. No
performance concern.

## Validation

- Focused Vitest (jsdom; it computes no grid widths, so it proves the semantic contract only):
  - `ExamWorkspaceLayoutSlice.spec.ts`: the root's `data-side` is `none`, `open`, `export`,
    `details` and `preview` in each state on desktop. Opening the preview clears the drawer, and
    opening a drawer clears the preview. Tablet and phone keep their drawer variants.
  - `LandingLayout.spec.ts`: the full-frame switch applies on both public `documents.conversion_hub`
    routes and on no other public route.
- Frontend `typecheck`, `lint` and `build` through the `integrated-frontend-stack` Skriptoteket
  commands.
- Staging walk (`staging-walk`, exam converter UI) on the guest and signed-in workspaces with an exam
  open. For each side kind, it reads `getBoundingClientRect().width` of the list, editor and side
  tracks at 1280, 1440, 1920 and 2560 px window widths. It checks that the editor is widest and that
  `document.documentElement.scrollWidth === clientWidth`. It takes screenshots at 1440 and 1920 px of
  the guest workspace with Öppna open and the signed-in workspace with the print preview open.
  Evidence goes to the retained root.
- `pdm run docs-validate`.

### Resume here (2026-10-19, planning by lead bd0f1693)

- Branch `codex/task-skript-41-02-workspace-width-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-41-02-workspace-width-remote`, from `origin/main`
  `eba9d0f2`. Never pushed.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a153bf-e25e-7acd-b6b4-551ee64c8708`.
  It holds the plan and the 13 Explorer discoveries.
- Status `proposed`. Open user rows in the plan: Q1 drawer widths, Q2 list width, Q3 preview width,
  Q4 editor line length, Q5 resizable columns. No code is written.
- Junior units after acceptance, run in parallel with disjoint files:
  - `ew-width-owner`: `examWorkspace.css`, `ExamWorkspaceView.vue`, `ExamWorkspaceEditorPane.vue`,
    `ExamWorkspaceDrawer.vue`, `ExamWorkspacePrintPreviewPanel.vue`, `ExamWorkspaceLayoutSlice.spec.ts`.
  - `guest-full-frame`: `LandingLayout.vue`, `LandingLayout.spec.ts`.
  - Then the lead runs the focused checks and asks for the staging walk.

## Stop Conditions

Stop and report in any of these cases: a fourth side-panel kind appears; another public route renders the
guest workspace; the signed-in shell must change to meet the editor-widest rule at 1040 px; the
staging walk shows horizontal scroll or an editor narrower than a side track.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| L1  | The empty margins come from LandingLayout's 1040 px `.landing-frame` and `.landing-main` padding; the workspace sets no width cap. |
| L2  | The column and side-panel widths apply to the guest and signed-in workspaces; the full-width change touches the guest route only; the signed-in 240 px sidebar stays. |
| L3  | LandingLayout fills the frame on the public `documents.conversion_hub` routes, selected by route name plus appId like AuthLayout; the top bar stays; other public pages keep 1040 px. |
| L4  | One width owner: per-track tokens on `.xw-root` and `data-side` on the workspace root; `.ws--drawer`, `.ws--preview` and `var(--xw-drawer, 380px)` fallbacks are deleted. |
| L5  | The editor is the widest column with any side panel open at every desktop workspace width from 1040 px, with no horizontal page scroll. |
| L6  | Tablet and phone layouts are unchanged; tablet floating panels read a named 380 px token. |
| L7  | jsdom tests prove the semantic contract; rendered widths are proven by the staging walk. |
