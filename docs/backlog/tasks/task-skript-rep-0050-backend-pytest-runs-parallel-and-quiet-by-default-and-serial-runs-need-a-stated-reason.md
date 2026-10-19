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
| D2  | `tests/conftest.py` registers `--serial-reason`. On the controller (not on xdist workers, detected by `config.workerinput`), a run without workers raises `pytest.UsageError` unless the reason is non-blank; the reason prints in the report header. This covers `-n 0`, `--pdb` (xdist turns distribution off) and `-o addopts=`. The check reads the worker transports xdist settled, so a negative `-n` or `--maxprocesses` is refused instead of running in-process, and an explicit count above `MAX_WORKERS` is refused (review 321854a9 F1). |
| D3  | `pdm run pytest` is a pdm script for `scripts.run_pytest_with_native_libs`, so focused runs carry the native-library environment. `test-parallel` and `test-sequential` are deleted with no alias. |
| D4  | `pdm run test-serial` is the only named serial route: `-n 0 -s -v --log-cli-level=INFO`, and it still needs `--serial-reason`. Valid reasons: stepping through a test with `--pdb`, or live log output of one failing test. |
| D5  | The governance `backend-test` producer and the pre-commit targeted runner call `pytest`. The pre-push check is unchanged: it calls `pdm run test`, which resolves through the producer. |
| D6  | `test-simulations` is `-m simulation` under the parallel default; the simulation suites print nothing. |
| D7  | Large runs use at most 12 workers (`MAX_WORKERS` in `tests/conftest.py`, the one owner; user decision 2026-10-19 from the load table below: 24 workers ran the full suite no faster, 101.1 s against 98.6 s, and slowed concurrent small runs by about 30%). `addopts` keeps `-n logical` so the sizing hook decides; the pre-push check inherits it through `pdm run test`. `auto` counts physical cores and gave 12; the earlier `-n logical` decision rested on figures mislabelled as 24 workers. |
| D8  | Docker integration tests stay outside the default selection and run through `pdm run test-docker` (`-m docker tests/integration`) under the same sized default. Each worker starts one Postgres 16 server on first use and migrates one template database once; `migrated_db`/`database_url` give each module a `CREATE DATABASE ... TEMPLATE` copy, and `empty_module_database`/`fresh_database` give empty databases. No test starts its own container. |
| D9  | `pytest_xdist_auto_num_workers` in `tests/conftest.py` sizes `-n logical` to the selection (user 2026-10-19: efficiency under real working load, where 10-15 agents run one to ten files while a full suite runs every 20-30 minutes): fewer than 12 selected files run in-process (the serial-reason check accepts it); a larger selection gets one worker per 6 files, at least 2, at most `MAX_WORKERS` (12). A sweep file declares `# xdist-weight: <n>` on its first line and counts as `n` files (`test_exam_workspace_docx_points_invariance.py`: 72, 26 s at 12 workers against about 140 s in-process). Measured 2026-10-19 (Hemma, wall/CPU): one 4-test file 0.9 s/0.9 s in-process against 4.0 s/33.5 s at 24 workers. With `--pyargs` a dotted package or module is sized by its files; an argument the hook cannot resolve makes the selection uncountable, and an uncountable run gets the cap rather than the in-process exemption (review 321854a9 F2). A path argument that does not exist stops with pytest's own `file or directory not found` usage error, because xdist workers would report it only as "no tests ran". |
| D10 | Scope extension (user 2026-10-19): wasteful tests are optimized in this task by Sonnet junior units. Every case and assertion stays; shared results are immutable or copied per test. Rules: no expensive work at import or collection time (every worker collects every module), immutable corpus inputs parsed once per process (`tests/fixtures/docx_corpus.py`), default exam conversions shared per run across workers (`docx_conversion_cache.py`), unit tests never read build artifacts. The rules live in `.codex/skills/skriptoteket-testing/references/backend-pytest.md`. |

## Measurements (Hemma, 2026-10-19)

| Run | Before | After |
| --- | --- | --- |
| `tests/unit/application/curated_apps` + `tests/unit/infrastructure/curated_apps` | 20m38s serial, 76,000-line log | 2m15s at 12 workers, 61-line log (before the test optimizations) |
| `tests/unit/domain/curated_apps` | 56 s serial | 28 s at 12 workers |
| Full `tests/unit` | 3m50s at 12 workers (`auto`), 2.5 GB peak RSS | about 100 s at 12 or 24 workers, with 10 concurrent small-run loops (commit `50597ba0`) |
| `test_exam_workspace_docx_points_invariance.py` | 1600 s summed worker time; 116 s wall | 26 s wall at 12 workers (weight 72) |
| Docker lane containers | about 116 per full run (one per module or test) | one per worker |

Load measurement at `50597ba0`: the full `tests/unit` suite with 10 concurrent loops of small focused runs (1-10 random files each, `pdm run pytest`).

| Scenario | Suite wall | Small runs | Small p50 / p90 / max | Peak load |
| --- | --- | --- | --- | --- |
| Small runs alone, 4 min | - | 589 | 2.2 / 8.5 / 24.1 s | 13.8 |
| Suite at 24 workers | 101.1 s | 101 | 6.1 / 22.6 / 47.6 s | 36.0 |
| Suite at 12 workers | 98.6 s | 135 | 4.6 / 16.4 / 40.2 s | 42.0 |

Known failures outside this task: nine Docker migration test files (`0011`, `0013`, `0017`, `0018`, `0019`, `0020`, `0021`, `0030`, `revision_coverage[6a1e9d3c4b7f]`) fail the same way on main (`users.external_id` missing; non-linear migration graph, TASK-SKRIPT-06-17-01).
