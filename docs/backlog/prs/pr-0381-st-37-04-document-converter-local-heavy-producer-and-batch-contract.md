---
type: pr
id: PR-0381
title: "ST-37-04 Document Converter local-heavy producer and batch contract"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-25
stories:
  - "ST-37-04"
tags:
  - backend
  - document-converter
  - batch
dependencies:
  - "PR-0379"
  - "PR-0380"
acceptance_criteria:
  - "Given simple document conversions are owned by the Skriptoteket app boundary, when the backend contract is expanded, then simple supported lanes can be planned and tested without submitting every job to Sir Convert."
  - "Given heavy PDF conversion still needs producer/model evidence, when OCR, formula-heavy, complex table, complex layout, or failed local extraction is detected, then the contract automatically routes to Sir Convert without asking the teacher where to process the file."
  - "Given single upload is insufficient, when the submit contract changes, then it supports a first general batch target of up to 10 validated input items or project entries without activating a frontend route."
  - "Given implementation cannot pick libraries by guesswork, when this slice begins, then it first records the researched local conversion candidates and the selected narrow proof path before production code is changed."
---

# PR-0381: ST-37-04 Document Converter Local-Heavy Producer And Batch Contract

## Problem

The current scoped Document Converter API from `PR-0379` is useful foundation,
but it still models one upload and submits conversion through the existing Sir
Convert-backed path. That contradicts the corrected product direction in
`PR-0380`: simple lanes should run inside the Skriptoteket app boundary, while
heavy/OCR/complex PDF lanes remain producer-owned.

## Goal

Define and implement the first backend contract that separates local simple
conversion from heavy Sir Convert conversion and introduces the general
Document Converter batch input model, while keeping the frontend route inert.

## Non-goals

- No route-visible Document Converter UI.
- No image, HTML/CSS, or copy mockup work.
- No public Document Converter capability.
- No durable job history beyond what the existing local job model can support.
- No final HTML/CSS preview UI contract; that belongs to `PR-0382`.

## Required Research Before Code

Before changing production code, research and record the candidate local
libraries or tools for the first simple lanes. The slice must not assume that
Pandoc, WeasyPrint, LibreOffice, PyMuPDF, python-docx, markdown tooling, or any
other dependency is acceptable without current syntax/runtime evidence.

Current repo evidence already narrows the candidate set:

- `weasyprint` is a runtime dependency and is already used by
  `WeasyPrintSeatingPdfRenderer`, `GroupingPdfRenderer`, and
  `WeasyPrintPdfRenderer`. HTML/CSS to PDF should start here and centralize the
  shared renderer rather than add another app-local wrapper.
- `markdown` is a runtime dependency and is already used to render committed
  SDS Markdown into HTML before PDF generation.
- `pdfplumber` is a runtime dependency and is already used as a local simple-PDF
  text fast path before Sir Convert fallback in class-list imports.
- `pypdf` is a runtime dependency and is already used by tests to inspect
  generated PDFs; it is a good candidate for PDF validation, merge/split, and
  metadata work, with lane-level production proof still required.
- `python-docx` is a runtime dependency and is already used by the script-bank
  Markdown-to-DOCX script for reference DOCX/style construction.
- `pypandoc` imports successfully in the repo runtime, but the `pandoc` binary
  is not currently on PATH. Any Markdown/DOCX lane that depends on Pandoc must
  first solve packaging/runtime proof or choose a different local path.
- `playwright` imports successfully and is already used for browser proof. It
  should remain a proof/preview automation candidate, not the default server PDF
  engine while WeasyPrint is sufficient.
- `reportlab` and `beautifulsoup4` import locally but live in the dev dependency
  group. They must not become production-path requirements unless this slice
  deliberately moves and proves them as runtime dependencies.

The output of the research should decide the narrow first implementation lane
or, if the evidence is not strong enough, convert this task into a smaller
spike before production runtime code is added.

`PR-0381` must also identify the shared rendering/extraction surface to expose
to curated apps. Repeated needs such as HTML/CSS-to-PDF, PDF validation, PDF
merge/concatenate, Markdown-to-HTML, and simple PDF text extraction should live
behind central protocols or infrastructure services instead of being copied
into each app.

### Research Result 2026-06-25

Current syntax evidence was checked through Context7/current docs for the
libraries selected for production use in this slice:

- WeasyPrint supports `HTML(string=..., base_url=...)`, optional `CSS(string=...)`,
  and `write_pdf()` for bytes when no output target is supplied.
- Python-Markdown supports `markdown.markdown(text, extensions=[...],
  output_format="html")` for Markdown-to-HTML rendering.
- pdfplumber supports `pdfplumber.open(...)` over paths or file-like byte
  streams and `page.extract_text()` for simple PDF text extraction.

Local runtime evidence from `pdm list` on 2026-06-25:

- Runtime dependency versions present: `weasyprint 68.1`, `Markdown 3.10.2`,
  `pdfplumber 0.11.9`, `pypdf 6.9.2`, `python-docx 1.2.0`,
  `pypandoc 1.17`, and `playwright 1.58.0`.
- Dev-only dependency versions present: `reportlab 4.4.10` and
  `beautifulsoup4 4.14.3`.
- `pdm run python -m pip show ...` is not a valid probe in the current PDM
  environment because the venv has no `pip` module; `pdm list` is the local
  package evidence for this slice.
- `pandoc` is currently present on this host at `/opt/homebrew/bin/pandoc`.
  It is not selected for production code in this slice because the system
  binary is not declared as a Skriptoteket runtime dependency or image contract.

Selected narrow proof path:

- Centralize reusable document surfaces behind protocols for
  HTML/CSS-to-PDF, Markdown-to-HTML, simple PDF text extraction, and local
  Document Converter artifact storage.
