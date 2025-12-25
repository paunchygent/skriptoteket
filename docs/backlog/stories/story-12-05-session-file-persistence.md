---
type: story
id: ST-12-05
title: "Session-scoped file persistence for action runs"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-12"
acceptance_criteria:
  - "Given a user uploads files and runs a tool with next_actions, when the user submits an action, then the original uploaded files are available in /work/input/ alongside action.json."
  - "Given a user starts a new run with new file uploads, when the run starts, then the previous session files are cleared and replaced with the new uploads."
  - "Given session files exceed the 50MB limit, when upload is attempted, then the user sees a clear error message about the size limit."
  - "Given session files have not been accessed for 24 hours, when the cleanup job runs, then the files are deleted."
  - "Given html_to_pdf_preview.py is run in production or sandbox, when the user clicks 'Konvertera till PDF', then the conversion succeeds using the original uploaded HTML file."
dependencies: ["ADR-0039", "ADR-0024"]
ui_impact: "No (transparent to user; files just work)"
data_impact: "Yes (new session_files storage; no schema change)"
---

## Context

Multi-step tools need access to originally uploaded files across action runs. Currently, action runs only receive
`action.json` - no files.

This story implements session-scoped file persistence per ADR-0039.

## Implementation plan

### Backend

1) Add session file storage service

   - Protocol: `SessionFileStorageProtocol`
   - Implementation: `LocalSessionFileStorage` (filesystem-based)
   - Methods: `store_files()`, `get_files()`, `clear_session()`, `cleanup_expired()`

2) Extend initial run flow

   - After file upload, store files to session storage keyed by `(tool_id, user_id, context)`
   - Clear any existing session files for that key

3) Extend action run flow

   - In `start_action` / `start_sandbox_action`, fetch session files
   - Pass file paths to runner alongside `action.json`

4) Runner contract extension

   - Runner mounts session files to `/work/input/` for action runs
   - Input manifest includes both original files and `action.json`

5) Cleanup job

   - Add `cleanup_expired_session_files` CLI command
   - Schedule via cron or systemd timer (hourly)

### No frontend changes required

Session files are transparent to the user - they upload files once and they persist through actions.

## Test plan

- Unit: session file storage service (store, retrieve, clear, TTL)
- Integration: multi-step tool run with file access in action step
- E2E: html_to_pdf_preview.py works in sandbox and production
