---
type: review
id: REV-PR-0381
title: "Review: PR-0381 Document Converter local-heavy producer and batch contract"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
reviewer: "codex-independent-reviewer"
prs:
  - PR-0381
links:
  - ST-37-04
  - EPIC-37
  - PR-0379
  - PR-0380
---

# Review: PR-0381 Document Converter Local-Heavy Producer And Batch Contract

## TL;DR

Review completed for the route-inactive Document Converter backend package that
adds batch submission, automatic local/heavy producer routing, shared document
rendering/extraction adapters, local server-owned result storage, and
regenerated scoped API types without activating the frontend route. The repair
pass resolves the two previously blocked issues: extractable-but-complex PDFs
now route to Sir Convert through explicit heavy-path signals, and local
artifact-store faults now fail closed as `FAILED` jobs instead of bubbling as
500s with stranded `submitted` state.

## Problem Statement

`PR-0380` corrected the product contract: simple document conversion belongs
inside Skriptoteket, while heavy/OCR/complex paths stay producer-owned. This
review checks whether `PR-0381` implements that backend contract without
reintroducing teacher-selected producer routing, browser artifact authority, or
route-visible Document Converter UI.

## Proposed Solution

Keep the scoped `documents.conversion_hub/document-converter` API namespace,
expand submit to a validated batch of up to 10 uploads, choose the producer
automatically per item, execute first simple local lanes through shared
document services, store local outputs server-side by local job id, and route
heavy or unsupported lanes to Sir Convert with explicit decision reasons.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0381-st-37-04-document-converter-local-heavy-producer-and-batch-contract.md` | Scope, research evidence, stop conditions, verification | 15 min |
| `src/skriptoteket/application/curated_apps/document_converter.py` | Scoped API models, validation, job/result identity | 15 min |
| `src/skriptoteket/application/curated_apps/document_converter_producers.py` | Automatic local/Sir Convert routing and local conversion lanes | 20 min |
| `src/skriptoteket/application/curated_apps/handlers/document_converter_jobs.py` | Batch job creation, UoW behavior, local artifact storage | 20 min |
| `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py` | Download/save authority for local and Sir Convert jobs | 15 min |
| `src/skriptoteket/protocols/documents.py`, `src/skriptoteket/protocols/document_converter.py`, `src/skriptoteket/infrastructure/documents/` | Shared document protocols and adapters | 20 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub.py` and `src/skriptoteket/di/curated_apps.py` | Scoped API wiring and Dishka providers | 20 min |
| `tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py`, `tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py`, `tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py`, `tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Focused Document Converter proof | 25 min |
| Adjacent Conversion Hub tests listed in `PR-0381` verification evidence | Exam Converter and Audio Transcription regression proof | 15 min |
| `frontend/apps/skriptoteket/src/api/openapi.d.ts` | Generated API type update | 10 min |

**Total estimated time:** ~2.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `/apps/document-converter` inactive. | Route-visible UI still waits for mockup/copy approval and later PR slices. | [x] |
| Use automatic producer routing only. | Teachers should never choose local versus Sir Convert. | [x] |
| Run only first proven simple lanes locally. | WeasyPrint, Python-Markdown, and pdfplumber have current syntax/runtime evidence; pypdf/python-docx/Pandoc remain future lane proof. | [x] |
| Store local outputs server-side by local job id. | Download/save authority must not come from browser artifact refs or bytes. | [x] |
| Centralize reusable document/PDF surfaces. | Prevents another app-local WeasyPrint/PDF wrapper and gives later curated apps protocol seams. | [x] |

## Review Checklist

- [x] Scope remains backend/API-only with no route/card/nav/public activation.
- [x] Batch submit validates up to 10 items and rejects invalid mixed input
  before producer submission.
- [x] Local versus Sir Convert routing is automatic, explicit, and fail-closed.
- [x] Local result download/save authority is server-owned and owner-scoped.
- [x] Exam Converter and Audio Transcription behavior remains unchanged.
- [x] Shared document services avoid duplicated app-local PDF boilerplate.
- [x] Verification evidence is sufficient for red-first and green closeout.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-25`
**Verdict:** approved

### Required Changes

None. Re-review verified that the previous heavy-PDF routing and local
artifact-store failure findings are resolved.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Route remains inactive.
- [x] Automatic producer routing.
- [x] Narrow local lane selection.
- [x] Server-owned local artifact authority.
- [x] Shared document service centralization.

### Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py`
  Passed: 8 tests.
- `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
  Passed: 28 tests.
- `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py`
  Passed: 33 tests.
- `pdm run lint`
  Passed.
- `pdm run typecheck`
  Passed.
- Re-review inspection against `PR-0380`, `PR-0381`, and the routed review/test
  skills confirmed that the previous blocked behaviors are now covered by code
  and truthful tests.

## Implementation Repair Response

**Date:** `2026-06-25`
**Status:** reviewed and accepted in the fixed-reviewer re-review.

### Repair Notes

- Added structured PDF text probing so producer routing can distinguish simple
  extractable PDFs from extractable-but-heavy PDFs. The policy now routes
  probe reasons such as `table_dense_pdf`, `formula_heavy_pdf`, and
  `layout_complex_pdf` to Sir Convert instead of treating any extracted text as
  a local lane.
- Kept simple extractable `pdf -> md` local when the probe returns text with no
  heavy reason.
- Wrapped local conversion/artifact persistence so artifact-store exceptions
  update the local job to `FAILED` with an observable error instead of bubbling
  as a 500 and leaving a stranded `submitted` job.

### Repair Verification

- `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py`
  Red before repair: 3 failed, 5 passed.
- `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py`
  Green after repair: 8 passed.
- `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
  Passed: 28 tests.
- `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py`
  Passed: 33 tests.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0381` | Implemented route-inactive batch and local/heavy producer contract pending independent review. |
| 2 | `REV-PR-0381` | Recorded independent review findings, verification evidence, and `changes_requested` verdict. |
| 3 | `PR-0381` | Added repair tests and implementation for complex PDF routing plus fail-closed local artifact-store failures. |
| 4 | `REV-PR-0381` | Re-reviewed the repair pass, verified the prior findings were resolved, and approved the slice. |
