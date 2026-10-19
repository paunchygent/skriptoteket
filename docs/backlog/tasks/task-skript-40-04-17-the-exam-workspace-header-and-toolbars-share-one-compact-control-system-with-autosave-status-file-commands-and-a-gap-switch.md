---
type: task
id: TASK-SKRIPT-40-04-17
title: The exam workspace header and toolbars share one compact control system with autosave status, file commands and a gap switch
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-19'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'User closure 2026-10-19 in Mac session 0b6afee3 ("Close TASK-SKRIPT-40-04-17 as done"). Independent ruthless-reviewer fd5c66c4 (Pi) at f87c2d44 returned changes_requested with F1-F3 medium and N1 low; all repaired at 7073e58e and admitted on focused proof without rereview. Merged to main as aac5bdfd and 32460f67. Hemma staging walks at 6a557b5d and 32460f67 passed every walked check; the 375 px coarse-pointer composition was not walked because Edge cannot emulate a coarse pointer or a window under 500 px.'
task_kind: story
acceptance_criteria:
  - The header is one row with the title block, the file group (Öppna, Spara som …, Exportera, Importera), PDF, the AI glyph and the autosave status slot, with no Spara button and no Ångra or Gör om, and every command keeps its word at a 1040 px workspace while only the title truncates
  - Header commands are 32 px boxless controls with a 20 px glyph and a 13 px word beside it; in-content tools are 28 px boxes with 16 px glyphs, 2 px apart, groups split by 1 x 18 px separators; both are 44 px on a coarse pointer
  - The autosave slot shows cloud-check with "Sparat", a loader with "Sparar …" or the blocker glyph with "Inte sparat" after a failed write, and never moves a neighbouring control
  - Clicking the exam title or its pencil edits the title in place; Enter or blur commits and Escape restores it
  - The question editor toolbar reads Ångra, Gör om | B, I, U, upphöjd, nedsänkt | Luckverktyg, Tom lucka | H1, H2, H3, with no Lucka text button
  - The list head is one 40 px row with "Frågor (n)", the collapse glyph, and glyph-only Ny uppgift and Markera that neither wraps nor clips at the 260 px minimum list width, and the mark bar shows only while marking
  - The new sizes are shared design-package tokens and the new glyphs are shared catalogue meanings, both reaching Skriptoteket through the mirror sync
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user reviewed the exam workspace header and toolbars on 2026-10-19 (twelve annotated points), iterated on an interactive mock built on a static copy of the staging workspace, and accepted the layout with the settings autosave, 32 px header commands, words beside the glyphs, no group names and the gap switch plus Tom lucka; on 2026-10-19 the user confirmed that Tom lucka stays and that an empty gap does not survive its question closing. This task builds that layout. The user closed the remaining questions (tokens, glyphs, ownership, narrowest width) the same day through AskUserQuestion in the planning session. The user approved readiness and the start of units 1, 2 and 4 on 2026-10-19; on the same day the user decided to start units 3 and 5 at once on the gap branch's merge with main (codex/task-skript-40-04-gap-toggle-back-remote, which carries 40-04-13 and 40-04-14) instead of waiting for main.

Scope (T15): the look and placement of the workspace header (`ExamWorkspaceHeader.vue`), the question list head (`ExamWorkspaceQuestionList.vue`), the question head (`ExamWorkspaceQuestionHead.vue`, `ExamWorkspaceQuestionTools.vue`) and the question editor toolbar (`ExamWorkspaceMarkToolbar.vue`), with the shared faces in `examWorkspace.css`. TASK-SKRIPT-40-04-11 is folded into this task and superseded; its decided terms for the writing-line stepper, the one-off offers and the menu rows carry over unchanged from its retained plan. Behaviour stays with its owners: the gap switch with 40-04-13, undo, redo and autosave with 40-04-14, the export menu with 40-04-16. This task supersedes 40-04-01 ledger row T25 (T16).

Units, each for one implementer, in order:

1. Shared package (T13, T14): in skill-repository `resources/frontend-design-system/huleedu-integrated/`, add the header command height (32 px, 44 px coarse), the toolbar separator (1 x 18 px, navy-20, 4 px margin) and the tool group gap (2 px) tokens, and the glyph meanings `gap-tool`, `empty-gap`, `autosave-saved`, `autosave-saving` and `file-import` in `uiGlyphs.ts`, through that repository's change route. Sync the Skriptoteket mirror.
2. Faces (T3, T4, T5): in `examWorkspace.css`, define the header command face and the in-content tool face from those tokens, and delete the literal `--xw-ctl` and `--xw-ctl-fine`.
3. Header (T1, T2, T6, T7, T8, T12): rebuild the header row, the status slot, Spara som, Importera, PDF, the AI glyph and the inline title edit.
4. List head and question head (T9, T10).
5. Editor toolbar (T11): the group order, the gap switch with its pressed underline and Tom lucka, using catalogue meanings only.

