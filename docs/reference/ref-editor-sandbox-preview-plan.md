---
type: reference
id: REF-editor-sandbox-preview-plan
title: "Reference: Editor sandbox preview plan"
status: active
owners: "agents"
created: 2025-12-27
topic: "editor-sandbox-preview"
---

## Overview

This plan defines the implementation approach for IDE-like editor sandbox behavior:
- Run unsaved code and schemas in the sandbox (no forced save).
- Guarantee multi-step runs use the same snapshot via snapshot_id.
- Persist sandbox settings per user + draft head, sandbox-only.
- Enforce per-tool draft head locks with admin/superuser override.

This plan is final for implementation planning. ADRs and stories below are
proposed for the docs workflow and should be authored after review.

## Locked Decisions (and dismissed options)

### Snapshot storage
- Chosen: Dedicated DB table `sandbox_snapshots` with TTL cleanup.
- Dismissed: In-memory cache (lost on restart). Reusing `tool_sessions`
  (semantic mismatch, no TTL lifecycle).

### Sandbox settings save payload
- Chosen: Include `settings_schema` in sandbox settings resolve + save requests.
- Dismissed: Require snapshot_id for settings (prevents saving before run).
  Persisted-schema-only (violates unsaved schema requirement).

### Next-actions context
- Chosen: Use `sandbox:{snapshot_id}` for next_actions state + session files.
- Dismissed: `sandbox:{draft_head_id}` (cross-talk between snapshots).

## Draft head semantics

- `draft_head_id` means the latest draft version id for the tool.
- When a save creates a new draft head, the backend updates the existing lock
  row to the new draft head within the same transaction. The UI does not need
  to re-acquire the lock.

## Proposed ADRs (to be written after review)

| ADR | Title | Scope |
| --- | --- | --- |
| ADR-0044 | Editor sandbox preview snapshots | Snapshot payload, TTL, snapshot_id for next_actions |
| ADR-0045 | Sandbox-only settings contexts | Per-user + draft head settings isolation |
| ADR-0046 | Draft head locks for editor concurrency | Lock acquisition, TTL, force takeover |

## Proposed Stories (to be written after review)

| Story | Title | Summary |
| --- | --- | --- |
| ST-14-06 | Sandbox preview snapshots | Preview runs use unsaved code/schemas and return snapshot_id |
| ST-14-07 | Draft head locks | Single editor lock with admin/superuser override |
| ST-14-08 | Sandbox settings isolation | Settings saved per user + draft head, sandbox-only |

## Data Model and Migration

### New tables
- `sandbox_snapshots`
  - id (UUID PK)
  - tool_id (UUID, indexed)
  - draft_head_id (UUID, indexed)
  - created_by_user_id (UUID, indexed)
  - created_at (timestamp)
  - expires_at (timestamp, indexed)
  - entrypoint (text)
  - source_code (text)
  - settings_schema (JSONB, nullable)
  - input_schema (JSONB, nullable)
  - usage_instructions (text, nullable)

- `draft_locks`
  - tool_id (UUID PK or unique)
  - draft_head_id (UUID)
  - locked_by_user_id (UUID)
  - locked_at (timestamp)
  - expires_at (timestamp)
  - forced_by_user_id (UUID, nullable)

### Existing tables
- `tool_runs`
  - add `snapshot_id` (UUID, nullable) to support run reload + action continuation

### TTL behavior
- Draft lock TTL: 10 minutes with heartbeat every 60 seconds.
- Sandbox snapshot TTL: 2 hours (cleanup job removes expired snapshots).

### Cleanup operations
- Add a CLI maintenance command (e.g. `pdm run cleanup-sandbox-snapshots`) that
  deletes expired snapshot rows.
- Run cleanup on a schedule (daily via cron in prod); log deleted counts.
- Opportunistic cleanup may run on snapshot creation as a fallback but is not
  the primary mechanism.

### Snapshot payload limits
- Enforce maximum sizes for snapshot payload fields (entrypoint, source_code,
  settings_schema, input_schema) with clear validation errors.
- Add config settings for limits to keep DB growth predictable.

## Domain and Application Changes

### Domain helpers
- `build_sandbox_preview_version(...)` to validate and normalize unsaved
  `entrypoint`, `source_code`, `settings_schema`, and `input_schema`.
