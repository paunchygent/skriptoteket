---
type: adr
id: ADR-0046
title: "Draft head locks for editor concurrency"
status: accepted
owners: "agents"
created: 2025-12-27
deciders: "lead-developer"
links: ["EPIC-14", "ST-14-07"]
---

## Context

Multiple contributors can open the same tool editor concurrently. Today,
concurrency is handled only by optimistic checks when saving, which is not
sufficient for sandbox preview runs or collaborative editing. We need a clear
single-editor model with explicit override for admins/superusers.

## Decision

Introduce draft head locks:

- Locks are scoped per tool + active draft head (latest draft version id).
- Editor boot returns lock metadata and the current draft head id.
- Locks have a TTL and are refreshed via a heartbeat from the editor.
- Save, preview run, start-action, and sandbox settings operations require an
  active lock.
- Admins and superusers can force takeover with an explicit action.
- When a save creates a new draft head, the backend updates the existing lock
  row to the new draft head within the same transaction (no UI re-acquire).

## Consequences

- New `draft_locks` storage and lock management endpoints.
- UI must handle read-only mode, lock status, and force takeover.
- Lock scope is draft-head edits + sandbox operations; tool metadata/taxonomy/
  maintainers remain editable while locked.
- Stale locks expire automatically; force takeover is audit-relevant.

## Alternatives considered

- No locks (optimistic only): rejected (insufficient for sandbox preview
  consistency).
- Hard locks without TTL: rejected (risk of stuck locks).
