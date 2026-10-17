---
type: task
id: TASK-SKRIPT-REP-0042
title: Repair the two failing docker-suite tests in the DOCX background job proof
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- All nine tests in tests/integration/test_exam_workspace_docx_background.py pass
  under -m docker against the real PostgreSQL test database, each assertion tracks
  the current job, diagnostics and recording contracts, and no test asserts wall-clock
  timing
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the two tests that fail on main in the docker-marked suite
`tests/integration/test_exam_workspace_docx_background.py` (2 failed, 7 passed
on main `26f65fda`, 2026-10-17). The suite sits outside `pdm run test-parallel`
because `addopts` excludes the `docker` marker. Causes found 2026-10-17:

- `test_quiz_job_saves_batches_progressively_and_publishes_complete_document`
  asserts `model.diagnostics == []` on a succeeded job. Since a864a085 a
  successful build retains one `stage="formatting"` event per item
  (`DocxBuildState.record_formatting`, codes `exact`, `aligned`, `rebuilt`);
  the job stores 28 of them. The unit tests already assert that no
  non-formatting event exists. The docker test moves to the current
  diagnostics contract.
- `test_every_recording_is_served_once_to_its_own_request[bf26_english_1_unit_test_kap_1_2_med_facit]`
  reports `no recording for docx_exam_build`. The current build request for
  bf26 batch `w2-10-01` fits no recording in
  `tests/fixtures/exam_conversion/docx_key_provenance_v14/bf26_english_1_unit_test_kap_1_2_med_facit/`
  (a recording fits when its anchors lie inside the request's visible anchors
  and overlap its pending anchors). The transport then answers 500 and the job
  retries as `w2-10-01c01` and falls back to review items for `body:0115` and
  `body:0116`. The repair finds which change moved the request, and makes the
  test replay the recording against the current request contract.

## Contract Inputs

- User request 2026-10-17: do the task in the parent session with a Sol
  driver/navigator pair and an independent Sol reviewer.
- Reproduction log: retained root `01a148db-64d7-7b40-9a2e-34373c3de59c`
  `evidence/baseline-main-26f65fda.log`.

## Core Vertical And Performance

The suite runs the production job handler, pipeline composition, job queue,
token ledger and QTI validators against real PostgreSQL with only the network
replaced by recorded replies; that stays. No performance concern.

## Validation

`pdm run pytest tests/integration/test_exam_workspace_docx_background.py -m docker -p no:cacheprovider -q -o addopts=""`
(all nine pass), plus the unit tests of any production or test-support file the
repair touches. Scoped ruff and mypy.

## Stop Conditions

- Stop and report if production behaviour, not the test, is wrong.
- Stop and ask the user before any live provider re-recording; it costs money.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The docker test asserts the current diagnostics contract: a succeeded job holds no non-formatting event, and its formatting events are the per-item transfer paths. |
| D2  | The bf26 replay matches the current build request contract; the fix follows the root cause of the request change, not a looser matcher that hides it. |
| D3  | No test asserts wall-clock timing; contract tests track the current contracts. |
| D4  | Production code changes only if the root cause shows production is wrong, and then only after reporting it. |
