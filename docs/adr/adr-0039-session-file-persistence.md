---
type: adr
id: ADR-0039
title: "Session-scoped file persistence for multi-step tools"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-25
links: ["ADR-0022", "ADR-0024", "ADR-0031", "EPIC-12"]
---

## Context

Multi-step tools (using `next_actions`) run each step in an isolated container. Currently, uploaded files are only
available in the initial run - action runs receive only `action.json` (with `{action_id, input, state}`).

This creates a design conflict:

- `tool_sessions.state` (JSON) is intended for workflow metadata + user preferences, not file content
- Tools that need prior input files across steps must either:
  - Store file content in JSON state (hacky, bloated, violates intended semantics)
  - Require user to re-upload on each action (poor UX)

Neither option is architecturally correct. The proper solution is session-scoped file storage that carries uploaded
files through action runs within a session.

## Decision

### 1) Session-scoped file storage

Add a `session_files` storage layer that:

- Associates files with `(tool_id, user_id, context)` - same key structure as `tool_sessions`
- Persists files uploaded in the initial run
- Injects files into `/work/input/` for action runs (alongside `action.json`)
- Clears files when a new session starts (new initial run with files)

### 2) Storage backend

Use local filesystem storage with session-keyed directories:

- Path: `{ARTIFACTS_ROOT}/sessions/{tool_id}/{user_id}/{context}/`
- Production: `context = "default"`
- Sandbox: `context = "sandbox:{version_id}"`

Future: migrate to object storage (S3/MinIO) for horizontal scaling.

### 3) Size limits and cleanup

- Per-session file limit: 50MB total
- Per-file limit: 10MB
- TTL: 24 hours from last access (or explicit clear on new upload)
- Cleanup job runs hourly to remove expired sessions

### 4) Runner contract extension

The runner receives session files in `/work/input/` for action runs:

- Initial run: uploaded files → session storage → `/work/input/`
- Action run: session files + `action.json` → `/work/input/`

Tools see consistent file access regardless of step.

## Consequences

### Benefits

- Tools work naturally with files across steps (no code changes for most tools)
- `tool_sessions.state` remains clean (workflow metadata only)
- html_to_pdf_preview.py works as-is
- Unified architecture for sandbox and production

### Tradeoffs

- Requires file storage infrastructure
- Cleanup job complexity
- Size limits may affect large-file workflows (mitigate: clear guidance + artifacts for large outputs)
