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
status: proposed
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
it: `with_printed_points` (`docx_source_rules.py:326-346`) and the rebuild path's
`native_carrier_spans` (`source_native_carriers.py:46-115`). QTI (`qti_import_leaf_items.py:86-92`)
and DigiExam (`digiexam_import.py:184`) take points from MAXSCORE and `maxScore` and copy
the prompt unchanged.

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

The removal runs on the body only, takes the settled points as input, and never changes the
chunks, `retry_source`, `original_wording` or `facit_text`. On the review path it sits in
`review_source_paragraphs`, because `aligned_source_item` aligns review items through a second
render of the same function (`docx_item_alignment.py:72-86`).

The carrier shapes, the reply and rebuild paths, QTI and DigiExam, disagreement and a stem
that holds only points wording wait on user questions Q1-Q6 (Resume here). Until they are
answered, this contract is proposed and only the decided terms below hold.

## Contract Inputs

- User decision 2026-10-19 "Import strips it", relayed by the orchestrator `944b5a5a` in the
  lead assignment `d19390d2`.
- Retained root `01a1546f-8119-7bd4-884f-9cbb125b8e0c`: plan
  `evidence/planning/TASK-SKRIPT-39-04-21/plan.md`; explorer discovery `e01`-`e21`; probes
  `evidence/probes/dump_replays.py` and `scan_points_wording.py`.
- Baseline replay dumps at `f3c71530`: `~/logs/replays-39-04-21/base/`, scan
  `~/logs/replays-39-04-21/base-scan.txt`.
- History: `334354b9` (39-04-12) deleted a points strip that "altered teacher stems";
  TASK-SKRIPT-39-04-20 (score-field line, Q2 hypothesis "Poäng:" residue);
  TASK-SKRIPT-39-04-11 D2 (one owner per points line).

## Core Vertical And Performance

One structural match over the last lines of each imported question's body, with no new
stored data and unchanged document, event and export formats.

## Validation

- Fail-first adversarial unit tests at the review seam (`review_source_paragraphs` through
  `review_source_item` and `aligned_source_item`): the three observed texts lose their
  wording and keep their points, and body and alignment hold the same paragraphs. A trailing
  sentence that mentions points ("Väljer eleven det får den 2 poäng.", "Give 3 points of
  view.") stays unchanged. Wording whose number differs from the points stays. The chunks,
  `printed_points(chunks)` and `original_wording` are unchanged.
- An order-of-operations test per importer: the item's `points` and the exported QTI
  MAXSCORE equal the source points after the removal. Per importer (after Q4 and Q5): strip
  and keep the points, keep look-alike text, and handle a stem that holds only points wording
  (after Q3).
- Regression test for `334354b9`: prose that mentions points stays unchanged on every
  changed path.
- The ten recorded replays at `f3c71530` and at the task head: only the three observed
  bodies change (D4).
- Focused test files only, named per unit; `pdm run lint`, `pdm run typecheck`,
  `pdm run docs-validate`.

## Stop Conditions

- A replay difference beyond D4 goes to the parent before merge.
- A new path that derives points from the body stops the task (D1).
- Matching is by structure only, never by an exam's wording; no fallback or compatibility
  path.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Order of operations: every reader of an item's points reads the source (chunks, MAXSCORE, `maxScore`) or the stored `points` field, never `NativeExamItem.body`. The removal runs on the body only, takes the settled points as input, and never changes the chunks, `retry_source`, `original_wording` or `facit_text`. A new path that derives points from the body fails the task. Source: user 2026-10-19 and the lead's map (Implementation Contract). |
| D2  | Root cause R1: `review_source_item` takes its points from the chunks, but its body (`review_source_paragraphs`) keeps every chunk verbatim. The DOCX review fix sits in `review_source_paragraphs`, so the review body and its alignment come from one render. |
| D3  | Value gate: wording is removed only when its number equals the item's points. With no points, or with several labels, nothing is removed. |
| D4  | Regression bar: in the ten recorded replays, only the three observed bodies change. bf26 q43 loses " (1 point)", and "Fråga 1" of omprov variants 1 and 2 loses its "Poäng: 6 poäng" paragraph. Points, facit, events and every other item stay byte-identical; any other difference goes to the parent before merge. |

### Resume here (2026-10-19)

- State: planned at `f3c71530`, status proposed; no code written. Lead `d19390d2`
  (implementation-specialist), branch `codex/task-skript-39-04-strip-points-wording-remote`,
  worktree `/home/paunchygent/apps/skriptoteket-task-skript-39-04-strip-points-wording-remote`;
  never pushed.
- Waiting on: user answers to Q1-Q6 through the orchestrator `944b5a5a` (retained plan
  ledger rows; recommendation A for each):
  - Q1, the carrier shapes, end of text only: a parenthesised label ending the last line, and
    a last paragraph that is only a points line, removed whole.
  - Q2, disagreement: the wording stays and the points stay.
  - Q3, a stem that is only points wording stays.
  - Q4, the DOCX reply and rebuild paths use the same rule.
  - Q5, QTI and DigiExam apply it, gated by `max_score`.
  - Q6, a bare label followed by more words stays text and stops counting as printed points.
- Next: on the answers, close the ledger, derive the remaining terms, then the fail-first
  unit and the implementation units through fresh juniors.
