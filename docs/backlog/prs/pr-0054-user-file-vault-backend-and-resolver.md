---
type: pr
id: PR-0054
title: "User file vault: backend + resolver"
status: ready
owners: "agents"
created: 2026-01-24
updated: 2026-01-24
stories:
  - "ST-14-36"
tags: ["backend"]
acceptance_criteria:
  - "Vault file refs can be listed, resolved, and staged into /work/input."
  - "Access control enforced for vault file refs; invalid refs return actionable errors."
  - "Soft-delete + restore + retention cleanup paths are implemented."
---

## Problem

ST-14-36 requires a persistent user file vault and file-ref resolver support. Today only session files are reusable.

Parent: EPIC-14. Dependencies: ADR-0059, ST-19-02.

## Goal

Implement backend persistence and resolver support for `vault:*` file refs, with access control, soft-delete, and
retention cleanup, without impacting existing session-file flows.

## Non-goals

- UI picker and UX (PR-0055).
- New runner contract versions (beyond existing resolver usage).

## Implementation plan

- Domain + protocols: model vault files, refs, retention policy.
- Persistence: repository + migration for vault storage + metadata (soft delete, retention).
- Resolver: add vault source handling to file-ref resolver; stage into /work/input like uploads.
- API: list vault files, save artifact/upload to vault, delete/restore endpoints.
- Tests: repository + resolver + access control + retention.
- Docs: update story/epic status when done.

## Test plan

- Backend tests: `pdm run test` (or focused tests for vault/resolver).
- Migration check: `pdm run db-upgrade` (if migration added).

## Rollback plan

- Revert commit; rollback migration; disable vault resolver path.
