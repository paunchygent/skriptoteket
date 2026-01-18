---
type: review
id: REV-EPIC-18
title: "Review: Execution queue and worker loop"
status: approved
owners: "agents"
created: 2026-01-17
updated: 2026-01-17
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
| Use Postgres queue with `FOR UPDATE SKIP LOCKED` | Avoid new infra (ADR-0007) while keeping durability | [x] |
| Add `queued/cancelled` run statuses | Accurate lifecycle visibility for users and ops | [x] |
| Adopt-first stale-lease recovery (clear lease, keep `running`) | Minimize duplicate execution risk; allow adoption/finalization | [x] |
| TTL leases via `locked_until` + heartbeat | Crash-safe leasing; enables reaper and adoption | [x] |
| Keep ADR-0016 fallback mode | Safe rollout and single-host deployments | [x] |

## Review Checklist

- [x] ADR defines clear queue/worker contracts
- [x] Epic scope is appropriate (not too broad)
- [x] Story acceptance criteria are testable
- [x] Risks identified with mitigations
- [x] Rollout/fallback strategy is explicit

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-01-17
**Verdict:** approved

### Previously Requested Changes (completed)

1. ADR-0062: make the run lifecycle and timestamps truthful (queued runs are not "started"); define state transitions explicitly.
2. ADR-0062: specify lease semantics as TTL (`locked_until`) with heartbeat, and define adopt-first stale lease recovery.
3. ST-18-01 / PR-0039: align acceptance criteria and test plan with TTL leases + adopt-first behavior (including the "container missing" policy).

## Changes Made

- Updated ADR-0062 to document truthful lifecycle (`requested_at`, nullable `started_at`), TTL leases (`locked_until`), adopt-first recovery, and container identity for idempotent adoption/finalization.
- Updated ST-18-01 and PR-0039 to align acceptance criteria and test plan with TTL leases + adopt-first semantics.
