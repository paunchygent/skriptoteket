---
type: pr
id: PR-0404
title: "ST-37-04 Document Converter multi-source saved-file batches"
status: done
owners: "agents"
created: 2026-06-28
updated: 2026-06-28
stories:
  - "ST-37-04"
tags:
  - backend
  - frontend
  - document-converter
  - mina-filer
  - batch
dependencies:
  - "PR-0385"
  - "PR-0396"
  - "PR-0399"
  - "PR-0400"
acceptance_criteria:
  - "Given a teacher selects multiple compatible files from `Mina filer`, when the batch is submitted, then the backend reads each file server-side by owner-scoped Vault refs, preserves the selected order, and creates one Document Converter job per source file."
  - "Given a saved-file batch is submitted, when the refs are empty, duplicated, cross-owner, deleted, missing on disk, unsupported, mixed-source-format, or more than 10 items, then the whole batch is rejected before any conversion job is created."
  - "Given the saved-file batch succeeds, when results are shown in Document Converter, then each source produces a separate output artifact using the existing result/artifact selector without promising combined or concatenated output."
  - "Given batch outputs are downloaded or saved, when filename stems are edited or saves are repeated, then protected API filename authority, extension preservation, source provenance, and repeated-save disambiguation from `PR-0396` still apply."
  - "Given a teacher uses the `Mina filer` picker in `Filkonvertering`, when several saved files are selected, then the UI supports selection, ordering, and removal without browser-uploading saved bytes or exposing raw refs, job ids, artifact ids, producer names, paths, or history language."
  - "Given the retained authenticated proof runs, when it exercises a `Mina filer` batch, then it proves the shared-auth route can select at least two saved files, submit them, receive separate outputs, and save/download at least one output without forbidden artifact-hygiene markers."
---

# PR-0404: ST-37-04 Document Converter Multi-Source Saved-File Batches

## Problem

`PR-0385` added the first owner-scoped `Mina filer` source path for Document
Converter, but it intentionally kept saved-file conversion single-source while
local uploads already accept ordered batches of up to 10 files. Teachers should
not have to repeat the same conversion one saved file at a time when the same
batch shape already exists for local uploads.

The follow-up must deepen Document Converter's app-specific saved-source
facade without rewriting core `Mina filer` or pretending saved outputs restore
project workspaces.

## Goal

Implement ordered multi-source `Mina filer` batches for `Filkonvertering`.

The batch contract is:

- selected sources are owner-scoped Vault refs only;
- the browser submits refs, never saved-file bytes;
- all sources must infer to the same supported source format;
- the max batch size is 10, matching local uploads;
- each source creates one existing Document Converter job and one separate
  output artifact;
- any invalid ref fails the whole batch before job creation.

## Product Decisions Closed For This Slice

- Saved-file batches are limited to one source format per batch.
- Saved-file batches share the local-upload maximum of 10 sources.
- Any invalid saved-file ref fails the whole batch; no partial conversion.
- Duplicate saved-file refs are rejected.
- The first slice produces separate outputs only.
- The current compatible-list picker may become an ordered multi-select, but
  search, sort, pagination, folders, tags, and shared picker extraction are out
  of scope.
- Saved project/package restoration remains out of scope.

## Non-goals

- No core `Mina filer` data-model rewrite.
- No shared `Mina filer` picker extraction.
- No `Mina filer` search, sort, pagination, folders, tags, or open-with
  behavior.
- No saved HTML/CSS project package model, manifest persistence, asset-bundle
  restore, or "restore workspace" promise.
- No combined or concatenated general file-conversion output.
- No mixed-source-format batch conversion.
- No Sir Convert status-vocabulary changes.
- No artifact-hygiene marker scrubbing; `PR-0400` fail-closed behavior remains
  the boundary.
- No `PR-0369` app-presentation backend/API expansion.

## Implementation Plan

1. Replace the Document Converter saved-file request contract's single
   `source_ref` payload with required ordered `source_refs`.
2. Add application-layer validation for empty refs, duplicate refs, count > 10,
   non-Vault refs, cross-owner refs, deleted refs, missing storage bytes,
   unsupported source formats, and mixed source formats.
3. Load all saved files server-side through owner-scoped Vault repository and
   storage protocols, preserve request order, and build one
   `ConversionHubUpload` per saved file.
4. Reuse `CreateDocumentConverterJobsHandler` so saved-file batches and local
   upload batches share producer routing, job creation, artifact storage,
   result polling, and hygiene validation.
5. Update the protected API route, generated OpenAPI types, and frontend API
   client so saved-file submissions post refs only.
6. Replace the single saved-file select in `Filkonvertering` with an ordered
   multi-select/list that supports selection, remove, and move up/down using
   the existing Document Converter source-column grammar.
7. Keep multiple saved-file results in the existing mode-scoped result state and
   artifact selector so downloads, saves, retries, and filename stems continue
   through the backend-authoritative `PR-0396` contract.
8. Extend retained authenticated proof to seed or use at least two compatible
   saved files, submit them through `Mina filer`, observe separate outputs, and
   save/download at least one artifact.

## Test Plan

- Red-first backend application test:
  `SubmitDocumentConverterSavedFileHandler` accepts ordered `source_refs`,
  reads Vault bytes server-side, preserves selected order, and returns one job
  per saved source.
- Red-first backend negative tests for empty refs, duplicate refs, >10 refs,
  non-Vault refs, cross-owner refs, deleted refs, missing-on-disk refs,
  unsupported file types, mixed source formats, and job-creation all-or-nothing.
- Red-first API test proving `/saved-files/jobs` accepts refs only, never
  multipart/browser bytes, and returns the same batch response shape as local
  uploads.
