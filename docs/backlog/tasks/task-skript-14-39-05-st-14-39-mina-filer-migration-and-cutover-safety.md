---
type: task
id: TASK-SKRIPT-14-39-05
title: ST-14-39 Mina filer migration and cutover safety
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
- Given File Service-backed reads and writes are proven locally, then migration planning
  defines dry-run inventory, checksum verification, dual-read, rollback, and cleanup
  gates before any data copy starts.
- Given production cutover is requested, then a retained approval packet names the
  exact env sync order, proof commands, rollback window, and destructive-action gate
  without committing secret values.
- Given any checksum, owner-scope, lifecycle, delete/restore, or Document Converter
  saved-source proof fails, then migration stops and local storage remains active.
- Given cleanup is considered, then local-vault deletion is a separate explicit destructive-action
  gate and is not bundled into the initial copy or cutover proof.
dependencies:
- ADR-SKRIPT-0088
- TASK-SKRIPT-14-39-03
- TASK-SKRIPT-14-39-04
---

## Context
### Problem
Object migration is a data-safety operation, not a natural extension of adapter
implementation. Copy, verification, dual-read, rollback, production env sync,
and cleanup need their own gate after the metadata and runtime consumer slices
are proven.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Story Contract Slice
### Goal
Define and implement the migration/cutover safety lane for durable `Mina filer`
bytes after `PR-0413` and `PR-0414` are reviewed and closed.
### Non-goals
- No implementation before the metadata schema and File Service adapter proofs
  are accepted.
- No destructive local-vault cleanup in the initial migration run.
- No migration of session files, runner artifacts, previews, transcript blobs,
  Document Converter generated artifacts, or Sir Convert job artifacts.
- No direct browser-to-R2 behavior, raw R2 object-key exposure, or R2
  credentials in Skriptoteket.
- No production `.env` value commits.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Plan
### Implementation Plan
1. Freeze the migration dry-run inventory and retained proof shape.
2. Copy through HuleEdu File Service only, then verify size and SHA-256 from
   File Service metadata.
3. Enable dual-read only inside a reviewed rollback window.
4. Cut over new writes only after protected route and Document Converter proof
   pass.
5. Keep destructive cleanup behind a separate explicit approval gate.
### Test Plan
- Red-first migration dry-run tests for active and soft-deleted vault records.
- Copy/finalize/checksum tests that fail closed on size or digest mismatch.
- Dual-read and rollback tests proving local reads remain available during the
  reviewed rollback window.
- Cutover proof for save, list, download, Document Converter saved-source batch,
  delete, restore, missing-object failure, and cross-owner denial.
- `pdm run docs-validate`
- `git diff --check`
### Rollback Plan
Stop migration, keep local storage authoritative for affected records, and use
the reviewed rollback manifest to restore reads. Destructive cleanup remains
blocked until a separate explicit approval closes the cleanup gate.

## Implementation Steps
The source record did not define a separate section for this package heading.

## Proof
The source record did not define a separate section for this package heading.

## Validation
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Lessons Learned
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Implementation Review
The source record did not define a separate section for this package heading.
