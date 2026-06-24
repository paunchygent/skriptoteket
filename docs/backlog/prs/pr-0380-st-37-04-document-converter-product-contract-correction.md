---
type: pr
id: PR-0380
title: "ST-37-04 Document Converter product contract correction"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-24
stories:
  - "ST-37-04"
tags:
  - planning
  - document-converter
  - product-contract
dependencies:
  - "PR-0375"
  - "PR-0379"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
acceptance_criteria:
  - "Given PR-0375 and PR-0379 froze a one-file, Sir Convert-first MVP assumption, when this correction closes, then Document Converter planning records that simple lanes run inside the Skriptoteket app boundary while Sir Convert is reserved for heavy OCR, complex PDF extraction, formula/table/layout, and explicit heavy conversion paths."
  - "Given single-upload document conversion is not useful enough for the intended product, when future Document Converter work is planned, then the general batch target is up to 10 uploaded input items or project entries before route-visible UI implementation."
  - "Given HTML/CSS to PDF is a core teacher value lane, when future implementation slices are created, then they include multi-file HTML/CSS project input, PDF controls, render progress, and final PDF preview before save/download."
  - "Given UI and copy are gated by the user's approval process, when route-visible work is sequenced, then image mockups, HTML/CSS mockups, and copy lock remain explicit blocked gates before production UI implementation."
---

# PR-0380: ST-37-04 Document Converter Product Contract Correction

## Problem

`PR-0375` and `PR-0379` created useful backend/API foundation for a scoped
Document Converter contract, but they also froze assumptions that are now too
narrow for the intended product:

- one upload is not the right input model;
- all document conversion should not default to Sir Convert;
- HTML/CSS to PDF needs multi-file project input, progress, controls, and
  preview rather than a blind artifact-only result;
- route-visible UI must wait for the approved mockup and copy pipeline.

If the next implementation proceeds from the older one-file/Sir Convert-first
assumption, it will build the wrong product even if the backend code is clean.

## Goal

Lock the corrected product boundary and create an iterative task queue that
lets implementation proceed, but keeps later UI, copy, storage, and heavy-route
decisions open until the preceding evidence exists.

## Locked Decisions

- Document Converter is a separate authenticated teacher-facing lane for PDF,
  DOCX, Markdown, HTML/CSS, and document or presentation output work.
- Simple conversions run inside the Skriptoteket app boundary. This means no
  browser-direct external service and no automatic Sir Convert call when the
  work can be handled by the Skriptoteket app runtime.
- Sir Convert is reserved for heavy paths: OCR-heavy PDFs, PDF to Markdown,
  DOCX, or HTML when quality depends on Docling/GPU/model-backed extraction,
  formula-heavy PDFs, complex tables/layout, and detected heavy conversion
  fallback.
- Heavy routing is automatic. Teachers should never choose where processing
  happens; Skriptoteket decides from source inspection and product logic,
  reusing Sir Convert decision patterns where they already exist.
- General Document Converter batch input targets up to 10 source documents or
  conversion project entries for the first useful product version.
- For HTML/CSS projects, the source-count cap is the HTML entry count: up to 10
  HTML source documents/projects. CSS is styling support rather than a source
  document, but the first cap is up to 10 CSS files. Linked images are support
  assets resolved by filename inside the uploaded project boundary.
- HTML/CSS to PDF is a core lane, not an optional afterthought. It must support
  multiple HTML/CSS inputs, shared CSS where appropriate, page controls,
  progress, and final PDF preview.
- HTML/CSS batch output must support separate PDFs, one combined PDF, or both.
  The first UI may emphasize separate or combined output, but the contract must
  leave both available.
- Preview PDFs are short-lived temporary server artifacts with an initial target
  TTL of 24 hours. They are saved to `Mina filer` only after explicit teacher
  action.
- Launch templates should start from templates that already exist or are
  deliberately created for this product: the academic/PhD-style template plus a
  small curated set with expressive, obvious styling. Template-library growth is
  later work.
- The renderer should provide a broad available font set where feasible and
  map missing fonts to similar fallbacks without making teachers decide.
- User-facing UI should not talk about "result artifacts"; that is
  observability/internal language.
- Current-session history is acceptable for the first route-visible product,
  while durable job history can wait.
- Future source selection from `Mina filer` is required, but it follows after
  upload and preview are proven. The backend/frontend plumbing should make that
  follow-up easy rather than forcing a redesign.
- UI and copy are gated: image-generated mockups first, then approved HTML/CSS
  mockups, then a separate user-reviewed copy sheet, then implementation.

## Open Product Questions

- Which exact library powers each simple lane after `PR-0381` checks current
  repo usage, current official syntax, install/runtime behavior, and the
  centralization opportunity?
- What source-inspection thresholds make a PDF "heavy" enough for Sir Convert:
  no extractable text, OCR need, formula density, table/layout complexity,
  failure of local extraction, or a combination?
- What are the first safe caps for linked image/font assets beyond the source
  document and CSS caps?
- Which concrete existing templates belong in the first template selector, and
  what are their approved user-facing names after the copy gate?

## Follow-up Task Queue

1. `PR-0381`: local/heavy producer policy and general batch API contract. This
   is the next implementation slice.
2. `PR-0382`: HTML/CSS project input and PDF preview contract. This starts
   after `PR-0381` closes enough batch and producer-shape evidence.
3. `PR-0383`: Document Converter mockup and copy approval package. This is UI
   planning only and must not create production UI.
4. `PR-0384`: route-visible Document Converter implementation. This is blocked
   until backend contracts, mockups, and copy are approved.
5. `PR-0385`: `Mina filer` source selection and current-session history
   hardening. This follows the first useful route-visible product unless it is
   explicitly pulled earlier by product decision.

## Non-goals

- No production code change in this planning correction.
- No Document Converter route activation.
- No public anonymous Document Converter capability.
- No UI copy, Swedish wording, or labels are approved by this task.
- No final choice of conversion libraries is made here.

## Test Plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Remove this planning correction and the `PR-0381` through `PR-0385` queue from
the governed docs. Leave `PR-0379` as the last accepted backend/API foundation,
with Document Converter route-visible work blocked until a new correction is
approved.
