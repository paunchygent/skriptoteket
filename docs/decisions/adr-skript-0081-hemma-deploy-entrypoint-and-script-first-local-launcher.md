---
type: adr
id: ADR-SKRIPT-0081
title: Hemma deploy entrypoint and script-first local launcher
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0081
---

## Context

### Source: Context

Skriptoteket already has one repo-owned Hemma deploy and readiness-gate script:
`scripts/hemma_deploy_and_verify_seating_export.sh`.

That on-host script is the current deploy truth. It fast-forwards the remote
checkout, redeploys the production stack, runs migrations, and fails closed if
the readiness verification does not pass.

What remains weak is the operator launch path from the local repo:

- the current runbook still relies on an ad hoc `ssh hemma "cd ... && ./script"`
  snippet
- repo guidance explicitly says to prefer heredoc-based remote bash sessions to
  avoid nested quoting mistakes
- there is no stable `pdm run ...` launcher for Hemma deploys in
  `pyproject.toml`
- this makes it too easy to improvise remote command composition, path
  discovery, detached execution, or log inspection outside the canonical lane

We therefore need to standardize the local entrypoint without replacing the
existing on-host deploy script.

## Decision

### Source: Decision



## Non-Decisions

The source does not provide a separate non-decisions section; no additional non-decisions is recorded.

## Consequences

### Source: Consequences

- Operators get one repo-owned local entrypoint instead of composing ad hoc SSH
  commands.
- The deploy logic stays centralized in the existing on-host script, so the
  readiness gate does not drift across two implementations.
- The canonical local launch path now prioritizes deploy survivability over
  foreground SSH attachment.
- The runbook can separate:
  - canonical local launch
  - direct on-host fallback/debug use
- The local launcher no longer returns the final deploy verdict inline; instead
  it must hand back the remote PID and log breadcrumbs that operators use to
  observe the on-host deploy to completion.
- If the launcher offers a live follow/monitor affordance, it should stay
  intentionally lightweight by filtering the raw log for existing `==>`
  milestones plus obvious failure patterns instead of inventing a structured
  second log format for this slice.
- This decision supersedes the older planning assumption from the historical
  seating-export deploy slice that the operator entrypoint should never have a
  local wrapper. The deploy logic still stays on-host; only the launch path is
  standardized.

### Source: 1. Keep the on-host script as the only deploy logic

`scripts/hemma_deploy_and_verify_seating_export.sh` remains the canonical Hemma
deploy and readiness-gate implementation.

The new work must not create a second deploy flow with duplicated compose,
migration, or readiness logic on the laptop side.

### Source: 2. Add one canonical local launcher

Skriptoteket will add one stable local operator command:
`pdm run hemma-deploy`.

That launcher exists only to connect to Hemma and invoke the checked-in on-host
script from the checked-out repo path.

### Source: 3. The local launcher must be detached, script-first, and quoting-safe

The launcher must use the repo-approved remote execution pattern for Hemma:

- no nested quoted SSH shell fragments when a heredoc or equivalently stable
  form can be used
- it must start the checked-in on-host deploy script as a detached remote
  process so the deploy survives loss of the initiating local or SSH session
- it must print the remote PID and remote log path immediately after successful
  handoff
- any optional human-readable follow/monitor path must tail the authoritative
  raw remote log and filter it down to existing milestone markers plus obvious
  failure patterns; that monitor stream is best-effort only and must not become
  a second deploy-truth surface
- no hidden alternate repo-path discovery logic beyond the documented Hemma
  checkout path

If the launcher cannot hand off successfully to the detached remote process, it
must exit non-zero locally and surface the launch failure clearly.

### Source: 4. Operator docs should treat the launcher as the canonical local entrypoint

Runbooks and operator-facing docs should point to `pdm run hemma-deploy` as the
normal local initiation path.

The direct on-host script invocation remains documented as the break-glass or
debug fallback, because the deploy still runs on Hemma.
