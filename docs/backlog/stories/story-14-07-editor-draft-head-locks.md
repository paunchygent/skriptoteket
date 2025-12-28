---
type: story
id: ST-14-07
title: "Editor draft head locks"
status: ready
owners: "agents"
created: 2025-12-27
epic: "EPIC-14"
acceptance_criteria:
  - "Given an editor loads a draft tool, when the editor initializes, then it acquires a draft head lock and refreshes it via heartbeat."
  - "Given another user opens the same tool while a lock is active, then the editor is read-only for draft-head edits and sandbox actions, but metadata/taxonomy/maintainers remain editable."
  - "Given an admin or superuser force-takes the lock, then the previous holder is notified and loses edit/preview permissions."
  - "Given a lock expires, then another user can acquire it without manual intervention."
  - "Given any editor save or sandbox operation occurs, then the backend enforces lock ownership for the active draft head."
  - "Given the lock holder saves and creates a new draft head, then the lock record updates to the new draft head in the same transaction."
dependencies:
  - "ADR-0046"
links: ["EPIC-14", "ADR-0046"]
ui_impact: "Yes (editor locking UX)"
data_impact: "Yes (draft_locks storage)"
risks:
  - "Stale locks can block work if heartbeat fails; TTL + clear messaging is required."
---

## Context

Concurrent edits on draft tools cause conflicts and break sandbox preview
consistency. A single-editor model is required for predictable iteration.

## Goal

Enforce per-tool draft head locks with TTL/heartbeat and admin/superuser
override.

## Non-goals

- Multi-user collaborative editing.
- Locking published tools or production runs.

## Implementation plan

1) Create draft lock storage and lock endpoints.
2) Add lock metadata to editor boot responses.
3) Enforce lock ownership in save and sandbox endpoints.
4) Update lock on draft head advancement during saves.
5) Add UI read-only mode, lock status display, and force-take action.

## Test plan

- Unit: lock acquisition, refresh, conflict, force takeover, expiry.
- Manual: open editor in two sessions and verify lock enforcement + force take.
