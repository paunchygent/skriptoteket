---
type: adr
id: ADR-SKRIPT-0067
title: 'Reagent Prep Chef SDS: markdown-first offline corpus'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
links:
  governing:
  - EPIC-SKRIPT-20
  - ST-SKRIPT-20-02
deciders:
- user-lead
retired_ids:
- ADR-0067
---

## Context
Reagent Prep Chef needs an SDS fallback that is:

- **Offline** and backend-hosted (no direct external vendor URLs in the SPA).
- **Reliable** (not dependent on brittle web scraping or PubChem candidate quality).
- **Swedish-first** (the app targets Swedish teachers; we do not add language detection).
- **Deterministic** (the same `sds_ref` always yields the same document).

The previous “fetch SDS PDFs + derive signals” approach (PubChem + provider registries + PDF parsing) has a low hit-rate
and creates a large maintenance surface (HTTP edge cases, non-SDS PDFs, parsing failures, rate limits, licensing
ambiguity).

For this product, **SDS documents themselves** (curated markdown) are the most valuable and durable artifact.

## Decision
### 1) Use a repo-owned SDS corpus with markdown as the source of truth

- The canonical SDS content is stored as **markdown** under:
  - `data/reagent_prep_chef/sds/markdown/` (committed to git).
- The app uses the markdown content “as-is” for the UI (no hazard inference pipeline required).

### 2) SDS PDFs are generated from markdown (cached outside git)

- The app serves SDS markdown in the UI as the primary document view.
- When a teacher needs a PDF, the backend generates a **Skriptoteket-branded** PDF rendered from the markdown corpus
  and caches it on disk **outside git** (deterministic input → deterministic output).
- Source/vendor PDFs may still exist as part of the curation workflow (PDF → markdown conversion), but they are not a
  runtime dependency and are **not** served to teachers in the app UI.

### 3) No runtime SDS fetching from external sources

- The backend must not fetch SDS content over HTTP at runtime.
- Adding/updating SDS content is a **curation workflow** (commit markdown; optionally provision PDFs).

### 4) Deterministic index + gap tracking

- A deterministic index is generated and committed:
  - `data/reagent_prep_chef/sds/index.json`
- Remaining gaps are tracked in:
  - `data/reagent_prep_chef/sds/gaps.md`

## Non-Decisions
The source record did not define a separate section for this package heading.

## Consequences
- **Backend simplification:** remove PubChem/SDS fetch + cache + derived-signal code paths.
- **Frontend simplification:** “Öppna SDS” uses markdown content (rendered in-app) and does not depend on PDFs.
- **Maintenance posture:** correctness is achieved by curation, not heuristics.
- **Operational workflow:** to add SDS coverage, commit a new markdown file and regenerate the index/gaps artifacts.
- **Future extension:** if/when we introduce a blob/file service, PDFs can migrate there without changing the markdown
  corpus contract.
