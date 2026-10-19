---
type: task
id: TASK-SKRIPT-40-04-10
title: Teachers see a printed-total difference in one line and fix the exam text or the questions
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
  - A printed-total difference reads as one line, "Provtexten säger N p, frågorna ger M p.", with two glyph-only actions, "Ändra provtexten till M p" and "Visa frågorna"; the line goes when the totals agree; the Använd actions are gone
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user reported on 2026-10-19 that the printed-total actions in the exam workspace do not work. This task replaces those actions with one line that states the difference and two fixes: change the exam text's total to the questions' sum, or go to the first question that carries the difference and correct its points. The user accepted the plan on 2026-10-19 and corrected the note design the same day (T4-T7: "One line + fix").

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
- A difference the source itself contains (its questions print 67 p, its total line says 70 p) belongs to no question; "Ändra provtexten" is its fix (T7).

So an exact per-question list needs the `source_points` addition, which the user chose on 2026-10-19 (T3, T7).

Non-goals: editing a printed total to a new number; any change to how the converter reads points; export changes (no export reads `printed_total`).

## Contract Inputs

- User report 2026-10-19 in the Hemma orchestrator session, with a screenshot: the footer reads "Totalt 67 p · provtexten anger 70 p" with the second part in amber, over "Använd 67 p" and "Använd beräknade summor". The user's words: "The action components for accepting the conversion score or reverting to the original score is not working." "I think it is a bit backwards to not accept the score. If we want to enable users to revert we must show them which items' scores that diverge from the source? Without clear information pointing to what exactly caused the mismatch, there is a bad bet for the user to revert the converter." "Either provide exact questions diverging in a expandable and clickable shortcut list that shows which items and by how many points they diverge or demote it to a informational and dismissible state."
- TASK-SKRIPT-40-04-06 D6 and D7 (the actions, commit `683bbd80`); TASK-SKRIPT-40-04-07 (the amber totals line and its fixed layout slots).
- Current code: `ExamWorkspaceQuestionList.vue` (footer note and both actions), `ExamWorkspaceQuestionRow.vue:139-152` (part row note and its Använd), `ExamWorkspaceEditorPane.vue:134-145` (part instruction editor's Använd), `examWorkspaceTotals.ts`, `useExamWorkspaceDocumentFields.ts:60-73`, `examWorkspaceListEntries.ts`; backend `native_exam_item.py:69-76`, `docx_source_rules.py:312-344`, `digiexam_import.py:184`, `qti_import_leaf_items.py:92-93`, `native_exam_document.py:39`.
- Retained discovery: root `01a15330-34cd-7103-bb71-cc8ef9b8a56f`, `discovery/explorer/*` (edit refusal, merge, backend writers, item points source).
- `huleedu-ui-design` for the note, the list, click economy and Swedish copy; `integrated-frontend-stack` for the SPA code.

## Core Vertical And Performance

The design is the user's one-line correction of 2026-10-19 (T4-T7); it supersedes the v2 yes/no mockup `evidence/design/points-banner-v2-yes-no-glyphs.png` and the text-button mockup in the retained root. The core vertical is one stored-format change and one small pure function. `native_exam_document_v9` adds `source_points` to every item (the points the source printed for that question, set at import), with no v8 reader; open exams are imported again. A pure function names the first question that carries the difference, which is the target of "Visa frågorna".

Units, each a fresh `junior-implementation-specialist` with disjoint files:

1. Backend v9 (done, `79ce96e5`): `source_points` on `NativeExamItem`, set by the DOCX, DigiExam and QTI importers; `native_exam_document_v9`; regenerated `openapi.d.ts` and fixtures. Frontend fixtures followed (`04373f71`).
2. Frontend account and display, first built to the v2 mockup (`f40acc17`, `a31ce0e4`, `8620e563`, `2f0bc6a1`), then rebuilt to the one-line design: delete the per-exam dismissed mark (`printed_total_dismissed`) from the v9 header, `dismissPrintedTotal`, the note's rows, heading, remainder and yes/no answers; the footer shows "Totalt {sum} p" and, while the printed exam total differs, the line "Provtexten säger {printed} p, frågorna ger {sum} p." followed by the two glyph-only actions of T6; "Ändra provtexten till {sum} p" clears the printed totals through `withoutPrintedTotals` in one undo step; "Visa frågorna" selects the first-target question. The Använd actions, the part rows' amber line and the part instruction editor's printed note stay removed (T9, T10). No list row moves when the line appears or goes (TASK-SKRIPT-40-04-07).

## Validation

- Reproduction of the reported click (F5), run by the Mac on staging as the first part of the final walk, on a main that does not yet contain this task (staging belongs to the Mac; Hemma does not walk it; orchestrator 2026-10-19):
  1. Import an exam whose printed total differs from its question sum (for example the user's exam that reads "Totalt 67 p · provtexten anger 70 p"), and wait until its conversion has finished.
  2. Before clicking, record whether "Använd N p" and "Använd beräknade summor" are enabled: the `disabled` attribute on `[data-test="exam-workspace-accept-exam-total"]` and `[data-test="exam-workspace-accept-all-totals"]`, and their grey `.xw-btn:disabled` colour.
  3. Click "Använd N p"; record the footer text and whether both buttons are now hidden. Press Ångra; confirm the amber note returns.
  4. Click "Använd beräknade summor"; record the same. Compare the two results with each other.
  5. Repeat steps 2 and 3 once while a conversion is still running.
  6. Record each observation with a screenshot. If either button was disabled or a click had no effect, report it to the parent as a defect outside this contract (Stop Conditions).
- Focused pytest for unit 1: each importer stores the printed per-question points, an estimated or unprinted question stores null, a points edit keeps `source_points`, and a v8 document is refused.
- Fail-first Vitest for the first-target function and for the display: the footer reads "Totalt N p" and, while the printed exam total differs, the line "Provtexten säger M p, frågorna ger N p."; the two actions have no text content, carry the shared glyphs and the exact tooltip and aria-label; "Ändra provtexten till N p" clears the printed exam and part totals in one undo step and Ångra restores the line; "Visa frågorna" selects the first question whose printed points differ or that lacks points; no row, heading, remainder, question or Använd button exists; both actions are disabled while the workspace is busy.
- `pdm run lint`, `pdm run typecheck`, frontend typecheck, ESLint and build; one exam-workspace domain suite at the end after the orchestrator's go.
- A staging walk of the exam converter on a re-imported exam whose printed total differs: read the line, click "Visa frågorna" and land on the question, correct its points and see the line go when the totals agree; on another difference click "Ändra provtexten till N p", undo it, and reload. Also walk it while a conversion is still running.

## Stop Conditions

Stop and report to the parent when the staging reproduction shows a defect outside this contract (for example the buttons were disabled by a stuck busy state), when an importer cannot name a question's printed points without a converter change, or when the line cannot be shown without moving list rows.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | A printed-total difference is information, never a save or export gate (user ruling 2026-10-17, kept).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| T2  | Reaching the printed number stays a points edit on the questions; no action sets points or a printed total to a chosen number (TASK-SKRIPT-40-04-06 non-goal, kept).                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| T3  | Each item stores `source_points`, the points the source printed for that question, set at import; null when the source printed none (user 2026-10-19 via the Mac parent).                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| T4  | While the printed exam total differs from the questions' sum, the footer shows one line under "Totalt {sum} p": "Provtexten säger {printed} p, frågorna ger {sum} p." with no list of rows, no heading, no explanation line, no question and no visible container. The line disappears when the totals agree (user correction 2026-10-19, AskUserQuestion answer "One line + fix (Recommended)" in the Hemma orchestrator session: "The text should changed or the items carrying the wrong points should be corrected"; supersedes the v2 yes/no mockup and the copy-review note design of the same day). |
| T5  | No remainder row and no per-part or per-question rows exist; the copy-review remainder and heading wordings are withdrawn (user correction 2026-10-19, AskUserQuestion answer "One line + fix (Recommended)" in the Hemma orchestrator session: "The text should changed or the items carrying the wrong points should be corrected"; supersedes the v2 yes/no mockup and the copy-review note design of the same day).                                                                                                                                                                                    |
| T6  | After the line come exactly two glyph-only actions from the shared glyph catalogue, each named only in its tooltip and aria-label: "Ändra provtexten till {sum} p" and "Visa frågorna" (user correction 2026-10-19, AskUserQuestion answer "One line + fix (Recommended)" in the Hemma orchestrator session: "The text should changed or the items carrying the wrong points should be corrected"; supersedes the v2 yes/no mockup and the copy-review note design of the same day).                                                                                                                       |
| T7  | "Ändra provtexten till {sum} p" clears the printed exam and part totals in one undo step (the former yes path). "Visa frågorna" selects the first question whose printed points differ or that lacks points, where the teacher corrects it. There is no dismiss (user correction 2026-10-19, AskUserQuestion answer "One line + fix (Recommended)" in the Hemma orchestrator session: "The text should changed or the items carrying the wrong points should be corrected"; supersedes the v2 yes/no mockup and the copy-review note design of the same day).                                              |
| T8  | `source_points` ships in one `native_exam_document_v9` change with no v8 reader; open exams are imported again (user 2026-10-19 via the Mac parent). The per-exam dismissed mark is removed from v9 with no reader left (user correction 2026-10-19, AskUserQuestion answer "One line + fix (Recommended)" in the Hemma orchestrator session: "The text should changed or the items carrying the wrong points should be corrected"; supersedes the v2 yes/no mockup and the copy-review note design of the same day).                                                                                      |
| T9  | The footer's Använd 67 p and Använd beräknade summor, the part rows' and the part instruction editor's Använd N p offers are removed; they are one-off decisions and follow the yes/no rule (user rulings 2026-10-19 in the Hemma orchestrator session ("no verbose buttons"; a question answered by binary yes/no glyphs) and the user's confirmation on the Mac ("Yes that works"), relayed by the Mac parent).                                                                                                                                                                                          |
| T10 | Part rows and the part instruction editor show plain points (user answers 2026-10-19, AskUserQuestion in the Hemma orchestrator session; plan row C2, kept).                                                                                                                                                                                                                                                                                                                                                                                                                                               |

## Resume here (2026-10-19, implementation)

- Branch `codex/task-skript-40-04-points-mismatch-remote`, worktree `/home/paunchygent/apps/skriptoteket-task-skript-40-04-points-mismatch-remote`, from `06985163`.
- Plan accepted 2026-10-19 (user answers, AskUserQuestion in the Hemma orchestrator session); every plan row closed. Status in_progress.
- 2026-10-19: origin/main f7eeada5 (TASK-SKRIPT-39-04-20) merged at c339584c, handoff conflict resolved explicitly; the orchestrator started unit 1 before 40-04-08 reached main.
- Done: 1a backend v9 (79ce96e5), 2 printed-total account `examWorkspacePrintedDifferences` (f40acc17), 1b frontend v9 fixtures (04373f71); each with fail-first and focused proof under evidence/lead-4ebb41f3/.
- Done: unit 3 footer note with glyph-only yes/no and every Använd button removed (a31ce0e4); lead-review repairs 3r (8620e563: exact printed numbers, note height cap, dead part printedTotal) and 3r2 (2f0bc6a1: rounded remainder).
- Copy packet for ui-copy-reviewer (orchestrator-routed): evidence/lead-4ebb41f3/copy/string-inventory.md and copy/screenshots/ (part, question, remainder, accepted, dismissed, tooltip-no; footer-texts.json), made by copy/shoot_points_note.py against a local Vite with mocked bootstrap.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15330-34cd-7103-bb71-cc8ef9b8a56f` (explorer discovery under `discovery/explorer/`).
- Next: copy review (orchestrator), then the domain suite when the slot frees (40-04-15 holds it), then code review; F5 in the Mac walk. F5 is folded into the final Mac walk (Validation). When 40-04-08 lands on main, merge it and repair the v9 fixtures.
