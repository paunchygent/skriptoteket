---
type: pr
id: PR-0382
title: "ST-37-04 Document Converter HTML/CSS project preview contract"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-25
stories:
  - "ST-37-04"
tags:
  - backend
  - frontend-contract
  - document-converter
  - html-css
dependencies:
  - "PR-0380"
  - "PR-0381"
acceptance_criteria:
  - "Given HTML/CSS to PDF is a core product lane, when this slice closes, then the contract supports multi-file HTML/CSS project input rather than a single flat upload."
  - "Given teachers need to judge the result before saving, when a render is requested, then the app can expose progress and a final PDF preview that can be discarded and regenerated."
  - "Given PDF output needs teacher controls, when the preview contract is defined, then page size, orientation, margins, and template selection are represented without approving final UI copy."
  - "Given batch output needs differ by lesson material, when HTML/CSS projects render, then the contract supports separate PDFs, one combined PDF, or both."
  - "Given UI work is gated, when this slice closes, then it defines backend/frontend data contracts only and does not implement route-visible production UI."
---

# PR-0382: ST-37-04 Document Converter HTML/CSS Project Preview Contract

## Problem

HTML/CSS to PDF is the strongest teacher-facing value lane, but it is not useful
as a one-file blind conversion. Teachers need to upload a small project, render
it, see the resulting PDF, then discard, adjust, and render again.

## Goal

Define and implement the contract for HTML/CSS project input and final-PDF
preview generation after the general batch/local-heavy contract in `PR-0381`
has established the producer shape.

## Prerequisites Closed

- `PR-0380` corrected the Document Converter product direction: simple lanes
  run inside the Skriptoteket app boundary, HTML/CSS to PDF is a first-class
  value lane, preview PDFs are temporary server artifacts with a 24-hour target
  TTL, and production UI remains gated by mockup and copy approval.
- `PR-0381` is done and approved by `REV-PR-0381`. It closed the local/heavy
  producer policy, added the batch input model, selected the first local
  HTML/CSS-to-PDF path through the shared WeasyPrint-backed document renderer,
  and kept `/apps/document-converter` inactive.

## Non-goals

- No final production UI.
- No user-facing Swedish copy.
- No template-library marketplace or saved template management.
- No durable history beyond current-session preview state unless explicitly
  pulled into this slice.

## Locked Product Decisions

- The first HTML/CSS batch cap counts source HTML documents/project entries:
  up to 10 HTML sources. CSS files are styling support and are capped at 10
  files for the first product version.
- Linked images are allowed when referenced by filename inside the uploaded
  project boundary. The renderer must resolve them safely without exposing raw
  filesystem paths or allowing path traversal.
- Fonts should use a broad available font set and graceful fallback mapping
  where requested fonts are unavailable.
- Output mode must support separate PDFs, one combined PDF, or both.
- Preview PDFs are short-lived temporary server artifacts with an initial target
  TTL of 24 hours. `Mina filer` save happens only after explicit teacher action.
- First template controls should use templates that already exist or are
  deliberately created for this product, starting with the academic/PhD-style
  template and a small expressive curated set. Final labels wait for the copy
  approval package.

## Contract Questions To Close

- Exact project manifest/request shape for HTML, CSS, images, and other assets.
- First asset count and total-size caps for linked images and fonts.
- Exact response shape for separate, combined, and both output modes.
- Exact temporary-artifact storage location and cleanup worker for the 24-hour
  TTL.
- The first concrete template inventory and internal template identifiers.

## Red-First Proof Plan

- Contract red: current backend cannot represent HTML/CSS project inputs.
- Contract red: current backend cannot request a render-only preview before
  save/download.
- Contract red: PDF controls are not represented for the preview request.

## Green Proof Plan

- Focused backend/application tests for project validation, render request,
  progress/status, preview readiness, discard/regenerate, and PDF controls.
- Type/schema refresh if API contracts change.
- Focused frontend contract tests only if non-route-visible client helpers are
  added.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check` if generated frontend types change
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Notes

Implemented route-inactive preview contract prepared for review on 2026-06-25:

- Added the first HTML/CSS project manifest contract with up to 10 HTML entries,
  up to 10 CSS files, up to 20 image assets, and zero uploaded font files for
  the first version. Fonts rely on server-available fallback stacks through the
  selected template CSS rather than uploaded font authority.
- Added PDF controls for paper size, orientation, per-side margins, and first
  internal template identifiers: `academic_phd`, `clean_worksheet`, and
  `expressive_handout`. No Swedish user-facing labels or UI copy were added.
- Added output modes `separate_pdfs`, `combined_pdf`, and `both`. Preview
  responses return server-issued `preview_id` plus artifact ids, filenames,
  content types, sizes, source entry ids, 24-hour `expires_at`, and no raw
  filesystem paths or browser-authored artifact references.
- Added the scoped backend API under
  `/api/v1/apps/documents.conversion_hub/document-converter/project-previews`.
  It supports render/status/download/discard and explicit save-to-`Mina filer`
  by `{preview_id, artifact_id}` only. `/apps/document-converter` remains
  inactive.
- Added an in-memory WeasyPrint project renderer using `project:///` as the
  base URL and a constrained fetcher. Relative CSS/images resolve only by
  manifest-declared bare filename; `file://`, HTTP(S), path traversal, nested
  paths, undeclared filenames, unsupported image suffixes, and uploaded fonts
  fail closed.
