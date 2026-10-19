---
type: task
id: TASK-SKRIPT-40-04-11
title: Exam workspace tools show only their glyph and name their action in a tooltip
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

Source: the user's request of 2026-10-19 in the Hemma orchestrator session, with a screenshot of a Fritextfråga item. The user circled the Skrivyta row (−, + and "Använd för alla fritextfrågor") and "+ Kriterium" and wrote: "Button *containers* are too big for a compact workspace", "Direction is NO visible containers for tools, just the glyphs" and "The Använd för alla fritextfrågor is a verbose button that confuses tooltip wording in container with smart design."

Cause: the Skrivyta field (TASK-SKRIPT-40-04-07) and the criteria field draw their own bordered buttons with Tailwind classes (`border border-navy/35 bg-panel`, `ExamWorkspaceWritingLinesField.vue:78/90/102`, `ExamWorkspaceCriteriaField.vue:190`) instead of the workspace's control family in `examWorkspace.css`. That family already has a boxless glyph button, `xw-btn xw-btn--compact xw-btn--icon xw-btn--ghost`, used by the ordering field's move and remove tools, and a boxless remove button, `xw-rm`. The prototype's other tools (`xw-btn` with a word) and the gap popover's `btn-ghost` buttons are boxed as well; `.btn-ghost` has a solid border, so TASK-SKRIPT-40-04-08's glyph-only add buttons are still boxed.

This task makes each tool in scope a glyph with no visible container. The action phrase becomes the native tooltip and the accessible name (T1, T2), and every tool is glyph-only (T6). The Skrivyta row becomes one compact row, and the overlap of that row with the Bedömningskriterier label is fixed from its measured cause (T3). Menu items, list entries and segment options keep their text, because their text names a choice or a destination, not an action. Persistent commands keep their form: Spara, Öppna, Exportera, Förhandsgranska, Tillbaka, the export-blocker fixes, and the drawer and dialog buttons. Three one-off offers are text buttons today: the type offer "Gör om till {typ}" (`ExamWorkspaceQuestionHead.vue:164`), "Ångra AI-tolkningen" (`ExamWorkspaceQuestionEditor.vue:361`) and "Lägg till i mina kurser" (`ExamWorkspaceDetailsDrawer.vue:254`). Whether each becomes text plus glyphs or keeps its text button is open question Q5. The printed-total note belongs to TASK-SKRIPT-40-04-10 and stays out of scope here; it is the user's own example of the one-off rule.

Non-goals: no change to the drift-checked mirrors in this repository (`components/ui/shared/`, `styles/action-buttons.css`, `design-system/huleedu-integrated/`); no new button component; no backend or document change.

## Contract Inputs

- Story: ST-SKRIPT-40-04 (exam workspace redesign); the approved prototype's control family in `frontend/apps/skriptoteket/src/views/apps/exam-workspace/examWorkspace.css`.
- User rule, 2026-10-19 (Hemma orchestrator session), with its refinement the same day: a simple one-off decision is never a button; it is text that states the choice plus yes/no glyphs from the shared glyph semantics, such as accept (`confirm`, "Acceptera") and dismiss (`close`), named only in the tooltip and aria-label. A control that is always there may sometimes keep text. Tools are glyph-only with no container. The user's own example of the rule is TASK-SKRIPT-40-04-10's points note: the question "Använd beräknade poäng?" as text, a large filled X for no (the default) and an outlined check for yes, using the shared `close` and `confirm` meanings.
- `huleedu-ui-design`: a button shows a glyph from the shared catalogue; the action phrase belongs in the native tooltip and accessible name; an icon-only action has no frame; hover and press tint the glyph's area; the layout holds still.
- TASK-SKRIPT-40-04-07 (done): the Skrivyta stepper and apply-to-all (`useExamWorkspaceDocumentFields.ts:76`, undoable through `editDocument` and `noteEdit`).
- TASK-SKRIPT-40-04-08 (in review): its copy decision L12 (add buttons carry their phrase as tooltip and accessible name). Its branch rewrites `ExamWorkspaceGapPopover.vue` and adds `ExamWorkspaceGapAnswerList.vue`.
- The retained plan with its evidence and ledger: `.orchestration/context/sessions/01a15383-370d-707d-876f-cf2953eb536b/evidence/planning/TASK-SKRIPT-40-04-11/plan.md` in the primary checkout.

## Core Vertical And Performance

The core vertical is the Fritextfråga editor: a teacher sees `Skrivyta`, the − glyph, the count, the + glyph and the apply-to-all glyph on one row, then the Bedömningskriterier label and the add glyph, with no boxes and no overlap; hovering a glyph shows its phrase; Tab reaches each glyph with a visible focus ring. No performance concern applies.

Planned junior units, each with its own focused spec; their final list depends on the open user questions in Resume here:

