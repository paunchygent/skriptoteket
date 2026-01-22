---
id: "062-execution-queue-worker-loop"
type: "implementation"
created: 2026-01-22
scope: "backend"
---

# 062: Execution Queue + Worker Loop Guardrails (ADR-0062)

Queue-backed execution is the **default** production mode. The goal is to keep HTTP requests fast and make execution
durable/retryable via Postgres leasing.

## Non-negotiables (REQUIRED)

- **When queueing is enabled**, the web/API path must enqueue and return promptly (no long runner waits in the request).
- **Workers own execution**: the worker loop claims jobs, runs the runner, and finalizes statuses/artifacts.
- **Leases must be safe**:
  - claim with `FOR UPDATE SKIP LOCKED`
  - lease TTL + heartbeat (no infinite locks)
  - stale-lease reaper clears leases so jobs become adoptable
- **No duplicate execution**: adopt-first + idempotency checks must prevent “double-run” outcomes after crashes/restarts.
- **Synchronous fallback is explicit**: only when `RUNNER_QUEUE_ENABLED=false` (preserve cap+reject behavior per ADR-0016).

## Source of truth

- ADR: `docs/adr/adr-0062-execution-queue-and-worker-loop.md`
- Epic: `docs/backlog/epics/epic-18-execution-queue-and-worker-loop.md`

## Key code entrypoints

- Worker loop: `src/skriptoteket/workers/execution_queue_worker.py`
- Queue protocols: `src/skriptoteket/protocols/execution_queue.py`
- Repositories: `src/skriptoteket/infrastructure/repositories/tool_run_job_repository.py`,
  `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`

## Verification (recommended)

- Default suite: `pdm run test`
- Docker-marked queue tests (override default marker filter):
  - `pytest -m docker --override-ini addopts=''`
