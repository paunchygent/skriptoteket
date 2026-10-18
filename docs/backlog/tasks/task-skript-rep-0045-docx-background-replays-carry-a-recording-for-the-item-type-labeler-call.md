---
type: task
id: TASK-SKRIPT-REP-0045
title: DOCX background replays carry a recording for the item-type labeler call
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - tests/integration/test_exam_workspace_docx_background.py passes for all nine recorded exams on origin/main, including the three grammatik and kursavslutande exams
  - The cause of the missing item_type_label recording is named and fixed at that cause
backlog_document_profile: contract-derived
---

## Implementation Contract

`tests/integration/test_exam_workspace_docx_background.py::test_every_recording_is_served_once_to_its_own_request` fails on origin/main (reproduced at a0a81ab5a by the 39-06-10 lead, 2026-10-18) for the three grammatik and kursavslutande exams with "no recording for item_type_label": 3 failed, 6 passed. The replay requires a recording for every build request (REP-0042, e95b9656b), and the background DOCX job now makes an item-type labeler call that those recordings lack. The test is docker-marked, so the default suite and the pre-push check miss it.

This task finds why those three exams reach the labeler without a recording (recordings older than the labeler step, a labeler call that should not happen for them, or a support-code key mismatch) and fixes that cause (R1-R3).

Non-goals: changing the labeler, the conversion or the replay rule.

## Contract Inputs

- `tests/integration/exam_workspace_docx_background_support.py` and its recordings; 39-05-04 (item-type labeler), REP-0042 (replay rule).
- Report from the 39-06-10 lead (146bc2d8) via the Hemma orchestrator, 2026-10-18.

## Core Vertical And Performance

The vertical is the recorded transport of the DOCX background job: each build request, labeler call included, is served once from its own recording. No performance concern.

## Validation

- `pdm run test tests/integration/test_exam_workspace_docx_background.py -m "integration or not integration"` on Hemma, all nine exams.
- Lint and typecheck for touched files.

## Stop Conditions

Stop and report to the parent before making any live model call beyond re-recording the missing labeler responses for the three exams, or if the fix needs a change to conversion behaviour.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| R1  | The root cause is named in the closeout before any fix. |
| R2  | If the recordings predate the labeler step, only the missing labeler responses for the three exams are re-recorded live, and the token count is reported; nothing else is re-recorded. |
| R3  | The replay rule that every build request needs its own recording stays. |

### R2 amendment (user ruling 2026-10-18)

Re-record live exactly the 14 stale `label_b` labeler calls: Svenska grammatik variant 1 `q2`, `q5`, `q6`, `q7` (4); variant 2 `q1`-`q7` (7); kursavslutande course final `q21`, `q22`, `q24` (3). Report the token count. The test support keeps capture-time request keys, so a changed labeler request shows as unmatched. Nothing else is re-recorded.

## Root Cause (R1)

The three Svenska exams' `label_b` recordings were captured on 2026-10-14 at `c270419e`. At that revision the second-pass labeler request was built from the raw grouping manifest. Commit `c67dcb70` (2026-10-17, "printed point totals reach their questions through one owner per points line") added `assign_points_lines` before labeling. Since then, the source text of all 14 recorded second-pass questions in those exams includes the points line (for example, course-final `q21` gains `Poäng: 1 poäng`). The replay support derived each recording's expected request text from the current production code instead of storing the request the recording answered. So it could not tell a stale recording from a current one. Deriving from the raw manifest left the new requests unmatched. Deriving from the placed manifest (`343f4eef`) served the old replies to the new requests, which was review finding F1.

Fix: each `label_b_<qid>.json` recording carries its capture-time request key in `label_b_<qid>.request.txt`. The transport matches only that stored key. The 14 stale replies are re-recorded live against the exact current requests. The production `placed_manifest` extraction from `343f4eef` is reverted, because the test support was its only other consumer.
