---
type: story
id: ST-12-05
title: "Session-scoped file persistence for action runs"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-12"
acceptance_criteria:
  - "Given a user uploads files and runs a tool with next_actions, when the user submits an action (production or editor sandbox), then the original uploaded files are available in /work/input/ alongside action.json."
  - "Given a user starts a new initial run with new file uploads for the same (tool_id, user_id, context), when the run starts, then the previous session files are cleared and replaced with the new uploads."
  - "Given a user starts a new initial run without any file uploads, when the run starts, then the previous session files remain available for subsequent action runs."
  - "Given uploaded files exceed the configured upload limits (defaults: 20MB per file, 50MB total), when upload is attempted, then the user sees a clear validation error and session files are not modified."
  - "Given a user attempts to upload a file named action.json, when upload is attempted, then the request is rejected with a clear validation error instructing the user to rename the file."
  - "Given session files have not been accessed for the configured TTL (default: 24 hours), when cleanup_expired() is invoked, then the files are deleted."
  - "Given html_to_pdf_preview.py is run in production or sandbox, when the user clicks 'Konvertera till PDF', then the conversion succeeds using the original uploaded HTML file."
dependencies: ["ADR-0039", "ADR-0024"]
ui_impact: "No (transparent to user; files just work)"
data_impact: "Yes (new session_files storage; no schema change)"
---

## Context

Multi-step tools need access to originally uploaded files across action runs. Currently, action runs only receive
`action.json` - no files.

This story implements session-scoped file persistence per ADR-0039.

Note: Multi-step tools also rely on server-owned session state (ADR-0024). The initial run MUST persist normalized state
to `tool_sessions` when it returns `next_actions`, otherwise the first action run will receive empty/stale state.

## Implementation plan

### Backend

1) Add session file storage service

   - Protocol: `SessionFileStorageProtocol`
   - Implementation: `LocalSessionFileStorage` (filesystem-based)
   - Methods: `store_files()`, `get_files()`, `clear_session()`, `cleanup_expired()`
   - MUST track `last_accessed_at` for TTL cleanup (touch on get / injection into a run).
   - MUST treat `action.json` as a reserved filename (reject uploads that collide with it).
   - MUST use a filesystem-safe encoding for `context` when mapping session keys to storage paths (ADR-0039).

2) Extend initial run flow

   - If the run includes uploaded files: clear any existing session files for `(tool_id, user_id, context)` and store
     the new uploads to session storage.
   - If the run includes **no** uploaded files: keep the existing session files (do not clear).
   - Context selection:
     - Production tool runs use `context="default"` (same context the SPA uses for `start_action`).
     - Editor sandbox runs use `context="sandbox:{version_id}"` (ADR-0038).
   - Optional-but-recommended: inject existing session files into the initial run when no new uploads are provided
     (consistent `/work/input/` behavior across steps).

3) Extend action run flow

   - In `start_action` / `start_sandbox_action`, fetch session files for the matching `(tool_id, user_id, context)`.
   - Execute the action run with a single input snapshot containing:
     - the persisted session files, and
     - `action.json` (platform-generated)
   - This is snapshot semantics: session files are copied into the run’s `/work/input/` (not mounted writable).

4) Runner contract (no new extension)

   - Reuse the existing multi-file contract (ADR-0031 / ST-12-01): the runner places all `input_files` in
     `/work/input/` and sets `SKRIPTOTEKET_INPUT_MANIFEST` accordingly.
   - `SKRIPTOTEKET_INPUT_MANIFEST` includes both original files and `action.json`; tools MUST ignore `action.json` when
     selecting user-provided inputs.

5) Cleanup (job owned by ST-12-06)

   - Expose `cleanup_expired()` in the storage service and keep TTL metadata updated.
   - CLI commands, scheduling, metrics, and runbook are implemented in ST-12-06.

### No frontend changes required

Session files are transparent to the user - they upload files once and they persist through actions.

## Test plan

- Unit: session file storage service (store, retrieve, clear/replace on new upload, TTL + last_accessed_at updates)
- Unit: reserved filename behavior (`action.json` rejected on upload)
- Integration: multi-step tool run where action step sees original uploaded files + `action.json` in `/work/input/`
- E2E: html_to_pdf_preview.py works in sandbox and production
