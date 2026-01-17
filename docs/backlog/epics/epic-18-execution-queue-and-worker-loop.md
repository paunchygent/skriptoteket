---
type: epic
id: EPIC-18
title: "Execution queue and worker loop"
status: proposed
owners: "agents"
created: 2026-01-17
outcome: "Tool execution runs asynchronously via a durable Postgres queue with worker leasing, removing HTTP request timeouts for long-running tools."
---

## Scope

- **Persistent execution queue**: introduce `tool_run_jobs` with leasing + retry semantics.
- **Worker loop**: claim jobs via `FOR UPDATE SKIP LOCKED`, execute Docker runner, and finalize results.
- **Run lifecycle updates**: add `queued`/`cancelled` to `RunStatus` and reflect state in existing run APIs.
- **Operational controls**: queue enable/disable setting, stale-lock reaper, basic metrics (queue depth, wait time).
- **Fallback mode**: when queueing is disabled, preserve ADR-0016 cap+reject behavior.

## Stories

- [ST-18-01: Postgres execution queue + worker loop (MVP)](../stories/story-18-01-execution-queue-worker-loop.md)

## Risks

- Worker crash leaves jobs locked (mitigate with lease timeout + reaper).
- Queue backlog could grow under load (mitigate via max attempts + visibility metrics).
- Incorrect status transitions could leave runs in `queued/running` forever (mitigate with strict state machine tests).

## Dependencies

- ADR-0062 (execution queue and worker loop)
- ADR-0013 (execution via ephemeral Docker containers)
- ADR-0015 (runner result contract)
- ADR-0007 (defer Kafka; prefer Postgres queue)
