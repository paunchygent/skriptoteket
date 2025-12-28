---
type: prd
id: PRD-editor-sandbox-v0.1
title: "Editor sandbox PRD v0.1"
status: active
owners: "agents"
created: 2025-12-27
product: "script-hub"
version: "0.1"
---

## Summary

Provide a safe, fast iteration workflow for tool authors inside the editor
sandbox: preview unsaved code and schemas, test multi-step actions, isolate
sandbox settings from production, and prevent concurrent draft edits with
explicit locks and admin override.

## Goals

- Authors can run unsaved editor changes without publishing or saving drafts.
- Multi-step tools can be tested end-to-end using snapshot-stable next_actions.
- Sandbox settings are isolated per user and draft head and never leak into
  published runs.
- Draft head edits and sandbox operations are protected by explicit locks with
  TTL heartbeat and admin/superuser takeover.
- Sandbox input and settings forms match the production run UI behavior.

## Non-goals

- Admin quick-create and slug lifecycle workflows (covered by PRD-tool-authoring-v0.1).
- AI/editor intelligence features (assistive code generation, suggestions).
- Curated tool authoring or runtime UX changes beyond sandbox preview parity.
- Post-publish slug edits, redirects, or tool deletion UX.
- Changes to the tool UI contract beyond snapshot preview support.

## User Roles

- Contributor: authoring and testing draft tools in the sandbox.
- Admin: full authoring + lock takeover.
- Superuser: override access for lock recovery.

## Requirements

### Sandbox preview and snapshots

- Sandbox preview runs accept unsaved snapshot payloads (entrypoint, source,
  schemas, usage instructions) and execute against that snapshot.
- Sandbox preview responses return snapshot_id and run details expose it later.
- start_action in sandbox requires snapshot_id and runs against the same snapshot.
- Sandbox sessions and files are scoped to sandbox:{snapshot_id}.
- Snapshot TTL and cleanup are defined and operational (scheduled job + logs).
- Snapshot payload size limits are enforced with clear validation errors.

### Draft head locks

- Editor acquires and refreshes a draft head lock on load (TTL + heartbeat).
- Locks are enforced on draft saves, sandbox preview runs, start_action, and
  sandbox settings resolve/save.
- Admins/superusers can force takeover with explicit audit visibility.
- When a save creates a new draft head, the lock updates in the same transaction.

### Input and settings parity

- Sandbox renders ToolInputForm and file picker parity based on input_schema.
- Sandbox renders ToolRunSettingsPanel based on settings_schema.
- Unsaved valid schemas are used for preview and settings validation.
- Invalid schema JSON shows actionable parse errors and blocks the operation.
- Sandbox settings are stored per user + draft head (hash-based context) and
  never affect production settings.

### UX and safety

- Read-only mode applies to non-lock owners for draft edits and sandbox actions.
- Errors for lock conflicts and snapshot expiry are actionable and clear.

## Metrics

- Authors can validate a draft change in under 2 minutes without publishing.
- Sandbox preview runs complete successfully for at least 95% of attempts.
- Lock conflicts are recoverable via explicit takeover without data loss.

## Links

- Epic: `docs/backlog/epics/epic-14-admin-tool-authoring.md`
- ADRs: `docs/adr/adr-0038-editor-sandbox-interactive-actions.md`,
  `docs/adr/adr-0044-editor-sandbox-preview-snapshots.md`,
  `docs/adr/adr-0045-sandbox-settings-isolation.md`,
  `docs/adr/adr-0046-draft-head-locks.md`
