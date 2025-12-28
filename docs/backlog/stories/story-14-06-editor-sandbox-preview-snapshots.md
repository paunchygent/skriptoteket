---
type: story
id: ST-14-06
title: "Editor sandbox preview snapshots"
status: ready
owners: "agents"
created: 2025-12-27
epic: "EPIC-14"
acceptance_criteria:
  - "Given an editor has unsaved code or schemas, when the user runs the sandbox, then the run uses the unsaved snapshot payload (not the last saved draft)."
  - "Given a sandbox run returns next_actions, when the user submits a next_action, then the request requires snapshot_id and executes against the same snapshot, even if the editor changes in between."
  - "Given a snapshot expires, when the user submits a next_action, then the UI receives an actionable error prompting a rerun."
  - "Given sandbox runs use session files or state, then the session context is isolated per snapshot_id (sandbox:{snapshot_id})."
  - "Given a sandbox preview run is loaded later, when the run details are fetched, then the response includes snapshot_id for action continuation."
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

## Implementation plan

1) Add sandbox snapshot storage and TTL cleanup.
2) Add preview run endpoint to accept snapshot payload.
3) Require snapshot_id on start-action for sandbox runs.
4) Enforce draft head lock for preview runs and start-action submissions.
5) Store snapshot_id on tool runs and return it from run details endpoints.
6) Update frontend sandbox runner to build snapshot payload and track
   snapshot_id per run.

## Test plan

- Unit: snapshot persistence + TTL, start-action snapshot_id enforcement.
- Integration: sandbox context isolation per snapshot_id.
- Manual: edit code, run sandbox without saving, confirm output reflects
  unsaved changes; perform next_action after editing and confirm stable behavior.
