---
type: story
id: ST-18-01
title: "Postgres execution queue + worker loop (MVP)"
status: ready
owners: "agents"
created: 2026-01-17
epic: "EPIC-18"
acceptance_criteria:
  - "Given queueing is enabled, when a tool run is requested, then a tool_run_jobs row is created with status queued and the API returns the run_id with status queued."
  - "Given a queued job, when a worker claims it, then tool_run_jobs and tool_runs transition to running and the job is leased with locked_at/locked_by."
  - "Given a job completes, when the worker finishes, then tool_run_jobs and tool_runs are updated to the terminal status and stdout/stderr/artifacts are persisted."
  - "Given a stale job lease, when the reaper runs, then the job is released back to queued or failed according to policy."
  - "Given queueing is disabled, when the runner is at capacity, then the API responds with SERVICE_UNAVAILABLE per ADR-0016."
dependencies:
  - "ADR-0062"
data_impact:
  - "New table: tool_run_jobs; new enum values in tool_runs.status."
risks:
  - "Lease timeout misconfiguration could trigger duplicate execution; mitigate with idempotency checks and conservative timeouts."
---

## Context

Runner execution is synchronous and capped, which risks HTTP timeouts and offers no durable scheduling or retry
semantics. This story introduces a Postgres-backed queue and worker loop while preserving the runner contract.

## Notes

- Align with ADR-0062 for queue schema + lease semantics.
- Keep ADR-0016 fallback mode behind configuration.
