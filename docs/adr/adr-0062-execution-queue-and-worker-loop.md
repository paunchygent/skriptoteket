---
type: adr
id: ADR-0062
title: "Execution queue and worker loop (Postgres)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-17
updated: 2026-01-17
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

### 1) Add a persistent execution queue in Postgres (`tool_run_jobs`)

Introduce a `tool_run_jobs` table to represent queued execution work. The table tracks scheduling, leases, and retries
separately from `tool_runs` (which continues to hold execution outputs and status).

**Proposed table (v1):**

- `id` (uuid, PK)
- `run_id` (uuid, FK to `tool_runs`, unique)
- `status` (enum: `queued`, `running`, `succeeded`, `failed`, `timed_out`, `cancelled`)
- `queue` (text, default `default`)
- `priority` (int, default 0)
- `attempts` (int, default 0) — increments only when starting a **new** runner container attempt
- `max_attempts` (int, default 1) — total allowed runner attempts
- `available_at` (timestamp, default now)
- `locked_by` (text, nullable)
- `locked_until` (timestamp, nullable) — TTL lease deadline (extended via heartbeat while running)
- `last_error` (text, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- `started_at` (timestamp, nullable)
- `finished_at` (timestamp, nullable)

**Indexes:**

- `(status, available_at, priority)` for claim ordering
- `(status, locked_until)` for stale-lease scans (reaper)
- `run_id` unique index

### 2) Make run lifecycle truthful (`tool_runs` timestamps + statuses)

When queueing is enabled, the API request path enqueues work and returns quickly.

`tool_runs` is the user-facing record and source of truth for read APIs (run details, results, status). It MUST reflect
the real lifecycle:

- `requested_at`: timestamp when the run was requested/enqueued.
- `started_at`: nullable; set only when a worker claims a job (i.e., actual execution begins).
- `finished_at`: nullable; set only when reaching a terminal status.

`tool_runs.status` mirrors `tool_run_jobs.status` (1:1; one job per run via `run_id` unique index).

### 3) Lease jobs with a TTL lease (`locked_until`) + heartbeat

Workers use a TTL lease to prevent permanent locks after crashes.

- Claiming a job sets:
  - `locked_by = <worker_id>`
  - `locked_until = now() + lease_ttl`
- A running worker extends `locked_until` periodically (“heartbeat”).
- Completion clears lease fields (`locked_by`, `locked_until`) and sets `finished_at`.

Workers MUST only finalize a job if they still own the lease (e.g., `locked_by` matches) to prevent two workers racing
to finalize after adoption.

### 4) Worker loop: claim queued jobs, and adopt stale running jobs (`FOR UPDATE SKIP LOCKED`)

Workers claim jobs in a transaction:

1. Prefer adoption of orphaned running jobs that have had their lease cleared by the reaper:
   - `status = 'running' AND locked_until IS NULL`
2. Otherwise, claim queued jobs:
   - `status = 'queued' AND available_at <= now()`
3. `ORDER BY priority DESC, created_at ASC`.
4. `FOR UPDATE SKIP LOCKED LIMIT 1`.
5. Set `locked_by`, `locked_until = now() + lease_ttl`.
6. If transitioning `queued → running`, also set `started_at` and update `tool_runs.started_at` and
   `tool_runs.status = 'running'` in the same transaction.

The worker then executes the runner (Docker) and updates both `tool_run_jobs` and `tool_runs` with the outcome in a
final transaction.

**Idempotency / duplicate mitigation:** the worker uses a deterministic runner container identity so that a new worker
can safely adopt/finalize a previous attempt without starting a duplicate execution:

- Container name and/or labels include at minimum `run_id` and `attempt`.
- On adoption, the worker looks up the container by label/name:
  - If found and exited: finalize the run by extracting outputs and updating terminal status.
  - If found and still running: resume heartbeats and wait for completion (or enforce a timeout policy).
  - If not found: treat as lost attempt; requeue or fail according to retry policy (below).

### 5) Reaper: clear stale leases; adopt-first (do not immediately requeue `running`)

A periodic reaper process ensures progress when workers crash:

- Find stale leased jobs:
  - `status = 'running' AND locked_until < now()`
- Clear lease fields but keep status `running`:
  - `locked_by = NULL`, `locked_until = NULL`

This makes the job eligible for adoption (Section 4) without changing semantic status. Attempts are not incremented by
the reaper. Attempts only increment when a worker starts a brand new runner container attempt.

If an adopting worker cannot find an existing runner container for the run, it MUST either:

- Requeue with backoff and increment attempts (`attempts += 1`, `available_at = now() + backoff`) if
  `attempts < max_attempts`, or
- Fail the run (`failed`) with a safe error summary when `attempts >= max_attempts`.

### 6) Extend run status semantics

Add `queued` and `cancelled` to `RunStatus` to reflect the true lifecycle. `tool_runs.status` mirrors the job status so
existing read APIs can surface accurate state without new endpoints.

### 7) Keep ADR-0016 behavior as a fallback mode

Queueing is enabled behind settings (e.g., `RUNNER_QUEUE_ENABLED`). When disabled, the system behaves exactly as ADR-0016
(cap + reject, no queue). When enabled, ADR-0016 is superseded for production execution but remains the fallback policy
for deployments that do not run workers.

## Consequences

- New DB table + migrations; existing APIs remain stable but gain `queued/cancelled` states.
- Introduces a background worker process (separate service or managed process alongside the web container).
- Requires a stale-lease reaper to recover from crashed workers (e.g., `locked_until < now()`).
- Adds operational metrics: queue depth, job wait time, attempt counts, and worker success/failure rates.
- Avoids adding Redis/Kafka while providing durable, transactional queue semantics.
