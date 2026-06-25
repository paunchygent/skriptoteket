---
type: review
id: REV-PR-0382
title: "Review: PR-0382 Document Converter HTML/CSS project preview contract"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
reviewer: "codex-independent-reviewer"
prs:
  - PR-0382
links:
  - ST-37-04
  - EPIC-37
  - PR-0381
  - REV-PR-0381
---

# Review: PR-0382 Document Converter HTML/CSS Project Preview Contract

## TL;DR

Re-review completed for the repaired `PR-0382` package. The repair pass closes
the three prior blockers: a cron-friendly cleanup surface now exists under
`pdm run cleanup-document-converter-project-previews`, preview persistence now
stages and rolls back cleanly while cleanup removes malformed/orphan/staging
directories, and the preview download route now publishes `application/pdf`
binary OpenAPI/types. Route-visible Document Converter UI remains inactive.

## Problem Statement

`PR-0380` and `PR-0381` established HTML/CSS project previews as a core
teacher-facing lane, but only as a backend/API contract while route-visible UI
remains blocked. This review checks whether `PR-0382` closes that contract
without activating production UI, weakening preview-asset sandboxing, leaking
filesystem authority, or publishing an incoherent OpenAPI surface.

## Proposed Solution

Keep the scoped backend namespace under
`/api/v1/apps/documents.conversion_hub/document-converter/project-previews`,
accept a validated multi-file project manifest, render separate/combined PDFs
through a constrained WeasyPrint fetcher, store temporary preview artifacts
server-side under owner-scoped ids, and allow explicit save-to-`Mina filer`
only through server-owned preview/artifact identifiers.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0382-st-37-04-document-converter-html-css-project-preview-contract.md` | Scope, stop conditions, TTL contract, verification claims | 20 min |
| `docs/backlog/prs/pr-0381-st-37-04-document-converter-local-heavy-producer-and-batch-contract.md` | Prior accepted producer/artifact authority contract | 10 min |
| `docs/backlog/reviews/review-pr-0381-document-converter-local-heavy-producer-and-batch-contract.md` | Prior review constraints and repair expectations | 10 min |
| `src/skriptoteket/application/curated_apps/document_converter_projects.py` | Manifest, PDF controls, preview response models | 20 min |
| `src/skriptoteket/application/curated_apps/handlers/document_converter_project_previews.py` | Render/status/download/save/discard/cleanup orchestration | 25 min |
| `src/skriptoteket/infrastructure/documents/document_converter_project_previews.py` | Asset sandbox, PDF merge, filesystem preview storage, cleanup semantics | 35 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub_document_converter_project_previews.py` | Thin router contract and OpenAPI surface | 20 min |
| `src/skriptoteket/protocols/document_converter.py`, `src/skriptoteket/di/curated_apps.py`, `src/skriptoteket/web/router.py` | Protocol-first DI, route wiring, cleanup reachability | 20 min |
| `tests/unit/application/curated_apps/test_document_converter_project_manifest.py`, `tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py`, `tests/unit/infrastructure/documents/test_document_converter_project_previews.py`, `tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py` | Focused manifest/render/sandbox/API proof | 30 min |
| `frontend/apps/skriptoteket/src/api/openapi.d.ts` | Generated frontend contract truthfulness | 10 min |

**Total estimated time:** ~3.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `/apps/document-converter` inactive. | Mockup/copy approval still gates route-visible UI. | [x] |
| Keep linked assets constrained to bare filenames inside `project:///`. | Prevents path traversal, URL fetches, and browser filesystem authority. | [x] |
| Keep save/download authority on `{preview_id, artifact_id}` only. | Preserves server-owned preview storage and Vault save authority. | [x] |
| Claim a real 24-hour temporary-artifact TTL. | Product contract requires actual cleanup behavior, not metadata-only expiry. | [x] |
| Publish the preview-download route as an accurate binary API contract. | OpenAPI is the frontend contract and must not lie about response media type. | [x] |

## Review Checklist

