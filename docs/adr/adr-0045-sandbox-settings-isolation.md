---
type: adr
id: ADR-0045
title: "Sandbox-only settings contexts"
status: accepted
owners: "agents"
created: 2025-12-27
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

## Consequences

- Users can iterate on settings without affecting published tool runs.
- Two settings stores exist (sandbox vs production), requiring clear UI
  messaging and explicit usage in editor endpoints.
- Additional API endpoints for sandbox settings resolve/save.

## Alternatives considered

- Require `snapshot_id` for settings: rejected (cannot save settings before
  first run).
- Persisted-schema-only settings: rejected (breaks unsaved schema iteration).
