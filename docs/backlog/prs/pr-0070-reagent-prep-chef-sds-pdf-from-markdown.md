---
type: pr
id: PR-0070
title: "Reagent Prep Chef — SDS PDF render from markdown (cache + branding)"
status: in_progress
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-20-02"
tags: ["curated-apps", "backend", "docker", "frontend"]
adrs: ["ADR-0067"]
acceptance_criteria:
  - "Given SDS markdown exists for a chemical, when the teacher clicks 'Öppna PDF', then the backend returns a generated PDF built from the markdown (no vendor PDF served)."
  - "Generated SDS PDFs include Skriptoteket branding (logo + consistent styling)."
  - "Generated SDS PDFs are cached on disk and reused; cache is refreshed when the markdown source is newer than the cached PDF."
  - "Works in local Docker dev (`compose.dev.yaml`) and Hemma production (`compose.prod.yaml`) via an explicit mounted cache directory."
  - "The UI and backend copy refers to app safety as 'säkerhetsdata' (not 'kuraterad post')."
---

## Problem

Riskbedömning can open SDS markdown (ADR-0067), but the SDS PDF button currently fails in Docker/prod because the code
assumes a vendor PDF is present under `data/reagent_prep_chef/sds/files/` (gitignored, not mounted).

We also want SDS PDFs to be **our own**, generated from the markdown corpus for a consistent look (and not dependent on
supplier PDFs at runtime).

## Goal

- Make `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/{sds_ref}` return a generated SDS PDF rendered from the repo-owned
  markdown corpus.
- Cache generated PDFs on disk (dev + Hemma) so repeated opens are fast.
- Ensure user-facing copy says **säkerhetsdata**.

## Non-goals

- No runtime fetching of external SDS sources.
- No serving of vendor/source PDFs in the app UI.
- No language detection; Swedish-first remains the default.

## Implementation plan

1. Update SDS store semantics so `get_pdf()` renders from markdown + caches result (WeasyPrint).
2. Add a configurable cache directory (Settings/env) and mount it in:
   - `compose.dev.yaml` (repo-local gitignored directory)
   - `compose.prod.yaml` (persistent volume / data disk path on Hemma)
3. Update `pdf_available` semantics in API responses to mean: “PDF can be generated because markdown exists”.
4. Update copy (“säkerhetsdata”) in backend + SPA.

## Test plan

- Unit: PDF generation returns valid PDF bytes and writes to cache.
- Manual (dev-local + docker dev):
  - Reagensberedning → Riskbedömning → Öppna SDS → Öppna PDF (should open a real PDF, not JSON error).
- Gates: `pdm run format && pdm run lint && pdm run typecheck && pdm run test && pdm run docs-validate`

## Rollback plan

- Revert store/compose changes; restore the previous “vendor PDF only” behavior.
- Clear the SDS PDF cache directory/volume if needed.
