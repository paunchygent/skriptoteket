---
type: task
id: TASK-SKRIPT-40-04-09
title: Teachers see which questions and parts cause a printed-total difference and
  can dismiss it
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
- A printed-total difference reads as information, names the parts and questions the
  data can attribute it to with their point difference, jumps to each on a click,
  and can be dismissed; the Använd actions are gone
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user reported on 2026-10-19 that the printed-total actions in the exam workspace do not work. This task replaces those actions with a printed-total difference that informs the teacher, names what the data can attribute it to, and can be dismissed. It is proposed: the user chooses the display (Q1) and the dismissal (Q2) before any junior writes code.

Root cause, from the code at `06985163`:

1. Both actions clear printed totals; neither restores the printed number. By TASK-SKRIPT-40-04-06 D6 and D7, "Använd 67 p" clears the exam's `printed_total` (`examWorkspaceTotals.ts` `withoutExamPrintedTotal`) and "Använd beräknade summor" clears the exam's and every part's (`withoutPrintedTotals`). Editing a printed total to a new number was a non-goal of 40-04-06, and reaching the printed number stays a points edit.
2. When no part prints a total of its own, as in the user's exam, the two actions produce the same document. A disposable Vitest probe at `06985163` showed that `withoutPrintedTotals(document)` deep-equals `withoutExamPrintedTotal(document)` for an exam printing 70 p over questions summing to 67 p. The second action differs only when a part prints a different total (`ExamWorkspaceTotalsSlice.spec.ts` "offers the footer action only while a level differs").
3. After either click, the only visible effect is that the amber note and both buttons disappear (`list__action--idle` is `visibility: hidden`). A teacher who reads one action as "accept the conversion" and the other as "revert to the printed score" sees the revert do what the accept did, so the revert "is not working".
4. Nothing tells the teacher which questions cause the 3 p difference, so accepting either total is a guess (the user's second point).

Mechanisms checked and ruled out by reading the code: `editDocument` refuses an edit only when no document is open or the workspace is busy (`useExamWorkspaceDocument.ts:350`). A busy workspace disables both buttons with the `.xw-btn:disabled` grey (`examWorkspace.css:49`), and the user's screenshot does not show which state the buttons were in. A teacher-cleared total is not brought back by a conversion arrival: the client merge keeps a changed local header (`examWorkspaceConversionMerge.ts:336`, `pick`), and the server merge replaces the header only while it still equals the last delivered one (`exam_workspace_conversion_merge_fields.py:30`). No backend code re-derives `printed_total` after import (`docx_header.py:68`, `docx_section_points.py:130-133` are the only writers). `ExamWorkspaceTotalsSlice.spec.ts` passes 23 of 23 at `06985163`. The user's click has not been reproduced on staging; the first validation step does that.

What the data supports:

- Exam level: `header.printed_total` against the sum of question points. Exact.
- Part level: `parents[].printed_total` against the part's question sum. Exact; each part row already shows it.
- Question level, today: the converter writes the points a question prints into the editable `points` field and keeps no copy (`docx_source_rules.py:324-344` `with_printed_points`; DigiExam `digiexam_import.py:184` and QTI `qti_import_leaf_items.py:92-93` copy `max_score`). After an edit, nothing records what the source printed. The data names only questions without points (`points === null`, counted as 0) and questions whose points were shared out from a part total (`points_estimated`, cleared by any points edit, `examWorkspaceItemEdits.ts:54`). It cannot say "Fråga 4: provtexten 3 p, nu 2 p".
- Question level, with one backend addition: every importer already knows the per-question printed value at import (`printed_points(own)` in DOCX, `max_score` in DigiExam and QTI). Storing it on the item as `source_points` (the number the source printed for that question, `null` when it printed none) makes the exact per-question difference available. This is a stored-format change (`native_exam_document_v8` to `v9`, no v8 reader; open exams must be re-imported).
- A difference the source itself contains (its questions print 67 p, its total line says 70 p) belongs to no question. The display states that remainder as such.

So option A as the user phrased it is supported exactly for parts today, and for questions only after the `source_points` addition. Option B is supported today.

Non-goals: editing a printed total to a new number; any change to how the converter reads points; export changes (no export reads `printed_total`).

## Contract Inputs

- User report 2026-10-19 in the Hemma orchestrator session, with a screenshot: the footer reads "Totalt 67 p · provtexten anger 70 p" with the second part in amber, over "Använd 67 p" and "Använd beräknade summor". The user's words: "The action components for accepting the conversion score or reverting to the original score is not working." "I think it is a bit backwards to not accept the score. If we want to enable users to revert we must show them which items' scores that diverge from the source? Without clear information pointing to what exactly caused the mismatch, there is a bad bet for the user to revert the converter." "Either provide exact questions diverging in a expandable and clickable shortcut list that shows which items and by how many points they diverge or demote it to a informational and dismissible state."
- TASK-SKRIPT-40-04-06 D6 and D7 (the actions, commit `683bbd80`); TASK-SKRIPT-40-04-07 (the amber totals line and its fixed layout slots).
- Current code: `ExamWorkspaceQuestionList.vue` (footer note and both actions), `ExamWorkspaceQuestionRow.vue:139-152` (part row note and its Använd), `ExamWorkspaceEditorPane.vue:134-145` (part instruction editor's Använd), `examWorkspaceTotals.ts`, `useExamWorkspaceDocumentFields.ts:60-73`, `examWorkspaceListEntries.ts`; backend `native_exam_item.py:69-76`, `docx_source_rules.py:312-344`, `digiexam_import.py:184`, `qti_import_leaf_items.py:92-93`, `native_exam_document.py:39`.
- Retained discovery: root `01a15330-34cd-7103-bb71-cc8ef9b8a56f`, `discovery/explorer/*` (edit refusal, merge, backend writers, item points source).
- `huleedu-ui-design` for the note, the list, click economy and Swedish copy; `integrated-frontend-stack` for the SPA code.

## Core Vertical And Performance

The core vertical is one pure function that turns the open document into a printed-total account: the exam's printed and summed totals, each part that differs, each question that differs, and the remainder no question explains. The footer, the part rows and the part instruction editor render that account; a click on an entry selects that question or part through the list's existing `select`. The dismissal is one ordinary document edit with one undo step, so it saves, autosaves and undoes like every other edit. Performance is not material: the account is a linear pass over the items, recomputed live.

Planned junior units, under the recommended mix (each a fresh `junior-implementation-specialist`, disjoint files):

1. Backend (only if Q1 includes question-level differences): `source_points` on `NativeExamItem`, required and nullable, set by the DOCX, DigiExam and QTI importers from the value each already reads; a points edit keeps it; `native_exam_document_v9` everywhere with no v8 reader; regenerate `openapi.d.ts` and the fixtures. Focused pytest for each importer and the document model.
2. Frontend account: `examWorkspacePrintedDifferences(document)` in `examWorkspaceTotals.ts`, with adversarial unit tests (decimal sums, a null-points question, a part inside the exam, a source-internal remainder, float noise).
3. Frontend display: the footer note, the expandable list and the dismissal; the part row and editor pane follow the same design; the Använd actions and their handlers are deleted. Fail-first component tests rewrite the accept blocks of `ExamWorkspaceTotalsSlice.spec.ts`.

Under option B alone, units 1 and 2 drop and unit 3 shows the note with its dismissal only.

## Validation

- Before any code: reproduce the user's click on staging at the current main on an exam whose printed total differs, and record which state the two actions were in and what each click did.
- Fail-first Vitest for the account function and for the display: the note reads as information and not as a warning to act on; no Använd action exists on the footer, a part row or the part instruction editor; each listed entry names its question or part and its point difference and selects it on a click; the remainder is stated when no question explains it; the dismissal clears the note in one undo step and Ångra brings it back; nothing moves the list rows when the note appears or goes (the 40-04-07 layout-slot rule).
- Focused pytest for unit 1 when it runs; `pdm run lint`, `pdm run typecheck`, frontend typecheck, ESLint and build; one exam-workspace domain suite at the end after the orchestrator's go.
- A staging walk of the exam converter on an exam whose printed total differs: open the list, click an entry and land on that question, dismiss the note, reload and confirm the dismissal holds as Q2 decides, and undo it. Also walk it while a conversion is still running.

## Stop Conditions

Stop and report to the parent when the staging reproduction shows a defect outside this contract (for example the buttons were disabled by a stuck busy state), when an importer cannot name a question's printed points without a converter change, or when the chosen dismissal needs client-stored state.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| P1  | Both Använd actions are removed: the footer's two and the part row's and the part instruction editor's one each, with their handlers (`acceptExamPrintedTotal`, `acceptPartPrintedTotal`, `acceptAllPrintedTotals`). They accept the same computed sums, offer no revert, and give the teacher nothing to judge by (root cause 1-4; user 2026-10-19). |
| P2  | A printed-total difference is information, never a warning to act on and never a save or export gate (keeps the 2026-10-17 ruling). |
| P3  | Reaching the printed number stays a points edit on the questions; no action sets points or a printed total to a chosen number (40-04-06 non-goal kept). |
| P4  | Exam and part differences are computed exactly from `printed_total` and the question sums, as today. |
| P5  | Display: open, user question Q1. Working assumption: the mix (Q1 option C). |
| P6  | Dismissal persistence: open, user question Q2. Working assumption: per exam, in the document (Q2 option 1). |

## Open Questions For The User

Q1. What does the difference show?

- A. An expandable list under the total: each part and question that diverges, with "provtexten X p, nu Y p", and a click that jumps to it. Exact for parts today; for questions it needs the backend unit (`source_points`, document v9, open exams re-imported).
- B. An informational note the teacher can dismiss ("Provtexten anger 70 p, frågorna ger 67 p"), with no list. Frontend only.
- C (recommended). B's note, always, plus A's list whenever the data attributes the difference: parts that differ, questions whose points differ from what the source printed, questions without points, and the remainder no question explains ("3 p anges inte av någon fråga"). This gives the teacher the evidence the user asked for and never a guess. It includes the backend unit.
- C without the backend unit: the list names parts that differ and questions without points or with shared-out points, but no per-question difference.

Q2. Does a dismissal persist?

- 1 (recommended). Per exam, in the document: dismissing clears the exam's and every part's printed total as one undo step, so it saves with the exam, holds after a reload and Ångra brings it back. It reuses the existing edit path and stores no client state. The printed number is then gone from this copy until Ångra or a re-import.
- 2. Only until the page reloads: the note returns on every open. No stored state.

## Resume here (2026-10-19, planning)

- Branch `codex/task-skript-40-04-points-mismatch-remote`, worktree `/home/paunchygent/apps/skriptoteket-task-skript-40-04-points-mismatch-remote`, from `06985163`.
- Status proposed; waiting for the user's answers to Q1 and Q2. No code has been written.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15330-34cd-7103-bb71-cc8ef9b8a56f` (explorer discovery under `discovery/explorer/`).
- Next: on the answers, close P5 and P6, run the staging reproduction, then launch the units above.
