---
type: task
id: TASK-SKRIPT-20-03-01
title: Reagent Prep Chef — SDS PDF originals for missing hazards (manual pipeline)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-20-03
task_kind: story
acceptance_criteria:
- For each target key listed in this task, at least one valid SDS PDF is downloaded
  from an allowed supplier portal (prefer Swedish when available).
- Each PDF is stored under `data/reagent_prep_chef/sds/files/` (gitignored) using
  the `<key>__<provider>__<revision>.pdf` naming convention.
- Each newly-added PDF passes a quick SDS sanity check (multi-section SDS; render-to-PNG
  spot check).
---

## Context

The source does not provide a separate context section; no additional context is recorded.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Story Contract Slice

### Source: Goal

Download valid SDS PDFs for the remaining missing hazards keys and store them in app-specific storage (outside git).

## Contract Inputs

### Source: Target keys (as of 2026-03-04)

From `data/reagent_prep_chef/sds/gaps.md`:

- `Al`
- `Al2O3`
- `AlCl3`
- `AlCl3·6H2O`
- `C2H6O`
- `C3H6O`
- `C7H6O2`
- `C7H6O3`
- `Ca(OH)2`
- `CaC2`
- `CaCl2`
- `Cu2O`
- `CuO`
- `H2O2`
- `H2SO4`
- `HCl`
- `HF`
- `K2Cr2O7`
- `KOH`
- `NH4Cl`
- `NH4NO3`
- `Na2CO3`
- `NaOH`
- `S`
- `SrCl2`

## Plan

### Source: Implementation plan

1. For each key, search for an SDS PDF in this order:
   - Supplier portals we actually buy from (if applicable).
   - Carl Roth (preferred).
   - Merck / Sigma-Aldrich, Thermo Fisher / Fisher Scientific / Alfa Aesar, Avantor / VWR, TCI, Honeywell.
2. Download a PDF that is a real SDS/MSDS for the pure substance (avoid fact sheets, legal acts, “terms” PDFs).
3. Name and store the PDF:
   - Folder: `data/reagent_prep_chef/sds/files/` (gitignored)
   - Filename: `<key>__<provider>__<revision>.pdf` (`revision` as `YYYY-MM-DD` if visible, otherwise `undated`)
4. Validate each PDF quickly (batch-friendly):
   - Basic metadata: `pdfinfo <file>`
   - Render page 1 to PNG and visually confirm it’s an SDS:
     - `pdftoppm -png -f 1 -l 1 <file> .artifacts/sds-corpus/png/<basename>/page`
5. Record per-file provenance (provider, revision date, language, URL) in the PR notes while executing (or in a local
   checklist under `.artifacts/sds-corpus/`).

## Implementation Steps

The source does not provide a separate implementation steps section; no additional implementation steps is recorded.

## Proof

### Source: Test plan

- Spot-check a few downloaded PDFs via `pdftoppm` PNG output.
- Re-run `pdm run python scripts/build_reagent_prep_chef_sds_index.py` after copying PDFs so `pdf_available` can be
  detected for the matching SDS entries (optional; app correctness is markdown-first).

## Validation

The source does not provide a separate validation section; no additional validation is recorded.

## Stop Conditions

### Source: Non-goals

- No runtime SDS fetching.
- No new PDF parsing/heuristics pipelines.
- No OneDrive integration (backup is separate from the app pipeline).

### Source: Rollback plan

- Remove the PDFs from `data/reagent_prep_chef/sds/files/`.
- Re-run `pdm run python scripts/build_reagent_prep_chef_sds_index.py` if the index was updated to reference them.

## Lessons Learned

The source does not provide a separate lessons learned section; no additional lessons learned is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: Problem

The SDS corpus is now markdown-first (ADR-0067), but we still need source PDFs to close remaining gaps reliably:

- PDFs are the conversion input for Sir Convert-a-Lot.
- PDFs provide an optional “original document” artifact outside git for later retrieval.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Implementation Review

The source does not provide a separate implementation review section; no additional implementation review is recorded.
