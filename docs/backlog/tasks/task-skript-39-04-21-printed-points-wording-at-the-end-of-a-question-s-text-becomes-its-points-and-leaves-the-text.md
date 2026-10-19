---
type: task
id: TASK-SKRIPT-39-04-21
title: Printed points wording at the end of a question's text becomes its points and
  leaves the text
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Points wording printed at the end of an imported question's text, whose number equals
  the question's points, leaves the text; the points, the QTI score, the source record and
  every points reader stay as before
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Defect, observed in TASK-SKRIPT-40-04-15 (branch `codex/task-skript-40-04-inline-points-remote`,
`dbbb5f8d`): the print adds "(N p)" after each question's text, and some imported question
texts still end in their source's own points wording, so the print doubles it ("... lunch
menu. (1 point) (1 p)", "Poäng: 6 poäng (6 p)").

User decision, 2026-10-19 (AskUserQuestion in the Hemma orchestrator session `944b5a5a`):
"Import strips it". Printed points wording at the end of a question's text becomes the
question's points and is removed from the text. The user's condition: "ensure it is not
stripped before the conversion needing the points to convert the item's point to the QTI
item is done. We have had issues with this earlier, so be careful with stripping and the
logic dependent on what is stripped and when."

Observed at `f3c71530` (the ten recorded replays): exactly three item bodies keep the
wording, all DOCX source-fallback review items (`parse_origin: source_fallback`):
`bf26_english_1_unit_test_kap_1_2_med_facit` q43 ("... lunch menu. (1 point)", 1 point) and
"Fråga 1" of `svenska_2_grammatik_omprov_variant_1_med_facit` and `_variant_2_med_facit`
(last paragraph "Poäng: 6 poäng", 6 points).

Root cause (R1). `review_source_item` (`docx_source_review.py:60-85`) reads the points from
the chunks (`printed_points(chunks)`, `:71`) but builds the body with
`review_source_paragraphs` (`shared_body.py:177-193`), which renders each chunk verbatim apart
from printed answer lines. No points wording is removed on this path. The reply paths remove
it: `with_printed_points` (`docx_source_rules.py:326-346`, only for a reply without points, a
label anywhere, leaving "Totalt:" of "Totalt: 36 p") and the rebuild path's
`native_carrier_spans` (`source_native_carriers.py:46-115`, which leaves "Poäng:" of a
recovered "Poäng: 6 poäng"). QTI (`qti_import_leaf_items.py:86-92`) and DigiExam
(`digiexam_import.py:184`) take points from MAXSCORE and `maxScore` and copy the prompt
unchanged.

Order of operations (D1). No reader of an item's points reads `NativeExamItem.body`:

- DOCX points come from chunk text: `printed_points` and `text_points`
  (`docx_source_rules.py:314-323`), `printed_points_plan` (`docx_points_lines.py:169`) and
  `apply_printed_points` (`docx_section_points.py:38`, run at `docx_ai_build.py:190`, after
  the review items at `:93`). The review checks in `docx_section_instructions.py:178-218` read
  the printed total. `native_carrier_spans` reads source text and its `points` argument.
- `original_wording` is built from chunk text (`docx_import_records.py:75`). Retry reads the
  saved `retry_source` chunks (`exam_workspace_docx_retry.py:180,264-265`), never the body.
- QTI and DigiExam points are the stored `max_score`. The QTI export writes
  `max_score=item.points` (`examnet_qti_leaf_items.py:67`). The AI answer-key suggestions send
  body text and never points (`answer_key_view.py:196-210`). The frontend parses no points
  from text.

`apply_printed_points` can still change a DOCX item's points after its body is built (a
printed point beats the reply). So the removal runs where every item's points are settled:
on the final item, beside the W10 answer-line gate (D2). It reads the stored `points`, edits
only the body and review, and never changes the chunks, `retry_source`, `original_wording`
or `facit_text`.

Behaviour (D5-D8):

