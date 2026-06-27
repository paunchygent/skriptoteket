---
type: pr
id: PR-0385
title: "ST-37-04 Document Converter files and result-state follow-up"
status: in_progress
owners: "agents"
created: 2026-06-23
updated: 2026-06-26
stories:
  - "ST-37-04"
tags:
  - document-converter
  - mina-filer
  - result-state
dependencies:
  - "PR-0382"
  - "PR-0384"
acceptance_criteria:
  - "Given a teacher is signed in, when Document Converter source selection is opened, then only that teacher's compatible saved PDF, DOCX, Markdown, and HTML files from `Mina filer` are offered."
  - "Given a teacher selects a compatible saved file, when conversion or preview starts, then the backend reads the file server-side by an owner-scoped file reference and the browser never becomes artifact authority."
  - "Given a saved file belongs to another owner or is deleted/missing, when Document Converter tries to use it as a source, then the backend fails it as not found/forbidden."
  - "Given the teacher uses local upload or `Mina filer` selection, when conversion/preview runs, then both sources enter the same conversion/preview workflow rather than parallel product code paths."
  - "Given a preview or conversion completes during the current route session, when the teacher continues working in the route, then the current usable result remains available for preview, download, save, or retry without exposing a history rail or pretending durable job history exists."
  - "Given a later preview/conversion fails, when a previous successful result exists in the current session, then the failure does not overwrite the last successful usable result."
  - "Given an output is saved to `Mina filer`, when the save succeeds, then the saved record has a stable display name, source reference, content type, and size/hash where available."
  - "Given the same output is saved more than once, when the teacher saves again, then the app creates another saved file record with the same stable source reference rather than pretending to update an existing project."
---

# PR-0385: ST-37-04 Document Converter Files And Result-State Follow-up

## Problem

Local upload and preview should be proven first. The product should still be
plumbed so teacher-owned source selection and re-entry from saved files can be
added immediately after the upload/preview path is stable.

## Goal

Implement the first `Mina filer` source selector and current-session result
state follow-up after the route-visible MVP proved the core workflow. This
slice has two implementation goals plus one explicit decision boundary.

## Decisions Closed For This Slice

- `PR-0384` and `PR-0388` satisfied the route-visible upload and preview
  blockers.
- First `Mina filer` sources are single-file only: PDF, DOCX, Markdown, and
  HTML.
- Unsupported saved files are hidden from Document Converter source selection.
- Route-local continuity is current-result state only. It must keep the current
  usable result and retry action available, but it must not expose a history
  rail, recent-job list, or durable-history language in the visible UI.
- The mode selector is a tab strip above the mode-specific workspace, not an
  in-workspace rail selector. The teacher-facing modes are `HTML/CSS-projekt`
  and `Filkonvertering`.
- Local file conversion may submit an ordered batch of up to 10 local files
  through the existing backend batch upload contract. Multi-source `Mina filer`
  refs and combined/concatenated file-conversion outputs remain deferred until
  their server-side contract is defined.
- Saving the same generated output twice creates another saved file record with
  the same stable source reference. The app does not silently update an earlier
  saved file.
- Reopening a saved output means using that saved file as a new source when its
  file type is supported. It does not restore a project workspace.

## Implementation Goal 1: `Mina filer` As Source

A teacher should be able to start Document Converter from an owner-scoped saved
file in `Mina filer`, without downloading and re-uploading it manually.

Verifiable behavior:

- Only the signed-in teacher's compatible saved files are selectable.
- Unsupported saved files are not offered as Document Converter inputs.
- Backend conversion reads saved files server-side by scoped file reference.
- The browser does not provide saved-file bytes back to the backend.
- Local upload and `Mina filer` selection feed the same conversion/preview
  workflow.
- Cross-owner file ids fail as not found/forbidden.

## Implementation Goal 2: Current Result State

The app should remember the useful current conversion/preview result during the
current route session so the teacher can preview it, download it, save it, or
retry without the interface pretending there is durable history or showing a
recent-job rail.

Verifiable behavior:

- Current-result state is created from completed previews/jobs.
- The current usable result survives normal in-route interaction but makes no
  durable-history promise.
- Visible result state exposes only teacher-meaningful facts: filename, result
  type, ready/failed state, and available actions.
- No raw preview ids, artifact ids, producer names, paths, TTLs, or `artifact`
  language appears in visible UI.
- Failed previews do not overwrite the last successful usable result.
- No visible `Historik`, `Arbetssätt`, `Aktuell källa`, or `Inget resultat än`
  labels appear in the route-visible UI.

## Decision Boundary: Save/Reopen

When a PDF is saved to `Mina filer`, the user gets a trustworthy saved file
record. PR-0385 does not promise full "reopen this exact project and regenerate
with all linked assets" behavior unless a later slice defines saved project
manifests and asset bundles.

Verifiable behavior:

- Saved outputs have stable names, source references, content type, and
  size/hash where available.
- Batch/separate outputs have predictable saved names.
- Saving the same result twice creates another saved file record with a stable
  source reference.
- Reopen from saved output means "use this saved file as a new source" where
  supported, not "restore the whole project workspace."

