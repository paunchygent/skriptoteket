---
type: adr
id: ADR-0039
title: "Session-scoped file persistence for multi-step tools"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-25
updated: 2026-01-12
links: ["ADR-0022", "ADR-0024", "ADR-0031", "EPIC-12", "EPIC-14"]
---

## Context

Multi-step tools (using `next_actions`) run each step in an isolated container. Currently, uploaded files are only
available in the initial run - action runs receive only the action payload (with `{action_id, input, state}`).

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
- Injects files into `/work/input/` for action runs
- Clears files when a new session starts (new initial run with files)
- Keeps existing session files when a new initial run starts without file uploads
- Works for both production and editor sandbox contexts

### 2) Storage backend

Use local filesystem storage with session-keyed directories:

- Path: `{ARTIFACTS_ROOT}/sessions/{tool_id}/{user_id}/{context_key}/`
- Production: `context = "default"`
- Sandbox: `context = "sandbox:{version_id}"`

`context_key` MUST be a filesystem-safe encoding of `context` (do not use raw `context` in paths). Store the original
`context` in metadata for debugging/inspection.

Implementation note: use `sha256(context.encode("utf-8")).hexdigest()` for `context_key`.

Future: migrate to object storage (S3/MinIO) for horizontal scaling.

### 3) Size limits and cleanup

- Upload limits are settings-driven (same caps used for input uploads):
  - `UPLOAD_MAX_FILE_BYTES` (default: 20MB)
  - `UPLOAD_MAX_TOTAL_BYTES` (default: 50MB)
- TTL is settings-driven (default: 24 hours) and is counted from `last_accessed_at`.
  - Access is defined as “session files were injected into a run” (initial run or action run).
  - Storage MUST update `last_accessed_at` on access.
- Cleanup job runs hourly to remove expired sessions (see ST-12-06 for scheduling/CLI/metrics).

### 4) Runner contract (no new extension)

The runner receives session files in `/work/input/` for action runs (while the action payload is provided via
`SKRIPTOTEKET_ACTION`; ADR-0024):

- Initial run: uploaded files → `/work/input/`
- Initial run (no uploads): do not implicitly inject prior session files; keep them for subsequent action runs
- Action run: session files → `/work/input/`

Tools see consistent file access across action runs; initial-run reuse is explicit (no implicit reuse).

This uses snapshot semantics: session files are copied into the container input directory per run (not mounted writable).
The runner contract does not change; we reuse the existing multi-file input contract (ADR-0031 / ST-12-01).

Future extension (ST-12-07): add explicit initial-run flags (`session_files_mode: none|reuse|clear`,
`session_context: default`) so users can opt in to reuse/clear without ambiguity.

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
