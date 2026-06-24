---
type: pr
id: PR-0379
title: "ST-37-04 Document Converter backend API contract"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - backend
  - api
  - document-converter
  - sir-convert
dependencies:
  - "PR-0375"
acceptance_criteria:
  - "Given Document Converter is still route-inactive, when the backend slice lands, then it exposes only the authenticated scoped API under `/api/v1/apps/documents.conversion_hub/document-converter/...` and does not add a frontend route, registry capability, runtime link, public capability, or PR-0369 app-presentation contract change."
  - "Given teachers submit one document conversion at a time, when a job is created through the scoped API, then Skriptoteket stores one owner-scoped local job from one upload and one route selection and rejects unsupported routes or multi-file submissions."
  - "Given a conversion succeeds, when the teacher polls the scoped job endpoint, then the response includes one `result_artifact` summary only after terminal success."
  - "Given downloads and saves must be server-authoritative, when the teacher downloads or saves the result, then Skriptoteket authorizes by local `job_id`, downloads the default Sir Convert artifact server-side, and never accepts browser-supplied artifact keys or artifact bytes for the Document Converter MVP save route."
  - "Given Mina filer persistence is owner-scoped, when the result is saved, then the Vault record is `APP_EXPORT` with `source_artifact_id=document-converter:{sir_convert_job_id}:converted_document`, quota rollback works, failed/stale jobs are rejected, and foreign jobs are hidden as not found."
---

# PR-0379: ST-37-04 Document Converter Backend API Contract

## Problem

`PR-0375` approved the Document Converter MVP boundary, but no truthful
backend/API surface exists yet. The current generic Conversion Hub API can
submit document-shaped Sir Convert jobs, but it does not give Document Converter
its own scoped contract, single-result artifact summary, or server-authoritative
save-to-Mina-filer path.

## Goal

Implement the backend/API-only Document Converter contract under the existing
technical app id:

`/api/v1/apps/documents.conversion_hub/document-converter/...`

The slice must make the backend contract testable locally while keeping the
frontend Document Converter card inert until a later route-visible slice.

## Follow-up correction

`PR-0379` remains the accepted route-inactive backend/API foundation. `PR-0380`
supersedes its one-upload and Sir Convert-first assumptions for future work:
the next slice is `PR-0381`, which must move toward app-boundary simple
conversion, local/heavy producer routing, and batch input before any
route-visible UI.

## Non-goals

- No `/apps/document-converter` frontend route, host, runtime link, home-card
  activation, or browser proof target.
- No public Document Converter API or anonymous capability.
- No bootstrap, catalog, app-detail, generated app identity, or PR-0369
  backend/app-presentation split.
- No Exam Converter, Audio Transcription, QTI, Exam.net, correction, or
  transcript export behavior changes.
- No browser-supplied artifact keys or artifact bytes for Document Converter
  download/save.

## Implementation plan

1. Add red-first backend tests for the scoped route catalog, job creation,
   job polling result artifact, artifact download, save-to-Vault, unsupported
   route rejection, multi-file rejection, failed/stale job rejection, quota
   rollback, and foreign-job hiding.
2. Add the scoped Document Converter route facade to the existing Conversion
   Hub API module or a small sibling module under the same `APP_ID`.
3. Reuse the existing Conversion Hub job creation, status refresh, and download
   handlers where their owner-scoped semantics already match the contract.
4. Add a narrow Document Converter result artifact model and save handler that
   loads the owner-scoped local job, confirms success, downloads the default
   Sir Convert artifact server-side, validates bytes and Vault limits, and
   stores the result as `APP_EXPORT`.
5. Wire the new handler through Dishka.
6. Update `.codex/handoff.md`, `docs/index.md`, and `ST-37-04` only for the
   new backend/API slice status.

## Test plan

- Red first:
  `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
- Focused green:
  `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py`
- Adjacent backend API checks if shared router contracts change:
  `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py`
- Close-out:
  `pdm run lint`
  `pdm run typecheck`
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`

## Implementation summary

- Added the scoped authenticated backend API surface under
  `/api/v1/apps/documents.conversion_hub/document-converter/...`:
  route catalog, one-upload job submission, owner-scoped status polling,
  result download, and server-authoritative save.
- The Document Converter submit route now fails closed on upload metadata and
  size: it validates the declared source format against filename suffix and
  content type before producer submission, and it reads the upload through the
  shared capped-upload helper using `UPLOAD_MAX_FILE_BYTES` and
  `UPLOAD_MAX_TOTAL_BYTES`.
- Added Document Converter response/save contracts in
  `src/skriptoteket/application/curated_apps/document_converter.py`.
- Added route-scoped handlers in
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py`
  so Exam Converter and Audio Transcription jobs are hidden from the Document
  Converter facade.
- Wired handlers through Dishka in `src/skriptoteket/di/curated_apps.py`.
- Refreshed generated frontend API types for the new backend contract without
  adding any `/apps/document-converter` frontend route, home-card link, public
  capability, or PR-0369 app-presentation split.
- Added focused web and application handler tests for route catalog, one-file
  submission, unsupported route rejection, result artifact summary, download,
  server-authoritative save, foreign-job hiding, and Vault rollback.

## Validation

- Red first:
  `/opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
  failed on missing `document_converter` models and
  `conversion_hub_document_converter` handlers.
- Focused green:
  `/opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
- Review-fix red:
  after adding the missing upload-validation tests, the same focused command
  failed because `submit_document_converter_job(...)` had no governed upload
  settings/capped-read path yet.
- Review-fix green:
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
- Adjacent green:
  `/opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py`
- Generated API types:
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run fe-gen-api-types`
- Gates:
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run lint`
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run typecheck`
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run fe-type-check`
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run docs-validate`
  `env PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin /opt/homebrew/bin/pdm run handoff-validate`
  `git diff --check`

## Rollback plan

Remove the scoped Document Converter API routes, result/save contracts, handler
DI provider, and focused tests. Keep the Document Converter frontend lane inert
and continue relying on `PR-0375` plus the follow-up correction in `PR-0380` as
the planning contract.
