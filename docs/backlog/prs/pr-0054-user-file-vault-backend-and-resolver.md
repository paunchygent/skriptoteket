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
  - "Vault file refs can be listed, resolved, and staged into /work/input (preserving field ownership in the input manifest)."
  - "Access control is enforced for vault file refs; invalid refs return actionable errors (no 500)."
  - "Soft-delete + restore + retention cleanup paths are implemented, with explicit, dedicated vault configuration."
---

## Problem

ST-14-36 requires a persistent user file vault and file-ref resolver support. Today only session files are reusable.

Parent: EPIC-14. Dependencies: ADR-0059, ST-19-02.

## Goal

Implement backend persistence and resolver support for `vault:*` file refs, with access control, soft-delete, and
retention cleanup, without impacting existing session-file flows.

## Decisions (LOCKED)

- **Dedicated vault storage config (REQUIRED):**
  - `VAULT_ROOT` (Path)
  - `VAULT_MAX_FILE_BYTES` (int)
  - `VAULT_MAX_TOTAL_BYTES` (int; per-user quota)
  - `VAULT_RETENTION_DAYS` (int; soft-delete retention)
  - Default: `VAULT_RETENTION_DAYS = 30`.
- **Vault ≠ session files/artifacts:** vault files MUST NOT be stored under `ARTIFACTS_ROOT/<run_id>/...` and MUST NOT
  reuse session-file cleanup semantics.
- **Per-field file mapping (REQUIRED):** staging MUST preserve which field each file belongs to for multi-file-field
  actions/runs (e.g. include a `field` property per staged file entry in `/work/request.json`).
- **No flat file_refs support:** APIs/commands MUST NOT accept flat `file_refs: list[str]`; the wire contract is
  `file_refs_by_field: Record[field, FileRef[]]` only.
- **Explicit user action only:** saving to vault is FORBIDDEN unless triggered by an explicit user interaction (no tool
  auto-persist).

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
