---
type: pr
id: PR-0068
title: "Reagent Prep Chef — SDS PDF originals for missing hazards (manual pipeline)"
status: ready
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-20-03"
tags: ["curated-apps", "data"]
adrs: ["ADR-0067"]
acceptance_criteria:
  - "For each target key listed in this task, at least one valid SDS PDF is downloaded from an allowed supplier portal (prefer Swedish when available)."
  - "Each PDF is stored under `data/reagent_prep_chef/sds/files/` (gitignored) using the `<key>__<provider>__<revision>.pdf` naming convention."
  - "Each newly-added PDF passes a quick SDS sanity check (multi-section SDS; render-to-PNG spot check)."
---

## Problem

The SDS corpus is now markdown-first (ADR-0067), but we still need source PDFs to close remaining gaps reliably:

- PDFs are the conversion input for Sir Convert-a-Lot.
- PDFs provide an optional “original document” artifact outside git for later retrieval.

## Goal

Download valid SDS PDFs for the remaining missing hazards keys and store them in app-specific storage (outside git).

## Non-goals

- No runtime SDS fetching.
- No new PDF parsing/heuristics pipelines.
- No OneDrive integration (backup is separate from the app pipeline).

## Target keys (as of 2026-03-04)

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

## Implementation plan

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

## Test plan

- Spot-check a few downloaded PDFs via `pdftoppm` PNG output.
- Re-run `pdm run python scripts/build_reagent_prep_chef_sds_index.py` after copying PDFs so `pdf_available` can be
  detected for the matching SDS entries (optional; app correctness is markdown-first).

## Rollback plan

- Remove the PDFs from `data/reagent_prep_chef/sds/files/`.
- Re-run `pdm run python scripts/build_reagent_prep_chef_sds_index.py` if the index was updated to reference them.
