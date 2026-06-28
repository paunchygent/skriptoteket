---
type: review
id: REV-PR-0401
title: "Review: PR-0401 Document Converter PDF image recovery planning"
status: approved
owners: "agents"
created: 2026-06-28
updated: 2026-06-28
reviewer: "codex-independent-planning-reviewer"
prs:
  - "PR-0401"
links:
  - "ST-37-04"
  - "EPIC-37"
  - "PR-0400"
---

# Review: PR-0401 Document Converter PDF Image Recovery Planning

## Findings

No findings.

## TL;DR

`approved`. `PR-0401` is sufficient as a docs-only planning slice because it
defines an upstream-first real-byte recovery route, keeps Skriptoteket
fail-closed until a concrete Sir Convert manifest and bytes exist, and avoids
promising DOCX image recovery from the current single-artifact API.

## Verdict

`approved`

`PR-0401` is sufficient as a docs-only planning slice because it converts the
PDF image-recovery concern left by `PR-0400` into a bounded upstream-first route:
Sir Convert must produce real recovered bytes, stable identity, terminal-only
manifest/bundle evidence, and upstream reinsertion before Skriptoteket exposes
any teacher-facing image-recovery claim. Skriptoteket remains a strict consumer
that validates manifests and fails closed on missing bytes, hash mismatches,
unsafe paths, or schema drift.

## Problem Statement

`PR-0400` closed the artifact hygiene problem by rejecting missing-image
metadata and placeholder content when no real source or extracted bytes exist.
`PR-0401` must keep that fail-closed baseline intact while planning a future
route for honest PDF image recovery.

## Proposed Solution

Make Sir Convert the producer of recovered PDF image bytes, stable image
identity, terminal-only manifests, companion bundles, and upstream
Markdown/HTML/DOCX insertion. Keep Skriptoteket as the consumer that validates
the manifest, displays status only after upstream contract support exists, and
rejects download/save when recovery claims cannot be verified.

## Scope Reviewed

- Target: `PR-0401`
- Planning doc:
  `docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md`
- Predecessor hygiene contract:
  `docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md`
- Upstream Sir Convert task:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md`
- Focused Sir Convert PDF checkpoint/Pandoc path and Skriptoteket artifact
  consumer/client protocol surfaces listed below.

## Artifacts to Review

| File | Focus | Time |
|---|---|---|
| `docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md` | Acceptance criteria, planning decision, manifest shape, stop conditions, close-out steps | 35 min |
| `docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md` and `docs/backlog/reviews/review-pr-0400-document-converter-artifact-content-hygiene-contract.md` | Predecessor boundary and deferred PDF image-recovery obligation | 20 min |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md` | Upstream task scope, status, bundle/manifest semantics | 25 min |
| Sir Convert v2 executor, checkpoint, PyMuPDF, Pandoc, API-resource docs/code | Validate factual claims about current producer route and resource limits | 35 min |
| Skriptoteket Document Converter protocols, handler, and Sir Convert client | Validate current consumer/client boundary and absence of recovery sidecar model | 25 min |

**Total estimated time:** ~2.5 hours

## Evidence Inspected

- `PR-0401` acceptance criteria require real-byte recovery, no placeholder
  metadata promise, layout-reconstruction stop conditions, linked upstream Sir
  Convert work, and a clear producer/consumer boundary
  (`docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md:18`).
- `PR-0401` records that current Sir Convert checkpoints lack image xrefs,
  extracted image bytes, artifact keys, placement, and insertion refs
  (`docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md:61`).
- `PR-0401` explicitly treats Sir Convert Task 272 as prerequisite authority and
  blocks DOCX image-recovery product behavior until Task 272 is amended or
  followed by a successor task
  (`docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md:87`,
  `docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md:95`).
- The planning decision keeps Sir Convert responsible for extraction,
  manifest/bundle production, and upstream Markdown/HTML insertion, while
  Skriptoteket owns only routing, validation, status/copy, and fail-closed
  consumption
  (`docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md:101`).
- Stop conditions reject placeholder metadata, diagnostic-only bytes as DOCX
  claims, unsafe/mismatched manifests, and rendered-page layout reconstruction
  for the editable DOCX lane
  (`docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md:175`).
- `PR-0400` explicitly deferred PDF image recovery to a separate governed task
  and rejected missing-image metadata as an implied recovery promise
  (`docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md:23`,
  `docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md:126`).
- Sir Convert Task 272 is still `proposed` and defines a PDF-to-Markdown
  companion bundle with `artifact-manifest.json`, relative image paths, privacy
  rules, and terminal-only publication, not a completed Skriptoteket DOCX image
  recovery contract
  (`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md:41`,
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md:163`).
- Sir Convert current PDF execution routes both PDF-to-Markdown and PDF-to-DOCX
  through checkpointed Markdown before optional DOCX generation
  (`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:221`,
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/v2_non_pdf_helpers.py:297`).
- The current PDF checkpoint model is chunk Markdown state and partial artifact
  metadata, with no recovered-image sidecar fields
  (`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py:64`,
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py:104`).
- Sir Convert's current PyMuPDF backend calls `pymupdf4llm.to_markdown(...)`
  and does not materialize image sidecars
  (`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/pymupdf_backend.py:79`).
- Pandoc HTML-to-DOCX currently receives a resource path, but the PDF route does
  not create linked recovered-image resources for it
  (`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_docx.py:61`).
- Sir Convert v2 resources are route-constrained and rejected for `pdf -> md`,
  so client-side re-upload is not a valid PDF recovery route
  (`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/interfaces/http_jobs_v2_request_validation.py:51`,
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/downstream_integration_contract_v2.md:87`).
- Skriptoteket's Document Converter result model exposes one converted result
  artifact, and the download/save handlers currently fetch the default upstream
  artifact; there is no recovery-manifest parser or recovered-image sidecar
  model in this boundary
  (`src/skriptoteket/application/curated_apps/document_converter.py:172`,
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py:170`,
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py:239`).
- The Sir Convert client protocol can download default and generic named
  artifacts, but that generic capability is not a Document Converter recovery
  contract by itself
  (`src/skriptoteket/protocols/sir_convert_a_lot_v2.py:118`,
  `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py:306`).
