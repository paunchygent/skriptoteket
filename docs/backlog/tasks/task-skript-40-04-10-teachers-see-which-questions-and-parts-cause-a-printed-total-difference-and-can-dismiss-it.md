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

The user reported on 2026-10-19 that the printed-total actions in the exam workspace do not work. This task replaces those actions with a printed-total difference that informs the teacher, names what the data can attribute it to, and can be dismissed. It is proposed until the part-level buttons (T8) and the dismiss label (T10) are decided and the plan is accepted.

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

The core vertical is one stored-format change and one pure function. `native_exam_document_v9` adds `source_points` to every item (the points the source printed for that question, set at import) and a per-exam dismissed mark to the header, with no v8 reader; open exams are imported again. `examWorkspacePrintedDifferences(document)` turns the open document into a printed-total account: the exam's printed and summed totals, each question whose points differ from `source_points` or have none, and the remainder no question explains. The footer renders the account as an amber note with an expandable list; a click on an entry selects that question through the list's existing `select`. Använd beräknade poäng and dismiss are ordinary document edits with one undo step each, so they save, autosave and undo like every other edit. Performance is not material: the account is a linear pass over the items, recomputed live.

Units, each a fresh `junior-implementation-specialist` with disjoint files, in this order:

1. Backend v9: `source_points` on `NativeExamItem` (required, nullable; null when the source printed none and for teacher-created and split questions; kept by a points edit and a type change), set by the DOCX (`printed_points(own)`, before any estimate), DigiExam and QTI (`max_score`) importers; the dismissed mark on `NativeExamHeader` (required boolean); `native_exam_document_v9` everywhere; regenerated `openapi.d.ts` and fixtures. Focused pytest per importer and for the model.
2. Frontend account: `examWorkspacePrintedDifferences` in `examWorkspaceTotals.ts`, with adversarial unit tests (decimals, float noise, null points, null `source_points`, a source-internal remainder, questions inside parts).
3. Frontend display: the note, the list, dismiss as the primary button (T9, label T10) and Använd beräknade poäng as the secondary one (reusing `withoutPrintedTotals`) in the footer of `ExamWorkspaceQuestionList.vue`; `acceptExamPrintedTotal` and the Använd 67 p button deleted; the part-level buttons as T8 decides. Fail-first component tests rewrite the accept blocks of `ExamWorkspaceTotalsSlice.spec.ts` and every spec that names `exam-workspace-accept-`.

## Validation

- Before any code: reproduce the user's click on staging at the current main on an exam whose printed total differs, and record which state the two actions were in and what each click did.
- Focused pytest for unit 1: each importer stores the printed per-question points, an estimated or unprinted question stores null, a points edit keeps `source_points`, and a v8 document is refused.
- Fail-first Vitest for the account function and for the display: the note reads as information; the footer offers exactly the dismiss action as the primary button and Använd beräknade poäng as the secondary one; each list entry reads "Fråga N: provtexten X p, nu Y p" and selects its question on a click; the remainder is stated when no question explains the difference; Använd beräknade poäng leaves only the sums on the footer and part lines in one undo step; dismiss closes the note and list, keeps a neutral grey "provtexten anger N p" and holds after a reload; Ångra undoes each; no row moves when the note appears or goes (the 40-04-07 layout-slot rule).
- `pdm run lint`, `pdm run typecheck`, frontend typecheck, ESLint and build; one exam-workspace domain suite at the end after the orchestrator's go.
- A staging walk of the exam converter on a re-imported exam whose printed total differs: open the list, click an entry and land on that question, use Använd beräknade poäng and undo it, dismiss and reload and confirm the grey number holds, and undo the dismissal. Also walk it while a conversion is still running.

## Stop Conditions

Stop and report to the parent when the staging reproduction shows a defect outside this contract (for example the buttons were disabled by a stuck busy state), or when an importer cannot name a question's printed points without a converter change.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | A printed-total difference is information, never a warning to act on and never a save or export gate (user ruling 2026-10-17, kept). |
| T2  | Reaching the printed number stays a points edit on the questions; no action sets points or a printed total to a chosen number (TASK-SKRIPT-40-04-06 non-goal, kept). |
| T3  | Each item stores `source_points`, the points the source printed for that question, set at import; null when the source printed none (user 2026-10-19 via the Mac parent). |
| T4  | Under the amber note an expandable list names each question whose points differ from `source_points` or are missing, as "Fråga N: provtexten X p, nu Y p", and a click jumps to that question; a difference no question explains is stated as a remainder (user 2026-10-19 via the Mac parent; remainder from plan F6). |
| T5  | The footer offers one working action, Använd beräknade poäng (renamed from Använd beräknade summor), beside a dismiss action; Använd 67 p is removed (user 2026-10-19 via the Mac parent). |
| T6  | Använd beräknade poäng clears the printed exam and part totals in one undo step. Dismiss keeps the printed numbers and stores a per-exam dismissed mark: the note and its list close and the footer keeps a neutral grey "provtexten anger N p". Both persist per exam and Ångra undoes each (user 2026-10-19 via the Mac parent). |
| T7  | `source_points` and the dismissed mark ship in one `native_exam_document_v9` change with no v8 reader; open exams are imported again (user 2026-10-19 via the Mac parent). |
| T8  | Open: whether the part rows' and the part instruction editor's own Använd N p buttons go (plan row Q5; recommended: removed). |
| T9  | Dismiss is the primary action of the points note: a clearly labelled, easy-to-hit button, never a small x the teacher has to look for; Använd beräknade poäng is the secondary action; dismiss behaves as T6 (user 2026-10-19 via the Mac parent: "a dismiss all is the default action for most users, so it should be easy to click and not find it"). |
| T10 | Open: the dismiss button's label (plan row Q7; recommended: Ignorera skillnaden); the final wording goes through `ui-copy-reviewer`. |

## Resume here (2026-10-19, planning)

- Branch `codex/task-skript-40-04-points-mismatch-remote`, worktree `/home/paunchygent/apps/skriptoteket-task-skript-40-04-points-mismatch-remote`, from `06985163`.
- Status proposed; no code has been written. User decisions 2026-10-19 (answered on the Mac, relayed by the Mac parent) are closed in the retained plan `evidence/planning/TASK-SKRIPT-40-04-10/plan.md` (Q1-Q4) and derived as T3-T7.
- T9 (dismiss is the primary action) recorded 2026-10-19 as plan row Q6.
- Open: Q5 (T8), the part-level Använd N p buttons, and Q7 (T10), the dismiss label. No junior launches before both are answered and the plan is accepted.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15330-34cd-7103-bb71-cc8ef9b8a56f` (explorer discovery under `discovery/explorer/`).
- Next: on the Q5 and Q7 answers, close T8 and T10, run the staging reproduction, then launch unit 1.
