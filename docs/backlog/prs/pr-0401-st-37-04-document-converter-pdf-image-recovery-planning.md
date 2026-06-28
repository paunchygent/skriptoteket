---
type: pr
id: PR-0401
title: "ST-37-04 Document Converter PDF image recovery planning"
status: done
owners: "agents"
created: 2026-06-27
updated: 2026-06-28
stories:
  - "ST-37-04"
tags:
  - backend
  - contracts
  - document-converter
  - sir-convert
dependencies:
  - "PR-0400"
acceptance_criteria:
  - "Given PDF-to-DOCX conversion can lose or flatten embedded images, when this planning slice closes, then Skriptoteket and Sir Convert have a governed implementation route for recovering real image bytes without preserving placeholder metadata as a false promise."
  - "Given image extraction from rendered PDFs can become a time sink, when the plan is accepted, then it records the stop conditions that separate feasible source/extracted-byte reinsertion from unsupported layout reconstruction."
  - "Given Sir Convert already owns heavy PDF extraction paths, when the plan closes, then any required Sir Convert upstream task is linked and the Skriptoteket boundary only promises recovered images when a concrete recovery manifest and bytes exist."
---

# PR-0401: ST-37-04 Document Converter PDF Image Recovery Planning

## Problem

`PR-0400` explicitly rejects preserving missing-image metadata in final
teacher-facing conversion artifacts when no real bytes can be recovered. That
does not remove the product need: teachers may still expect PDF-to-DOCX and
PDF-to-Markdown conversions to carry over embedded images when the conversion
stack can do so honestly.

## Goal

Plan the future image-recovery implementation path without smuggling it into
artifact-hygiene remediation:

- identify which PDF image cases are realistically recoverable from source
  bundles, embedded PDF resources, or Sir Convert extraction manifests;
- define the manifest/sidecar contract that links recovered image bytes to
  converted Markdown/HTML/DOCX insertion points;
- define stop conditions for layout-aware DOCX reconstruction that is too
  brittle or too expensive for the current product lane;
- link any required Sir Convert upstream task and define Skriptoteket's
  consumer boundary.

## Research Findings

Read-only research on 2026-06-28 found that the current Sir Convert PDF route
does not yet expose a stable product contract for recovered image bytes:

- Sir Convert currently executes PDF routes as
  `PDF -> checkpointed Markdown -> optional Pandoc HTML/DOCX`. The v2 executor
  delegates `pdf -> md` and `pdf -> docx` through
  `execute_pdf_to_markdown_with_checkpoints_v2`, then for DOCX writes an
  intermediate Markdown/HTML pair named `pdf_checkpointed_output.*` before
  Pandoc produces the final DOCX. See upstream
  `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`,
  `v2_pdf_checkpointed_executor.py`, and `v2_non_pdf_helpers.py`.
- Existing PDF checkpoints are chunk-level Markdown state. They record chunk
  relpaths, page spans, hashes, size, backend, OCR state, warnings, timings,
  and formula authority. They do not record PDF image xrefs, extracted image
  bytes, image artifact keys, page/bbox placement, or Markdown/HTML insertion
  refs. See upstream `pdf_checkpoints_v2.py`.
- Current PyMuPDF-backed PDF conversion uses `pymupdf4llm.to_markdown(...)`
  and does not materialize image sidecars. Context7/PyMuPDF docs confirm the
  library can extract embedded image bytes from a PDF image xref with
  `Document.extract_image(xref)`, returning image bytes plus metadata such as
  extension, width, height, colorspace, resolution, and soft-mask xref, but
  that API does not solve editable-document placement or insertion refs by
  itself.
- Pandoc can carry real local resources into DOCX when HTML references local
  files and the service provides a resource path. Sir Convert already passes a
  resource root to HTML-to-DOCX conversion, but no current PDF stage creates a
  resources directory or links extracted images from terminal Markdown/HTML.
- Sir Convert v2 already has an `md`/`html` resources-bundle concept, but the
  current API docs reject resources for `pdf -> md`. Therefore PDF image
  recovery must be an upstream PDF-output contract, not a client-side
  re-upload trick.
- Skriptoteket Document Converter currently consumes one terminal producer
  artifact for each Sir Convert-backed file conversion. It can download generic
  named upstream artifacts through the client protocol, but the Document
  Converter handler has no recovery-manifest parser, no recovered-image
  sidecar model, and no product promise for image recovery.

Existing upstream authority:

- Sir Convert
  `docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md`
  is the required upstream anchor. It already proposes terminal-only companion
  bundles for PDF-to-Markdown jobs with `artifact-manifest.json`,
  `assets/images/...`, relative Markdown image links, privacy rules, and no
  checkpoint-time companion leakage.
- That task is not sufficient by itself to promise PDF-to-DOCX image recovery
  in Skriptoteket. PR-0401 therefore treats Task 272 as the prerequisite
  manifest/artifact contract and requires either an amendment to Task 272 or a
  successor Sir Convert task before DOCX media reinsertion can become
  user-visible product behavior.

## Planning Decision

Sir Convert owns PDF image recovery. It must extract real bytes, assign stable
image identity, retain recovered image artifacts, produce a recovery manifest,
and insert source-derived resource references into Markdown/HTML before DOCX
generation when the route claims recovered images.

Skriptoteket owns only the consumer boundary:

