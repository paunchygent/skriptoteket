---
type: adr
id: ADR-0045
title: "Sandbox-only settings contexts"
status: accepted
owners: "agents"
created: 2025-12-27
updated: 2025-12-28
deciders: "lead-developer"
links: ["EPIC-14", "ST-14-08"]
---

## Context

Tool settings are currently stored in per-user sessions keyed only by the
settings schema hash. This couples editor sandbox settings to production tool
runs when schemas match. For IDE-like sandbox behavior, settings should be
isolated to the draft head and not leak into normal runs.

## Decision

Define sandbox-only settings contexts:

- Sandbox settings are stored per user + draft head + schema variation under
  `sandbox-settings:{sha256(f"{draft_head_id}:{schema_hash}")[:32]}` to remain
  within the 64-character context limit.
- Editor sandbox settings endpoints accept `settings_schema` in the request
  body so unsaved schema edits can be validated and stored.
- Production tool runs continue to use the existing shared context
  `settings:{schema_hash}`.

## Addendum (2025-12-28)

- Editor API endpoints are `POST /api/v1/editor/tool-versions/{version_id}/sandbox-settings/resolve`
  and `PUT /api/v1/editor/tool-versions/{version_id}/sandbox-settings` (save).
- Backend will introduce a settings service wrapper around `tool_sessions` for
  resolve/save validation and context derivation.
- `ExecuteToolVersion` gains an optional `settings_context` override so sandbox
  runs read sandbox settings without touching production contexts.

## Consequences

- Users can iterate on settings without affecting published tool runs.
- Two settings stores exist (sandbox vs production), requiring clear UI
  messaging and explicit usage in editor endpoints.
- Additional API endpoints for sandbox settings resolve/save.

## Alternatives considered

- Require `snapshot_id` for settings: rejected (cannot save settings before
  first run).
- Persisted-schema-only settings: rejected (breaks unsaved schema iteration).