- Red-first frontend API test proving `source_refs` are posted in UI order.
- Red-first frontend component/state tests proving `Mina filer` multi-select,
  order, remove, source-format inference, same-format rejection, and
  multi-output result selector behavior.
- Red-first forbidden-UI-language tests or assertions extending existing
  Document Converter coverage so saved-file batches do not expose raw refs,
  job ids, artifact ids, producer names, paths, or durable-history/project
  restore language.
- Focused green commands:
  - `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py`
  - `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
  - `/opt/homebrew/bin/pdm run fe-gen-api-types`
  - `/opt/homebrew/bin/pdm run lint`
  - `/opt/homebrew/bin/pdm run typecheck`
  - `/opt/homebrew/bin/pdm run fe-type-check`
  - `/opt/homebrew/bin/pdm run fe-lint`
  - `/opt/homebrew/bin/pdm run fe-build`
  - `/opt/homebrew/bin/pdm run docs-validate`
  - `/opt/homebrew/bin/pdm run handoff-validate`
  - `git diff --check`
- Live authenticated proof through the HuleEdu browser-session ceremony and
  Docker `skriptoteket_web` backend lane. Record retained artifact paths in
  this PR and `.codex/handoff.md`.

## Verification Notes

- Implemented locally on 2026-06-28. Backend accepts required ordered
  `source_refs`, rejects the retired single `source_ref` request shape,
  validates the whole saved-file batch before job creation, reads saved bytes
  server-side from owner-scoped Vault storage, and reuses
  `CreateDocumentConverterJobsHandler` to create one ordered Document
  Converter job per saved file.
- Batch validation now rejects empty refs, duplicate refs, more than 10 refs,
  non-Vault refs, cross-owner/deleted/missing metadata, missing-on-disk files,
  unsupported file types, mixed source formats, and source-format mismatches
  before any conversion job is created.
- Frontend `Mina filer` selection now supports appending compatible saved
  files, visible order, remove, move up/down, same-format checks, duplicate and
  count guards, and posts refs only in the visible order.
- Red-first backend evidence:
  `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py`
  failed because the handler did not accept `source_refs` and the API model
  still required `source_ref`.
- Red-first frontend evidence:
  `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts`
  failed because the client posted `source_ref` and the UI retained only one
  saved-file selection.
- Green focused backend:
  `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py`
  passed with `15 passed`.
- Green focused frontend:
  `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts`
  passed with `25 passed`.
- Additional green gates: `/opt/homebrew/bin/pdm run fe-gen-api-types`,
  `/opt/homebrew/bin/pdm run lint`, `/opt/homebrew/bin/pdm run typecheck`,
  `/opt/homebrew/bin/pdm run fe-type-check`, `/opt/homebrew/bin/pdm run fe-lint`,
  and `/opt/homebrew/bin/pdm run fe-build`.
- Review remediation red-first evidence:
  `/opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py -k saved_file_request`
  failed because the retired `source_ref`-only payload still validated.
- Review remediation green evidence:
  `/opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_saved_file_contract.py`
  passed with `1 passed`, and regenerated OpenAPI no longer advertises
  `source_ref`.
- Franklin review remediation was accepted after
  `REV-PR-0404` / independent GPT-5.5 XHigh requested changes. The frontend
  now has red-first coverage for succeeded result artifacts with
  `filename: null` or a missing filename, and
  `documentConverterSingleFileSubmission.ts` fails closed instead of using a
  raw job id as a visible output label. The independent rereview approved the
  full PR after this remediation.
- Live authenticated browser proof is green:
  `/opt/homebrew/bin/pdm run python -m scripts.authenticated_home_work_apps --base-url http://localhost:5173 --viewport compact`
  wrote
  `.artifacts/authenticated-home-work-apps/20260628T173523Z/manifest.redacted.json`.
  The manifest records two seeded compatible PDF sources selected from
  `Mina filer`, visible order changed to source B before source A, refs-only
  ordered batch submission, two separate Markdown outputs, one downloaded
  Markdown artifact, one saved result with HTTP `200`, and no forbidden marker
  hits.

## Overseer Verifiable Goals

An overseer can close this PR only when all of these are true:

1. Backend saved-file batch submission accepts ordered `source_refs`, creates
   one job per saved file, preserves order, and never accepts browser-supplied
   saved-file bytes.
2. Backend validation fails the whole request before job creation for empty,
   duplicate, non-Vault, cross-owner, deleted, missing-on-disk, unsupported,
   mixed-source-format, or >10 saved-file refs.
3. The frontend `Mina filer` source UI supports selecting several compatible
   saved files, ordering them, removing them, and submitting refs in visible
   order while retaining the current left-source / middle-operations /
   right-preview layout grammar.
4. Multiple saved-file outputs are represented as separate outputs in the
   existing Document Converter result/artifact selector, with no combined-output
   promise and no durable project-restore/history language.
5. Download and save actions for every saved-file batch output keep the
   `PR-0396` backend-authoritative filename, extension, content type,
   provenance, and repeated-save disambiguation behavior.
6. Artifact hygiene remains fail-closed: teacher-facing batch outputs do not
   expose `PR-0400` forbidden markers, raw artifact ids, temp stems, producer
   names, paths, or implementation-detail metadata.
7. Focused backend, frontend, type/lint/build, docs, handoff, and diff hygiene
   gates pass with exact commands recorded in the PR.
8. A retained authenticated browser proof exercises a real `Mina filer` batch
   with at least two saved files and records separate output, save/download, and
   forbidden-language/marker checks.
9. A retained review artifact approves the implementation after the reviewer
   verifies the tests, contracts, UI behavior, and proof evidence.

## Rollback Plan

Revert the saved-file batch request/UI changes and keep `Mina filer` source
conversion on the single-ref `PR-0385` contract while preserving local-upload
batch behavior.