- `compute_sandbox_settings_session_context(draft_head_id, settings_schema)`
  -> `sandbox-settings:{sha256(f"{draft_head_id}:{schema_hash}")[:32]}` (<=64 chars).
- `compute_sandbox_run_context(snapshot_id)` -> `sandbox:{snapshot_id}`.

### New protocols
- `SandboxSnapshotRepositoryProtocol` with `create`, `get_by_id`,
  `delete_expired`.
- `DraftLockRepositoryProtocol` with `get_for_tool`, `upsert`, `delete`.
- `GetSandboxSettingsHandlerProtocol` and
  `UpdateSandboxSettingsHandlerProtocol`.

### New handlers
- `RunSandboxPreviewHandler`:
  - Enforce contributor+maintainer and draft lock.
  - Validate snapshot payload and persist with TTL.
  - Execute using preview version and return `snapshot_id`.
- `StartSandboxActionHandler` (editor):
  - Require `snapshot_id` for actions.
  - Execute using stored snapshot.
  - Use `sandbox:{snapshot_id}` for state and session files.
- `GetSandboxSettingsHandler` and `UpdateSandboxSettingsHandler`:
  - Require lock.
  - Use sandbox settings context derived from draft head + schema hash.
- Lock enforcement applies to preview runs, start-action, sandbox settings
  resolve/save, and draft-head save endpoints (create draft + save draft).

### Lock handlers
- `AcquireDraftLockHandler` and `ReleaseDraftLockHandler`:
  - Acquire or refresh lock if owned.
  - Return lock metadata for UI.
  - Allow force takeover for admin/superuser.

## API Changes

### Editor sandbox preview run (changed)
`POST /api/v1/editor/tool-versions/{version_id}/run-sandbox`

Multipart:
- `snapshot` JSON string
  - `entrypoint`, `source_code`, `settings_schema`, `input_schema`,
    `usage_instructions`
- `inputs` JSON string
- `files` (optional)

Response:
- `run_id`, `status`, `started_at`, `state_rev?`, `snapshot_id`

### Sandbox start-action (changed)
`POST /api/v1/editor/tool-versions/{version_id}/start-action`

Body:
- `action_id`, `input`, `expected_state_rev`, `snapshot_id`

### Sandbox session (changed)
`GET /api/v1/editor/tool-versions/{version_id}/session`

Query:
- `snapshot_id` (optional; when present, uses sandbox:{snapshot_id})

### Sandbox settings (new)
`POST /api/v1/editor/tool-versions/{version_id}/sandbox-settings/resolve`

Body:
- `settings_schema`

Response:
- ToolSettingsResponse + `draft_head_id`

`PUT /api/v1/editor/tool-versions/{version_id}/sandbox-settings`

Body:
- `expected_state_rev`, `values`, `settings_schema`

### Draft lock (new)
`POST /api/v1/editor/tools/{tool_id}/draft-lock`

Body:
- `draft_head_id`, `force?`

Response:
- `tool_id`, `draft_head_id`, `locked_by_user_id`, `expires_at`, `is_owner`

`DELETE /api/v1/editor/tools/{tool_id}/draft-lock`

Body:
- `draft_head_id` (optional safety)

### Editor run details (changed)
`GET /api/v1/editor/tool-runs/{run_id}`

Response:
- include `snapshot_id` when the run was created from a sandbox preview snapshot

### Editor boot response (changed)
Add `draft_head_id` and `draft_lock` to editor boot payloads.

## Frontend Changes (summary)

- Acquire draft lock on editor load and refresh heartbeat.
- Disable draft-head edits and sandbox actions when lock not owned.
- Metadata/taxonomy/maintainers remain editable while locked (scope is draft head).
- Sandbox run uses snapshot payload from unsaved editor state and stores
  `snapshot_id` for actions.
- Sandbox settings panel uses sandbox settings endpoints and passes current
  `settings_schema` text.

## Test Plan

### Unit tests
- Preview run: snapshot persistence, lock enforcement, returns snapshot_id.
- Start-action requires snapshot_id and fails on expired snapshot.
- Sandbox settings validate schema and values, correct context.
- Draft lock acquisition, heartbeat refresh, conflict, force takeover.

### Integration
- TTL cleanup for snapshots.
- Lock enforcement on save + preview endpoints.