1. Overlap probe (lead): measure the computed styles of both fieldsets and the legend in a real browser at 390, 1024 and 1440 px, record the cause, then decide the fix.
2. Tool class: `examWorkspace.css` gives the ghost icon tool its pressed look without a border and, if accepted, a 44 px hit area on coarse pointers.
3. Skrivyta row: `ExamWorkspaceWritingLinesField.vue` and its spec.
4. Criteria field: `ExamWorkspaceCriteriaField.vue` (add glyph `add`, phrase "Lägg till kriterium"; remove moves to `xw-rm`) and its spec.
5. Editor tools, if the scope is the whole workspace: `ExamWorkspaceOrderingField.vue` (Lägg till steg, Blanda om), `ExamWorkspaceInstructionEditor.vue` (Deluppgift), `ExamWorkspaceQuestionEditor.vue` (Redigera instruktionen, and Ångra AI-tolkningen as Q5 decides), `ExamWorkspaceQuestionHead.vue` (the type offer as Q5 decides).
6. Gap tools, after TASK-SKRIPT-40-04-08 merges: `ExamWorkspaceGapPopover.vue` (Lägg till alternativ, remove an automatic spelling, Visa som text with `convert-type`), `ExamWorkspaceGapAnswerList.vue`.
7. Header and list tools, if the scope is the whole workspace: `ExamWorkspaceHeader.vue` (AI, Ångra, Gör om), `ExamWorkspaceQuestionTools.vue`, `ExamWorkspaceQuestionList.vue` (Ny uppgift, Markera, Lägg till instruktioner).
9. Course offer, if Q5 converts it: `ExamWorkspaceDetailsDrawer.vue`.
8. Apply-to-all glyph, if a new meaning is accepted: the shared catalogue in the skill repository, then the mirror sync here (needs the parent's cross-repository authority).

## Validation

- Each changed component's focused Vitest spec checks, per tool: the accessible name, the native title, the reason title while disabled, the emitted event, the glyph, and that the button carries the boxless tool class and no border class.
- Keyboard: each changed tool is reachable with Tab in visual order and activates with Enter and Space; focus-visible shows the workspace focus ring.
- The Skrivyta spec checks that the count slot keeps its width from 1 to 40 rader.
- Screenshots of the changed controls at rest, on hover and on focus at 390, 1024 and 1440 px go to `ui-copy-reviewer` and the user for the copy and the look.
- Frontend typecheck, lint and build for the touched app.
- No staging walk: the user's rule of 2026-10-17 limits staging walks to the exam converter.

## Stop Conditions

- Stop before writing code until the user has answered the open questions in Resume here and the status is ready.
- Stop and report when the overlap probe shows a cause outside the two fields and their parent's layout.
- Stop and report when a unit would need to edit a drift-checked mirror in this repository.
- Stop before unit 6 until TASK-SKRIPT-40-04-08 is on main.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | Every tool in scope uses the workspace's boxless glyph button, `xw-btn xw-btn--icon xw-btn--ghost`, at its surface's existing size: compact (`xw-btn--compact`) in editor fields and lists, regular in the header; a remove or delete tool uses `xw-rm`. No per-component border classes and no new button component. |
| T2  | A glyph-only tool shows no text. Its action phrase is both its aria-label and its native title; while disabled by a bound or a no-op its title gives the reason. The glyph is decorative to assistive technology. |
| T3  | The Skrivyta controls and the Bedömningskriterier label do not overlap at 390, 1024 and 1440 px. The fix follows the cause measured in a real browser. |
| T4  | Work starts from main after TASK-SKRIPT-40-04-08 merges; the lead merges current main into this branch before a unit touches a file that TASK-SKRIPT-40-04-09 or TASK-SKRIPT-40-04-10 also changes. |
| T5  | Validation is the focused component specs, keyboard reach and focus ring, and screenshots for copy review named above; no staging walk. |
| T6  | Tools are glyph-only with no container (user 2026-10-19). Persistent commands, menu items, list entries and segment options keep their text. How the one-off offers look is Q5. |

## Resume here (2026-10-19, planning)

Status stays proposed. Five user questions are open in the retained plan's ledger (D3-D6, D11); each has options and a recommendation:

- Scope: (A) the Fritextfråga item only; (B) every off-system box (Skrivyta, criteria, gap popover, gap answer list); (C) every tool in the workspace while commands keep their form. Recommended: C.
- Apply-to-all: a new shared glyph meaning `apply-to-all` with Lucide Layers (alternatives CopyCheck, CheckCheck; none is in the catalogue yet, and the names are not yet checked against @lucide/vue 1.47.0; `copy` already means "Spara som …"); tooltip "Använd {n} rader för alla fritextfrågor"; disabled "Alla fritextfrågor har redan {n} rader"; no confirmation, since Ångra reverts it. The new meaning is a skill-repository change.
- Stepper: the count "{n} rader" between − and + in a slot sized for "40 rader"; the label reads "Skrivyta". Recommended.
- Look: the workspace's existing hover tint, focus ring and pressed tint without a border, plus a 44 px hit area on coarse pointers. Recommended.
- Q5, the three one-off offers (before and after mockup: `evidence/mockups/one-off-offers.png` in the retained root): for each, either text that states the choice plus glyphs, or keep its text button. Type offer: "Provfilen tyder på {typ}" plus accept ("Gör om till {typ}"), optionally a dismiss ("Behåll {typ}") that needs a new stored mark. AI-tolkat facit: the key line plus an undo glyph ("Ångra AI-tolkningen"). Mina kurser: "inte i mina kurser" plus an add glyph. Recommended: convert all three, with accept only on the type offer, because the user rule calls a one-off choice text plus glyphs, as in the 40-04-10 points note; the user decides each offer.

Next: when the user answers, record each answer as a closed ledger row, add the accepted terms here, fill the acceptance criteria, and ask the parent for ready.
