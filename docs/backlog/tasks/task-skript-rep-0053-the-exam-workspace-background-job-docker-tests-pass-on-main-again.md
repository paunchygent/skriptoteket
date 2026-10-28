---
type: task
id: TASK-SKRIPT-REP-0053
title: The exam workspace background-job Docker tests pass on main again
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-28'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - pytest -m docker tests/integration/test_exam_workspace_docx_background.py passes on main
  - Each fix states whether the test or the product code was wrong
backlog_document_profile: contract-derived
---

## Implementation Contract

Two Docker-marked tests in `tests/integration/test_exam_workspace_docx_background.py` fail on main 6000a1669 and 32d503c98; the pre-push suite does not run them:

- `test_quiz_job_saves_batches_progressively_and_publishes_complete_document`: an `all(...)` assertion is false.
- `test_every_recording_is_served_once_to_its_own_request[bf26_english_1_unit_test_kap_1_2_med_facit]`: the served recording order differs at index 17 (`docx_w2-12-01` against `docx_w2-11-01c01`) and the expected list has one more item, `label_b_q50`.

Find which earlier change made each fail. Fix the product when the product is wrong, and update the test or its recordings when the test lags an accepted change.

## Contract Inputs

- Failure log on Hemma: `~/logs/3910-docker-main.log`; `git log` on the test file, its recordings and the background job.

## Core Vertical And Performance

One background Word import job with recorded AI answers, from the first batch to the published document. No performance change.

## Validation

- `pdm run pytest -m docker tests/integration/test_exam_workspace_docx_background.py` passes, with the cause of each failure recorded in the commit message.

## Stop Conditions

- A fix would change accepted product behaviour. Report it instead.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Repair each failure at its cause: product code when it is wrong, test expectations or recordings when they lag an accepted change. |
| D2  | Light route: one junior, the focused Docker test file as proof, no review. Orchestrator decision 2026-10-28.                       |
