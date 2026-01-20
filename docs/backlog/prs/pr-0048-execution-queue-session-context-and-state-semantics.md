---
type: pr
id: PR-0048
title: "Fix: session_context propagation + state semantics (execution queue + interactive tools)"
status: ready
owners: "agents"
created: 2026-01-20
updated: 2026-01-20
stories:
  - "ST-18-01"
adrs:
  - "ADR-0024"
  - "ADR-0062"
  - "ADR-0039"
tags: ["backend", "runner", "execution-queue", "interactive", "bugfix", "tests", "db"]
acceptance_criteria:
  - "Queue-finalized runs persist interactive ToolSession state into the correct session context (no hard-coded 'default')."
  - "Tool run session context is persisted on ToolRun and is the single source of truth for session-state persistence in the worker."
  - "State semantics are explicit and regression-tested: state missing/null preserves existing state; state={} clears state; state_rev always increments for interactive turns."
  - "If session state persistence fails for a run that returns next_actions, the run is marked failed (not degraded) with a clear error_summary."
  - "Tests cover both sync and queued code paths for interactive tool runs (including sandbox), plus at least one migration/idempotency check for the new ToolRun field."
---

## Problem

After introducing the Postgres execution queue + worker loop (ST-18-01 / ADR-0062), interactive tools that rely on
session state (`ToolSession.state`) can break in queued runs:

- The execution worker persists normalized session state into a hard-coded `context="default"` rather than the actual
  session context used by the run, so action runs receive empty/stale state.
- Separately, tools that omit `state` in some return branches can unintentionally clear previously persisted state
  because the platform currently treats missing `state` as `{}`.

This causes hard-to-debug behavior: `next_actions` render, but subsequent actions can’t access saved state and/or
session-scoped files consistently.

## Goal

- Make session context propagation deterministic and auditable by persisting `session_context` on `tool_runs`.
- Ensure session state persistence uses that context in the worker (no implicit defaults).
- Make state update semantics explicit and safe-by-default.
- Prefer strict failure over “half-working” interactivity: if state persistence fails, the run must be failed.

## Non-goals

- No changes to the runner contract v2 shape (`result.json`) beyond state semantics in the app.
- No UX redesign of interactive tools beyond clearer failure surfacing via run status/error_summary.
- No changes to role/permission rules for actions.

## Implementation plan

### 1) Persist `session_context` on ToolRun (source of truth)

- Add `tool_runs.session_context` (text) with a safe default for existing rows.
- Thread `session_context` through:
  - `RunActiveToolCommand` → `ExecuteToolVersionCommand` → `start_tool_version_run`/`enqueue_tool_version_run`
  - Sandbox runs (`RunSandboxHandler`): use `sandbox:{snapshot_id}` (existing pattern for sessions/files).
  - Curated app runs: record `command.context` on the run as well (even though the runner isn’t involved).
- Update domain model + repository hydration so `ToolRun` always carries `session_context`.

### 2) Fix queued-run state persistence to use `run.session_context`

- In the worker finalization path (`execution_queue_job_db.py:finalize_job`), replace the hard-coded `"default"` with
  `run.session_context` when reading/writing `ToolSession`.
- Ensure `ToolSession` is created/updated for the correct context on completion when `ui_payload.next_actions` exist.

### 3) Make state semantics explicit (missing state != clear state)

Adopt these semantics:

- `state` missing/null ⇒ **no change** (preserve existing `ToolSession.state`)
- `state: {}` ⇒ **clear** (persist `{}`)
- `state: {...}` ⇒ **overwrite** with normalized state
- For interactive turns (`ui_payload.next_actions` present), `state_rev` MUST increment even when state is “no change”.

Implementation notes:

- Extend the normalization result to preserve whether `raw_result.state` was present, so the pipeline doesn’t lose the
  distinction between “omitted” and “explicit empty object”.
- Update:
  - `RunActiveToolHandler` post-run session update
  - `RunSandboxHandler` post-run session update
  - `StartActionHandler` / `StartSandboxActionHandler` session update
  - Worker finalization session update

### 4) Strict failure on session persistence errors

If a run returns `ui_payload.next_actions` but session-state persistence fails (conflict, DB error, unexpected exception):

- Mark the run as `failed` with a clear `error_summary` (e.g. “Execution failed (session state persistence error).”).
- Mark the job as `failed` for consistency.
- Do not leave `next_actions` available for a run that cannot safely continue.

## Test plan

Backend:

- `pdm run test`
- `pdm run typecheck`
- `pdm run lint`
- If a migration is added: `pdm run pytest -m docker --override-ini addopts=''` (idempotency)

Coverage targets (must have dedicated tests):

- Worker finalization persists state into `run.session_context` (not `"default"`).
- Missing/null state preserves existing session state (and still bumps `state_rev`).
- Explicit `state={}` clears existing session state.
- State persistence failure forces `run.status=failed` (queued path).
- Sandbox: session context is `sandbox:{snapshot_id}` and follows the same rules.

## Rollback plan

- Roll back by reverting the code changes.
- Keep the `tool_runs.session_context` column (safe to retain, used only by new code paths).
- If needed, disable queueing via `RUNNER_QUEUE_ENABLED=false` as an operational mitigation.
