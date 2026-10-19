---
type: task
id: TASK-SKRIPT-REP-0050
title: Backend pytest runs parallel and quiet by default and serial runs need a stated
  reason
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-19'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Every pytest run (`pdm run pytest`, `pdm run test`, the governance backend-test producer, the pre-commit targeted runner, the Hemma pre-push check) runs under xdist with no `-s`, `-v` or live log streaming; captured INFO logs and stdout print only for failing tests
  - A serial run (`-n 0`, `--pdb`, or overridden addopts) stops with a usage error unless it passes a non-blank `--serial-reason`; `pdm run test-serial` is the named serial route
  - The curated_apps application and infrastructure unit suites pass under the default command, with before and after wall times recorded
  - The domain curated_apps suite and the frontend tests are unaffected; lint, typecheck and docs-validate pass
backlog_document_profile: contract-derived
---

## Implementation Contract

User decision 2026-10-19 ("parallel + quiet"): serial 20-minute backend suites, repeated at merge and again in the pre-push check, slow all work. The fast mode must be built into the pytest configuration and the pdm scripts, so agents get it without being told and cannot drop to a slow serial run without a stated reason. It is not a memory or session rule.

Non-goals: the frontend Vitest wrapper (`frontend/apps/skriptoteket/scripts/vitest-run.mjs`, owned by another session), CI outside Hemma, and the shared `local-devops` Skriptoteket reference in skill-repository (a follow-up in that repository).

## Contract Inputs

Routes mapped 2026-10-19 on main `f7eeada5`:

- `[tool.pytest.ini_options].addopts`: `-s -v --durations=10 --log-cli-level=INFO`, `log_cli = true`. Every route below read it, so every run streamed every INFO line.
- `pdm run pytest`: the venv executable, serial and verbose. Agents used it for focused runs.
- `pdm run test`: `repository-governance-routine test`, which resolves the `backend-test` producer to `pdm run test-parallel` (`-n auto`) per component, plus `fe-test`. Parallel but verbose.
- `test-parallel` (`-n auto`), `test-sequential` (`-n 0`) and `test-simulations` (serial, verbose, addopts overridden) in `[tool.pdm.scripts]`.
- `scripts/run_precommit_targeted_unit_tests.py`: `pdm run test-parallel -q <targets>`.
- `scripts/hemma_pre_push_check.sh`: `pdm run typecheck && pdm run test` on Hemma for every push to main.
- Measured 2026-10-19 on Hemma (24 cores): `tests/unit/application/curated_apps` plus `tests/unit/infrastructure/curated_apps` = 2721 tests, 20m38s serial, 76,000-line log; `tests/unit/domain/curated_apps` = 2676 tests, 56 s serial.

## Core Vertical And Performance

The vertical is one pytest invocation from any route above. The performance target is the curated_apps application and infrastructure unit suite in a few minutes instead of about 20.

## Validation

- `pdm run pytest tests/unit/governance/test_pytest_execution_policy.py` (default options, refused serial runs, reasoned serial run).
- `pdm run pytest tests/unit/application/curated_apps tests/unit/infrastructure/curated_apps` and `pdm run pytest tests/unit/domain/curated_apps`, timed.
- `pdm run test --plan` shows the `pytest` producer.
- `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

## Stop Conditions

Stop and report to the parent if a test fails only in parallel and its cause cannot be fixed inside the test or its fixture, or if 24 workers measurably thrash Hemma.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | `addopts` is `-n logical --dist worksteal --durations=10 --import-mode=importlib -m 'not (financial or slow or docker or simulation)'`. `log_cli*` settings are deleted; `log_level = "INFO"` keeps INFO records captured, so they print under a failing test only. |
| D2  | `tests/conftest.py` registers `--serial-reason`. On the controller (not on xdist workers, detected by `config.workerinput`), a run without workers raises `pytest.UsageError` unless the reason is non-blank; the reason prints in the report header. This covers `-n 0`, `--pdb` (xdist turns distribution off) and `-o addopts=`. |
| D3  | `pdm run pytest` is a pdm script for `scripts.run_pytest_with_native_libs`, so focused runs carry the native-library environment. `test-parallel` and `test-sequential` are deleted with no alias. |
| D4  | `pdm run test-serial` is the only named serial route: `-n 0 -s -v --log-cli-level=INFO`, and it still needs `--serial-reason`. Valid reasons: stepping through a test with `--pdb`, or live log output of one failing test. |
| D5  | The governance `backend-test` producer and the pre-commit targeted runner call `pytest`. The pre-push check is unchanged: it calls `pdm run test`, which resolves through the producer. |
| D6  | `test-simulations` is `-m simulation` under the parallel default; the simulation suites print nothing. |
| D7  | Worker count is `logical`: one worker per hardware thread, 24 on Hemma (user decision 2026-10-19, relayed by the Hemma orchestrator). `auto` counts physical cores and gave 12. `addopts` is the one owner of the count; the pre-push check reaches it through `pdm run test`. |
| D8  | Docker integration tests stay outside the default selection and run through `pdm run test-docker` (`-m docker tests/integration`) under the same sized default. Each worker starts one Postgres 16 server on first use and migrates one template database once; `migrated_db`/`database_url` give each module a `CREATE DATABASE ... TEMPLATE` copy, and `empty_module_database`/`fresh_database` give empty databases. No test starts its own container. |
| D9  | `pytest_xdist_auto_num_workers` in `tests/conftest.py` sizes `-n logical` to the selection: one selected file runs in-process (the serial-reason check accepts it), N files use `min(N, hardware threads)` workers. Measured 2026-10-19 (Hemma, wall/CPU): one 4-test file 0.9 s/0.9 s serial against 4.0 s/33.5 s at 24 workers; one 13-test file 11.6 s/12.6 s serial against 19.6 s/200.7 s at 24 workers. User scope extension 2026-10-19: the Hemma orchestrator raised the oversubscription concern. |
| D10 | Scope extension (user 2026-10-19): wasteful tests are optimized in this task by Sonnet junior units. Every case and assertion stays; shared results are immutable or copied per test. Rules: no expensive work at import or collection time (every worker collects every module), immutable corpus inputs parsed once per process (`tests/fixtures/docx_corpus.py`), default exam conversions shared per run across workers (`docx_conversion_cache.py`), unit tests never read build artifacts. The rules live in `.codex/skills/skriptoteket-testing/references/backend-pytest.md`. |
