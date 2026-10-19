---
type: task
id: TASK-SKRIPT-39-04-20
title: A paragraph that holds only a score field is consumed whole as the points source
  and leaves no slash in the question
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
  - A source line that holds only a score field ("/N p", with optional blank space or leading underscores) is consumed whole as the item's points source and leaves no text in the item; a score field after question text and a slash used elsewhere stay as today; the points value is unchanged
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Defect, observed in the Mac staging walk at `003c874a` on 2026-10-19:
`tests/fixtures/exam_conversion/docx_user_exams/omprov_grammatik_sve2.docx` prints a
score-field paragraph such as "/4 p" or "/8 p" after each question's answer lines. The
converter takes the item's points from it, but leaves a lone "/" paragraph at the end of
the question body. The "/" shows in the editor, the preview and every printed PDF and
DOCX, right before "Poäng: 4 poäng".

Root cause (R1). The nine omprov items are built on the source-formatting rebuild path
(formatting event `rebuilt`): the reply lists neither the score-field paragraph nor any
"/" text, and `source_item_formatting.item_source_formatting` rebuilds the body from the
item's own source chunks, joined with `\n`. A recovered score is excluded from that
rebuild by `source_native_carriers.native_carrier_spans`, which takes the span of each
`POINT_LABEL` match whose value equals the item's points. `POINT_LABEL` covers "4 p" and
an optional `(` wrapper, never the score field's `/`, so the excluded span is "4 p" and the
rebuilt body keeps a paragraph holding only "/". The points themselves come from the
reply (`points: 4`) and are correct. No other owner consumes a question-owned points
line whole on the rebuild path: the "Poäng: N poäng" lines of
`svenska_2_kursavslutande_prov_med_facit` never reach an item body only because those
items are built on the `exact` path.

Baseline at `06985163` (ten replays): a lone "/" body paragraph ends 9 omprov items and
6 `exempelprov_grammatik_sve2_v2_1` items; no other exam has one. A disposable probe that
widens the carrier span over the whole score-field line removes exactly that paragraph
from each item (the paragraph is dropped, not emptied) and keeps every points value.

## Contract Inputs

- Mac parent request 2026-10-19 (this defect and its done-definition), relayed by the
  Hemma orchestrator `944b5a5a` in the lead assignment.
- Retained root `01a1531c-ada5-7ff9-91e0-337d659b55d5`: `evidence/probes/score_field_probe.py`
  (the lone "/" per item), `score_field_chunks.py` (source paragraphs "/4 p" ... "/12 p"),
  `widen_span_probe.py` (the seam), `dump_replays.py` (the ten replays); explorer results
  `8a44de93` (rebuild path and carrier span) and `83c7a18c` (every label remover in `src/`).
- Baseline replay dumps at `06985163`: `~/logs/replays-39-04-score-field/base/`.

## Core Vertical And Performance

One more structural check per recovered score inside `native_carrier_spans`; no new data
is stored and the document and event formats are unchanged.

## Validation

- Fail-first adversarial unit tests on the carrier seam through `aligned_native_item`:
  "/4 p", "/ 4 p", "____ /8 p", "/4 poäng" and "/4,5 p" lines are consumed whole and leave
  no paragraph; a score field after question text on the same line ("Skriv tre ord /4 p")
  keeps today's output; a slash elsewhere ("verb/nominaliseringar", "1/2") stays; a score
  field whose value differs from the item's points stays visible; the item's points are
  unchanged.
- A focused fixture test on `omprov_grammatik_sve2` (and `exempelprov_grammatik_sve2_v2_1`):
  no item body holds a "/" line and each item keeps its points. It fails at `06985163`.
- The ten recorded replays (39-04-15/16/17 set: the eight `docx_key_provenance_v14` exams
  and the two user exams), dumped at `06985163` and at the task head: only the 15 items
  that hold a lone score-field remnant change, and each change is exactly that paragraph
  removed. Any other difference goes to the parent before merge.
- On Hemma, after the orchestrator's go: `PYTHONHASHSEED=0 pdm run test-parallel
  tests/unit/application/curated_apps tests/unit/domain/curated_apps -q -p no:randomly`;
  `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

### Resume here (2026-10-19)

- State: contract decided (D1-D9), status `in_progress`; implementation not started.
- Next: unit U1 (fresh junior): `SCORE_FIELD` in `docx_source_rules.py`, the widening in
  `native_carrier_spans`, fail-first unit tests and the fixture test; then the replays.
- Branch `codex/task-skript-39-04-score-field-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-39-04-score-field-remote`; never pushed.
- Retained root:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a1531c-ada5-7ff9-91e0-337d659b55d5`.

## Stop Conditions

- A replay difference other than a removed lone score-field paragraph goes to the parent
  before merge.
- Matching is by structure only (a pattern for the whole line), never by the exam's
  wording; no fallback and no compatibility path.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | A score-field line is one `\n`-separated line of an item's joined source text that holds one `POINT_LABEL` match and otherwise only a `/` before it, with optional blank space around the `/` and optional underscores and blank space before it: `^[ \t_]*/[ \t]*<POINT_LABEL>[ \t]*$`. The pattern `SCORE_FIELD` lives beside `POINT_LABEL` in `docx_source_rules.py` and is built from `POINT_LABEL.pattern`, so units ("p", "poäng", "points") and decimals follow `POINT_LABEL`. Decided by the implementation lead from R1 and the Mac parent's done-definition. |
| D2  | `native_carrier_spans` keeps its conditions for a recovered score (value equals the item's points, outside quotes, recovered). When such a score's line is a score-field line, its excluded span widens to the whole line. The rebuild then drops the empty paragraph. The points value is unchanged. |
| D3  | A score field after question text on the same line ("Skriv tre ord /4 p") is no score-field line; its output stays as today. Whether its `/` should also go is user question Q1, raised to the orchestrator and outside this task. |
| D4  | A slash anywhere else stays ("verb/nominaliseringar", "1/2", a "/" line with no points label). A bare "4 p" line is already excluded whole and stays so. A line of underscores and a label with no `/` ("____ 4 p") is no score field and keeps today's output. |
| D5  | Reply text is out of scope: no recorded reply emits a score-field paragraph into an item body, and `with_printed_points` (`_without_label`) is unchanged. |
| D6  | Write boundary: `docx_source_rules.py`, `source_native_carriers.py` and tests. `review_answer_key_cut` and the left-out accounting (TASK-SKRIPT-39-04-18 and -19, in parallel) are not touched. |
| D7  | Regression bar: in the ten replays, only the 9 omprov and 6 exempelprov items with a lone "/" paragraph change, each by losing exactly that paragraph; every other field and every event stays byte-identical. |
| D8  | No backward compatibility, fallback or wording comparison (repository invariant, ST-SKRIPT-39-04). |
| D9  | Status `ready` on the Mac parent's request of 2026-10-19 (this defect and its done-definition), relayed by the Hemma orchestrator `944b5a5a` in the lead assignment; then `in_progress` under the same assignment. |
