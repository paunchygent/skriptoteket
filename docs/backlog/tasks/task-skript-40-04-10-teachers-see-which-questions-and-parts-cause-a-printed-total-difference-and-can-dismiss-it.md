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
status: in_progress
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

The user reported on 2026-10-19 that the printed-total actions in the exam workspace do not work. This task replaces those actions with a printed-total difference that informs the teacher, names what the data can attribute it to, and can be dismissed. The user accepted the plan on 2026-10-19.

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

The design is the user-confirmed mockup `evidence/design/points-banner-v2-yes-no-glyphs.png` in the retained root (T4); it replaces the text-button mockup `evidence/design/user-approved-points-note-mockup-2026-10-19.webp`. The core vertical is one stored-format change and one pure function. `native_exam_document_v9` adds `source_points` to every item (the points the source printed for that question, set at import) and a per-exam dismissed mark to the header, with no v8 reader; open exams are imported again. `examWorkspacePrintedDifferences(document)` turns the open document into a printed-total account: the exam's printed and summed totals, each part whose printed total differs from its question sum, each question whose points differ from `source_points` or are missing, and the remainder no entry explains. The footer renders the account as the amber note; a click on an entry selects that part or question through the list's existing `select`. The no and yes answers are ordinary document edits with one undo step each, so they save, autosave and undo like every other edit. Performance is not material: the account is a linear pass over the items, recomputed live.

Units, each a fresh `junior-implementation-specialist` with disjoint files, in this order:

1. Backend v9 (waits until TASK-SKRIPT-39-04-20 and TASK-SKRIPT-40-04-08 have merged to main, then starts from that main): `source_points` on `NativeExamItem` (required, nullable; null when the source printed none and for teacher-created and split questions; kept by a points edit and a type change), set by the DOCX (`printed_points(own)`, before any estimate), DigiExam and QTI (`max_score`) importers; the dismissed mark on `NativeExamHeader` (required boolean); `native_exam_document_v9` everywhere; regenerated `openapi.d.ts` and fixtures. Focused pytest per importer and for the model.
2. Frontend account: `examWorkspacePrintedDifferences` in `examWorkspaceTotals.ts`, with adversarial unit tests (decimals, float noise, null points, null `source_points`, a part difference, a source-internal remainder, questions inside parts).
3. Frontend display in the footer of `ExamWorkspaceQuestionList.vue`, built to the v2 mockup: "Totalt 67 p"; the amber note with its heading and arrow-glyph jump rows; its last line the text "Använd beräknade poäng?" followed by exactly two glyph-only answers: no, a large filled navy circle carrying the shared `close` glyph (the default, larger hit area, sets the dismissed mark), and yes, a smaller outlined circle carrying the shared `confirm` glyph (clears the printed totals through `withoutPrintedTotals`). Each answer's name is its tooltip and aria-label only; the tooltip wording goes through `ui-copy-reviewer` ("Nej, behåll provtextens poäng" in the mockup is a placeholder). After no, the total line reads "Totalt 67 p · provtexten anger 70 p" with the printed part in neutral grey. Delete the footer's Använd 67 p and Använd beräknade summor, the part row's (`ExamWorkspaceQuestionRow.vue:139-152`) and the part instruction editor's (`ExamWorkspaceEditorPane.vue:134-145`) Använd N p buttons, and `acceptExamPrintedTotal` and `acceptPartPrintedTotal`. Fail-first component tests rewrite the accept blocks of `ExamWorkspaceTotalsSlice.spec.ts` and every spec that names `exam-workspace-accept-`.

## Validation

