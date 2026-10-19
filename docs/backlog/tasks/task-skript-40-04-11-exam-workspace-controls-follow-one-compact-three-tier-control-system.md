---
type: task
id: TASK-SKRIPT-40-04-11
title: Exam workspace controls follow one compact three-tier control system
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
acceptance_criteria: []
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Source: four user messages of 2026-10-19, relayed by the Hemma orchestrator session (944b5a5a).

1. On a Fritextfråga item, the user circled the boxed Skrivyta row and "+ Kriterium". Quotes: "Button *containers* are too big for a compact workspace" and "Direction is NO visible containers for tools, just the glyphs".
2. On the workspace header (staging 26f84883), the user wrote:
   - "you barely see the file name";
   - "why is Osparat so far from the save button?";
   - the undo buttons are "super large" and "should be within the toolbar integrated";
   - Förhandsgranska should be "a preview glyph and then PDF with a tooltip";
   - the admin-only AI note "eats a lot of valuable space";
   - "buttons are too spaced out";
   - Ny uppgift and Markera should be "only the glyph and the little word", lined up on the glyph.
3. On density, the user wrote: "the buttons are too large"; controls should "size-wise align with the nav bar"; and the workspace "gives a bit of a scattered impression… almost like it's a tablet type of user interface". VS Code is the benchmark.
4. The user clarified the scope: this task is the control design system of the compact exam workspace. It covers button sizes, containers, toolbar layout, and padding and spacing, with exact values and no wasted space. The user's three tiers are:
   - glyph only where the glyph is clear;
   - glyph plus a short eyebrow word directly above it where the glyph alone is not clear;
   - text inside a container where a button needs it.

   One shared owner holds the rule, the sizes, the gaps and the states. There is no per-component control CSS.

Cause: the workspace has no single control owner, so each surface sizes its own controls. Measured on main 26f84883:

- `.xw-btn` is a bordered 36 px box (44 px on touch) with a 20 px glyph (`examWorkspace.css:16-48`).
- The mark toolbar uses 32 px Tailwind boxes with 16 px Lucide components imported directly, bypassing the shared glyph catalogue, which already has these meanings (`ExamWorkspaceMarkToolbar.vue:87-163`).
- The Skrivyta, criteria and gap fields use 40 px and 44 px bordered Tailwind boxes (`ExamWorkspaceWritingLinesField.vue:78/90/102`, `ExamWorkspaceCriteriaField.vue:186/199`, `ExamWorkspaceGapAutomaticValues.vue:52`).
- Raw 28 px values sit in `.xw-rm`, `.xw-linkbtn`, `.xw-label` and `.xw-okline` (`examWorkspace.css:74-126`) and in `.qhead__type` (`ExamWorkspaceQuestionHead.vue:351`).
- Heads are raw 52 px and 60 px (`ExamWorkspaceDrawer.vue:103`, `ExamWorkspacePrintPreviewPanel.vue:129`, `ExamWorkspaceQuestionList.vue:310`, `ExamWorkspaceHeader.vue:348`).
- Glyph sizes are 12, 14, 16, 18, 20 and 32 px across the directory.

The shared tokens already define a 28 px workbench control (`--huleedu-workbench-control-height`), a 16 px workbench glyph and a 20 px navigation glyph. The workspace uses them in only a few places.

This task puts one control system into `examWorkspace.css` and moves every exam workspace control onto it. Under the recommended answers to D12 and D13, every value is an existing huleedu-integrated token or a calc of tokens, so the shared package needs no new token. The system is drafted in `evidence/mockups/controls/proposed-controls.css` in the retained root, and the mocks at 1440 and 1920 px are beside it.

The export menu's rows and its download and save logic belong to a separate lead (user correction, 2026-10-19). This task touches the export files only to rename classes and to put the Exportera trigger in the header's tier 2.

Non-goals:

- No change to the shell top bar or the navigation rail.
- No backend or document change.
- No change to the 40-04-10 points notes beyond the class rename; their decided glyph look is 40-04-10's.

## Contract Inputs

