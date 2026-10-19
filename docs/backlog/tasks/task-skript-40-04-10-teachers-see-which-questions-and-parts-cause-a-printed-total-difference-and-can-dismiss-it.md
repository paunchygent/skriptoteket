---
type: task
id: TASK-SKRIPT-40-04-10
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

The user reported on 2026-10-19 that the printed-total actions in the exam workspace do not work. This task replaces those actions with a printed-total difference that informs the teacher, names what the data can attribute it to, and can be dismissed. It is proposed until the user confirms T8 (plan row Q5) and the plan is accepted.

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

So an exact per-question list needs the `source_points` addition, which the user chose on 2026-10-19 (T3, T7).

Non-goals: editing a printed total to a new number; any change to how the converter reads points; export changes (no export reads `printed_total`).

## Contract Inputs

- User report 2026-10-19 in the Hemma orchestrator session, with a screenshot: the footer reads "Totalt 67 p · provtexten anger 70 p" with the second part in amber, over "Använd 67 p" and "Använd beräknade summor". The user's words: "The action components for accepting the conversion score or reverting to the original score is not working." "I think it is a bit backwards to not accept the score. If we want to enable users to revert we must show them which items' scores that diverge from the source? Without clear information pointing to what exactly caused the mismatch, there is a bad bet for the user to revert the converter." "Either provide exact questions diverging in a expandable and clickable shortcut list that shows which items and by how many points they diverge or demote it to a informational and dismissible state."
- TASK-SKRIPT-40-04-06 D6 and D7 (the actions, commit `683bbd80`); TASK-SKRIPT-40-04-07 (the amber totals line and its fixed layout slots).
- Current code: `ExamWorkspaceQuestionList.vue` (footer note and both actions), `ExamWorkspaceQuestionRow.vue:139-152` (part row note and its Använd), `ExamWorkspaceEditorPane.vue:134-145` (part instruction editor's Använd), `examWorkspaceTotals.ts`, `useExamWorkspaceDocumentFields.ts:60-73`, `examWorkspaceListEntries.ts`; backend `native_exam_item.py:69-76`, `docx_source_rules.py:312-344`, `digiexam_import.py:184`, `qti_import_leaf_items.py:92-93`, `native_exam_document.py:39`.
- Retained discovery: root `01a15330-34cd-7103-bb71-cc8ef9b8a56f`, `discovery/explorer/*` (edit refusal, merge, backend writers, item points source).
- `huleedu-ui-design` for the note, the list, click economy and Swedish copy; `integrated-frontend-stack` for the SPA code.

## Core Vertical And Performance

The core vertical is one stored-format change and one pure function. `native_exam_document_v9` adds `source_points` to every item (the points the source printed for that question, set at import) and a per-exam dismissed mark to the header, with no v8 reader; open exams are imported again. `examWorkspacePrintedDifferences(document)` turns the open document into a printed-total account: the exam's printed and summed totals, each question whose points differ from `source_points` or have none, and the remainder no question explains. The footer renders the account as an amber note with an expandable list; a click on an entry selects that question through the list's existing `select`. The note's text ends with the decision as a question; its yes answer (accept) and no answer (dismiss) are ordinary document edits with one undo step each, so they save, autosave and undo like every other edit. Performance is not material: the account is a linear pass over the items, recomputed live.

Units, each a fresh `junior-implementation-specialist` with disjoint files, in this order:

1. Backend v9: `source_points` on `NativeExamItem` (required, nullable; null when the source printed none and for teacher-created and split questions; kept by a points edit and a type change), set by the DOCX (`printed_points(own)`, before any estimate), DigiExam and QTI (`max_score`) importers; the dismissed mark on `NativeExamHeader` (required boolean); `native_exam_document_v9` everywhere; regenerated `openapi.d.ts` and fixtures. Focused pytest per importer and for the model.
2. Frontend account: `examWorkspacePrintedDifferences` in `examWorkspaceTotals.ts`, with adversarial unit tests (decimals, float noise, null points, null `source_points`, a source-internal remainder, questions inside parts).
3. Frontend display in the footer of `ExamWorkspaceQuestionList.vue`: the note's text (the difference, the list, and the decision as a question such as "Använd beräknade poäng?"), then exactly two glyph-only answers (T10): no (meaning `close`, the default, with the larger hit area; sets the dismissed mark) and yes (meaning `confirm`; clears the printed totals through `withoutPrintedTotals`). Both Använd text buttons in the footer, the part row's (`ExamWorkspaceQuestionRow.vue:139-152`) and the part instruction editor's (`ExamWorkspaceEditorPane.vue:134-145`) Använd N p buttons, and `acceptExamPrintedTotal` and `acceptPartPrintedTotal` are deleted (T8); the part lines stay informational. Fail-first component tests rewrite the accept blocks of `ExamWorkspaceTotalsSlice.spec.ts` and every spec that names `exam-workspace-accept-`.

## Validation

- Before any code: reproduce the user's click on staging at the current main on an exam whose printed total differs, and record which state the two actions were in and what each click did.
- Focused pytest for unit 1: each importer stores the printed per-question points, an estimated or unprinted question stores null, a points edit keeps `source_points`, and a v8 document is refused.
- Fail-first Vitest for the account function and for the display: the note reads as information; the note's text ends with the decision as a question; exactly two glyph-only answers follow, no (`close`, the default, with the larger hit area) and yes (`confirm`), with no text inside either and their names as tooltip and aria-label only; no text button exists in the footer, on a part row or in the part instruction editor; each list entry reads "Fråga N: provtexten X p, nu Y p" and selects its question on a click; the remainder is stated when no question explains the difference; yes leaves only the sums on the footer and part lines in one undo step; no closes the note and list, keeps a neutral grey "provtexten anger N p" and holds after a reload; Ångra undoes each; no row moves when the note appears or goes (the 40-04-07 layout-slot rule).
- `pdm run lint`, `pdm run typecheck`, frontend typecheck, ESLint and build; one exam-workspace domain suite at the end after the orchestrator's go.
- A staging walk of the exam converter on a re-imported exam whose printed total differs: open the list, click an entry and land on that question, answer yes and undo it, answer no and reload and confirm the grey number holds, and undo the no. Also walk it while a conversion is still running.

## Stop Conditions

Stop and report to the parent when the staging reproduction shows a defect outside this contract (for example the buttons were disabled by a stuck busy state), or when an importer cannot name a question's printed points without a converter change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | A printed-total difference is information, never a warning to act on and never a save or export gate (user ruling 2026-10-17, kept). |
| T2  | Reaching the printed number stays a points edit on the questions; no action sets points or a printed total to a chosen number (TASK-SKRIPT-40-04-06 non-goal, kept). |
| T3  | Each item stores `source_points`, the points the source printed for that question, set at import; null when the source printed none (user 2026-10-19 via the Mac parent). |
| T4  | Under the amber note an expandable list names each question whose points differ from `source_points` or are missing, as "Fråga N: provtexten X p, nu Y p", and a click jumps to that question; a difference no question explains is stated as a remainder (user 2026-10-19 via the Mac parent; remainder from plan F6). |
| T5  | The note's text states the difference, the per-question list and the decision as a question (for example "Använd beräknade poäng?"). No button carries text: there is no Använd 67 p, no Använd beräknade summor and no Använd beräknade poäng button (user corrections 2026-10-19, the second given directly in the Hemma orchestrator session: "It's a fucking text. And then you have yes or no binary fucking answer glyphs. No verbose buttons."). The rule behind it (user refinement 2026-10-19, direct): a persistent button that is always there may keep longer text, but a one-off decision ("do you want to use this or not?") is never a button; it is question text plus yes/no glyphs. The points note and the part-row Använd N p offers are one-off decisions. The decision sentence's wording goes through `ui-copy-reviewer` as text. |
| T6  | Yes (accept) clears the printed exam and part totals in one undo step. No (dismiss) keeps the printed numbers and stores a per-exam dismissed mark: the note and its list close and the footer keeps a neutral grey "provtexten anger N p". Both persist per exam and Ångra undoes each (user 2026-10-19 via the Mac parent). |
| T7  | `source_points` and the dismissed mark ship in one `native_exam_document_v9` change with no v8 reader; open exams are imported again (user 2026-10-19 via the Mac parent). |
| T8  | The part rows' and the part instruction editor's Använd N p text buttons go under T5; the part lines stay informational (orchestrator relay of the user's rule 2026-10-19; plan row Q5 stays open as a confirmation only). |
| T9  | No (dismiss) is the default answer: easy to hit, with a large hit area, never a tiny x tucked away (user 2026-10-19 via the Mac parent: "a dismiss all is the default action for most users, so it should be easy to click and not find it"). |
| T10 | The two answers are glyph-only and use the shared meanings in `uiGlyphs.ts`: yes is `confirm` (lucide Check, as in `ExamWorkspaceQuestionTools.vue:59`), no is `close` (lucide X, as in the drawers and help panels). Each answer's name (Acceptera for yes) is its tooltip and aria-label only (user correction 2026-10-19 in the Hemma orchestrator session: "you present the decision and then you say yes or no. And that is acceptera... This is part of the semantics."). |

## Resume here (2026-10-19, planning)

- Branch `codex/task-skript-40-04-points-mismatch-remote`, worktree `/home/paunchygent/apps/skriptoteket-task-skript-40-04-points-mismatch-remote`, from `06985163`.
- Status proposed; no code has been written. User decisions 2026-10-19 (answered on the Mac, relayed by the Mac parent) are closed in the retained plan `evidence/planning/TASK-SKRIPT-40-04-10/plan.md` (Q1-Q4) and derived as T3-T7.
- T9 (dismiss is the primary action) recorded 2026-10-19 as plan row Q6.
- T5, T8-T10 (decision as text, yes/no glyph answers, no text buttons anywhere) follow the user corrections of 2026-10-19 (plan rows Q3, Q7).
- Open: Q5, a confirmation only that the part-level Använd N p buttons go (T8). No junior launches before the plan is accepted.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15330-34cd-7103-bb71-cc8ef9b8a56f` (explorer discovery under `discovery/explorer/`).
- Next: on the Q5 confirmation, run the staging reproduction, then launch unit 1.
