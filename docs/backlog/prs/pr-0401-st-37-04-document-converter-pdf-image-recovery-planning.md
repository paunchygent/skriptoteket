---
type: pr
id: PR-0401
title: "ST-37-04 Document Converter PDF image recovery planning"
status: ready
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
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

## Non-goals

- No implementation in this planning slice.
- No placeholder preservation as a substitute for recovered image bytes.
- No promise that every PDF image can be reinserted into DOCX.
- No broad PDF-to-DOCX layout engine rewrite.

## Implementation Plan

1. Audit current Sir Convert PDF extraction and checkpoint outputs for any
   existing image sidecar, resource manifest, or page-position evidence.
2. Classify recoverable cases: source-bundle image references, embedded PDF
   images with stable extraction ids, OCR/extraction artifacts with linked
   image bytes, and unsupported layout-only cases.
3. Define the recovery manifest shape and ownership boundary.
4. Decide whether image reinsertion belongs first in Markdown/HTML intermediate
   output, DOCX generation, or both.
5. Write the follow-on implementation PR/task with red-first artifact tests and
   retained sample fixtures.

## Test Plan

- No code tests in this planning slice.
- Planning close-out requires `pdm run docs-validate` and `git diff --check`.

## Rollback Plan

Remove this planning PR slice and leave `PR-0400`'s fail-closed artifact hygiene
contract as the active behavior until a new recovery plan is approved.