- Story: ST-SKRIPT-40-04 (exam workspace redesign). The prototype's control family is in `frontend/apps/skriptoteket/src/views/apps/exam-workspace/examWorkspace.css`.
- User rule on one-off decisions, 2026-10-19: a simple one-off decision is text that states the choice, plus yes/no glyphs from the shared catalogue (`confirm`, `close`). The names go only in the tooltip and aria-label. TASK-SKRIPT-40-04-10's points note is the user's own example.
- User answers of 2026-10-19 (AskUserQuestion, orchestrator session):
  - the scope is the whole workspace;
  - apply-to-all runs at once, with no confirmation, and Ångra reverses it; its glyph is stacked layers, with the tooltip "Använd {n} rader för alla fritextfrågor";
  - the count sits between − and +, and the "Skrivyta: 10 rader" label goes;
  - new glyph meanings go into the shared skill-repository `uiGlyphs.ts` through that repository's change route.
- `huleedu-ui-design` (`visual-system.md`, `dense-workspaces.md`):
  - use the shared `--huleedu-workbench-*` roles;
  - icon-only actions have no frame;
  - hover and press tint the glyph's area, and hover applies on fine pointers only;
  - the touch target is 44 px;
  - repeated operational actions sit in compact glyph rows.
- Token ownership: `REF-frontend-design-system-resource-package-contract` (skill repository, lines 86-100) keeps consumer token files byte-identical and changed only through `design-system sync`. A workspace alias block in a repo-owned CSS file is outside the mirror.
- The parallel owners and their shared files:
  - TASK-SKRIPT-41-02-04 (workspace width): `ExamWorkspaceQuestionList.vue`, `examWorkspace.css`, `ExamWorkspaceEditorPane.vue`, `ExamWorkspaceDrawer.vue` and `ExamWorkspacePrintPreviewPanel.vue`.
  - The gap-toggle-back lead (73032e62): `ExamWorkspaceMarkToolbar.vue` and the editor-toolbar undo and redo.
  - The export lead: `ExamWorkspaceExportMenu.vue`, `ExamWorkspaceExportBlockers.vue` and `ExamWorkspaceExportDrawer.vue`.
- The retained plan, with the full control inventory and the ledger: `.orchestration/context/sessions/01a15383-370d-707d-876f-cf2953eb536b/evidence/planning/TASK-SKRIPT-40-04-11/plan.md` in the primary checkout.

## Core Vertical And Performance

The core vertical is one Fritextfråga editing pass at 1440 px on a fine pointer. The teacher sees:

- the header as one 52 px bar: the title with its metadata; Ångra and Gör om; the Öppna, Exportera and PDF eyebrow tools; the AI glyph; then Osparat directly beside Spara;
- the list head with the Ny uppgift and Markera eyebrow tools;
- the question head;
- the 36 px editor toolbar;
- the Skrivyta row "− 10 + | layers";
- the Bedömningskriterier label with its add glyph.

Every tool is a 28 px boxless box with a 20 px glyph, the same glyph size as the navigation rail. A coarse pointer gets the same controls at 44 px. No performance concern applies.

Planned junior units, in order. Each unit has its own focused spec. The final list depends on the open questions in Resume here.

1. Overlap probe (lead): measure the computed layout of the Skrivyta and Bedömningskriterier fieldsets in a real browser at 1024 and 1440 px, and record the cause.
2. Shared glyph meanings (skill repository, through its change route):
   - add `apply-to-all` (Lucide Layers), `make-gap` (TextCursorInput) and `gap-tool` (MousePointerClick);
   - release a package version, then run `design-system sync` and `pdm run design-system-validate` here.
3. Control system: add the token block and the `.xw-tool`, `.xw-tool--eyebrow`, `.xw-cmd`, `.xw-bar` and `.xw-stepper` classes and the state rules to `examWorkspace.css`. The values come from the draft.
4. Header: `ExamWorkspaceHeader.vue`, plus the Exportera trigger in `ExamWorkspaceExportMenu.vue`:
   - the title and inline metadata;
   - the tool groups;
   - the AI note becomes the tooltip and the `aria-describedby` text of the AI glyph;
   - Osparat moves beside Spara.
5. List: `ExamWorkspaceQuestionList.vue`:
   - the head carries the Ny uppgift and Markera eyebrow tools, and the mark bar shows only while marking;
   - Lägg till instruktioner becomes a list entry.
