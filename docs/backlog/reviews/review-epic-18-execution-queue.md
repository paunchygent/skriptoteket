---
type: review
id: REV-EPIC-18
title: "Review: Execution queue and worker loop"
status: pending
owners: "agents"
created: 2026-01-17
reviewer: "lead-developer"
epic: EPIC-18
adrs:
  - ADR-0062
stories:
  - ST-18-01
---

## TL;DR

Propose a Postgres-backed execution queue with a worker loop that claims jobs using `FOR UPDATE SKIP LOCKED`, executes
Docker runners asynchronously, and updates run state without holding HTTP requests open. This supersedes ADR-0016 when
queueing is enabled while keeping it as a fallback mode.

## Problem Statement

Synchronous execution + cap/reject limits tool runs to short timeouts and loses durability for retries/cancellation.
We need a durable queue that preserves the runner contract and fits the current infrastructure constraints.

## Proposed Solution

Adopt ADR-0062: add `tool_run_jobs` for scheduling/leasing, implement a worker loop that executes runs out-of-band, and
extend run statuses to include `queued/cancelled`. Keep ADR-0016 behavior as a fallback when workers are disabled.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0062-execution-queue-and-worker-loop.md` | Queue design + lifecycle semantics | 15 min |
| `docs/backlog/epics/epic-18-execution-queue-and-worker-loop.md` | Scope, risks, dependencies | 5 min |
| `docs/backlog/stories/story-18-01-execution-queue-worker-loop.md` | Acceptance criteria + MVP slice | 5 min |

**Total estimated time:** ~25 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use Postgres queue with `FOR UPDATE SKIP LOCKED` | Avoid new infra (ADR-0007) while keeping durability | [ ] |
| Add `queued/cancelled` run statuses | Accurate lifecycle visibility for users and ops | [ ] |
| Keep ADR-0016 fallback mode | Safe rollout and single-host deployments | [ ] |

## Review Checklist

- [ ] ADR defines clear queue/worker contracts
- [ ] Epic scope is appropriate (not too broad)
- [ ] Story acceptance criteria are testable
- [ ] Risks identified with mitigations
- [ ] Rollout/fallback strategy is explicit