- Context7 documentation checked PyMuPDF `Document.extract_image(xref)` and
  Pandoc `--resource-path`: PyMuPDF can return embedded image bytes and
  metadata, and Pandoc can resolve local image resources for DOCX, but neither
  provides Skriptoteket with trustworthy editable-document placement or a
  terminal recovery manifest by itself.

## Key Decisions

| Decision | Rationale | Approve? |
|---|---|---|
| Sir Convert owns PDF image recovery and terminal artifact truth. | Extraction, stable byte identity, manifests, and reinsertion belong with the producer that sees the PDF route internals. | [x] |
| Skriptoteket owns strict consumer validation only after upstream contract support exists. | Prevents the app from inventing recovery semantics from generic artifact download support. | [x] |
| Missing bytes or untrusted insertion evidence cannot become placeholder metadata or DOCX recovery claims. | Preserves the `PR-0400` artifact hygiene boundary. | [x] |
| Full PDF layout reconstruction is out of scope for the editable DOCX lane. | Avoids turning a bounded recovery plan into a visual-facsimile converter rewrite. | [x] |
| DOCX image recovery remains deferred until Task 272 is amended or followed. | Task 272 is currently PDF-to-Markdown bundle authority, not a completed DOCX recovery contract. | [x] |

## Review Checklist

- [x] Findings are recorded first.
- [x] Acceptance criteria are checked against `PR-0401`.
- [x] Upstream Sir Convert Task 272 status and scope are verified.
- [x] Sir Convert PDF checkpoint/Pandoc path claims are verified against code.
- [x] Skriptoteket Document Converter artifact consumer/client protocol claims
      are verified against code.
- [x] The plan does not overpromise DOCX image recovery before upstream
      manifest/resources exist.
- [x] Required review/doc close-out steps are present.
- [x] Scope remains planning/docs-only and does not drift into implementation.

## Acceptance-Criteria Check

| Criterion | Result |
|---|---|
| Real-byte recovery route | Passed. The plan routes recovery through upstream Sir Convert byte extraction, stable image identity, manifest/bundle retention, and upstream reinsertion before claims. |
| No placeholder metadata promise | Passed. The plan forbids placeholder metadata and diagnostic-only bytes as DOCX recovery claims. |
| Stop conditions for layout reconstruction | Passed. The plan rejects full PDF layout reconstruction for the editable DOCX lane and names visual facsimile as a separate future product route. |
| Linked upstream Sir Convert task | Passed. Task 272 is linked and correctly treated as prerequisite, not completed capability. |
| Clear Skriptoteket/Sir Convert boundary | Passed. Sir Convert owns extraction and terminal artifact truth; Skriptoteket owns validation, copy/status after contract existence, and fail-closed consumption. |
| No DOCX image-recovery overpromise | Passed. The plan explicitly requires Task 272 amendment or successor upstream work before DOCX media reinsertion becomes user-visible behavior. |

## Required Changes

None.

## Review Feedback

**Reviewer:** `codex-independent-planning-reviewer`
**Date:** `2026-06-28`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions (Optional)

- Keep the future Skriptoteket implementation slice blocked on an upstream
  manifest/bytes contract. Generic named-artifact download support is useful
  plumbing, but it is not sufficient proof for teacher-facing recovery claims.

### Decision Approvals

- [x] Real-byte recovery route is upstream-owned.
- [x] Placeholder metadata remains forbidden.
- [x] Layout reconstruction stop conditions are explicit.
- [x] Task 272 is the linked prerequisite, with DOCX recovery deferred until
      amended or followed.
- [x] Skriptoteket/Sir Convert ownership is clear.

## Residual Risks And Test Gaps

- No implementation or code tests were expected in this planning slice. The
  future implementation task still needs red-first Sir Convert fixture tests for
  stable image ids, SHA-256 hashes, relative safe paths, terminal-only manifests,
  and DOCX `word/media/*` evidence when recovery is claimed.
- Task 272 currently targets PDF-to-Markdown companion bundles. DOCX media
  reinsertion remains deferred until Task 272 is amended or a successor task
  defines and proves the DOCX terminal-artifact contract.
- Skriptoteket should stay fail-closed until the upstream manifest and real
  bytes exist; generic named-artifact download support is not enough to expose
  teacher-facing recovery status.

## Verification

- Read required docs and focused code surfaces with line-numbered inspection.
- Ran Context7 checks for PyMuPDF and Pandoc third-party claims.
- This review artifact was created as the only file changed by this reviewer.

## Changes Made

| Change | Artifact | Description |
|---|---|---|
| 1 | `REV-PR-0401` | Created retained independent review record with verdict `approved`. |
