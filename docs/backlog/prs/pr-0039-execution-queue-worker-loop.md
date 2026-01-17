---
type: pr
id: PR-0039
title: "Execution queue + worker loop (Postgres)"
status: ready
owners: "agents"
created: 2026-01-17
updated: 2026-01-17
stories:
  - "ST-18-01"
adrs:
  - "ADR-0062"
tags: ["backend", "db", "infra"]
acceptance_criteria:
  - "Queue-enabled runs are enqueued and return a queued status without blocking the HTTP request."
  - "Workers claim jobs with SKIP LOCKED, execute the runner, and persist final results."
  - "Stale leases are detected and released or failed per policy."
---

## Problem

Runner execution is synchronous and capped (ADR-0016), which makes long-running tools prone to HTTP timeouts and leaves
no durable record for scheduling/retries.

## Goal

Introduce a Postgres-backed execution queue and worker loop that executes runs asynchronously while keeping the existing
runner contract intact.

## Non-goals

- Redis/Celery/Kafka integration.
- UI redesign for queued states beyond surfacing existing run status.
- Multi-host worker orchestration beyond basic leasing.

## Implementation plan

1. Add `tool_run_jobs` table + indexes; extend `RunStatus` with `queued`/`cancelled`.
2. Enqueue job on run start when `RUNNER_QUEUE_ENABLED` is true.
3. Implement worker loop with `FOR UPDATE SKIP LOCKED` leasing.
4. Update run + job states and persist outputs/artifacts on completion.
5. Add reaper for stale locks; expose minimal metrics.

## Test plan

- Unit tests for job claim/release and state transitions.
- Integration test for end-to-end enqueue → worker execution → run completion.
- Failure mode test for stale lock recovery.

## Rollback plan

- Disable queue via configuration; revert to ADR-0016 cap+reject behavior.