- Implement local Document Converter producer support for simple
  `html -> pdf`, `md -> pdf`, and extractable-text `pdf -> md`.
- Route failed PDF text extraction, OCR/no-text PDFs, `pdf -> docx`, DOCX
  routes, HTML-to-DOCX/Markdown, and other unsupported local routes through an
  explicit automatic Sir Convert producer decision.
- Keep pypdf and python-docx as recorded candidates for later lane-level proof;
  do not use them in production code in `PR-0381`.
- Keep reportlab and beautifulsoup4 out of production paths because they remain
  dev dependencies.

## Implementation Plan

1. Start red-first with backend contract tests that prove the current
   Document Converter submit path accepts only one upload and lacks local versus
   heavy producer routing.
2. Add an explicit local/heavy producer decision model at the application
   boundary. Keep domain state independent of concrete converter libraries, and
   keep routing automatic rather than user-selected.
3. Expand upload validation to the first batch shape: up to 10 validated input
   items or project entries, fail-closed on size, type, route, and count.
4. Keep Sir Convert routing only for heavy paths named in `PR-0380`.
5. Extract or introduce a central reusable document/PDF rendering surface before
   adding another app-specific WeasyPrint or PDF helper.
6. Keep the existing scoped API namespace unless the implementation proves a
   concrete `PR-0369` app-presentation contract need.
7. Refresh generated API types only if response/request schemas change.
8. Update docs and handoff with the accepted contract and verification.

## Red-First Proof Plan

- Backend red: current submit contract rejects or cannot express a valid batch
  of more than one document item.
- Backend red: current application path has no local versus heavy producer
  decision and defaults to the existing Sir Convert job creation path.
- Backend red: heavy-routing decision is not represented as automatic product
  logic.
- Backend red: current renderer usage is app-local and has no shared
  Document Converter service/protocol for repeated PDF needs.
- Boundary red: unsupported count, source/target mismatch, and mixed invalid
  files fail before producer submission.

## Green Proof Plan

- Focused backend tests for batch count, validation, local/heavy routing,
  owner-scoped status, no cross-owner access, and no browser-supplied artifact
  authority.
- Focused adjacent Conversion Hub tests to prove Exam Converter and Audio
  Transcription behavior is unchanged.
- `pdm run lint`
- `pdm run typecheck`
- generated API type refresh and `pdm run fe-type-check` if schemas change
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Notes

Implemented package prepared for `REV-PR-0381` review on 2026-06-25:

- The scoped Document Converter submit route now accepts a general batch of up
  to 10 validated uploads, validates every item against the selected
  source/output route, and reads bytes through the shared capped upload helper
  before the application handler runs.
- Automatic producer routing now returns one decision per submitted item.
  Simple `html -> pdf`, `md -> pdf`, and extractable-text `pdf -> md` routes
  are handled inside the Skriptoteket app boundary. Failed local PDF text
  extraction, extractable-but-complex PDF probes, heavy PDF routes, DOCX
  routes, DOCX outputs, and unsupported local routes explicitly route to Sir
  Convert.
- Local Document Converter results are stored server-side under the local job
  id and used for download/save authority. Browser-supplied artifact keys or
  bytes are still excluded from the Document Converter save path.
- Reusable document surfaces are now centralized behind protocols and
  infrastructure adapters for HTML-to-PDF rendering, Markdown-to-HTML
  rendering, simple PDF text extraction, and local Document Converter artifact
  storage. Existing direct WeasyPrint renderer call sites now delegate to the
  shared renderer helper instead of duplicating the third-party call pattern.
- The scoped API namespace remains
  `/api/v1/apps/documents.conversion_hub/document-converter/...`; no
  `/apps/document-converter` route, app card, registry capability, public
  capability, or `PR-0369` app-presentation API split was activated.
- The OpenAPI-derived frontend types were regenerated because the scoped
  Document Converter submit response now exposes per-item producer decisions.

## Verification Evidence

Red-first evidence before production implementation:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py` | Failed during collection because `DocumentConverterProducerKind` did not exist yet. This proved the current production contract had no producer decision model/routing surface; the batch test covered the missing multi-item submit contract. |

Green evidence after implementation:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Passed: 15 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py` | Passed: 33 tests, proving adjacent Exam Converter and Audio Transcription behavior remained unchanged. |
| `pdm run lint` | Passed before docs closeout. |
| `pdm run typecheck` | Passed before docs closeout. |
| `pdm run fe-gen-api-types` | Passed; regenerated the OpenAPI TypeScript surface for the scoped response schema. |
| `pdm run fe-type-check` | Passed. |

Repair evidence after `REV-PR-0381` changes requested:

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py` | Red before repair: 3 failed, 5 passed. Complex extractable PDFs were still marked `local_pdf_text_to_markdown`, local artifact-store `OSError` bubbled, and the handler returned a succeeded local job for the complex PDF case. |
| `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py` | Green after repair: 8 passed. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py` | Passed: 28 tests. |
| `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py` | Passed: 33 tests, proving adjacent Exam Converter and Audio Transcription behavior remained unchanged. |

## Stop Conditions

- Stop if the first local conversion lane cannot be proven with a maintained,
  acceptable dependency.
- Stop if implementation would activate `/apps/document-converter` before the
  mockup and copy gates.
- Stop if simple conversion silently falls back to Sir Convert without an
  explicit automatic heavy-path decision.
- Stop if the implementation duplicates app-local PDF boilerplate instead of
  exposing the existing proven PDF/rendering approach centrally.
- Stop if batch upload semantics require unresolved product decisions from
  `PR-0380`.

## Rollback Plan

Remove the new local/heavy producer contract, batch request/response changes,
tests, generated type changes, and docs updates. Preserve `PR-0379` as the last
accepted one-file scoped backend foundation.
