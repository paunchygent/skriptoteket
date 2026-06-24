---
type: review
id: REV-PR-0379
title: "Review: PR-0379 Document Converter backend API contract"
status: approved
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
reviewer: "codex-independent-reviewer"
prs:
  - PR-0379
links:
  - ST-37-04
  - EPIC-37
  - PR-0375
---

# Review: PR-0379 Document Converter Backend API Contract

## TL;DR

PR-0379 is approved on fixed-reviewer re-review. The retained
post-implementation finding is resolved: the Document Converter submit route
validates declared source format against filename suffix and content type, reads
through the shared capped upload helper, and rejects oversized uploads before
the job handler runs.

## Problem Statement

Document Converter needs a truthful server contract before any route-visible
frontend can be activated. This review checks whether `PR-0379` is narrow enough
to implement that contract without leaking into Exam Converter,
Audio Transcription, public APIs, registry identities, or frontend navigation.

## Proposed Solution

Expose a scoped authenticated backend facade under
`/api/v1/apps/documents.conversion_hub/document-converter/...`, reuse the
existing owner-scoped Conversion Hub job ledger and Sir Convert client, and add
a server-authoritative save handler for the single default converted artifact.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0379-st-37-04-document-converter-backend-api-contract.md` | Scope, stop conditions, proof obligations | 20 min |
| `docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md` | Governing MVP contract | 10 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Parent story status and route-inactive boundary | 5 min |

**Total estimated time:** ~35 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the first implementation under `documents.conversion_hub/document-converter`. | Matches `PR-0375` and avoids bootstrap/catalog/app-detail changes before a route-visible need exists. | [x] |
| Reuse the existing local job ledger for owner-scoped submit, poll, and download. | The ledger already owns local job identity and cross-owner hiding. | [x] |
| Add a dedicated server-authoritative save handler for Document Converter. | Prevents the MVP from inheriting the Exam Converter browser-upload save authority. | [x] |
| Keep frontend activation out of scope. | Backend/API proof must exist before `/apps/document-converter` can be truthful. | [x] |

## Review Checklist

- [x] Scope is backend/API-only and authenticated-only.
- [x] No frontend route, runtime link, registry capability, public capability,
  or PR-0369 app-presentation split is included.
- [x] Artifact download/save are authorized by local `job_id`.
- [x] Browser-supplied artifact keys and artifact bytes are excluded from the
  Document Converter MVP save route.
- [x] Verification plan includes focused red/green backend tests and docs
  validation.

## Review Feedback

**Reviewer:** `skriptoteket_reviewer`
**Date:** `2026-06-23`
**Verdict:** approved

### Required Changes

None.

### Suggestions (Optional)

Keep result artifact metadata deliberately modest in this first slice. Filename,
content type, size, and checksum may be filled from server-authoritative
downloads/saves when known; the poll endpoint should not invent producer data.

### Decision Approvals

- [x] Scoped backend namespace.
- [x] Existing ledger reuse.
- [x] Dedicated server-authoritative save handler.
- [x] No frontend activation.

## Changes Made

- Initial review approval for implementation.
- Pass 1 post-implementation review reopened the slice with one retained
  upload-validation finding and `changes_requested`.
- Fixed-reviewer re-review independently verified the remediation and now owns
  the retained `approved` verdict below.

## Post-Implementation Review

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-23`
**Verdict:** changes_requested

### Scope

Post-implementation review of the current uncommitted `PR-0379` backend/API
slice against the governed `PR-0375` Document Converter MVP contract.

