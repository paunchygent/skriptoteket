---
type: pr
id: PR-0040
title: "Execution queue test coverage (EPIC-18 / ADR-0062)"
status: ready
owners: "agents"
created: 2026-01-18
updated: 2026-01-18
stories:
  - "ST-18-01"
tags: ["backend", "tests", "db", "infra"]
acceptance_criteria:
  - "Queue-enabled production runs are enqueued (tool_runs + tool_run_jobs) and return status=queued without calling the runner."
  - "ToolRunJob domain transitions (enqueue/start/finish/requeue) are covered by unit tests (protocol-free, deterministic)."
  - "PostgreSQLToolRunJobRepository leasing semantics (claim/adopt-first/heartbeat/reaper) are covered by integration tests against Postgres."
  - "Worker job processing (process_claim) is covered by unit tests using protocol fakes (no DB, no real Docker)."
  - "DockerToolRunner.try_adopt is covered by unit tests using monkeypatched docker client (no real Docker daemon)."
  - "LocalRunInputStorage store/get/delete is covered by unit tests using a tmp artifacts root."
---

## Problem

EPIC-18 / ADR-0062 introduced a Postgres execution queue (`tool_run_jobs`), TTL leases + reaper, adopt-first recovery,
and new queued lifecycle semantics (`requested_at`, nullable `started_at`). We currently lack targeted tests for most of
the new queue/worker behavior.

## Goal

Add focused unit + integration tests that validate the queue lifecycle, lease/adoption/reaper semantics, and worker job
processing behavior — aligned with the repo testing rules:

- Mock protocols; avoid patching implementation details.
- Focus on behavior and invariants.
- Keep test files small (<400–500 LOC).

## Non-goals

- Full end-to-end “real Docker runner executes a tool” tests.
- Multi-worker concurrency stress tests (can be added later if needed).
- UI tests (SPA already has coverage for queued status rendering/polling).

## Implementation plan

1. Add domain unit tests for `ToolRunJob` state-machine helpers:
   - New file: `tests/unit/domain/scripting/test_tool_run_jobs.py`
   - Cover: `enqueue_job`, `mark_job_started`, `mark_job_finished`, `requeue_job_with_backoff`, validation errors.

2. Add application unit tests for queue-enabled enqueue path:
   - New file: `tests/unit/application/scripting/handlers/test_execute_tool_version_queueing.py`
   - Use protocol mocks (`ToolRunRepositoryProtocol`, `ToolRunJobRepositoryProtocol`, `RunInputStorageProtocol`,
     `ToolRunnerProtocol`).
   - Cover:
     - `RUNNER_QUEUE_ENABLED=True` + production run ⇒ creates queued run/job + stores inputs (if any) and returns.
     - Ensure `runner.execute` is never called in queue path.
     - Ensure sandbox/action/override cases do not enqueue (fallback to existing pipeline).

3. Add integration tests for Postgres queue repository semantics:
   - New file: `tests/integration/infrastructure/repositories/test_tool_run_job_repository.py`
   - Use existing integration DB fixture patterns (similar to `test_tool_run_repository.py`).
   - Cover:
     - `claim_next` adopts-first (`running && locked_until is NULL`) before queued.
     - `claim_next` transitions queued → running, sets lease fields, sets `started_at`, increments attempts, and updates
       `tool_runs.status/started_at`.
     - `heartbeat` returns true only when `locked_by` matches; false otherwise.
     - `clear_stale_leases` clears `locked_by/locked_until` for stale leased running jobs and returns a count.

4. Add worker job processor unit tests using protocol fakes (no DB):
   - New file: `tests/unit/workers/test_execution_queue_job_processor.py`
   - Create small in-memory fake implementations of:
     - `ToolRunRepositoryProtocol`, `ToolRunJobRepositoryProtocol`, `ToolVersionRepositoryProtocol`,
       `ToolSessionRepositoryProtocol`, `UserRepositoryProtocol`, `UnitOfWorkProtocol`
     - `RunInputStorageProtocol`, `ToolRunnerProtocol`, `ToolRunnerAdoptionProtocol`, `ClockProtocol`,
       `SleeperProtocol`, `UiPayloadNormalizerProtocol`, `UiPolicyProviderProtocol`, `BackendActionProviderProtocol`
   - Use a minimal container adapter that returns the fakes from `request.get(<Protocol>)`.
   - Cover:
     - Adoption path: `try_adopt -> None` and `attempts < max_attempts` ⇒ requeue w/ backoff, no finalize.
     - Adoption path: `try_adopt -> None` and `attempts >= max_attempts` ⇒ finalize failed.
     - Non-adoption path: runner success ⇒ finalize terminal + `run_inputs.delete` called.

5. Extend existing Docker runner unit tests to cover adoption logic:
   - Update file: `tests/unit/infrastructure/runner/test_docker_runner.py`
   - Cover `DockerToolRunner.try_adopt`:
     - No matching containers ⇒ returns `None`.
     - Container `created` ⇒ cleaned up and returns `None`.
     - Container completes with valid `result.json` ⇒ returns parsed result + archives artifacts.
     - Timeout path ⇒ returns `TIMED_OUT` and archives output safely.

6. Add unit tests for run input storage:
   - New file: `tests/unit/infrastructure/runner/test_run_input_storage.py`
   - Cover `LocalRunInputStorage.store/get/delete` roundtrip with `tmp_path`.

## Test plan

- `pdm run test`
- `pdm run pytest -m docker --override-ini addopts=''` (migration idempotency suite; keep passing)

## Rollback plan

- Revert PR-0040 only (tests). No production behavior changes.