- request routing and producer selection;
- strict parsing/validation of any Sir Convert recovery manifest;
- teacher-facing status/copy after a supported upstream contract exists;
- download/save fail-closed behavior when a claimed recovered image is missing,
  hash-mismatched, or not bound to real bytes.

Skriptoteket must not reconstruct PDF layout, mutate DOCX media after the
terminal artifact arrives, or preserve missing-image metadata as a promise that
images can be restored later.

## Feasible Routes

1. Sir Convert recovered-image manifest plus upstream reinsertion.
   Recommended first implementation route. Sir Convert extracts real image
   bytes, creates deterministic relative resource paths, inserts references in
   Markdown/HTML, and lets Pandoc carry media into DOCX. Skriptoteket validates
   the terminal artifact and optional manifest summary.
2. Sir Convert companion bundle consumed by Skriptoteket for proof/status only.
   Useful for reporting that images were recovered, but not enough for DOCX
   reinsertion unless the upstream terminal DOCX already contains the media.
3. PDF-to-Markdown/HTML resources bundle.
   Viable only after Sir Convert extends the PDF route contract. The current
   resources upload contract applies to `md`/`html` inputs, not PDF-source
   recovery.
4. Full PDF layout reconstruction into DOCX.
   Not recommended. It is a separate visual-facsimile product route, not a
   safe extension of the current editable document conversion lane.
5. No recovery.
   Correct behavior when no real bytes exist, bytes cannot be tied to insertion
   evidence, or extraction evidence is diagnostic only. In this case the output
   remains clean and does not include placeholders or implied recovery metadata.

## Recovery Manifest Shape

A future Sir Convert recovery manifest should be terminal-only and include:

- `schema_version`
- `job_id`
- `source_sha256`
- `output_format`
- `pipeline`
- `recovery_status`: `recovered`, `partial`, or `unavailable`
- `images[]`

Each image entry should include:

- deterministic `image_id`
- `page_number`
- `source_kind`: for example `pdf_xobject`, `rendered_region`, or
  `producer_artifact`
- optional `pdf_xref`
- `occurrence_index`
- optional `bbox` plus coordinate space when placement evidence is reliable
- `media_type`
- `extension`
- `size_bytes`
- `sha256`
- retrieval path or named artifact key
- terminal-document insertion refs, when available
- `status` and safe `unavailable_code`

The manifest must use only relative paths or named artifact keys, never private
source roots, original private filenames, workdirs, OCR excerpts, raw job ids
in visible content, or checkpoint-only paths.

## Stop Conditions

- No real bytes: no recovered image entry and no placeholder metadata.
- Real bytes without trustworthy insertion evidence: diagnostic/companion
  artifact only; no DOCX reinsertion claim.
- Hash mismatch, missing named artifact, unsafe path, unsupported media type,
  or manifest schema mismatch: fail closed before teacher-facing download/save
  claims image recovery.
- Rendered page snapshots or bbox crops are unsupported for the editable DOCX
  lane unless a later approved visual-facsimile product route accepts that
  tradeoff.
- Upstream checkpoint or partial artifacts must not expose terminal companion
  paths before finalization.

## Follow-On Implementation Shape

The next implementation work should happen upstream first:

1. Sir Convert Task 272 or a successor task adds/extends a terminal recovered
   image manifest and companion bundle for PDF outputs, with synthetic fixture
   PDFs containing text plus embedded PNG/JPEG assets.
2. Sir Convert proves stable image ids and SHA-256 hashes across reruns,
   downloadable recovered bytes, relative safe paths, no checkpoint-time
   companion leakage, and DOCX ZIP media under `word/media/*` only when terminal
   DOCX recovery is claimed.
3. Skriptoteket adds a narrow consumer slice only after that upstream contract
   exists: strict manifest parsing, optional status display, and fail-closed
   artifact download/save when manifest claims cannot be verified.

## Non-goals

- No implementation in this planning slice.
- No placeholder preservation as a substitute for recovered image bytes.
- No promise that every PDF image can be reinserted into DOCX.
- No broad PDF-to-DOCX layout engine rewrite.

## Implementation Plan

1. Treat Sir Convert Task 272 as the linked upstream prerequisite for recovered
   image artifacts and companion bundle semantics.
2. Amend or follow Task 272 before implementation if DOCX media reinsertion is
   required; do not let Skriptoteket promise DOCX image recovery from the
   current single-artifact API.
3. Keep Skriptoteket fail-closed until a concrete recovery manifest and bytes
   are present.
4. Use the recovery manifest shape and stop conditions above for the future
   implementation task.
5. Keep this slice docs-only and close it with review, docs validation, and
   diff hygiene.

## Test Plan

- No code tests in this planning slice.
- Planning close-out requires retained review, `pdm run docs-validate`,
  `pdm run handoff-validate`, and `git diff --check`.

## Verification Notes

- Research completed through an independent read-only subagent on 2026-06-28.
  Findings were verified against focused Sir Convert PDF checkpoint/Pandoc
  code, Skriptoteket Document Converter artifact-consumer code, and
  Context7/PyMuPDF docs before this planning doc was updated.
- Retained review:
  `docs/backlog/reviews/review-pr-0401-document-converter-pdf-image-recovery-planning.md`
  with verdict `approved`.
- Close-out validation:
  `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`.

## Rollback Plan

Remove this planning PR slice and leave `PR-0400`'s fail-closed artifact hygiene
contract as the active behavior until a new recovery plan is approved.