| File | Focus |
|------|-------|
| `src/skriptoteket/web/api/v1/apps_conversion_hub.py` | Scoped Document Converter submit/status/download/save routes |
| `src/skriptoteket/application/curated_apps/document_converter.py` | Result artifact contract and route scoping |
| `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py` | Owner-scoped job access, artifact download, Vault save semantics |
| `src/skriptoteket/di/curated_apps.py` | Dishka wiring for the new handlers |
| `tests/unit/web/conversion_hub/test_apps_document_converter_api.py` | API boundary regression proof |
| `tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Handler behavior and rollback proof |

### Findings

#### High: Document Converter submit path skips the governed upload validation contract and buffers uploads without the repo cap helper

`src/skriptoteket/web/api/v1/apps_conversion_hub.py:253`

`PR-0375` makes the web boundary responsible for validating the declared route,
extension/content type, size limits, and exactly one source file before
producer submission (`docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md:156`).
The implemented `submit_document_converter_job(...)` route only checks the
route pair, file count, and filename, then forwards
`upload.content_type or "application/octet-stream"` and `await upload.read()`
directly to the handler. That means a mismatched upload such as an audio file
declared as HTML/PDF is accepted until Sir Convert fails it, and an oversized
upload is read fully into memory instead of using the repo's existing capped
upload helper in `src/skriptoteket/web/uploads.py:21`.

Why it matters: this breaks the approved MVP contract and removes the local
fail-closed guarantee the Document Converter facade is supposed to provide.
It also reintroduces an avoidable operational risk because the endpoint reads
the whole multipart payload without enforcing `Settings.UPLOAD_MAX_FILE_BYTES`
or `Settings.UPLOAD_MAX_TOTAL_BYTES`.

Concrete fix: validate the single upload against the declared
`ConversionHubSourceFormatV2` before calling the handler, and read it through
the existing capped upload helper (or an equivalent shared helper) wired to the
repo upload settings. Reject extension/content-type mismatches and over-limit
uploads with `validation_error(...)` at the web boundary instead of letting
Sir Convert discover them later.

Proof requirement: add focused API tests that prove
1. a mismatched filename/content type is rejected before `CreateConversionHubJobsHandler.handle(...)` runs, and
2. an over-limit upload is rejected through the capped-upload path.
Run `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`.

### Approved Checks

| Review question | Result | Evidence |
|-----------------|--------|----------|
| Is the new backend surface still scoped to `/api/v1/apps/documents.conversion_hub/document-converter/...` with no frontend route/card activation? | Approved | The diff adds only scoped backend endpoints plus generated OpenAPI types; no frontend route, app host, or public capability files changed. |
| Do status/download/save stay authorized by local owner-scoped `job_id` and hide foreign or non-document jobs as not found? | Approved | `GetDocumentConverterJobHandler`, `DownloadDocumentConverterArtifactHandler`, and `SaveDocumentConverterArtifactHandler` load the local job, owner-check it, route-scope it, and reject foreign/non-document jobs through `not_found(...)`. |
| Does `GET job` expose `result_artifact` only after success and does save stay server-authoritative? | Approved | `build_document_converter_result_artifact(...)` returns `None` unless the job is `SUCCEEDED`, and save/download both fetch the default Sir Convert artifact server-side by `job_id` with no browser-supplied artifact key or bytes. |
| Does save persist Vault `APP_EXPORT` with the required `document-converter:{sir_convert_job_id}:converted_document` source id and clean up stored bytes after post-store failure? | Approved | `SaveDocumentConverterArtifactHandler` writes `VaultFileSourceKind.APP_EXPORT`, builds the required source id, and deletes stored bytes in the exception path after a post-store failure. |

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Passed: 13 tests. |
| Code review of `src/skriptoteket/web/api/v1/apps_conversion_hub.py:236-277` against `docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md:156` | Failed: the route does not validate extension/content type or upload size limits before reading the file and submitting the local job. |

## Fixed-Reviewer Re-review

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-23`
**Verdict:** approved

### Decision

`approved`

No findings. The retained upload-validation finding is resolved, and the
Document Converter backend slice now matches the governed `PR-0375` upload
contract without widening scope into frontend activation or generic Conversion
Hub behavior changes.

### Pass 1 Finding Resolution

| Prior finding | Resolution evidence | Status |
|---------------|---------------------|--------|
| High: Document Converter submit path skipped the governed upload validation contract and buffered uploads without the repo cap helper. | `src/skriptoteket/application/curated_apps/document_converter.py:162` through `src/skriptoteket/application/curated_apps/document_converter.py:201` add fail-closed filename suffix and content-type validation against the declared `ConversionHubSourceFormatV2`. `src/skriptoteket/web/api/v1/apps_conversion_hub.py:239` through `src/skriptoteket/web/api/v1/apps_conversion_hub.py:290` now inject `Settings`, validate the single upload before submission, and read bytes through `read_upload_files(...)` using `UPLOAD_MAX_FILE_BYTES` and `UPLOAD_MAX_TOTAL_BYTES`. `tests/unit/web/conversion_hub/test_apps_document_converter_api.py:242` through `tests/unit/web/conversion_hub/test_apps_document_converter_api.py:313` prove mismatched suffix, mismatched content type, and oversized uploads are rejected before `CreateConversionHubJobsHandler.handle(...)` runs. | Resolved. |

### Approved Checks

| Review question | Result | Evidence |
|-----------------|--------|----------|
| Does the scoped Document Converter submit route now enforce the governed upload boundary at the web layer? | Approved | The route validates the declared source/output pair, requires exactly one upload, rejects filename suffix/content-type mismatches through `validate_document_converter_upload(...)`, and only forwards validated metadata to the handler. |
| Does the route reuse the repo’s capped upload helper instead of unbounded reads? | Approved | `submit_document_converter_job(...)` calls `read_upload_files(...)`, which uses `_read_upload_file_with_limit(...)` and enforces both per-file and total upload caps before the handler sees the bytes. |
| Do focused regressions now prove fail-closed behavior before producer submission? | Approved | The Document Converter API test suite now includes explicit rejection cases for mismatched suffix, mismatched content type, and oversized uploads, and each asserts the create-job handler was not called. |
| Did the remediation stay within the approved backend/API-only slice? | Approved | The diff is limited to the scoped Document Converter backend contract, shared upload-validation reuse, focused backend tests, and retained docs/handoff updates; no frontend route/card activation or `PR-0369` expansion was introduced. |

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Passed: 16 tests. |
| `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py` | Passed: 19 tests. |
| `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run docs-validate` | Passed. |
| Code review of `src/skriptoteket/application/curated_apps/document_converter.py`, `src/skriptoteket/web/api/v1/apps_conversion_hub.py`, and `tests/unit/web/conversion_hub/test_apps_document_converter_api.py` against `docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md:156` | Approved: the route now validates extension/content type and size caps before reading/submitting the upload. |