- [x] Scope stayed backend/API-only with no route, nav, card, mockup, Swedish copy, or marketplace activation.
- [x] Manifest validation enforces filename-only HTML/CSS/image declarations and zero uploaded fonts.
- [x] Preview save/download authority remains owner-scoped and server-owned.
- [x] Asset fetcher rejects `file://`, HTTP(S), path traversal, nested paths, and undeclared files.
- [x] Output modes cover separate PDFs, combined PDF, and both.
- [x] 24-hour preview retention is enforced through a production cleanup entrypoint.
- [x] Temporary preview storage fails closed without orphaning retained preview bytes.
- [x] OpenAPI/generated frontend types accurately describe the binary download route.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-25`
**Verdict:** `approved`

### Required Changes

None.

### Repair Re-review

The prior findings are resolved:

1. The cleanup surface now exists as a real Typer/PDM command at
   `cleanup-document-converter-project-previews`, wired through
   [src/skriptoteket/cli/main.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/cli/main.py:53),
   [pyproject.toml](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/pyproject.toml:406),
   and
   [src/skriptoteket/cli/commands/cleanup_document_converter_project_previews.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/cli/commands/cleanup_document_converter_project_previews.py:29).
   Focused CLI proof now verifies expired preview deletion.
2. Preview persistence is now staged and rollback-safe in
   [src/skriptoteket/infrastructure/documents/document_converter_project_preview_store.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/documents/document_converter_project_preview_store.py:43),
   and cleanup now removes expired, malformed, orphan, and leftover staging
   directories via
   [cleanup_expired()](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/documents/document_converter_project_preview_store.py:137).
   Focused infrastructure tests cover metadata-write rollback and malformed/orphan cleanup.
3. The preview download route now publishes an explicit PDF binary contract in
   [src/skriptoteket/web/api/v1/apps_conversion_hub_document_converter_project_previews.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/web/api/v1/apps_conversion_hub_document_converter_project_previews.py:101),
   and regenerated types now expose `"application/pdf"` in
   [frontend/apps/skriptoteket/src/api/openapi.d.ts](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/frontend/apps/skriptoteket/src/api/openapi.d.ts:10680).
   Focused OpenAPI contract proof passes.

## Suggestions

None.

## Verification

- Static review against `AGENTS.md`, `.codex/handoff.md`, `.codex/rules/020`, `025`, `040`, `042`, `048`, `050`, `070`, `096`, `ruthless-code-review`, `testing`, `skriptoteket-testing`, and `skriptoteket-backend-dev`.
- `pdm run test tests/unit/cli/test_cleanup_document_converter_project_previews.py`
  Passed: `1 passed`.
- `pdm run test tests/unit/infrastructure/documents/test_document_converter_project_previews.py`
  Passed: `14 passed`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py::test_project_preview_download_openapi_contract_is_pdf_binary`
  Passed: `1 passed`.
- `pdm run cleanup-document-converter-project-previews --artifacts-root .artifacts/pr-0382-cleanup-empty-proof-rereview`
  Passed; reported `deleted_previews=0 deleted_artifacts=0`.
- `pdm run fe-gen-api-types`
  Passed; regenerated `frontend/apps/skriptoteket/src/api/openapi.d.ts`.
- `pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py tests/unit/cli/test_cleanup_document_converter_project_previews.py`
  Passed: `36 passed in 1.90s`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
  Passed: `28 passed in 0.37s`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py`
  Passed: `33 passed in 0.39s`.
- Scope inspection confirmed no route-visible `/apps/document-converter` activation, no Swedish copy additions, no marketplace/template-management surface, and no `PR-0369` reopening in the reviewed patch.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0382` | Created the retained independent review record with findings and a `changes_requested` decision. |
| 2 | `PR-0382` | Reviewed the route-inactive preview contract, asset sandbox, preview storage semantics, generated API types, and focused tests. |
| 3 | `PR-0382` | Repair pass added the cleanup command, rollback-safe preview store, malformed/orphan cleanup, and binary OpenAPI/types for preview downloads. |
| 4 | `REV-PR-0382` | Re-reviewed the repair pass, reran focused/regression proof, and approved the slice. |