- A printed points label is a parenthesised label ("(1 point)", "(2 p)") or a label that
  ends its line ("Poäng: 6 poäng", "Max 36p"). A bare label followed by more words ("Give 3
  points of view.") is text and supplies no points.
- At the end of a question's text, two shapes are points wording. One is a parenthesised
  label ending the last line ("... lunch menu. (1 point)"); the label and the blank space
  before it leave. The other is a last line that is only a points line ("Poäng: 6 poäng",
  "Totalt: 6 p", "6 p"); the whole line leaves, and an emptied paragraph is dropped.
- The wording leaves only when its number equals the item's points. When the wording is the
  whole question text, it stays.
- When the shape matches but the number differs, the wording and the points stay. The item
  records the exact wording in `leftover_points_text` (for example "(3 poäng)"). With no
  settled points, or when the wording is the whole question text, nothing is recorded.
- Word (every path: review, reply, rebuild, retry), QTI and DigiExam apply the same rule. A
  sentence that mentions points ("Väljer eleven det får den 2 poäng.", "Använd mellan 3
  poäng och 5 poäng.") never matches: it is neither removed nor offered.
- The exam workspace points note (TASK-SKRIPT-40-04-10) shows one offer for all candidates:
  "{n} frågor har kvar poängtext, t.ex. ‘(3 poäng)’. Ta bort?". It has three glyphs, named
  only in the tooltip and aria-label:
  - A check removes each item's stored text from its body (an emptied paragraph is dropped)
    and clears the field on every item, as one undo step.
  - An X clears the field on every item, as one undoable edit, and keeps the text.
  - An arrow jumps to the first candidate.
  The count n covers only items whose body still ends in their stored text. The example is
  the first candidate's stored text.

## Contract Inputs

- User decision 2026-10-19 "Import strips it" and the user answers of 2026-10-19 (Q1 "End of
  text only", Q4/Q5 "All importers", Q6 "Yes, stop it"), relayed by the orchestrator
  `944b5a5a`; Q3 decided A by the orchestrator.
- User direction 2026-10-19, which replaces Q2 "Keep + flag": the least editing for the
  teacher; wording the rule leaves becomes one offer, chosen through AskUserQuestion as "One
  offer for all". User correction 2026-10-19: candidates use the same shapes as the strip, and
  the volt question must stay unchanged. N1-N3 were decided A by the orchestrator under the
  user's rules. Gate: `agent-planning:user-closure-gate`.
- Retained root `01a1546f-8119-7bd4-884f-9cbb125b8e0c`: plan
  `evidence/planning/TASK-SKRIPT-39-04-21/plan.md` (ledger closed); explorer discovery
  `e01`-`e21`; probes `evidence/probes/dump_replays.py`, `scan_points_wording.py` and
  `q6_label_probe.py`.
- Baseline replay dumps at `f3c71530`: `~/logs/replays-39-04-21/base/`, scan
  `~/logs/replays-39-04-21/base-scan.txt`; the Q6 grammar replay
  `~/logs/replays-39-04-21/q6/` is byte-identical to the base.
- History: `334354b9` (39-04-12) deleted a points strip that "altered teacher stems";
  TASK-SKRIPT-39-04-20 (score-field line; its Q2 hypothesis, the "Poäng:" residue);
  TASK-SKRIPT-39-04-11 D2 (one owner per points line).

## Core Vertical And Performance

One structural match over the last line of each imported question's body. The only new
stored data is one optional item field, `leftover_points_text`. Event and export formats are
unchanged.

Units, each for one fresh junior:

- U1: the label grammar and the shared rule. `POINT_LABEL` (and `SCORE_FIELD`,
  `_LABEL_RUN`) in `docx_source_rules.py`; new `points_wording.py` with the text rule, the
  native-body removal and `with_settled_points_wording`.
- U2 (after U1): Word wiring and the field.
  - `NativeExamItem.leftover_points_text`, and the regenerated openapi types.
  - `with_settled_points_wording` sets the field.
  - The final gate in `docx_ai_build.py` and `exam_workspace_docx_retry.py`.
  - `with_printed_points` reads points only.
  - A recovered points line in `native_carrier_spans` leaves whole.
- U3 (after U2's field, beside the rest of U2): QTI and DigiExam wiring in
  `qti_import_leaf_items.py` and `digiexam_import.py`.
- U4 (after TASK-SKRIPT-40-04-10 merges and `origin/main` is merged): the offer line in the
  40-04-10 points note, with the check, X and arrow, and its Vitest specs.

## Validation

- U1, fail-first, in `tests/unit/domain/curated_apps/exam_workspace/test_points_wording.py` and
  `test_docx_points_line.py`:
  - Both shapes leave whole and keep the number.
  - Look-alike text stays: "Give 3 points of view.", "Väljer eleven det får den 2 poäng.",
    "The train leaves at 3 p.m.", a mid-text "(2 p)".
  - Differing numbers keep the text and leave the review unchanged.
  - A stem that is only points wording stays.
  - The volt question ("Pelle gör en fin volt, Sara gör en ful. Sätt poäng på Sara och
    Pelles volter. Använd mellan 3 poäng och 5 poäng.") is unchanged, for every importer
    (U1-U3), and records no candidate.
  - Marks and gap or picture segments around the cut are kept.
- U2, fail-first: a fixture test that the three observed items lose their wording and keep
  their points, `original_wording` and `retry_source`, and that no other item of those exams
  changes.
  - `with_printed_points` reads the points and leaves the text.
  - "Totalt: 36 p" and a recovered "Poäng: 6 poäng" on the rebuild path leave no "Totalt:"
    or "Poäng:".
  - The retry gate applies the rule.
  - Regression for `334354b9`: a stem that mentions points mid-sentence is unchanged.
- U3, fail-first, with synthetic QTI and DigiExam items:
  - A trailing "(2 p)" with max_score 2 leaves and the item keeps 2 points; the exported
    MAXSCORE equals the points.
  - The fixture prompts ending "får den 2 poäng." are unchanged.
  - A differing number keeps the text and records it as the candidate.
  - With no max_score, nothing is recorded.
  - A stem that is only "(2 p)" stays and records nothing.
- U2 and U3 candidate cases: the field holds the exact stored wording, and is None for the
  volt question, a mid-text label, no settled points and a whole-stem wording.
- U4, Vitest:
  - The line shows the count and the example text.
  - The check removes only bodies that still end in their stored text, as one undo step, and
    clears every field.
  - The X keeps the text and the offer does not return.
  - The arrow selects the first candidate.
  - With no candidate there is no line.
- Replay bar (D4): the ten recorded replays at `f3c71530` and at the task head differ only
  in the three observed bodies. The new field adds `leftover_points_text: null` to every
  item; any item with a non-null value is listed to the parent.
- Focused test files only, per unit; `pdm run lint`, `pdm run typecheck`,
  `pdm run docs-validate`; the domain suite on the orchestrator's go.

## Stop Conditions

- A replay difference beyond D4 goes to the parent before merge.
- A new path that derives points from the body stops the task (D1).
- Matching is by structure only, never by an exam's wording; no fallback or compatibility
  path.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Order of operations: every reader of an item's points reads the source (chunks, MAXSCORE, `maxScore`) or the stored `points` field, never `NativeExamItem.body`. The removal runs on the body only, takes the settled points as input, and never changes the chunks, `retry_source`, `original_wording` or `facit_text`. A new path that derives points from the body fails the task. Source: user 2026-10-19 and the lead's map (Implementation Contract). |
| D2  | Root cause R1: `review_source_item` takes its points from the chunks, but its body (`review_source_paragraphs`) keeps every chunk verbatim. Seam: the removal runs on the final item beside the W10 gate (`docx_ai_build.py:193`, retry `exam_workspace_docx_retry.py:250`), because `apply_printed_points` can still change points after the body is built. Like `gated_item`, it edits only the final body. Refined by the lead from the seam first proposed in `review_source_paragraphs`. |
| D3  | Value gate: wording is removed only when its number equals the item's points. With no points, or with several labels, nothing is removed. |
| D4  | Regression bar: in the ten recorded replays, only the three observed bodies change. bf26 q43 loses " (1 point)", and "Fråga 1" of omprov variants 1 and 2 loses its "Poäng: 6 poäng" paragraph. Points, facit, events and every other item stay byte-identical; any other difference goes to the parent before merge. |
| D5  | A printed points label is a parenthesised label or a label followed on its line only by blank space and at most one punctuation mark. A bare label followed by more words is text and supplies no points (Q6 A, user 2026-10-19 "Yes, stop it"). The probe replays are byte-identical under this grammar. |
| D6  | Points wording is one of two shapes at the end of a question's text: a parenthesised label ending its last line, which leaves with the blank space before it, or a last line that is only a points line (`points_line`, one label), which leaves whole, an emptied paragraph being dropped (Q1 A, user "End of text only"). When it is the whole question text, it stays (Q3 A, orchestrator). |
| D7  | When the shape matches (D6) but the number differs from the item's points, the wording and the points stay and no review reason is added. The item records the exact wording in `NativeExamItem.leftover_points_text: str \| None`. Nothing is recorded with no settled points (N2 A) or when the wording is the whole question text (N3 A). A bare label inside a sentence is never recorded (user correction 2026-10-19; the volt question). Replaces Q2 "Keep + flag" (user direction 2026-10-19). |
| D8  | Every importer applies D5-D7. Word applies them on the review, reply, rebuild and retry paths: `with_printed_points` reads points only, and `native_carrier_spans` drops a recovered points line whole. QTI and DigiExam apply them to the final leaf item, gated by `max_score` (Q4/Q5 A, user "All importers"). |
| D9  | No backward compatibility, fallback or wording comparison (repository invariant, ST-SKRIPT-39-04). Status `ready` through `agent-planning:user-closure-gate` on the user answers of 2026-10-19, relayed by the orchestrator `944b5a5a`. |
| D10 | One offer for all candidates, in the 40-04-10 points note: "{n} frågor har kvar poängtext, t.ex. ‘(3 poäng)’. Ta bort?". It has three glyphs, named only in the tooltip and aria-label. The check removes each item's stored text from the end of its body and clears every field, as one structural `editDocument`, which is one undo step. The X clears every field in one undoable edit and keeps the text, so the offer does not return; undo brings it back (N1 A). The arrow selects the first candidate. The count n covers only bodies that still end in their stored text. The line is added to the 40-04-10 note after that task merges; the note is not forked. User "One offer for all" 2026-10-19 and the orchestrator 944b5a5a. |
| D11 | After conversion, only Skriptoteket's converted structure counts: candidates are decided from the stored item body and its settled `points`, never from the source exam's structure or numbering. Any item the offer or the arrow names is named by its list number in the workspace. User rule 2026-10-19, relayed by the orchestrator 944b5a5a. |

### Resume here (2026-10-19)

- State: contract accepted, status ready. U1 done at `04456045` (grammar D5, shared rule
  `points_wording.py`). U2 running: the `leftover_points_text` field, Word final gate and retry,
  `with_printed_points` reads only, whole points line in `native_carrier_spans` (work order
  `evidence/work-orders/u2-word-wiring-and-field.md` in the retained root). Lead `d19390d2`
  (implementation-specialist), branch `codex/task-skript-39-04-strip-points-wording-remote`,
  worktree `/home/paunchygent/apps/skriptoteket-task-skript-39-04-strip-points-wording-remote`;
  never pushed.
- Next: when U1 returns, U2 (the field first), then U3; the replay bar; the domain suite on
  the orchestrator's go. U4 waits for TASK-SKRIPT-40-04-10 to merge into `origin/main`.
