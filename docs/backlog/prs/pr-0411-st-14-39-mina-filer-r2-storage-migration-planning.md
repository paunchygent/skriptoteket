---
type: pr
id: PR-0411
title: "ST-14-39 Mina filer R2 storage migration planning"
status: ready
owners: "agents"
created: 2026-07-02
updated: 2026-07-02
stories:
  - "ST-14-39"
tags:
  - backend
  - storage
  - r2
  - mina-filer
  - file-refs
  - docs-as-code
dependencies:
  - "ADR-0059"
  - "ADR-0064"
  - "ADR-0088"
links:
  - "docs/adr/adr-0088-cloudflare-r2-storage-boundary-for-mina-filer-and-filerefs.md"
  - "docs/reference/ref-cloudflare-r2-skriptoteket-file-storage-migration-pre-runbook.md"
  - "docs/backlog/stories/story-14-39-cloudflare-r2-backed-mina-filer-storage-migration.md"
  - "docs/backlog/reviews/review-pr-0411-mina-filer-r2-storage-migration-planning.md"
acceptance_criteria:
  - "The accepted package states that Skriptoteket consumes HuleEdu File Service for object lifecycle in this tranche and does not implement a direct R2 adapter."
  - "The accepted package preserves Skriptoteket `Mina filer` catalog/list authority for v1 while treating HuleEdu File Service list as optional until a later catalog-authority tranche."
  - "The accepted package defines exact File Service settings, secret-source labels, Docker service/readiness requirements, migration manifest fields, checksum proof, dual-read window, cutover gate, rollback gate, delete safety, and redaction rules."
  - "The accepted package defines red-first tests for save, list, download, owner denial, missing object, checksum mismatch, delete/restore, purge eligibility, and Document Converter ordered saved-source batches."
  - "The accepted package defines exact live shared-auth proof and production `.env` sync order without committing credential values."
---

# PR-0411: ST-14-39 Mina Filer R2 Storage Migration Planning

## Problem

Moving `Mina filer` bytes to Cloudflare R2 is not just a boto3 endpoint change.
Skriptoteket must preserve product identity, owner-scoped metadata,
`vault:*` `FileRef` behavior, protected save/download semantics, retention, and
Document Converter server-side saved-file batches.

## Goal

Prepare the first reviewed migration slice so implementation can start without
implicit architecture decisions.

The adapter decision is now closed for this tranche: Skriptoteket consumes the
validated HuleEdu File Service contract for object lifecycle and keeps
`Mina filer` catalog/list authority locally for v1.

## Non-Goals

- No code changes in this planning slice.
- No production credential sync or object copy.
- No direct browser-to-R2 credential or raw object-key exposure.
- No Skriptoteket direct R2 adapter in this tranche.
- No HuleEdu Upload v2 essay, BOS, assessment, or batch semantics in the
  Skriptoteket consumer.
- No migration of Sir Convert job artifacts.
- No migration of session files, runner artifacts, previews, or transcript blobs
  unless `ADR-0088` is updated and reviewed.

## Implementation Plan

1. Review `ADR-0088` against the validated HuleEdu File Service contract.
2. Freeze the Skriptoteket catalog metadata contract and database migration
   fields for opaque File Service object references and mirrored content facts.
3. Freeze local/dev/prod File Service config names, secret-source labels, Docker
   services, and readiness checks.
4. Define the migration manifest schema, dry-run command surface, checksum
   verification, dual-read window, rollback gate, and cleanup gate.
5. Define delete/restore/purge mapping between Skriptoteket catalog state and
   HuleEdu File Service lifecycle state.
6. Define the red-first backend, API, frontend, migration, and browser proof
   matrix.
7. Retain `REV-PR-0411` approval before any implementation or prod env changes.

## Test Plan

This PR is docs-only. The implementation PR it authorizes must include
red-first coverage for:

- vault save/list/download with migrated and non-migrated records;
- owner denial and cross-owner `vault:*` refs;
- deleted, restored, purge-eligible, missing-object, and checksum-mismatch
  states;
- Document Converter ordered saved-file `source_refs` using migrated vault
  records;
- File Service finalize succeeds but Skriptoteket database commit fails;
- Skriptoteket database commit succeeds but File Service finalize or checksum
  verification fails;
- migration dry-run and copy manifest verification;
- logs and retained proof redaction for object keys, tokens, and signed URLs.

Focused planning validation:

- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` changes
- `git diff --check`

## Rollback Plan

The planning slice rolls back by reverting the docs. Runtime rollback belongs
to the later implementation slice and must be defined before any data copy:
local reads remain valid until checksum proof, dual-read proof, and the
post-cutover rollback window have passed.

## Open Questions

`ADR-0088` and the linked reference own the remaining open question ledger.
`PR-0411` may not close with any item left as "decide during implementation".