## Non-goals

- No durable per-user Document Converter job history.
- No visible route-session history rail or recent-job list.
- No public file source selection.
- No multi-file HTML/CSS project source selection from `Mina filer`.
- No multi-source `Mina filer` conversion batch until the backend accepts
  multiple scoped refs in one request.
- No combined/concatenated general file-conversion output until the backend
  owns the combined artifact contract.
- No saved project/package model, project manifest persistence, asset bundle
  restore, or "reopen exact workspace" promise.
- No artifact-observability language in user-facing UI.
- No `PR-0369` app-presentation contract expansion.

## Implementation Plan

- Add a backend-owned saved-file source surface that lists only compatible
  active owner files and submits a scoped Vault ref through the existing
  Document Converter job path.
- Extend the route with a `Filkonvertering` mode for local upload or `Mina filer`
  while preserving the existing HTML/CSS project preview mode.
- Keep current preview/job result state route-local so teachers can use the
  latest usable result, download it, save it, or retry from the same route
  session without seeing job history.
- Move mode selection into a tab strip above the mode-specific workspace and
  keep source/output controls inside the selected mode.
- Let local upload file conversion submit an ordered batch of up to 10 files
  where the existing backend batch contract already supports it.

## Test Plan

- Red-first backend/API tests for owner-scoped compatible saved-file selection,
  unsupported saved-file filtering, server-side saved-file conversion, and
  cross-owner/deleted file rejection.
- Red-first frontend tests for `Mina filer` source selection, shared
  conversion/preview flow, teacher-facing current-result state, ordered local
  upload batches, and forbidden raw identifier/artifact/history language.
- Focused save/reopen contract tests for stable saved names/source references
  and duplicate-save behavior.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Proof

Implemented locally on 2026-06-26.

- Backend now exposes `/api/v1/apps/documents.conversion_hub/document-converter/saved-files`
  and `/saved-files/jobs`, filters compatible owner-scoped Vault sources
  server-side, validates Vault refs/ownership/active state, reads bytes from
  `VaultStorageProtocol`, and reuses `CreateDocumentConverterJobsHandler`
  instead of browser re-upload.
- Frontend `/apps/document-converter` now keeps the original HTML/CSS project
  preview lane and adds a `Filkonvertering` lane for local upload or
  `Mina filer`, backed by the new scoped saved-file APIs.
- Correction pass on 2026-06-27 removes the visible history rail and inner
  `Arbetssätt` selector, replaces them with mode tabs above the workspace,
  removes redundant empty-result labels, changes result control language to
  `Källformat` / `Exportformat`, and keeps current-result state as a private
  route-local continuity mechanism.
- Local upload file conversion now accepts an ordered batch of up to 10 local
  files through the existing upload job contract. `Mina filer` remains
  single-source until a multi-ref saved-source request contract exists.
- Follow-up review remediation on 2026-06-26 tightened route-session history
  truthfulness without expanding naming scope: project-mode history now treats
  only the active live preview entry as live state, older HTML/CSS history
  selections reload their own preview blob and actions, and single-file polling
  leaves nonterminal queued/running jobs pending instead of recording a false
  failure. Cross-app save/export naming stays deferred to a later governed
  slice.
- Focused red-first proof was captured before implementation:
  `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py`
  failed with `ModuleNotFoundError` for the missing saved-source handler, and
  `pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  failed because the single-file API module and route surface did not exist.
- Focused red-first proof for the retained review remediation:
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  failed because selecting an older HTML/CSS history entry still left the view
  showing the newer live preview result, and
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  failed because a queued/running job past the polling budget was shown as
  `Misslyckades` instead of staying pending.
- Focused red-first proof for the sole-reviewer follow-up findings:
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  failed because a reopened older `separate_pdfs` history result lost its
  artifact selector, and
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  failed because an immediately succeeded local conversion never fetched job
  status and was recorded as failed.
- Final focused green proof:
  `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py`,
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/documentConverterFileApi.spec.ts`,
  `pdm run lint`,
  `pdm run typecheck`,
  `pdm run fe-type-check`,
  `pdm run fe-lint`,
  `pdm run fe-build`,
  `pdm run docs-validate`,
  `pdm run handoff-validate`,
  and `git diff --check`.
- Final live authenticated route proof passed after recovering the local
  shared-auth lane and updating retained proof helpers to match the current
  browser-auth and quiet auto-preview contracts:
  `pdm run run-local-pdm auth-integration check`,
  `pdm run test tests/unit/test_docker_dev_shared_auth_contract.py`,
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`, and
  `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90`.
  Green artifact:
  `.artifacts/authenticated-home-work-apps/20260626T223707Z/manifest.redacted.json`.
  It records authenticated desktop and compact route captures, blob-backed
  preview iframes, auto-render/refresh, downloaded PDFs rendered to PNG, expected
  heading/callout/caption/missing-resource text, visible CSS/image accents, and
  no raw external URL or filesystem path text.

## Rollback Plan

Remove the files/history extensions and keep the route-visible MVP on local
upload plus current-session state.
