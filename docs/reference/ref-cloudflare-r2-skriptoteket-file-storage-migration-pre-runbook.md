---
type: reference
id: REF-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook
title: "Cloudflare R2 Skriptoteket file storage migration pre-runbook"
status: active
owners: "agents"
created: 2026-07-02
updated: 2026-07-02
topic: "cloudflare-r2-skriptoteket-file-storage-migration"
---

# Cloudflare R2 Skriptoteket File Storage Migration Pre-Runbook

## Purpose

This reference gathers the repo-local facts needed before writing an operational
runbook for moving Skriptoteket durable user-file bytes to Cloudflare R2. It is
not an implementation plan and it does not authorize credential sync, runtime
changes, data copy, or cleanup.

## Canonical Rules

- `ADR-0088` owns the storage-boundary decision.
- `Mina filer` and `vault:*` `FileRef` behavior must remain stable for users.
- Protected Skriptoteket APIs remain the authorization, filename, content-type,
  and save/download authority.
- The browser must not receive R2 credentials, raw object keys, raw bucket URLs,
  or unredacted signed URLs in retained evidence.
- HuleEdu File Service owns object lifecycle for the v1 migration: init,
  finalize, canonical metadata, download, and final object delete.
- Skriptoteket keeps `Mina filer` catalog/list authority for v1. File Service
  list is optional until a later reviewed tranche moves browse/catalog
  authority.
- HuleEdu Upload v2 essay, BOS, assessment, or batch semantics must not leak
  into the Skriptoteket consumer contract.
- Sir Convert job artifacts remain upstream-owned unless the teacher explicitly
  saves an output to `Mina filer`.

## Current Storage Surfaces

| Surface | Current boundary | Durability | Migration stance |
|---|---|---|---|
| `Mina filer` vault | `VaultStorageProtocol` and `LocalVaultStorage` | durable user-owned files | First migration candidate. |
| Session files | `SessionFileStorageProtocol` and local session roots | session-scoped input/staging | Open question; likely remains local until a separate decision. |
| Document Converter artifacts | App artifact store under conversion/document-converter infrastructure | generated app outputs | Do not migrate with the first vault slice. |
| Document Converter previews | Project preview store | generated preview state | Do not migrate with the first vault slice. |
| Runner artifacts | Runner artifact manager/storage | tool-run output staging | Separate decision if needed. |
| Transcript formatter blobs | Database-backed app state | durable app data | Not part of object-storage cutover. |

## Proposed Architecture

The application-facing boundary stays `VaultStorageProtocol`. Infrastructure
provides a HuleEdu File Service client adapter for migrated `Mina filer` bytes.
The direct Skriptoteket R2 adapter path is not part of this tranche.

V1 ownership split:

- Skriptoteket owns catalog/list/browse state, display names, picker
  eligibility, owner-scoped `vault:*` refs, and product authorization.
- HuleEdu File Service owns object lifecycle: init, upload/finalize, canonical
  object metadata, download byte retrieval, and final object delete.
- File Service `list` may stay unused in v1. Skriptoteket can browse from local
  catalog metadata until a later accepted tranche moves catalog authority.
- Skriptoteket stores opaque File Service object references, not R2 bucket/key
  values.

The backend must keep the same domain shape:

1. authenticated user action creates or selects a vault record;
2. application layer validates owner, deleted state, quota, and file limits;
3. File Service client initializes, finalizes, reads metadata, downloads bytes,
   or requests delete behind `VaultStorageProtocol`;
4. repository commits Skriptoteket catalog state and mirrored content facts;
5. protected routes return only product-safe metadata and file responses.

## Config And Secrets To Decide

Skriptoteket uses HuleEdu File Service for migrated `Mina filer` bytes. The
implementation slice must finalize names and secret-source labels for:

```text
FILE_STORAGE_BACKEND=huleedu_file_service
HULEEDU_FILE_SERVICE_BASE_URL=<internal or gateway URL>
HULEEDU_FILE_SERVICE_AUDIENCE=<signed identity audience>
HULEEDU_FILE_SERVICE_PRODUCT_NAMESPACE=skriptoteket
HULEEDU_FILE_SERVICE_TIMEOUT_SECONDS=<bounded timeout>
HULEEDU_FILE_SERVICE_DELETE_MODE=purge_via_file_service
```

Skriptoteket containers must not receive R2 access keys for this tranche.

Secret values belong only in local/prod `.env` files or secret managers. Docs
may list variable names and source systems, never credential values.

## Docker And Runtime Notes

- Local and production containers currently depend on local vault roots for
  persisted bytes. The File Service-backed tranche removes that dependency only
  for migrated records after cutover; local scratch and pre-migration fallback
  remain separate runtime concerns.
- Web and worker containers must use the same storage backend and metadata
  schema.
- Docker readiness must include the HuleEdu Gateway/File Service lane and
  signed product identity flow.
- Use BuildKit for any Docker build work.

## Migration Phases

1. Inventory active and soft-deleted vault metadata.
2. Produce a dry-run manifest with record id, owner id hash, size, content type,
   SHA-256, current local path, target File Service object reference, and
   lifecycle state.
3. Copy bytes through File Service init/finalize without mutating existing
   records.
4. Verify File Service metadata size and checksum for every copied object.
5. Enable dual-read for migrated records, with local fallback only during the
   reviewed cutover window.
6. Flip new writes to the target backend after smoke proof.
7. Disable local fallback after rollback criteria expire.
8. Run reviewed retention cleanup only after a separate destructive-action gate.

## Open Question Ledger

The runbook cannot be written until these are closed:

1. Exact File Service endpoints and fields for init, finalize, metadata/head,
   download, delete, and checksum verification?
2. Exact database migration fields and constraints for opaque File Service
   object references and mirrored content facts?
3. Exact handling for File Service finalize success followed by Skriptoteket DB
   commit failure?
4. Exact delete, restore, purge, quota, and missing-object behavior across
   Skriptoteket catalog state and File Service lifecycle state?
5. Exact migration batch manifest schema and storage location?
6. Exact dual-read and rollback window?
7. Exact tests and browser proof required for `Mina filer` plus Document
    Converter saved-source batches?
8. Exact prod `.env` sync order for Skriptoteket, HuleEdu, and Sir Convert?
9. Exact observability events, metrics, alerts, and redaction rules?

## Stop Conditions

Stop the migration and keep local storage active if any of these are true:

- owner-scoped access cannot be proved through protected routes;
- checksum or size mismatches occur during copy verification;
- delete/restore/retention behavior is not specified;
- service logs expose raw object keys, credentials, or signed URLs;
- Document Converter saved-source batches cannot read migrated vault files
  server-side without browser reupload;
- HuleEdu File Service endpoints expose Upload v2 essay, BOS, assessment, or
  batch semantics to the Skriptoteket consumer;
- rollback cannot restore reads for already migrated records.