6. Question head and tools: `ExamWorkspaceQuestionHead.vue` and `ExamWorkspaceQuestionTools.vue`.
7. Editor toolbar: `ExamWorkspaceMarkToolbar.vue` moves to `UiGlyph` meanings and tier 1 tools, and the floating gap button in `ExamWorkspaceRichTextEditor.vue` takes its size from the tokens. This unit is coordinated with lead 73032e62.
8. Fritextfråga fields:
   - `ExamWorkspaceWritingLinesField.vue`: "− 10 +", then the apply-to-all glyph;
   - `ExamWorkspaceCriteriaField.vue`: the add glyph moves into the label row, remove becomes a tier 1 delete, and the inputs use `xw-input`.
9. Other editor tools: the ordering, instruction, gap popover, gap answer list and gap automatic value components, the course combobox clear, the inline notice close, the phone strip and the sign-in bar.
10. Panels, dialogs and menus: the drawer, print preview, details drawer, open drawer, editor pane, import box and save-as dialog; the class rename in the three export files; menu rows at 32 px.
11. Removal and guard:
    - delete `.xw-btn*`, `.xw-rm`, `.xw-linkbtn`, `--xw-ctl` and `--xw-ctl-fine`;
    - remove all control sizing from scoped CSS;
    - a static spec fails on Tailwind size classes, raw control sizes or the deleted classes in the exam workspace directory.
12. One-off offers, as Q5 decides.

## Validation

- Each changed component's focused Vitest spec checks, per control:
  - its tier class;
  - its accessible name, which contains the eyebrow word for tier 2;
  - its native title, with the reason title while disabled;
  - the emitted event, and the pressed or expanded state where one exists.
- The guard spec in unit 11 passes on the whole exam workspace directory.
- Keyboard: Tab reaches each changed control in visual order; Enter and Space activate it; focus-visible shows the 2 px `--huleedu-action-40` ring.
- The lead takes browser screenshots on local dev at 1440 and 1920 px on a fine pointer and at 1024 px with coarse-pointer emulation. They cover the header, the list head, the question head, the editor toolbar and the Fritextfråga fields, at rest, on hover and on focus, and they go to the user and `ui-copy-reviewer`.
- Frontend typecheck, lint and build for the app; `pdm run design-system-validate` after unit 2.
- No staging walk: the user's rule of 2026-10-17 limits staging walks to the exam converter.

## Stop Conditions

- Stop before writing code until the user has answered the open questions in Resume here and the status is ready.
- Stop and report when a value cannot be expressed with an existing shared token, because that needs a package change.
- Stop and report when a unit would edit a drift-checked mirror by hand rather than through `design-system sync`.
- Before units 5, 7 and 10, merge current main and check the named parallel owners' branches. If one of them changes the same lines, stop and report.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | One owner: `examWorkspace.css` holds the tier rule's classes, every control size, the bar heights, the gaps and the states, as a `.xw-root` token block whose values alias existing huleedu-integrated tokens. Components add no control CSS and pass no glyph size to a control; `.xw-tool svg` and `.xw-cmd svg` set it (user 2026-10-19 scope clarification). Whether any value needs a new shared token is D12 and D13. |
| T2  | Three tiers (user 2026-10-19). Tier 1, `.xw-tool`: the glyph only, where the glyph is a convention or its row names it. Tier 2, `.xw-tool--eyebrow`: a short word directly above the glyph where the glyph alone is ambiguous. Tier 3, `.xw-cmd`: text inside a container for primary, committing and dialog commands. Menu rows, list entries, segment options and value triggers (title, question type) are not tiered controls and keep their text. |
| T3  | Names: a tier 1 or tier 2 control's action phrase is its aria-label and native title; a tier 2 aria-label contains its eyebrow word (WCAG 2.5.3). While disabled by a bound or a no-op, the title gives the reason. Glyphs are decorative to assistive technology. |
| T4  | Apply-to-all (user 2026-10-19): a tier 1 glyph with the new shared meaning `apply-to-all` (Lucide Layers). Tooltip and aria-label "Använd {n} rader för alla fritextfrågor"; while every free-text item already has n lines, the title is "Alla fritextfrågor har redan {n} rader". It runs at once, with no confirmation; Ångra reverses it. |
| T5  | Stepper (user 2026-10-19): the field label reads "Skrivyta"; the row is the decrement glyph, the count, the increment glyph, a separator and the apply-to-all glyph. The count has the title "{n} rader" and a slot two digits wide. The label no longer repeats the count. |
| T6  | Scope (user 2026-10-19): every control in the exam workspace except the export menu's rows and its download and save logic, which belong to the export lead. The export files get only the class rename and the header trigger. |
| T7  | New glyph meanings go into the shared skill-repository `uiGlyphs.ts` through that repository's change route, then reach this repository through `design-system sync` (user 2026-10-19). The mark toolbar uses the catalogue's existing `bold`, `italic`, `underline`, `superscript`, `subscript` and `heading-1..3` meanings. |
| T8  | Validation is the focused specs, the guard spec, keyboard reach and focus ring, and the screenshots named above; no staging walk. |

