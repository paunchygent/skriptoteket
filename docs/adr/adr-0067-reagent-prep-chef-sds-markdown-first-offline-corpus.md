---
type: adr
id: ADR-0067
title: "Reagent Prep Chef SDS: markdown-first offline corpus"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-03-04
links: ["EPIC-20", "ST-20-02"]
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

### 2) PDFs are optional and stored outside git

- If we have the original PDF, it can be stored under:
  - `data/reagent_prep_chef/sds/files/` (gitignored).
- The backend may serve PDFs when present, but the product must not depend on PDFs being present in git.

### 3) No runtime SDS fetching from external sources

- The backend must not fetch SDS content over HTTP at runtime.
- Adding/updating SDS content is a **curation workflow** (commit markdown; optionally provision PDFs).

### 4) Deterministic index + gap tracking

- A deterministic index is generated and committed:
  - `data/reagent_prep_chef/sds/index.json`
- Remaining gaps are tracked in:
  - `data/reagent_prep_chef/sds/gaps.md`

## Consequences

- **Backend simplification:** remove PubChem/SDS fetch + cache + derived-signal code paths.
- **Frontend simplification:** “Öppna SDS” uses markdown content (rendered in-app) and does not depend on PDFs.
- **Maintenance posture:** correctness is achieved by curation, not heuristics.
- **Operational workflow:** to add SDS coverage, commit a new markdown file and regenerate the index/gaps artifacts.
- **Future extension:** if/when we introduce a blob/file service, PDFs can migrate there without changing the markdown
  corpus contract.
