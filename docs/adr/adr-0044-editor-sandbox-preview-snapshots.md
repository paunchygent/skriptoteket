---
type: adr
id: ADR-0044
title: "Editor sandbox preview snapshots"
status: accepted
owners: "agents"
created: 2025-12-27
deciders: "lead-developer"
links: ["EPIC-14", "ST-14-06"]
---

## Context

The editor sandbox currently runs the last saved draft version, which forces
authors to save on every change and breaks IDE-like iteration. Multi-step tools
(next_actions) require a stable execution context across steps; using the live
editor state or the persisted draft head is not sufficient when users keep
editing during a session.

## Decision

Introduce sandbox preview snapshots for editor runs:

- A sandbox run accepts unsaved editor payload (entrypoint, source_code,
  settings_schema, input_schema, usage_instructions) and persists a snapshot
  record with a TTL.
- The sandbox run response includes `snapshot_id`.
- Subsequent `start-action` requests must include `snapshot_id`, and the backend
  executes against the stored snapshot to guarantee multi-step consistency.
- Sandbox next_actions state and session files are stored under
  `sandbox:{snapshot_id}` context, isolating runs by snapshot.
- Snapshot metadata is recorded on `tool_runs` so run details can return
  `snapshot_id` after reloads.

## Consequences

- New storage for `sandbox_snapshots` plus TTL cleanup job.
- Add a CLI maintenance command for cleanup (scheduled daily in ops), with
  opportunistic cleanup on snapshot creation as a fallback.
- Updated editor API contracts and OpenAPI/TS types.
- Frontend must send snapshot payload and track snapshot_id for actions.
- Snapshot expiration yields actionable errors (re-run required).

## Alternatives considered

- In-memory snapshot cache: rejected (lost on restart, brittle in dev/prod).
- Reusing tool_sessions storage: rejected (semantic mismatch, no TTL lifecycle).
- Auto-saving drafts before runs: rejected (pollutes version history).
