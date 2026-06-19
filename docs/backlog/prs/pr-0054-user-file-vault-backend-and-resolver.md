---
type: pr
id: PR-0054
title: "User file vault: backend + resolver"
status: done
owners: "agents"
created: 2026-01-24
updated: 2026-06-18
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
- **Resolver sources param (REQUIRED):** the file-refs endpoints MUST accept `sources` and delegate via a composite
  resolver (session + vault); default `sources=["session","vault"]` when omitted.
- **Session vs vault context semantics:** `context` applies to session refs only; vault ignores `context`.
- **Dedicated vault API surface:** implement a `/api/v1/vault` module for list/save/delete/restore (no mixing with
  session-files endpoints).
- **Vault storage layout:** store bytes under `VAULT_ROOT/<user_id>/<file_id>` (deterministic path; not stored in DB).
- **Vault DB schema (minimal + provenance):** `id`, `user_id`, `name`, `bytes`, `created_at`, `deleted_at`,
  `source_kind`, `source_run_id`, `source_artifact_id` (nullable).
- **Quota enforcement:** maintain `user_vault_usage` with row-level lock for updates; usage excludes soft-deleted files.
- **Soft delete behavior:** DB-only soft delete (set `deleted_at`); files remain on disk until cleanup.
- **Vault list response shape:** list endpoint returns `files` plus `usage`/`limits` and optional `next_cursor`.
- **Save-to-vault request shape:** `POST /api/v1/vault/files` with
  `{source_kind:"run_artifact", run_id, artifact_id, name?}`; validate size/quota and ownership; no path leakage.
- **Retention cleanup:** add `cleanup-vault-files` CLI command to delete soft-deleted vault files past
  `VAULT_RETENTION_DAYS` and update usage.

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

## Code review (as of 2026-01-28)

### ✅ Strong points

- **Thin web layer:** `src/skriptoteket/web/api/v1/vault.py` delegates to handlers and returns typed results.
- **Access control:** handlers verify `vault_file.user_id == actor.id` before exposing bytes/metadata.
- **Vault storage layout:** `LocalVaultStorage` uses deterministic paths `VAULT_ROOT/<user_id>/<file_id>` (bytes are not
  stored in DB).
- **Download support added:** `GET /api/v1/vault/files/{file_id}/download` + `DownloadVaultFileHandler` returns a
  `Content-Disposition: attachment` response with mime sniffing via `mimetypes`.

### ⚠️ Issues / risks

- **Operational persistence:** production compose previously did not persist `VAULT_ROOT`, causing DB rows to outlive
  on-disk bytes and leading to `NOT_FOUND` on download. Fix is to mount a persistent volume at `VAULT_ROOT` in
  production and deploy it.
- **Potential N+1:** `ListVaultFilesHandler` resolves `source_label` by calling `runs.get_by_id()` per file. This is OK
  short-term but should be revisited if vault lists grow (bulk fetch method or join-based query).
- **Test file size budget:** `tests/unit/application/scripting/handlers/test_vault_handlers.py` is ~530 LoC (above the
  <400–500 LoC guideline). Consider splitting into `test_vault_list.py`, `test_vault_save.py`, etc.

### 🧪 Test coverage notes

- Download behavior is covered in `tests/unit/application/scripting/handlers/test_download_vault_file_handler.py`.
- Missing-on-disk flag for list responses is covered in
  `tests/unit/application/scripting/handlers/test_list_vault_files_missing_on_disk.py`.

## Rollback plan

- Revert commit; rollback migration; disable vault resolver path.

## Closeout Status (as of 2026-06-18)

`PR-0359` repairs this slice to `done`. The backend vault persistence, owner
checks, soft-delete/restore/retention path, dedicated `/api/v1/vault` module,
and `vault:*` resolver support are present in the current repo.
