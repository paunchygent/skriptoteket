---
type: adr
id: ADR-0016
title: "Execution concurrency and backpressure (v0.1: cap + reject, no queue)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-14
updated: 2025-12-14
---

## Context

EPIC-04 runs tool scripts via sibling Docker runner containers (ADR-0013). The Docker SDK is synchronous, and each run
consumes CPU, memory, and Docker daemon capacity.

Without an explicit concurrency policy, the API server can:

- Block the event loop (if Docker SDK calls leak onto it)
- Exhaust thread pools / Docker daemon resources
- Create unbounded queuing and timeouts under load

The v0.1 scope explicitly avoids introducing a distributed task queue.

## Decision

### 1 Global concurrency cap (Settings-driven)

Introduce `RUNNER_MAX_CONCURRENCY` in Settings and enforce it as a global cap per app process.

Implementation intent:

- All Docker SDK calls execute off the event loop (thread pool).
- A single global semaphore limits concurrent executions to `RUNNER_MAX_CONCURRENCY`.

### 2 Backpressure behavior: reject when saturated

When the runner is at capacity, the system MUST reject new execution requests immediately (no in-process queueing).

Rationale:

- Avoids long-running requests waiting on capacity (request/proxy timeouts).
- Prevents unbounded memory growth and “hidden queues”.
- Keeps behavior predictable and operationally safe for v0.1.

### 3 No persistent queue in v0.1

We do not add Celery/ARQ/Redis-based queuing in v0.1. If/when a queue is introduced, it will supersede this ADR and
define scheduling, fairness, and retry semantics explicitly.

## Consequences

- The UI must handle “runner busy” responses and prompt the user to retry.
- Capacity planning is explicit: operators set `RUNNER_MAX_CONCURRENCY` to fit host limits.
- Provides a clean upgrade path to a real job queue without changing the runner contract (ADR-0015).
