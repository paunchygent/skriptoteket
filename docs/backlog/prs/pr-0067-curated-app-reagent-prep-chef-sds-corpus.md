---
type: pr
id: PR-0067
title: "Curated app: Reagent Prep Chef — SDS corpus gap fill + commit (ADR-0067)"
status: done
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-20-03"
tags: ["curated-apps", "data", "docs"]
adrs: ["ADR-0067"]
dependencies: ["PR-0068"]
acceptance_criteria:
  - "SDS markdown corpus is committed under `data/reagent_prep_chef/sds/markdown/` and is treated as the source of truth."
  - "Deterministic index and gaps docs are regenerated and committed: `data/reagent_prep_chef/sds/index.json`, `data/reagent_prep_chef/sds/gaps.md`."
  - "After regeneration, `data/reagent_prep_chef/sds/gaps.md` shows `Missing markdown: 0`."
  - "SDS PDFs remain outside git under `data/reagent_prep_chef/sds/files/` (gitignored) and are optional for app correctness."
  - "Docs index is updated to include ST-20-03 and PR-0067."
---

## Problem

Reagensberedning now relies on an offline, repo-owned SDS markdown corpus (ADR-0067). The UX and backend contracts are
in place, but the corpus is not yet complete for all curated hazards keys.

## Goal

- Commit the SDS markdown corpus + deterministic index/gap tracking docs to the repo.
- Fill remaining SDS markdown gaps so every curated hazard key has SDS markdown.
- Keep the pipeline maintainable: manual curation + conversion, no runtime scraping.

## Non-goals

- No runtime SDS fetching.
- No SDS-derived density/CLP/heuristics extraction pipelines.
- No OneDrive integration (backup-only).

## Implementation plan

0. Source PDFs (see PR-0068; Swedish-first, supplier portals only).
1. Convert PDFs → markdown (batch conversion via Sir Convert-a-Lot).
2. If a Swedish SDS is not available from the supplier, produce a Swedish markdown version as the final committed file
   (no language detection in product).
3. Fix conversion formatting issues (headings/section numbers/tables) so the markdown is readable in-app.
4. Stage markdown under `.artifacts/sds-corpus/manual-markdown/` and sync into repo-owned storage:
   - `pdm run python scripts/sync_reagent_prep_chef_sds_markdown.py`
5. Provision PDFs (optional) under `data/reagent_prep_chef/sds/files/` (gitignored).
6. Regenerate index + gaps:
   - `pdm run python scripts/build_reagent_prep_chef_sds_index.py`
7. Verify `data/reagent_prep_chef/sds/gaps.md` shows `Missing markdown: 0`.
8. Update `docs/index.md`.

## Test plan

- `pdm run docs-validate`
- `pdm run test` (at least the SDS route unit tests)
- Manual: open Reagensberedning → Riskbedömning → “Öppna SDS” for a few previously-missing keys.

## Rollback plan

- Revert the corpus changes (markdown/index/gaps) and keep the backend behavior unchanged (it already fails gracefully
  when an SDS is missing).
