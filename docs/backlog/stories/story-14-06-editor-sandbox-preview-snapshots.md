---
type: story
id: ST-14-06
title: "Editor sandbox preview snapshots"
status: done
owners: "agents"
created: 2025-12-27
updated: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given an editor has unsaved code or schemas, when the user runs the sandbox, then the run uses the unsaved snapshot payload (not the last saved draft)."
  - "Given a sandbox run returns next_actions, when the user submits a next_action, then the request requires snapshot_id and executes against the same snapshot, even if the editor changes in between."
  - "Given a snapshot expires, when the user submits a next_action, then the UI receives an actionable error prompting a rerun."
  - "Given sandbox runs use session files or state, then the session context is isolated per snapshot_id (sandbox:{snapshot_id})."
  - "Given a sandbox preview run is loaded later, when the run details are fetched, then the response includes snapshot_id for action continuation."
  - "Given a user does not hold the active draft head lock, when they run a sandbox preview or start-action, then the API rejects the request."
  - "Given a snapshot payload exceeds configured limits, when the user runs the sandbox, then the API returns a validation error with a clear message."
dependencies:
  - "ADR-0044"
  - "ADR-0046"
  - "ADR-0038"
  - "ADR-0039"
  - "ADR-0022"
  - "ADR-0024"
  - "ST-14-07"
links: ["EPIC-14", "ADR-0044"]
ui_impact: "Yes (SandboxRunner preview flow)"
data_impact: "Yes (snapshot storage + new API contracts)"
risks:
  - "Snapshot payload errors could block runs; UI must show actionable validation errors."
  - "Snapshot TTL too short could interrupt multi-step flows."
---

## Context

Sandbox runs currently execute the last saved draft version, which forces
authors to save on every change. Multi-step tools require a stable execution
context across actions, which is not guaranteed when users continue editing.

## Goal

Enable IDE-like sandbox preview runs that execute unsaved code and schemas
while ensuring multi-step actions remain stable via snapshot_id.

## Non-goals

- Changing the UI action schema contract.
- Changing runner inputs beyond snapshot payload support.

## Decisions (locked)

- Storage: `sandbox_snapshots` table with explicit columns + `tool_runs.snapshot_id`.
- Endpoint: extend existing `POST /api/v1/editor/tool-versions/{version_id}/run-sandbox` (multipart) to accept snapshot payload.
- Execution: reuse `ExecuteToolVersion` with snapshot overrides (entrypoint/source_code/schema/usage).
- Limits: TTL 24h, payload max 2MB (canonical JSON byte count).
- Cleanup: CLI command scheduled via systemd timer (opportunistic cleanup optional).

## Implementation plan

1) Add `sandbox_snapshots` storage + `tool_runs.snapshot_id` + TTL cleanup command.
2) Extend `run-sandbox` (multipart) to accept snapshot payload; enforce 2MB limit; return `snapshot_id`.
3) Require `snapshot_id` on start-action and use `sandbox:{snapshot_id}` context for sessions/files.
4) Include `snapshot_id` in run details response for reload continuation.
5) Enforce draft head lock for preview runs and start-action submissions.
6) Update frontend sandbox runner to build snapshot payload and track `snapshot_id` per run.

## Test plan

- Unit: snapshot persistence + TTL, start-action snapshot_id enforcement.
- Integration: sandbox context isolation per snapshot_id.
- Manual: edit code, run sandbox without saving, confirm output reflects
  unsaved changes; perform next_action after editing and confirm stable behavior.
