---
type: task
id: TASK-SKRIPT-14-39-04
title: ST-14-39 Mina filer File Service client adapter and protected proof
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: blocked
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-14-39
task_kind: story
acceptance_criteria:
- Given File Service-backed `Mina filer` storage is enabled for a record, then Skriptoteket
  uses a HuleEdu File Service client behind `VaultStorageProtocol` for init/finalize,
  metadata, download, and delete lifecycle operations.
- Given a browser lists, downloads, saves, deletes, restores, or uses a saved file
  in Document Converter, then all access still goes through protected Skriptoteket
  routes and owner-scoped `vault:*` refs.
- Given File Service returns missing, mismatched, unauthorized, or lifecycle-invalid
  metadata, then the product route fails closed without falling back to raw object
  URLs, R2 keys, browser bytes, or latest local bytes.
- Given local proof is run, then retained evidence shows protected save, list, download,
  Document Converter ordered saved-source batch, delete/restore, missing-object failure,
  and cross-owner denial without exposing secrets or raw object identity.
---

## Context

### TASK-SKRIPT-14-39-04: ST-14-39 Mina Filer File Service Client Adapter And Protected Proof


The runtime consumer must preserve the current `Mina filer` product contract
while moving object lifecycle behind HuleEdu File Service. A thin HTTP client is
not enough: the adapter must sit behind `VaultStorageProtocol`, honor
Skriptoteket catalog/list authority, and keep protected routes as the browser
contract.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Story Contract Slice


Implement the first Skriptoteket runtime consumer for product-neutral HuleEdu
File Service object lifecycle for `Mina filer` records, with red-first proof
for protected route behavior and Document Converter saved-source batches.

## Contract Inputs

No separate contract inputs is stated in the source.

## Plan


1. Add the HuleEdu File Service client adapter only after the producer API and
   `PR-0413` metadata contract are ready.
2. Bind the adapter behind `VaultStorageProtocol` without changing the public
   `vault:*` ref shape.
3. Keep Skriptoteket APIs responsible for authorization, filename,
   content-type, save/download responses, soft delete, restore, and list UI
   metadata.
4. Prove Document Converter saved-source batches still submit ordered refs only
   and load bytes server-side.
5. Record local shared-auth proof before any production sync or migration task
   can start.

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


- Red-first File Service client tests for init/finalize, metadata, download,
  delete, timeout, unauthorized, missing-object, and checksum mismatch.
- Red-first `VaultStorageProtocol` adapter tests proving fail-closed behavior
  and no local/latest-byte fallback for File Service-backed records.
- Backend/API tests for save, list, download, delete, restore, owner denial,
  and missing-object response behavior.
- Document Converter saved-source batch tests for migrated `vault:*` refs,
  ordering, all-or-nothing failure, and server-side byte loading.
- Local shared-auth browser proof for save, list, download, Document Converter
  saved-source batch, delete/restore, missing-object failure, and cross-owner
  denial.
- `pdm run docs-validate`
- `git diff --check`

## Validation

No separate validation is stated in the source.

## Stop Conditions


Disable the File Service-backed storage setting and leave local vault reads
active for records that have not been cut over. Do not introduce a direct R2
fallback.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Non-goals


- No direct R2 adapter, raw object key persistence, browser-facing R2 URL, or
  R2 credentials in Skriptoteket.
- No HuleEdu Upload v2 essay, BOS, assessment, or batch semantics.
- No prod env sync, object copy, migration backfill, destructive cleanup, or
  local-vault deletion.
- No migration of session files, runner artifacts, previews, transcript blobs,
  Document Converter generated artifacts, or Sir Convert job artifacts.
- No move of catalog/list authority to HuleEdu File Service list.

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Implementation Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
