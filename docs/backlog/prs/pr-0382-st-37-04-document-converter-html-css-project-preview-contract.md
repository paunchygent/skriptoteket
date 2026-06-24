---
type: pr
id: PR-0382
title: "ST-37-04 Document Converter HTML/CSS project preview contract"
status: ready
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

## Stop Conditions

- Stop if rendering needs a route-visible UI decision or copy approval.
- Stop if the implementation cannot safely sandbox linked assets.
- Stop if a proposed preview model exposes raw filesystem paths, producer
  credentials, or browser-supplied artifact authority.

## Rollback Plan

Remove the project-preview contract, preview state, tests, generated types, and
docs updates. Keep the `PR-0381` batch/local-heavy foundation intact.