- Reproduction of the reported click (F5), run by the Mac on staging as the first part of the final walk, on a main that does not yet contain this task (staging belongs to the Mac; Hemma does not walk it; orchestrator 2026-10-19):
  1. Import an exam whose printed total differs from its question sum (for example the user's exam that reads "Totalt 67 p · provtexten anger 70 p"), and wait until its conversion has finished.
  2. Before clicking, record whether "Använd N p" and "Använd beräknade summor" are enabled: the `disabled` attribute on `[data-test="exam-workspace-accept-exam-total"]` and `[data-test="exam-workspace-accept-all-totals"]`, and their grey `.xw-btn:disabled` colour.
  3. Click "Använd N p"; record the footer text and whether both buttons are now hidden. Press Ångra; confirm the amber note returns.
  4. Click "Använd beräknade summor"; record the same. Compare the two results with each other.
  5. Repeat steps 2 and 3 once while a conversion is still running.
  6. Record each observation with a screenshot. If either button was disabled or a click had no effect, report it to the parent as a defect outside this contract (Stop Conditions).
- Focused pytest for unit 1: each importer stores the printed per-question points, an estimated or unprinted question stores null, a points edit keeps `source_points`, and a v8 document is refused.
- Fail-first Vitest for the account function and for the display: the footer reads "Totalt N p" with the amber note "Provtexten anger M p. Dessa skiljer sig:" below it; each row has the arrow glyph, reads "Del 2: Satslösning — provtexten 22 p, nu 20 p", "Fråga 5 — provtexten 12 p, nu 10 p" or "Fråga 8 — provtexten 4 p, saknar poäng", and selects its part or question on a click; the remainder row appears only when the entries do not explain the difference; the note's last line is the text "Använd beräknade poäng?"; the note contains no text button, and no Använd button exists in the footer, on a part row or in the part instruction editor; exactly two glyph-only answers follow, no (`close`) and yes (`confirm`), with no visible text and their names in the tooltip and aria-label only; the no answer's hit area is larger than the yes answer's; yes leaves "Totalt 67 p" alone and clears the printed totals in one undo step; no closes the note, the total line reads "Totalt 67 p · provtexten anger 70 p" with the printed part in neutral grey, and it holds after a reload; Ångra undoes each; no list row moves when the note appears or goes (the 40-04-07 layout-slot rule).
- `pdm run lint`, `pdm run typecheck`, frontend typecheck, ESLint and build; one exam-workspace domain suite at the end after the orchestrator's go.
- A staging walk of the exam converter on a re-imported exam whose printed total differs, compared with the v2 mockup: click a part row and a question row and land on each, answer yes and undo it, answer no and reload and confirm the grey printed part holds, and undo the no. Also walk it while a conversion is still running.

## Stop Conditions

Stop and report to the parent when the staging reproduction shows a defect outside this contract (for example the buttons were disabled by a stuck busy state), when an importer cannot name a question's printed points without a converter change, or when the mockup cannot be built without moving list rows.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | A printed-total difference is information, never a save or export gate (user ruling 2026-10-17, kept). |
| T2  | Reaching the printed number stays a points edit on the questions; no action sets points or a printed total to a chosen number (TASK-SKRIPT-40-04-06 non-goal, kept). |
| T3  | Each item stores `source_points`, the points the source printed for that question, set at import; null when the source printed none (user 2026-10-19 via the Mac parent). |
| T4  | The footer is built to the v2 mockup (`evidence/design/points-banner-v2-yes-no-glyphs.png`; user rulings 2026-10-19 in the Hemma orchestrator session ("no verbose buttons"; a question answered by binary yes/no glyphs) and the user's confirmation on the Mac ("Yes that works"), relayed by the Mac parent): "Totalt 67 p"; below it an amber note headed "Provtexten anger 70 p. Dessa skiljer sig:"; then one row per differing part or question, each with an arrow glyph and a jump to it: "Del 2: Satslösning — provtexten 22 p, nu 20 p", "Fråga 5 — provtexten 12 p, nu 10 p", "Fråga 8 — provtexten 4 p, saknar poäng". |
| T5  | When the listed rows do not explain the whole difference (the source contradicts itself), one more row in the same style states the remainder for points no question accounts for (user answers 2026-10-19, AskUserQuestion in the Hemma orchestrator session; plan row C1). |
| T6  | The note's last line is the text "Använd beräknade poäng?" followed by exactly two glyph-only answers and no text button: no is a large filled navy circle with the shared `close` glyph and is the default with the larger hit area; yes is a smaller outlined circle with the shared `confirm` glyph. Each answer's name is its tooltip and aria-label only; the tooltip wording goes through `ui-copy-reviewer` (user rulings 2026-10-19 in the Hemma orchestrator session ("no verbose buttons"; a question answered by binary yes/no glyphs) and the user's confirmation on the Mac ("Yes that works"), relayed by the Mac parent; supersedes the Stäng and Använd beräknade poäng text buttons of `bbf14efd`). |
| T7  | Yes clears the printed exam and part totals in one undo step; the total line reads "Totalt 67 p". No keeps the printed numbers and stores a per-exam dismissed mark; the note closes and the total line reads "Totalt 67 p · provtexten anger 70 p" with the printed part in neutral grey. Both persist per exam and Ångra undoes each (user rulings 2026-10-19 in the Hemma orchestrator session ("no verbose buttons"; a question answered by binary yes/no glyphs) and the user's confirmation on the Mac ("Yes that works"), relayed by the Mac parent; user 2026-10-19 via the Mac parent). |
| T8  | `source_points` and the dismissed mark ship in one `native_exam_document_v9` change with no v8 reader; open exams are imported again (user 2026-10-19 via the Mac parent). |
| T9  | The footer's Använd 67 p and Använd beräknade summor, the part rows' and the part instruction editor's Använd N p offers are removed; they are one-off decisions and follow the yes/no rule (user rulings 2026-10-19 in the Hemma orchestrator session ("no verbose buttons"; a question answered by binary yes/no glyphs) and the user's confirmation on the Mac ("Yes that works"), relayed by the Mac parent). |
| T10 | Part differences appear only as rows of the note; the part row shows plain points as in the mockup, so its amber "provtexten anger" line also goes (user answers 2026-10-19, AskUserQuestion in the Hemma orchestrator session; plan row C2). |

## Resume here (2026-10-19, planning)

- Branch `codex/task-skript-40-04-points-mismatch-remote`, worktree `/home/paunchygent/apps/skriptoteket-task-skript-40-04-points-mismatch-remote`, from `06985163`.
- Plan accepted 2026-10-19 (user answers, AskUserQuestion in the Hemma orchestrator session); every plan row closed. Status in_progress.
- 2026-10-19: origin/main f7eeada5 (TASK-SKRIPT-39-04-20) merged at c339584c, handoff conflict resolved explicitly; the orchestrator started unit 1 before 40-04-08 reached main.
- Unit 1 split: 1a backend v9 (source_points, printed_total_dismissed, importers, version, openapi regen), junior launched with order evidence/lead-4ebb41f3/orders/u1a-backend-v9.md; 1b frontend fixtures and v9 literals follows on the regenerated types.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15330-34cd-7103-bb71-cc8ef9b8a56f` (explorer discovery under `discovery/explorer/`).
- Next: integrate 1a, launch 1b, then units 2 and 3. F5 is folded into the final Mac walk (Validation). When 40-04-08 lands on main, merge it and repair the v9 fixtures.
