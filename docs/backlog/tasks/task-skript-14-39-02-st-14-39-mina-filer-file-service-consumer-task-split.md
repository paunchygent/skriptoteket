---
type: task
id: TASK-SKRIPT-14-39-02
title: ST-SKRIPT-14-39 Mina filer File Service consumer task split
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-14-39
task_kind: story
acceptance_criteria:
- The slice records that Skriptoteket is a HuleEdu File Service consumer for `Mina
  filer` object lifecycle and must not implement a direct R2 adapter or Upload v2
  consumer fallback.
- The slice records that the product-neutral HuleEdu File Service object-file API
  is a producer prerequisite before runtime consumer implementation can close.
- The slice creates bounded follow-up PR tasks for Skriptoteket metadata/schema, File
  Service client adapter plus protected route proof, and migration/cutover safety.
- The slice keeps production env sync, object copy, destructive cleanup, raw R2 identity
  exposure, and non-`Mina filer` surfaces out of scope.
- The slice updates the story and ADR discovery surfaces so future agents find the
  task split without relying on chat history.
---

## Context

The source does not provide a separate context section; no additional context is recorded.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Story Contract Slice

### Source: Goal

Turn the retained blockers from `ADR-0088`, `PR-0411`, and `REV-PR-0411` into
owned, bounded PR tasks that can be implemented without broadening the first
runtime slice.

## Contract Inputs

### Source: Explorer Evidence

Exploration found these current constraints:

- HuleEdu has validated the shared R2/File Service direction, but the visible
  API surface still exposes Upload v2 and `/v1/content` routes rather than a
  product-neutral object-file API for init, finalize, metadata, download, and
  delete.
- Skriptoteket's durable saved-file identity is still `vault:<uuid>`.
  `user_vault_files` does not yet carry content type, SHA-256, opaque File
  Service object reference, lifecycle state, migration batch id, finalized
  timestamp, or purge/delete state beyond `deleted_at`.
- Current `Mina filer` and Document Converter saved-source behavior is
  owner-scoped, refs-only, ordered, and fail-closed. The browser must continue
  to submit saved-file refs, not bytes or object URLs.

## Plan

The source does not provide a separate plan section; no additional plan is recorded.

## Implementation Steps

### Source: Task Split

| Slice | Status | Owns | Blocked by |
|---|---|---|---|
| HuleEdu product-neutral File Service object-file API | external prerequisite | Producer endpoints and fields for namespace-aware user files | HuleEdu-owned task not tracked in this repo |
| `PR-0413` | blocked | Skriptoteket catalog metadata, migration columns, lifecycle mirror, and fail-closed repository/domain contract | Product-neutral File Service reference shape |
| `PR-0414` | blocked | HuleEdu File Service client adapter behind `VaultStorageProtocol`, protected route proof, and Document Converter saved-source reads | HuleEdu producer API and `PR-0413` |
| `PR-0415` | blocked | Migration dry-run, dual-read, cutover, rollback, and destructive-cleanup gates | `PR-0413`, `PR-0414`, and explicit cutover approval |

`PR-0413`, `PR-0414`, and `PR-0415` are created by this slice as local
Skriptoteket work packages. The HuleEdu producer task must be created and
closed in the HuleEdu or cross-repo governance lane before local runtime
consumer completion is claimed.

## Proof

### Source: Test Plan

This PR is docs-only.

- `pdm run docs-validate`
- `git diff --check`
- Retained review by `ruthless_review_agent` before terminal closeout.

## Validation

The source does not provide a separate validation section; no additional validation is recorded.

## Stop Conditions

### Source: Non-goals

- No product code changes in this planning and task-creation slice.
- No production `.env` sync, secret value documentation, or runtime deployment.
- No object copy, backfill, destructive cleanup, or local-vault deletion.
- No direct Skriptoteket R2 adapter, browser-facing R2 URL, raw object key, or
  R2 credential exposure.
- No HuleEdu Upload v2 essay, BOS, assessment, or batch semantics in the
  Skriptoteket consumer.
- No migration of session files, runner artifacts, previews, transcript blobs,
  Document Converter generated artifacts, or Sir Convert job artifacts.

### Source: Rollback Plan

Revert this docs slice if the task split is rejected. No runtime state,
credentials, or object data are changed.

## Lessons Learned

The source does not provide a separate lessons learned section; no additional lessons learned is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: PR-0412: ST-14-39 Mina Filer File Service Consumer Task Split



### Source: Problem

`PR-0411` and `REV-PR-0411` approved the direction, but they intentionally left
implementation blockers open. Treating that approval as runtime readiness would
hide the biggest dependency: the current visible HuleEdu File Service route
surface is still Upload v2-shaped, while the Skriptoteket tranche requires a
product-neutral object-file contract.

Skriptoteket also needs local `Mina filer` work before bytes can move: metadata
schema, File Service client wiring, fail-closed protected routes, and migration
safety are separate concerns.

### Source: Planning Decisions

1. `REV-PR-0411` approval does not make `ST-14-39` implementation-ready by
   itself. It approves the direction and keeps implementation blockers visible.
2. The first local implementation task is metadata/schema readiness, not a
   direct storage adapter.
3. The first runtime consumer task is a File Service client adapter behind
   `VaultStorageProtocol`, not direct R2 and not HuleEdu Upload v2.
4. Migration/cutover is a later safety task. It must not be bundled into the
   first metadata or client-adapter implementation slice.

### Source: Implementation Evidence

The planning/task-creation slice is implemented:

- `PR-0413` records the metadata/schema follow-up task.
- `PR-0414` records the File Service client adapter and protected proof
  follow-up task.
- `PR-0415` records the migration and cutover safety follow-up task.
- `ST-14-39` links the new task split and orders local follow-up work.
- `ADR-0088` routes the remaining open questions to named follow-up PR tasks
  while keeping the HuleEdu product-neutral File Service object-file API as an
  external producer prerequisite.

Independent retained review `REV-PR-0412` approved this docs-only slice on
2026-07-04 with no findings.

Validation:

- `pdm run docs-validate` passed.
- `git diff --check` passed.
- `pdm run docs-sync` is not available in this repo; PDM reports
  `Command 'docs-sync' is not found in your PATH.`

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Implementation Review

The source does not provide a separate implementation review section; no additional implementation review is recorded.