### Playwright (proposal)
- Run unsaved code and verify outputs reflect the editor text.
- Next-action uses snapshot after editing code.
- Sandbox settings persist per user + draft head only.
- Force lock takeover by admin.
- Reload run details and confirm snapshot_id is returned for preview runs.

## Reviewer File List (complete)

Docs and ADRs:
- `docs/reference/ref-editor-sandbox-preview-plan.md`
- `docs/backlog/epics/epic-14-admin-tool-authoring.md`
- `docs/backlog/stories/story-14-03-sandbox-next-actions-parity.md`
- `docs/backlog/stories/story-14-04-sandbox-input-schema-form-preview.md`
- `docs/backlog/stories/story-14-05-editor-sandbox-settings-parity.md`
- `docs/backlog/stories/story-14-06-editor-sandbox-preview-snapshots.md`
- `docs/backlog/stories/story-14-07-editor-draft-head-locks.md`
- `docs/backlog/stories/story-14-08-editor-sandbox-settings-isolation.md`
- `docs/adr/adr-0022-tool-ui-contract-v2.md`
- `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`
- `docs/adr/adr-0027-full-vue-vite-spa.md`
- `docs/adr/adr-0030-openapi-as-source-and-openapi-typescript.md`
- `docs/adr/adr-0038-editor-sandbox-interactive-actions.md`
- `docs/adr/adr-0039-session-file-persistence.md`
- `docs/adr/adr-0044-editor-sandbox-preview-snapshots.md`
- `docs/adr/adr-0045-sandbox-settings-isolation.md`
- `docs/adr/adr-0046-draft-head-locks.md`

Backend and domain:
- `src/skriptoteket/web/api/v1/editor.py`
- `src/skriptoteket/web/api/v1/tools.py`
- `src/skriptoteket/web/editor_support.py`
- `src/skriptoteket/application/scripting/handlers/run_sandbox.py`
- `src/skriptoteket/application/scripting/handlers/start_sandbox_action.py`
- `src/skriptoteket/application/scripting/handlers/execute_tool_version.py`
- `src/skriptoteket/application/scripting/handlers/get_tool_version_settings.py`
- `src/skriptoteket/application/scripting/handlers/update_tool_version_settings.py`
- `src/skriptoteket/application/scripting/tool_settings.py`
- `src/skriptoteket/domain/scripting/models.py`
- `src/skriptoteket/domain/scripting/tool_settings.py`
- `src/skriptoteket/domain/scripting/tool_inputs.py`
- `src/skriptoteket/domain/scripting/policies.py`
- `src/skriptoteket/domain/scripting/tool_sessions.py`
- `src/skriptoteket/protocols/scripting.py`
- `src/skriptoteket/protocols/tool_settings.py`
- `src/skriptoteket/protocols/tool_sessions.py`
- `src/skriptoteket/protocols/session_files.py`
- `src/skriptoteket/protocols/uow.py`
- `src/skriptoteket/di/scripting.py`

Infrastructure:
- `src/skriptoteket/infrastructure/db/models/tool_run.py`
- `src/skriptoteket/infrastructure/db/models/tool_session.py`
- `src/skriptoteket/infrastructure/repositories/tool_version_repository.py`
- `src/skriptoteket/infrastructure/repositories/tool_session_repository.py`
- `migrations/` (new migration)
- `alembic.ini`

Frontend:
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useToolVersionSettings.ts`
- `frontend/apps/skriptoteket/src/composables/tools/toolSettingsForm.ts`
- `frontend/apps/skriptoteket/src/composables/tools/useToolInputs.ts`
- `frontend/apps/skriptoteket/src/components/tool-run/ToolRunSettingsPanel.vue`
- `frontend/apps/skriptoteket/src/views/ToolRunView.vue`
- `frontend/apps/skriptoteket/src/api/client.ts`
- `frontend/apps/skriptoteket/src/api/openapi.ts`

Tests and scripts:
- `tests/unit/application/scripting/handlers/test_tool_version_settings_handlers.py`
- `tests/unit/application/scripting/handlers/` (new tests)
- `scripts/_playwright_config.py`
- `src/skriptoteket/script_bank/bank.py`
- `src/skriptoteket/script_bank/scripts/demo_settings_test.py`
