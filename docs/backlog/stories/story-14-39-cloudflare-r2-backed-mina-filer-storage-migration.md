---
type: story
id: ST-14-39
title: "Cloudflare R2-backed Mina filer storage migration"
status: ready
owners: "agents"
created: 2026-07-02
updated: 2026-07-02
epic: "EPIC-14"
dependencies: ["ADR-0059", "ADR-0064", "ADR-0088"]
acceptance_criteria:
  - "Given the migration is approved, when implementation begins, then ADR-0088 states that Skriptoteket consumes the validated HuleEdu File Service contract for object lifecycle and does not implement a direct R2 adapter in this tranche."
  - "Given a vault file is migrated, when the owner lists, downloads, restores, or uses it through a `vault:*` FileRef, then the protected route behavior matches the existing `Mina filer` contract without exposing object keys or signed URLs."
  - "Given Document Converter receives ordered saved-file `source_refs`, when migrated files are selected, then the backend loads bytes server-side from owner-scoped vault refs, preserves order, and fails the whole batch for invalid refs."
  - "Given migration proof is produced, when cutover is requested, then the manifest includes record ids, opaque File Service object references, sizes, SHA-256 checksums, lifecycle state, and rollback instructions."
---

# ST-14-39: Cloudflare R2-Backed Mina Filer Storage Migration

## Context

`ST-14-36` delivered reusable `Mina filer` uploads and picker behavior on local
vault storage. The next production storage question is how to move durable
user-file bytes to Cloudflare R2 while preserving `vault:*` `FileRef` behavior,
protected download/save semantics, soft delete/restore, retention, and
Document Converter saved-source batches.

The HuleEdu slice has validated the shared File Service contract. Skriptoteket
therefore consumes HuleEdu File Service for object lifecycle while keeping
`Mina filer` catalog/list authority in Skriptoteket for v1.

## Plan

1. Approve or revise `ADR-0088`.
2. Keep `REF-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook` as
   the migration fact base.
3. Implement `PR-0411` only after the review closes every open question or moves
   a question into a named follow-up decision.
4. Require red-first tests for owner scoping, missing-object behavior, checksum
   mismatch, delete/restore, retained soft-deleted records, and Document
   Converter saved-source batches.
5. Require live shared-auth browser proof before production cutover.

## Non-Goals

- No production `.env` sync in the planning slice.
- No destructive deletion of local vault bytes in the first implementation
  slice.
- No migration of Sir Convert job artifacts through Skriptoteket storage.
- No direct browser R2 credentials or raw R2 download links.
- No HuleEdu Upload v2 essay, BOS, assessment, or batch semantics in the
  Skriptoteket consumer.
- No migration of session files, runner artifacts, previews, or transcript blobs
  without separate decision coverage.

## Open Questions

All open questions from `ADR-0088` are story blockers. The story may not move to
implementation-ready while any question is answered only as "decide during
implementation".

## Linked Artifacts

- `ADR-0088`: Cloudflare R2 storage boundary for `Mina filer` and FileRefs.
- `REF-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook`: repo
  architecture, config, Docker, and migration pre-runbook facts.
- `PR-0411`: first implementation-planning slice.
- `REV-PR-0411`: retained review gate.