## Resume here (2026-10-19, held)

Status stays proposed. HELD on the orchestrator's instruction (944b5a5a, 2026-10-19): the user moved the toolbar and button redesign (density, sizes, tiers, tokens, header layout) into its own Mac session, "Exam workspace toolbar redesign: inventory and mockups", which owns the contract now. No junior was launched and no code was written. The branch has current origin/main merged (41-02-04, 0b52aed4).

Handover material (retained root `.orchestration/context/sessions/01a15383-370d-707d-876f-cf2953eb536b/` in the primary checkout):

- `evidence/planning/TASK-SKRIPT-40-04-11/plan.md`: its Evidence section holds the 98-control inventory with file:line and the proposed tiers; its ledger holds the decisions D1-D17.
- `evidence/mockups/controls/proposed-controls.css`, `before-1440.png`, `after-1440.png`, `before-1920.png`, `after-1920.png`, and `build.py`, which regenerates them.
- `evidence/mockups/one-off-offers.png`.

The user's answers of 2026-10-19 (AskUserQuestion, relayed by the orchestrator), recorded as given. The orchestrator reported that the user accepted the plan with them; the held status replaces that acceptance until the redesign session decides:

- D12 sizes: "28 box / 16 glyph". Tools are a 28 px box with a 16 px glyph; this is not the lead's recommendation of a 20 px glyph.
- D14: 44 px on a coarse pointer.
- D15: the eyebrows as mocked (Öppna, Exportera, PDF, Ny uppgift, Markera, Import). Gör till lucka stays T1.
- D6 states: as mocked.
- Q5 one-offs: text plus accept and dismiss glyphs. The course offer has no dismiss.
- D13: A, a local `.xw-root` alias block over the existing shared tokens; no new shared values.
- D16 header, changed by other decisions:
  - the user chose autosave as Spara (TASK-SKRIPT-40-04-14, lead 73032e62), so the Spara button and Osparat go;
  - the header ends in a fixed-width status slot: a cloud-check glyph plus "Sparat", which becomes "Sparar …" while a write runs, with no shift;
  - "Spara som …" moves into the Öppna/Exportera group;
  - the rest of D16 is as recommended.
- Gap tool, decided in TASK-SKRIPT-40-04-13:
  - the switch (text-select glyph) is the only gap control;
  - the toolbar Lucka and the floating Gör till lucka glyph are removed, and there is no empty-gap control;
  - Ångra and Gör om become the first two glyphs of the question toolbar (TASK-SKRIPT-40-04-14);
  - so Gör till lucka and Lucka leave the inventory, and the switch and the toolbar undo pair are styled as T1.
- Ownership: 73032e62 owns MarkToolbar's behaviour and this task owns the shared look (classes and tokens); the export lead (TASK-SKRIPT-40-04-16) owns ExportMenu. Merge order on shared files: 41-02-04, then 40-04-08, then the others.

Lead notes for the new owner:

- The type offer's dismiss can clear the item's `suggested_kind` through `editDocument`, which Ångra reverses; no new stored field is needed.
- The AI-interpretation offer's accept ("Behåll AI-tolkningen") would need a stored mark that the interpretation was kept, because `canUndoInterpretation` (`examWorkspaceItemEdits.ts:169`) shows the offer for as long as `answer_key.origin` is `ai_interpreted`.
- A new `apply-to-all` glyph meaning needs a governed skill-repository release (the precedent is TASK-SKILL-REP-0330, huleedu-integrated 0.1.32) in a parent-owned skill-repository worktree.

Next: the redesign session's contract decides this task's future.
