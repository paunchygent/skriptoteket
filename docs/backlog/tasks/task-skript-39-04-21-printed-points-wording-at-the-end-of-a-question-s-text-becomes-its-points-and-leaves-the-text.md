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
- The wording leaves only when its number equals the item's points. When the numbers differ,
  the wording and the points stay and the item goes to review with "Poängen i frågetexten
  skiljer sig från frågans poäng. Kontrollera poängen.". When the wording is the whole
  question text, it stays.
- Word (every path: review, reply, rebuild, retry), QTI and DigiExam apply the same rule. A
  sentence that mentions points ("Väljer eleven det får den 2 poäng.") never matches.

## Contract Inputs

- User decision 2026-10-19 "Import strips it" and the user answers of 2026-10-19 (Q1 "End of
  text only", Q2 "Keep + flag", Q4/Q5 "All importers", Q6 "Yes, stop it"), relayed by the
  orchestrator `944b5a5a`; Q3 decided A by the orchestrator. Gate:
  `agent-planning:user-closure-gate`.
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

One structural match over the last line of each imported question's body, with no new
stored data and unchanged document, event and export formats.

Units, each for one fresh junior:

- U1: the label grammar and the shared rule. `POINT_LABEL` (and `SCORE_FIELD`,
  `_LABEL_RUN`) in `docx_source_rules.py`; new `points_wording.py` with the text rule, the
  native-body removal and `with_settled_points_wording`.
- U2 (after U1): Word wiring. The final gate in `docx_ai_build.py` and
  `exam_workspace_docx_retry.py`; `with_printed_points` reads points only; a recovered
  points line in `native_carrier_spans` leaves whole.
- U3 (after U1, beside U2): QTI and DigiExam wiring in `qti_import_leaf_items.py` and
  `digiexam_import.py`.

## Validation

- U1, fail-first, in `tests/unit/domain/curated_apps/exam_workspace/test_points_wording.py` and
  `test_docx_points_line.py`:
  - Both shapes leave whole and keep the number.
  - Look-alike text stays: "Give 3 points of view.", "Väljer eleven det får den 2 poäng.",
    "The train leaves at 3 p.m.", a mid-text "(2 p)".
  - Differing numbers keep the text and add the review reason once.
  - A stem that is only points wording stays.
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
  - A differing number is flagged.
  - A stem that is only "(2 p)" stays.
- Replay bar (D4): the ten recorded replays at `f3c71530` and at the task head differ only
  in the three observed bodies.
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
| D7  | When the wording's number differs from the item's points, the wording and points stay and the item goes to review with "Poängen i frågetexten skiljer sig från frågans poäng. Kontrollera poängen.", appended once to its existing reasons (Q2 B, user "Keep + flag"). |
| D8  | Every importer applies D5-D7. Word applies them on the review, reply, rebuild and retry paths: `with_printed_points` reads points only, and `native_carrier_spans` drops a recovered points line whole. QTI and DigiExam apply them to the final leaf item, gated by `max_score` (Q4/Q5 A, user "All importers"). |
| D9  | No backward compatibility, fallback or wording comparison (repository invariant, ST-SKRIPT-39-04). Status `ready` through `agent-planning:user-closure-gate` on the user answers of 2026-10-19, relayed by the orchestrator `944b5a5a`. |

### Resume here (2026-10-19)

- State: contract accepted, status ready; no code written. Lead `d19390d2`
  (implementation-specialist), branch `codex/task-skript-39-04-strip-points-wording-remote`,
  worktree `/home/paunchygent/apps/skriptoteket-task-skript-39-04-strip-points-wording-remote`;
  never pushed.
- Next: U1 through a fresh junior; then U2 and U3 in parallel; then the replay bar and the
  domain suite on the orchestrator's go.
