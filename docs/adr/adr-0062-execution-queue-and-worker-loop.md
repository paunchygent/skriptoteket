---
type: adr
id: ADR-0062
title: "Execution queue and worker loop (Postgres)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-17
supersedes:
  - ADR-0016
---

## Context

Tool execution currently happens synchronously within the API request path. ADR-0016 enforces a global concurrency cap
with immediate rejection (no queue), which is safe for v0.1 but has clear limits:

- Long-running tools can exceed HTTP timeouts.
- Cancellation and retries are coarse; users can lose progress on transient failures.
- The API must hold the request open while a runner container executes.

We need a durable, observable execution queue and worker loop while keeping the existing runner contract (ADR-0015) and
Docker runner constraints (ADR-0013). ADR-0007 also defers Kafka/streaming infrastructure until needed, so a Postgres
queue is preferred.

## Decision

### 1) Add a persistent execution queue in Postgres

Introduce a `tool_run_jobs` table to represent queued execution work. The table tracks scheduling, leases, and retries
separately from `tool_runs` (which continues to hold execution outputs and status).

**Proposed table (v1):**

- `id` (uuid, PK)
- `run_id` (uuid, FK to `tool_runs`, unique)
- `status` (enum: `queued`, `running`, `succeeded`, `failed`, `timed_out`, `cancelled`)
- `queue` (text, default `default`)
- `priority` (int, default 0)
- `attempts` (int, default 0)
- `max_attempts` (int, default 1)
- `available_at` (timestamp, default now)
- `locked_at` (timestamp, nullable)
- `locked_by` (text, nullable)
- `last_error` (text, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- `started_at` (timestamp, nullable)
- `finished_at` (timestamp, nullable)

**Indexes:**

- `(status, available_at, priority)` for claim ordering
- `(locked_by, locked_at)` for heartbeat/reaper
- `run_id` unique index

### 2) Introduce a worker loop that claims jobs via `FOR UPDATE SKIP LOCKED`

Workers claim jobs in a transaction:

1. Select eligible rows: `status = 'queued' AND available_at <= now()`.
2. `ORDER BY priority DESC, created_at ASC`.
3. `FOR UPDATE SKIP LOCKED LIMIT 1`.
4. Update to `status = 'running'`, set `locked_at`, `locked_by`, `started_at`.

The worker then executes the runner (Docker) and updates both `tool_run_jobs` and `tool_runs` with the outcome in a
final transaction.

### 3) Extend run status semantics

Add `queued` and `cancelled` to `RunStatus` to reflect the true lifecycle. `tool_runs.status` mirrors the job status so
existing read APIs can surface accurate state without new endpoints.

### 4) Keep ADR-0016 behavior as a fallback mode

Queueing is enabled behind settings (e.g., `RUNNER_QUEUE_ENABLED`). When disabled, the system behaves exactly as ADR-0016
(cap + reject, no queue). When enabled, ADR-0016 is superseded for production execution but remains the fallback policy
for deployments that do not run workers.

## Consequences

- New DB table + migrations; existing APIs remain stable but gain `queued/cancelled` states.
- Introduces a background worker process (separate service or managed process alongside the web container).
- Requires a stale-lease reaper to recover from crashed workers (e.g., `locked_at` older than a timeout).
- Adds operational metrics: queue depth, job wait time, attempt counts, and worker success/failure rates.
- Avoids adding Redis/Kafka while providing durable, transactional queue semantics.