## Contract Inputs

- Story ST-SKRIPT-40-04 and the code on main at `f3c715305`.
- Retained plan with the closed ledger: `.orchestration/context/sessions/01a15437-a20c-72f4-b0b8-397637488146/evidence/planning/TASK-SKRIPT-40-04-17/plan.md`.
- Accepted mock and decisions: `.orchestration/context/sessions/01a15437-a20c-72f4-b0b8-397637488146/evidence/planning/toolbar-redesign/` (`decisions.md`, `inventory.md`, `mockups/rip/`).
- TASK-SKRIPT-40-04-11 retained plan (Hemma, `01a15383-370d-707d-876f-cf2953eb536b/evidence/planning/TASK-SKRIPT-40-04-11/plan.md`) for the carried-over terms.
- `huleedu-ui-design` invariants: glyph first, names in tooltip and aria-label; the layout holds still.

## Core Vertical And Performance

The core vertical is one Lucktext editing pass at a 1040 px workspace on a fine pointer: the teacher renames the exam by clicking its title, switches on Luckverktyg, clicks a word to make a gap, undoes it from the editor toolbar, and watches the status slot go from "Sparar …" to "Sparat" while no control moves. No material performance concern: the change is presentation only.

## Validation

- Focused Vitest specs beside the touched components: header structure and order, the status slot states, inline title edit (commit, blur, Escape), list head and mark bar, question head tools, editor toolbar order, tooltips and pressed states.
- `pdm run design-system-validate` after the mirror sync.
- Staging walk on Hemma (`staging-walk`) at 1440 px and at 1280 px with the sidebar expanded, checking every state change leaves controls in place, and with the question list dragged to its 260 px minimum and a two-digit question count, checking the list head neither wraps nor clips.

## Stop Conditions

