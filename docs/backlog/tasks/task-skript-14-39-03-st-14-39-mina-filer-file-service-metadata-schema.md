---
type: task
id: TASK-SKRIPT-14-39-03
title: ST-14-39 Mina filer File Service metadata schema
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
- Given a `Mina filer` record is saved or migrated, then Skriptoteket can persist
  an opaque File Service object reference and mirrored content facts without storing
  R2 bucket/key identity as a domain concept.
- Given a `vault:*` ref is resolved, then repository/domain behavior can fail closed
  for cross-owner, deleted, missing-object, checksum-mismatched, or lifecycle-invalid
  records.
- Given File Service object metadata is unavailable or incomplete, then the catalog
  record remains unusable for protected download and saved-source batch authority.
- Given migration is not yet authorized, then schema work does not copy bytes, sync
  prod env, delete local vault bytes, or enable a runtime File Service adapter.
---

## Context

`user_vault_files` currently describes local vault files well enough for
`vault:<uuid>` resolution, but it does not carry the object identity and
mirrored content facts needed for a HuleEdu File Service-backed record.

The schema must be shaped before runtime adapter work so product code cannot
quietly persist raw R2 identity or treat local paths as durable object identity.

Add the Skriptoteket metadata foundation for File Service-backed `Mina filer`
records while preserving local catalog/list authority and `vault:*` refs.

Expected fields include an opaque File Service object reference, content type,
size, SHA-256, File Service lifecycle state, migration batch id where relevant,
finalized timestamp, and delete/purge state. Exact names and constraints must
match the product-neutral File Service object-file contract.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

Add the Skriptoteket metadata foundation for File Service-backed `Mina filer`
records while preserving local catalog/list authority and `vault:*` refs.

Expected fields include an opaque File Service object reference, content type,
size, SHA-256, File Service lifecycle state, migration batch id where relevant,
finalized timestamp, and delete/purge state. Exact names and constraints must
match the product-neutral File Service object-file contract.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Plan

1. Confirm the product-neutral File Service object-reference shape from the
   HuleEdu producer task.
2. Add database migration fields and constraints for File Service-backed vault
   records.
3. Extend the repository/domain model so `vault:*` resolution can distinguish
   local, migrated, missing, checksum-mismatched, deleted, restored, and
   purge-eligible states without exposing object keys.
4. Keep current local records readable until a later migration/cutover task
   explicitly changes read routing.

## Implementation Steps

1. Confirm the product-neutral File Service object-reference shape from the
   HuleEdu producer task.
2. Add database migration fields and constraints for File Service-backed vault
   records.
3. Extend the repository/domain model so `vault:*` resolution can distinguish
   local, migrated, missing, checksum-mismatched, deleted, restored, and
   purge-eligible states without exposing object keys.
4. Keep current local records readable until a later migration/cutover task
   explicitly changes read routing.

## Proof

- Red-first repository/domain tests for object metadata persistence.
- Red-first tests for fail-closed `vault:*` resolution when object reference,
  lifecycle, checksum, owner, or deleted state is invalid.
- Migration test proving the new fields are nullable or staged safely for
  existing local records before cutover.
- `pdm run test` with the focused backend tests named by implementation.
- `pdm run docs-validate`
- `git diff --check`

## Validation

- Red-first repository/domain tests for object metadata persistence.
- Red-first tests for fail-closed `vault:*` resolution when object reference,
  lifecycle, checksum, owner, or deleted state is invalid.
- Migration test proving the new fields are nullable or staged safely for
  existing local records before cutover.
- `pdm run test` with the focused backend tests named by implementation.
- `pdm run docs-validate`
- `git diff --check`

## Stop Conditions

Revert the schema and domain changes before any runtime adapter or migration
uses them. Once data is written to the new fields, rollback requires the later
cutover task's data policy.

## Lessons Learned

No separate material is recorded in the source snapshot.

## Notes

### Problem

`user_vault_files` currently describes local vault files well enough for
`vault:<uuid>` resolution, but it does not carry the object identity and
mirrored content facts needed for a HuleEdu File Service-backed record.

The schema must be shaped before runtime adapter work so product code cannot
quietly persist raw R2 identity or treat local paths as durable object identity.

### Goal

Add the Skriptoteket metadata foundation for File Service-backed `Mina filer`
records while preserving local catalog/list authority and `vault:*` refs.

Expected fields include an opaque File Service object reference, content type,
size, SHA-256, File Service lifecycle state, migration batch id where relevant,
finalized timestamp, and delete/purge state. Exact names and constraints must
match the product-neutral File Service object-file contract.

### Non-goals

- No File Service client calls.
- No direct R2 adapter or R2 credentials in Skriptoteket.
- No Upload v2 essay, BOS, assessment, or batch fields.
- No migration/backfill, object copy, prod env sync, or local-vault deletion.
- No change to Document Converter generated artifact or preview storage.

### Implementation Plan

1. Confirm the product-neutral File Service object-reference shape from the
   HuleEdu producer task.
2. Add database migration fields and constraints for File Service-backed vault
   records.
3. Extend the repository/domain model so `vault:*` resolution can distinguish
   local, migrated, missing, checksum-mismatched, deleted, restored, and
   purge-eligible states without exposing object keys.
4. Keep current local records readable until a later migration/cutover task
   explicitly changes read routing.

### Test Plan

- Red-first repository/domain tests for object metadata persistence.
- Red-first tests for fail-closed `vault:*` resolution when object reference,
  lifecycle, checksum, owner, or deleted state is invalid.
- Migration test proving the new fields are nullable or staged safely for
  existing local records before cutover.
- `pdm run test` with the focused backend tests named by implementation.
- `pdm run docs-validate`
- `git diff --check`

### Rollback Plan

Revert the schema and domain changes before any runtime adapter or migration
uses them. Once data is written to the new fields, rollback requires the later
cutover task's data policy.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
