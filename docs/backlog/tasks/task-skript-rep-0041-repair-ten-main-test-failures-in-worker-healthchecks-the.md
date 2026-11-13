---
type: task
id: TASK-SKRIPT-REP-0041
title: Repair ten main test failures in worker healthchecks, the compose contract
  and alignment timing
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-16'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-code-review
  decided_at: '2026-10-17T00:10:00+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Independent Sol review .orchestration/context/sessions/01a146ac-4ce2-72db-8d74-98aef59f9a51/evidence/review-rep0041.md (changes requested, F1 timeout double) and rereview evidence/rereview-rep0041.md in the same root (approved, F1 resolved); merged to main as 23fc5cf0; focused 97 passed on main after the merge.'
task_kind: repository
acceptance_criteria:
  - The six worker-healthcheck tests in tests/unit/cli/test_native_healthchecks.py pass on the Mac and on Linux without changing the production script's behaviour.
  - The two compose-contract tests in tests/unit/test_docker_dev_shared_auth_contract.py assert the current native worker healthcheck in compose.yaml and compose.prod.yaml.
  - The focused-item timing test in test_source_alignment_repair6.py is deleted, and no test in the suite asserts a wall-clock duration or speed ratio that depends on the host or its load.
  - The six healthcheck tests assert the current behaviour of healthcheck_execution_worker.sh, step by step.
  - All ten pass alone and in one pdm run test-parallel run; scoped ruff and mypy pass; the diff is reviewed, merged into main and pushed.
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair ten tests that fail on main (evidence: full suite at 2c1d1fcd, 19 failed,
4,229 passed; nine of those belong to TASK-SKRIPT-39-05-14 and are repaired
there). Causes found 2026-10-16:

- Worker healthchecks (six tests): `healthcheck_execution_worker.sh` runs
  `timeout 4 psql ...`. The test sets `PATH` to its fake tools plus
  `/usr/bin:/bin`. macOS has no `timeout` there (only Homebrew's
  `/opt/homebrew/bin/timeout`), so the database step fails before the Docker
  and artifact checks the tests target. The production script runs in the
  Linux container, where `timeout` exists, and stays unchanged. The test
  environment supplies `timeout` so the script runs the same path on both
  hosts.
- Compose contract (two tests): the 2026-10-05 health work replaced the worker
  healthcheck with `["CMD", "/bin/sh", ".../healthcheck_execution_worker.sh"]`.
  The tests still expect the retired `CMD-SHELL` fast command. The tests move
  to the current compose contract; the retired constant goes away if nothing
  else uses it.
- Alignment timing (two cases): the wall-clock bound and the ratio check pass
  alone and fail under eight-worker load. User decision 2026-10-16: delete the
  timing test. Search the suite for other assertions on elapsed wall-clock
  time or speed ratios and delete those too. A timeout that only bounds a wait
  for an observable result stays.

## Contract Inputs

- User request 2026-10-16: do the ten-failure repair in the parent session with
  a Sol driver/navigator pair and an independent Sol reviewer.
- Evidence: `.orchestration/context/sessions/01a144e3-b8c4-7ea5-bee6-6dfc5e242786/evidence/full-suite-main-2c1d1fcd.log`.

## Core Vertical And Performance

The tests run the real shell script with fake `psql` and `curl`; that stays.
No timing proof remains; correctness tests stay.

## Validation

`PYTHONPATH=src pdm run pytest -q -p no:cacheprovider tests/unit/cli/test_native_healthchecks.py tests/unit/test_docker_dev_shared_auth_contract.py tests/unit/domain/curated_apps/exam_workspace/test_source_alignment_repair6.py`
plus every file a timing deletion touches, then the same files under `pdm run test-parallel`. Scoped ruff and mypy.

## Stop Conditions

Stop and report if the production healthcheck script or compose files appear
wrong rather than the tests.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Production healthcheck script and compose files stay unchanged; the tests change. |
| D2  | The healthcheck test environment supplies `timeout` so the same script path runs on macOS and Linux. |
| D3  | The compose-contract tests assert the current native worker healthcheck. |
| D4  | Host-dependent timing tests are deleted: the repair6 focused-item timing test and any other test asserting elapsed wall-clock time or a speed ratio. |
| D5  | Contract tests assert the current contracts, and the healthcheck tests assert the current script behaviour. |