- Added filesystem temporary preview storage under the existing artifacts root,
  owner-scoped by user id and preview id, with discard support and a
  cron-friendly `pdm run cleanup-document-converter-project-previews`
  maintenance surface for the 24-hour target TTL. API responses expose only
  server-owned ids and metadata.
- Extracted a shared Document Converter Vault save service so existing
  single-result saves and new project-preview saves use the same quota,
  rollback, and `APP_EXPORT` behavior.
- Regenerated OpenAPI-derived frontend types because the scoped API schema
  changed. No production frontend route, card, mockup, or copy was added.

Repair notes after `REV-PR-0382` changes requested:

- Added the production cleanup entrypoint
  `cleanup-document-converter-project-previews`, registered in Typer and PDM,
  which invokes the application cleanup handler over
  `Settings.ARTIFACTS_ROOT`.
- Hardened filesystem preview persistence so artifacts and metadata are staged
  before atomic publish; metadata-write failures roll back staged bytes, and
  cleanup now removes expired, malformed, no-metadata, and leftover staging
  preview directories.
- Published the preview download route as an explicit `application/pdf`
  binary OpenAPI response and regenerated the OpenAPI-derived TypeScript types.

## Verification Evidence

Red-first evidence before production implementation:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py` | Failed during collection with 4 `ModuleNotFoundError` errors because `skriptoteket.application.curated_apps.document_converter_projects` did not exist. This proved the current backend could not represent HTML/CSS project preview contracts. |

Green evidence after implementation:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py` | Passed: 32 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Passed: 28 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py` | Passed: 33 tests, proving adjacent Exam Converter and Audio Transcription behavior remained unchanged. |
| `pdm run fe-gen-api-types` | Passed; regenerated the scoped OpenAPI TypeScript surface. |
| `pdm run lint` | Passed. |
| `pdm run typecheck` | Passed. |
| `pdm run fe-type-check` | Passed. |
| `pdm run docs-validate` | Passed after docs closeout. |
| `pdm run handoff-validate` | Passed after handoff closeout. |
| `git diff --check` | Passed. |

Repair red-first evidence after `REV-PR-0382`:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/cli/test_cleanup_document_converter_project_previews.py` | Failed: 1 failed because Typer reported `No such command 'cleanup-document-converter-project-previews'`. |
| `pdm run test tests/unit/infrastructure/documents/test_document_converter_project_previews.py` | Failed: 2 failed, 12 passed. Metadata-write failure left the preview directory behind, and malformed/orphan cleanup returned `deleted_previews=0` instead of `2`. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py::test_project_preview_download_openapi_contract_is_pdf_binary` | Failed: 1 failed because `/openapi.json` exposed `application/json` instead of `application/pdf` for preview download. |

Repair green evidence:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/cli/test_cleanup_document_converter_project_previews.py` | Passed: 1 test; the CLI command deleted the expired preview directory and kept the active one. |
| `pdm run cleanup-document-converter-project-previews --artifacts-root .artifacts/pr-0382-cleanup-empty-proof` | Passed; PDM wrapper invoked the production cleanup surface and reported `deleted_previews=0 deleted_artifacts=0` on an empty override root. |
| `pdm run test tests/unit/infrastructure/documents/test_document_converter_project_previews.py` | Passed: 14 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py::test_project_preview_download_openapi_contract_is_pdf_binary` | Passed: 1 test. |
| `pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py tests/unit/cli/test_cleanup_document_converter_project_previews.py` | Passed: 36 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Passed: 28 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py` | Passed: 33 tests. |
| `pdm run fe-gen-api-types` | Passed; regenerated `frontend/apps/skriptoteket/src/api/openapi.d.ts` with preview download as `application/pdf`. |
| `pdm run lint` | Passed after import-order repair. |
| `pdm run typecheck` | Passed. |
| `pdm run fe-type-check` | Passed. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |

## Stop Condition Check

- Linked assets are sandboxed through manifest-declared bare filenames and the
  custom `project:///` fetcher.
- Preview APIs do not expose raw filesystem paths or accept browser-supplied
  artifact bytes/keys for download or save.
- No route-visible UI, Swedish copy, mockup implementation,
  `/apps/document-converter` activation, template marketplace, durable history,
  or `PR-0369` reopening was added.

## Stop Conditions

- Stop if rendering needs a route-visible UI decision or copy approval.
- Stop if the implementation cannot safely sandbox linked assets.
- Stop if a proposed preview model exposes raw filesystem paths, producer
  credentials, or browser-supplied artifact authority.

## Rollback Plan

Remove the project-preview contract, preview state, tests, generated types, and
docs updates. Keep the `PR-0381` batch/local-heavy foundation intact.