- 40-04-14's autosave state or 40-04-13's gap-switch behaviour is not in this task branch's base when unit 3 or 5 starts (user decision 2026-10-19: the base may be the gap branch's merge with main instead of main): stop that unit and report; do not build an interim Spara button or Lucka button.
- 40-04-13's empty-gap insert, and its removal of a gap still empty when its question closes, is not in the base when unit 5 starts: build the rest of unit 5 and stop before Tom lucka; do not add the behaviour here.
- The skill-repository change for unit 1 is refused or not merged: stop before unit 2.
- The header cannot fit with words at a 1040 px workspace: stop and report the measured widths.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Autosave is the only save: no Spara button and no Osparat. A fixed-width status slot at the header's right end shows cloud-check with "Sparat", a spinning loader with "Sparar …" during a write, or after a failed write (40-04-14's `unsaved` state) the `blocker` glyph with "Inte sparat" and the failure detail as its tooltip, in a slot sized for its widest state.                                                                                                        |
| T2  | "Spara som …" is a header file command with the copy glyph, in the file group.                                                                                                                                                                                                                                                                                                                                                                                                    |
| T3  | Header command face: 32 px, boxless, 20 px glyph, 13 px weight-500 word beside it, 8 px inline padding, 6 px gap, 4 px radius; hover action 5 % on fine pointers only; pressed or open action 10 %; 2 px action-40 focus ring at offset 0; disabled navy-30; 44 px on coarse pointers.                                                                                                                                                                                            |
| T4  | In-content tool face: 28 px box, 16 px glyph, boxless, glyph only with the name in title and aria-label; hover white with a navy-20 border; pressed action 10 % with an action border; disabled opacity 0.4; 2 px between tools; 1 x 18 px navy-20 separator with 4 px margin between groups; 44 px on coarse pointers.                                                                                                                                                           |
| T5  | Words beside the glyph only where the glyph leaves the meaning open (Öppna, Spara som, Exportera, Importera, PDF, Import); Ny uppgift and Markera are glyph only (T9); no eyebrow words and no visible group names in this workspace.                                                                                                                                                                                                                                             |
| T6  | Header row: title block (title 16 px/600, pencil, meta "kurs · poäng" 12 px navy-70) · Öppna, Spara som …, Exportera ▾, Importera · PDF (eye, pressed toggle, tooltip "Förhandsgranska PDF") · AI · status slot; only the title truncates; no Ångra or Gör om in the header.                                                                                                                                                                                                      |
| T7  | Clicking the title or its pencil edits the title in place with the text selected; Enter or blur commits; Escape restores.                                                                                                                                                                                                                                                                                                                                                         |
| T8  | AI is glyph only; while limited to administrators it is disabled with the admin note as its tooltip and description, and no note text shows.                                                                                                                                                                                                                                                                                                                                      |
| T9  | List head is one 40 px row that fits at the 260 px minimum list width without wrapping or clipping: "Frågor (n)" (never truncated), the collapse glyph, Ny uppgift as a glyph-only tool (plus glyph, tooltip "Ny uppgift"; user 2026-10-19 after the 260 px measurement) and Markera as a glyph-only toggle (square, square-check when pressed, tooltip "Markera frågor") at every width; the "Skapa del av markerade (n)" row shows only while marking.                          |
| T10 | Question head shows Import (glyph and word), Granskad (check toggle, tooltips "Markera som granskad" / "Ångra granskad") and Fler åtgärder in the tool face, 2 px apart.                                                                                                                                                                                                                                                                                                          |
| T11 | Editor toolbar: Ångra, Gör om \| B, I, U, upphöjd, nedsänkt \| Luckverktyg (⌥⌘G), Tom lucka \| H1, H2, H3; tooltips "Ångra (⌘Z)" and "Gör om (⇧⌘Z)"; Tom lucka inserts an empty gap to fill afterwards, and a gap still empty when its question closes is removed (user 2026-10-19; this reverses 40-04-13 Q6 and Behaviour 9, whose behaviour stays with 40-04-13); no Lucka text button and no floating gap glyph; the pressed switch shows a 2 px action underline in its box. |
| T12 | At a 1040 px workspace every header command keeps its word on one row and only the title truncates; no desktop width collapses the words.                                                                                                                                                                                                                                                                                                                                         |
| T13 | The header command height, toolbar separator and tool group gap become shared tokens in the skill-repository design package, synced to the mirror; `examWorkspace.css` consumes them and deletes `--xw-ctl` and `--xw-ctl-fine`.                                                                                                                                                                                                                                                  |
| T14 | `gap-tool`, `autosave-saved`, `autosave-saving` and `file-import` become shared `uiGlyphs.ts` meanings, together with `empty-gap` for Tom lucka; the editor toolbar imports no Lucide icon directly.                                                                                                                                                                                                                                                                              |
| T15 | This task owns the look and placement of the header, list head, question head and editor toolbar; 40-04-11 is folded in and superseded with its other terms carried over; 40-04-13, 40-04-14 and 40-04-16 keep their behaviour and use these faces.                                                                                                                                                                                                                               |
| T16 | Supersedes 40-04-01 ledger row T25; Ångra and Gör om live in the editor toolbar.                                                                                                                                                                                                                                                                                                                                                                                                  |
| T17 | No walking skeleton: presentation inside the SPA, no system boundary crossed.                                                                                                                                                                                                                                                                                                                                                                                                     |
| T18 | Proof is focused component specs plus a Hemma staging walk at 1440 px, at a 1040 px workspace and with the question list at its 260 px minimum.                                                                                                                                                                                                                                                                                                                                   |

## Outcome

Units 1-5 are on `main`. The task merged as `aac5bdfd`; Tom lucka joined after 40-04-13's empty-gap insert landed, and the T11 order fix (Luckverktyg, Tom lucka) merged as `32460f67`. Independent code review at `f87c2d44` requested changes: F1 toolbar clipping, F2 two components over 500 lines, F3 an import relay through component refs (all medium), and N1 the title size (low). The parent admitted all four and repaired them at `7073e58e` on focused proof. Record: `.orchestration/context/sessions/01a15437-a20c-72f4-b0b8-397637488146/evidence/reviews/TASK-SKRIPT-40-04-17/` (`review-f87c2d44.md`, `admission-f87c2d44.md`). The Hemma staging walks at `6a557b5d` and `32460f67` passed every walked check: header row at 1422 px and at the 1040 px workspace, inline rename, status slot, 260 px list head, mark bar, gap switch, toolbar scroll at the editor minimum, a real Importera click, the T11 order and the Tom lucka insert. Not walked: the 375 px coarse-pointer composition, because Edge cannot emulate a coarse pointer or a window under 500 px. Record: `evidence/staging-walk-6a557b5d/walk-record.md` in the same root. The user closed the task on 2026-10-19 (`agent-planning:user-closure-gate`).
