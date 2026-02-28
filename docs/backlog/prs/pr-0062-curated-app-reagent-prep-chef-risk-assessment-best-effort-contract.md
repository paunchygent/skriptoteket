---
type: pr
id: PR-0062
title: "Curated app: Reagent Prep Chef — Riskbedömning best effort contract (SDS missing flags + UI gating)"
status: in_progress
owners: "agents"
created: 2026-02-18
updated: 2026-02-28
stories:
  - "ST-20-02"
tags: ["curated-apps", "backend", "frontend"]
dependencies:
  - "PR-0060"
acceptance_criteria:
  - "Given Riskbedömning draft generation runs and SDS/derived data is incomplete, when the API returns, then it returns HTTP 200 with a deterministic draft plus explicit missing flags (no hard failure due to SDS incompleteness)."
  - "Given SDS PDF is not available offline for the current hazard, when the user clicks 'Öppna SDS', then the UI blocks the action and shows a clear 'SDS saknas offline' message tied to the contract flags."
  - "Given the draft is missing required confirmation/context and/or required SDS-derived data, when the user attempts export/save, then the UI is gated by `export_gate.ready=false` and renders actionable blockers (missing fields + missing confirmations + missing SDS-derived inputs)."
  - "Given export-risk-pdf is executed, when the request is handled, then no external fetch is attempted and export remains fail-closed if required SDS-derived inputs are missing."
  - "OpenAPI types are regenerated and the SPA compiles/type-checks against the updated schema."
---

## Problem

The current Riskbedömning draft endpoint is effectively **all-or-nothing** because the handler requires complete SDS
derivation. In practice, SDS coverage is incomplete (prefetch run 2026-02-01: ok=10, fail=154), which causes the tab to
fail instead of providing a usable “best effort” draft with clear next actions.

This blocks teacher workflows and makes it hard to distinguish:

- “we have a cached SDS PDF, but parsing failed for one section”
- “we have no SDS at all for this hazard”
- “we can compute some outputs, but not CLP band for target concentration”

## Goal

Define and ship a **best effort** API/UI contract for Riskbedömning so that:

- Draft generation returns deterministically even when SDS-derived inputs are incomplete.
- Missingness is explicit, typed, and UI-actionable (`missing_flags`).
- Export/save remains deterministic/offline and fail-closed via a single backend-provided gate (`export_gate`).

## Non-goals

- No “guessing” hazards/CLP/heuristics. Missing data must surface as missing with explicit flags.
- No external SDS URLs opened by the SPA.
- No new scraping/parsing strategy required to ship the contract (parsing improvements can be separate follow-ups).

## Proposed contract model (best effort)

### New enums (string literals)

`ReagentPrepChefRiskMissingFlag` (draft-level, UI-facing):

- `sds_ref_missing`
- `sds_pdf_missing`
- `sds_density_missing`
- `sds_clp_bands_missing`
- `sds_heuristics_missing`
- `clp_unavailable_for_target`
- `heuristics_unavailable`

### New models

`ReagentPrepChefSdsSnapshot` (best-effort status for SDS + derived inputs):

- `sds_ref: str | None`
- `pdf_available: bool`
- `missing_flags: list[ReagentPrepChefRiskMissingFlag]`
- `sources: list[str]`

`ReagentPrepChefRiskExportGate` (single source of truth for UI gating):

- `ready: bool`
- `missing_confirmations: list[str]`
- `missing_context_fields: list[str]`
- `missing_data_flags: list[ReagentPrepChefRiskMissingFlag]`

### Changes to existing draft/result models

Extend `ReagentPrepChefRiskAssessmentDraft`:

- Add `sds: ReagentPrepChefSdsSnapshot`
- Add `missing_flags: list[ReagentPrepChefRiskMissingFlag]`
- Add `export_gate: ReagentPrepChefRiskExportGate`

Make these fields best-effort tolerant:

- `clp: ReagentPrepChefClpClassification | None`
- `heuristics: ReagentPrepChefChemistryHeuristics | None`

Rules:

- `missing_flags` is the union of SDS + derived missingness for the current draft.
- `export_gate.ready` is computed server-side from:
  - existing confirmation requirements (`requires_confirmation`, `missing_confirmations`)
  - existing export context requirements (`scope`, `participants`, `approver`, `assessment_date`, `next_review_date`)
  - required SDS-derived inputs for export (`missing_data_flags`)

## UI behavior (gating + rendering)

- Riskbedömning tab renders draft even when `missing_flags` is non-empty.
- CLP and heuristics sections:
  - render normally when present
  - otherwise render a “Saknas — konsultera SDS” panel tied to the specific missing flags
- SDS button:
  - enabled only when `draft.sds.pdf_available=true`
- Export/Save buttons:
  - enabled only when `draft.export_gate.ready=true`
  - otherwise show the blockers from `draft.export_gate.*`

## Assumption validation (data-first, before implementation)

Before implementing the contract, validate assumptions against **real SDS fetch shapes** using the existing seed report:

```bash
PYTHONPATH=src pdm run python -m skriptoteket.cli validate-sds-assumptions \
  --report .artifacts/sds-cache/full-report.json \
  --out .artifacts/sds-cache/assumption-validation.json
```

Interpretation:

- `derived_status=ok`: full pipeline succeeded for the hazard.
- `derived_status=partial`: at least one PDF candidate was found, but the pipeline failed later (e.g. missing density,
  missing heuristics, missing CLP bands) → this is the primary justification for `missing_flags` + draft-tolerant UI.
- `derived_status=fail`: no usable PDF candidate found (true SDS gap).

This diagnostic output is the “sample truthy” driver for what missing flags we must support first and how export should
fail-closed.

Evidence (local run as of 2026-02-18):

- Sample from the 2026-02-01 seed report (`sample_ok=3`, `sample_fail=12`) produced `derived_status: ok=3, partial=12`.
- Top fail stages in that sample: `candidate_missing_heuristics` (7), `candidate_missing_density` (4),
  `candidate_missing_clp_bands` (1).

## Small-slice validation (PR-0062 infra: cache partial SDS for heuristics/density/clp)

This slice is the first implementation step of PR-0062: ensure that SDS PDFs are cached even when derived SDS inputs
are incomplete (heuristics/density/CLP bands), so the draft contract can safely surface `missing_flags` while keeping
export strict/offline.

### Evidence (local run as of 2026-02-18)

Target the dominant failure modes from the seed report with a small fail-only sample:

```bash
PYTHONPATH=src pdm run python -m skriptoteket.cli validate-sds-assumptions \
  --report .artifacts/sds-cache/full-report.json \
  --out .artifacts/sds-cache/assumption-validation-heuristics.json \
  --sample-ok 0 \
  --sample-fail 6 \
  --sample-seed 123
```

Observed results:

- `Aggregate derived_status: partial=6`
- The six hazards hit the expected failure modes (`candidate_missing_density`, `candidate_missing_heuristics`,
  `candidate_missing_clp_bands`).
- PDFs were cached under `.artifacts/sds-cache-assumptions/files/` for the sample hazards (including the ones that
  probed as `fail`), enabling offline SDS viewing independent of derived completeness.

Unit tests added for strict vs best-effort cache semantics:

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_index_store.py
```

## Small-slice implementation (PR-0062 backend: draft `missing_flags` + `export_gate`)

This slice wires the draft endpoint to run best-effort (`require_complete=false`) and returns explicit contract flags
derived from SDS cache completeness (heuristics/density/clp) so the SPA can gate export deterministically.

### Evidence (local run as of 2026-02-18)

Unit tests for handler behavior (flags + gate):

```bash
pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py
```

Live API check (login + POST risk draft) shows the draft payload contains both `missing_flags` and `export_gate` and
that `export_gate.ready=false` when SDS-derived inputs are missing (NaCl sample).

## Small-slice implementation (PR-0062 frontend: gate export + SDS buttons via `export_gate`/flags)

This slice updates the SPA to treat the backend as the source of truth for export gating:

- Export/Save buttons are gated by `draft.export_gate.ready` (not local heuristics).
- SDS open is blocked with an explicit toast when `sds_ref` is missing or `missing_flags` includes `sds_pdf_missing`.
- OpenAPI types are regenerated so the SPA compiles against the new contract.

Evidence (local run as of 2026-02-18):

```bash
pdm run fe-gen-api-types
pdm run fe-type-check
pdm run fe-test
```

## Implementation plan

This PR is executed as **small, data-driven slices**. Each slice is validated against real cached PDFs / real API
responses before adding more code.

### Slice 1 (DONE): Assumption validation (truthy failure taxonomy)

- Add CLI helper to probe the fetch+derive pipeline against a small sample from the full seed report:
  - `src/skriptoteket/cli/commands/validate_sds_assumptions.py`
- Evidence (local, 2026-02-18):
  - `PYTHONPATH=src pdm run python -m skriptoteket.cli validate-sds-assumptions --report .artifacts/sds-cache/full-report.json --out .artifacts/sds-cache/assumption-validation-heuristics.json --sample-ok 0 --sample-fail 6 --sample-seed 123`

### Slice 2 (DONE): Cache partial SDS-derived inputs (density/clp/heuristics)

- Add `require_complete` to SDS index store so draft callers can consume partial cached entries:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_index_store.py`
  - `src/skriptoteket/protocols/reagent_prep_chef.py`
- Ensure fetcher returns “best partial” candidate instead of dropping the PDF on incomplete derivation:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`
- Evidence (unit, 2026-02-18):
  - `pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_index_store.py`

### Slice 3 (DONE): Best-effort risk draft contract (missing_flags + export_gate)

- Backend:
  - Contract models: `src/skriptoteket/application/curated_apps/reagent_prep_chef.py`
  - Handler best-effort draft: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`
  - Route uses `require_complete=false` for draft: `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`
- Frontend:
  - Gate export/save by `draft.export_gate.ready`: `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefRisk.ts`
  - SDS open blocked when SDS missing offline: `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefStepRisk.vue`
  - OpenAPI types refreshed: `frontend/apps/skriptoteket/src/api/openapi.d.ts`
- Evidence (local, 2026-02-18):
  - `pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py`
  - `pdm run fe-gen-api-types && pdm run fe-type-check && pdm run fe-lint && pdm run fe-test`

### Slice 4 (DONE): Make the seed report actionable (ok/partial/fail) and build a fresh baseline

Goal: stop conflating “no PDF exists” with “PDF exists but derived signals are missing”.

- Add `--best-effort` seeding mode to `seed-sds-cache`:
  - Cache as much as possible (`require_complete=false`), but report each hazard as:
    - `ok`: has PDF + all required derived signals present
    - `partial`: has PDF but missing one or more derived signals (density/clp/heuristics)
    - `fail`: no usable PDF candidate / fetch failed
- Run a fresh baseline with best-effort mode, store the report under `.artifacts/`:
  - `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache --only-missing --best-effort --no-fail-fast --concurrency 4 --report .artifacts/sds-cache/full-report-best-effort.json`
- Use that report to select a small “top partial causes” set (3–5 hazards per missing category) for parser iteration.

Evidence (local, 2026-02-18):

- Report: `.artifacts/sds-cache/full-report-best-effort.json`
- Log: `.artifacts/sds-cache/seed-best-effort.log`
- Summary: `ok=10 partial=151 fail=3 total=164` (fail keys: `CuCl2·2H2O`, `CuS`, `SnO2`)
- Missingness within `partial` (counts): `clp_bands=151`, `density_g_ml=121`, `heuristics=72`
- Top partial combos: `clp_bands+density_g_ml=70`, `clp_bands+density_g_ml+heuristics=51`, `clp_bands+heuristics=21`, `clp_bands=9`

### Slice 5 (DONE): Add explicit `draft.sds.pdf_available` + move UI off the `sds_ref` heuristic

Goal: make the SDS button gating a first-class contract instead of “string presence”.

- Backend:
  - Add `ReagentPrepChefSdsSnapshot` and include it in the draft payload (`draft.sds.pdf_available`,
    `draft.sds.sds_ref`, `draft.sds.sources`).
  - Remove the legacy `draft.sds_ref` field from the contract (use `draft.sds.sds_ref`).
- Frontend:
  - Gate the SDS button on `draft.sds.pdf_available` (no more `sds_ref` heuristics).
  - Regenerate OpenAPI types; keep compile/typecheck green.

Evidence (local, 2026-02-18):

- Backend + routes tests:
  - `pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py tests/unit/web/reagent_prep_chef/test_risk_routes.py`
- Lint/type/docs:
  - `pdm run lint`, `pdm run docs-validate`
- Frontend:
  - `pdm run fe-gen-api-types && pdm run fe-type-check && pdm run fe-lint && pdm run fe-test`

### Slice 6 (IN PROGRESS): Parsing improvements driven by the baseline report

Goal: improve the dominant “partial” outcomes (`clp_bands`, `density_g_ml`, `heuristics`) using a small, real-data
sample set so we can validate changes against known failure modes before broadening.

#### Truthy sample set v1 (from `.artifacts/sds-cache/full-report-best-effort.json`)

Selection criteria:

- Must exist in the 2026-02-18 baseline report (`status=partial` or `status=ok`).
- Must have a cached PDF file in `/tmp/skriptoteket/artifacts/sds-cache/files/` (so we can open/debug it).
- Cover each missing combo (top causes), **and** include at least one “real SDS” PDF source (not only
  OSHA/CFR/fact-sheets) to avoid overfitting to non-SDS documents.

Partial samples (grouped by `missing`):

- `["clp_bands"]` (OSHA SDS guidance PDF fallback; CLP bands missing only)
  - `Na2CO3` — Natriumkarbonat
  - `Ca(OH)2` — Kalciumhydroxid
  - `C7H6O3` — Salicylsyra
- `["clp_bands","heuristics"]` (CFR hazard table + NJ fact sheet)
  - `HF` — Fluorvätesyra
  - `H2SO4` — Svavelsyra
  - `H2O2` — Väteperoxid
  - `C2H6O` — Etanol
  - `C7H6O2` — Bensoesyra (NJ fact sheet)
- `["clp_bands","density_g_ml"]` (OSHA fallback + real SDS variants)
  - `CaCl2` — Kalciumklorid (OSHA fallback)
  - `CaC2` — Kalciumkarbid (Carl Roth SDS)
  - `Cu2O` — Koppar(I)oxid (SDS)
  - `CuO` — Koppar(II)oxid (SDS)
  - `SrCl2` — Strontiumklorid (ChemicalBook SDS)
- `["clp_bands","density_g_ml","heuristics"]` (CFR hazard table + NJ fact sheets)
  - `K2Cr2O7` — Kaliumdikromat
  - `KOH` — Kaliumhydroxid
  - `NH4NO3` — Ammoniumnitrat
  - `NH4Cl` — Ammoniumklorid (NJ fact sheet)
  - `S` — Svavel (NJ fact sheet)

OK anchors (regression):

- `C3H6O` — Aceton
- `AlCl3` — Aluminiumklorid
- `Al2O3` — Aluminiumoxid

True fail keys (no cached PDF / no usable candidate found in baseline):

- `CuCl2·2H2O`, `CuS`, `SnO2`

#### Slice 6.1 (DONE): Density extraction unit normalization (PubChem)

Observation (real baseline data): PubChem “Density” sections commonly include units such as `g/cm³` (unicode
superscript) and `g/cu cm`, which previously caused `extract_density_g_ml` to return `None` for many hazards
(e.g. `CaCl2`, `K2Cr2O7`).

Implementation:

- Expand unit parsing + normalization in:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/pubchem_extractors.py`

Evidence (unit):

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_pubchem_extractors_density.py
```

Evidence (real data, fresh cache root):

- Report: `.artifacts/sds-cache/slice-6-density-check-report.json`
- Result: `CaCl2` moved from missing `["clp_bands","density_g_ml"]` → `["clp_bands"]`; `K2Cr2O7` moved from missing
  `["clp_bands","density_g_ml","heuristics"]` → `["clp_bands","heuristics"]`.

#### Slice 6.2 (DONE): Reject false-positive “SDS” PDFs + pin failure root causes

Observation (truthy sample set v1, 2026-02-18): the dominant “partial” cases were caused by **non-SDS PDFs** being
selected as the SDS document:

- OSHA SDS-format guidance PDF (`OSHA3514.pdf`) → not substance-specific SDS
- CFR hazmat regulations PDFs (`CFR-...-title49-...-part171/part172.pdf`) → not SDS
- NJ “Right to Know” hazardous substance fact sheets (`rtkweb/documents/fs/*.pdf`) → not SDS

These documents can contain the phrase “Safety Data Sheet” and section-like numbering, which previously made them pass
`is_sds_document`, producing misleading “SDS available” UX while still missing `clp_bands`/`heuristics`.

Implementation (fail-closed, no guesswork):

- Filter known false-positive URLs out of candidate selection:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_pdf_providers.py`
- Harden SDS document validation to reject guidance/regulations/fact-sheets and require SDS-like section structure:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/text_extractors.py`
- Pin root causes in validation output:
  - Add `hazard=<key>` prefix to progress logs and include `error_code` + `error_details` (e.g. attempted CIDs) in the
    seed report JSON:
    - `src/skriptoteket/cli/commands/seed_sds_cache.py`
  - Include structured details when best-effort SDS fetch fails (attempted CIDs, best-partial info):
    - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`

Evidence (unit):

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_document_detection.py
```

Evidence (real data, truthy sample set v1, fresh cache root):

- Report: `.artifacts/sds-cache/slice-6-sample-report-v3.json`
- Log (root cause pinned per hazard): `.artifacts/sds-cache/slice-6-sample-seed-v3.log`
- Summary: `ok=3 partial=4 fail=14 total=21`
  - `partial` (real SDS PDFs): `CaC2`, `CuO`, `Cu2O`, `SrCl2` (all missing `density_g_ml` + `clp_bands`)
  - `fail`: no acceptable SDS PDF candidate after quality filters (fail-closed; do not cache/present misleading PDFs)

#### Slice 6.3 (DONE): Density fallback from SDS PDF text (Section 9)

Observation (after Slice 6.2): the only remaining real SDS PDFs in the truthy sample were missing density because
PubChem has no density heading for their CIDs:

- `CaC2`, `CuO`, `Cu2O`, `SrCl2` → `pubchem_density=None` (verified)

However, several of the SDS PDFs contain explicit density lines (typically in Section 9), so we can extract density
deterministically (no guessing) and unlock downstream CLP band conversion attempts.

Implementation:

- Add PDF-text density extractor (Section 9 preferred):
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/density.py`
- Use it as a fallback when PubChem density is missing:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`

Evidence (unit):

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_pdf_density_extractor.py
```

Evidence (real data, fresh cache root):

- Report: `.artifacts/sds-cache/slice-6-density-from-pdf-report.json`
- Log: `.artifacts/sds-cache/slice-6-density-from-pdf-seed.log`
- Result: `CaC2`, `CuO`, `Cu2O` moved from missing `["clp_bands","density_g_ml"]` → `["clp_bands"]` (still missing
  `clp_bands`); `SrCl2` remains missing density (SDS contains only “Vapour density” / “Relative density” headings with
  no numeric value).

#### Slice 6.4 (DONE): Curated SDS linkouts for KOH/H2SO4/H2O2 (truthy CLP parser inputs)

Observation (truthy sample set v1): after Slice 6.2 hardening, several “high value” hazards fail-closed because
PubChem candidates are non-SDS PDFs (CAS terms PDF, NJ RTK act PDF), leaving no usable SDS PDF to cache.

Goal: add a tiny curated linkout slice so we can iterate the CLP-band parser on **real SDS PDFs** for these hazards.

Implementation:

- Add curated linkouts (and bump `as_of`) in:
  - `data/sds_linkouts/curated.json` (CIDs: `14797` = `KOH`, `1118` = `H2SO4`, `784` = `H2O2`)
- Fix a real false-negative discovered during validation: many real SDS PDFs contain the phrase “Right to Know” in
  regulatory sections; our non-SDS filter was rejecting those even when the structure was clearly SDS-like.
  - Narrow fact-sheet rejection to the explicit “Hazardous Substance Fact Sheet” title:
    `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/text_extractors.py`
  - Pin the regression:
    `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_document_detection.py`

Evidence (unit):

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_document_detection.py
```

Evidence (real data, fresh cache root):

```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/slice-6-4 \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'KOH' --only 'H2SO4' --only 'H2O2' \\
  --report .artifacts/sds-cache/slice-6-4-report.json
```

- Report: `.artifacts/sds-cache/slice-6-4-report.json`
- Log: `.artifacts/sds-cache/slice-6-4-seed.log`
- Summary: `ok=0 partial=3 fail=0 total=3` (all three cached; missing only `clp_bands`)

#### Slice 6.4.1 (DONE): Validate `is_sds_document` on pinned real PDFs (no regressions)

Concern: Slice 6.4 changed the “Right to Know” non-SDS rejection to avoid false negatives on real SDS documents. Before
iterating CLP parsing further, we validate that the SDS detector still reject the previously observed false positives
(OSHA guidance, CFR regulations, NJ fact sheets, CAS terms PDF).

Implementation:

- Add a small network-backed validation harness (local-only) that downloads pinned real PDFs and checks that
  `is_sds_document` matches an expected SDS/non-SDS label:
  - `src/skriptoteket/cli/commands/validate_sds_document_detector.py`

Evidence (real data):

```bash
PYTHONPATH=src pdm run python -m skriptoteket.cli validate-sds-document-detector \\
  --out .artifacts/sds-cache/slice-6-4-doc-detector-report.json
```

- Report: `.artifacts/sds-cache/slice-6-4-doc-detector-report.json` (summary: `ok=9 fail=0 skipped=0`)
- Log: `.artifacts/sds-cache/slice-6-4-doc-detector.log`

#### Slice 6.5 (PARTIAL): Iterate CLP-band parser on truthy SDS PDFs (H2SO4 ok; KOH/H2O2 still missing)

Root causes pinned from real SDS content (Slice 6.4 PDFs):

- `H2SO4` (Carl Roth) includes CLP SCL lines in **Section 3** (“Specific Conc. Limits”), while Section 2 contains only
  hazard classification (no `C ≥ …%` / `…% ≤ C < …%` bands). The previous parser only scanned Section 2 when present,
  so it returned no bands.
- `KOH` and `H2O2` (Columbus Chemical) provide hazard statements for the product, but do **not** contain any
  concentration-limit/SCL lines in extractable text, so the parser still cannot derive `clp_bands` from these PDFs.

Implementation:

- Scan both Section 2 and Section 3 for concentration-band lines (instead of “Section 2 only if present”):
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/clp_bands.py`
- Allow CLP SCL percent lines without an explicit per-line basis when the section indicates a “Specific Conc. Limits”
  table (treat `%` as `w/w` and record a note):
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/clp_bands.py`
- Pin the regression with a unit test that mirrors the Section 2 vs Section 3 split:
  - `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_clp_bands_parser.py`

Evidence (unit):

```bash
PYTHONPATH=src pdm run pytest -q \\
  tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_clp_bands_parser.py
```

Evidence (real data, fresh cache root):

```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/slice-6-5 \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'KOH' --only 'H2SO4' --only 'H2O2' \\
  --report .artifacts/sds-cache/slice-6-5-report.json
```

- Signal scan artifact (what the PDFs actually contain): `.artifacts/sds-cache/slice-6-5-clp-signal-scan.json`
- Report: `.artifacts/sds-cache/slice-6-5-report.json`
- Log: `.artifacts/sds-cache/slice-6-5-seed.log`
- Result: `H2SO4` moved `partial → ok`; `KOH` and `H2O2` remain `partial` (missing `clp_bands`).

#### Slice 6.6 (DONE): Curate truthy SDS PDFs w/ SCL lines (KOH ok; H2O2 now “parser failure”, not “content missing”)

Root cause (pre-Slice 6.6):

- `KOH` and `H2O2` (Columbus Chemical) did not contain extractable SCL / concentration-limit lines, so we had no
  truthy input to iterate the CLP-band parser against.

Implementation:

- Update curated SDS linkouts to point to EU REACH/CLP-style SDS PDFs with “Specific concentration limit(s)” tables:
  - `data/sds_linkouts/curated.json` (CID `14797` = `KOH`, CID `784` = `H2O2`)

Evidence (real data, fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-6-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'KOH' --only 'H2O2' \\
  --report .artifacts/sds-cache/slice-6-6-report.json
```

- Report: `.artifacts/sds-cache/slice-6-6-report.json`
- Log: `.artifacts/sds-cache/slice-6-6-seed.log`
- Result: `KOH` moved `partial → ok`; `H2O2` remains `partial` (missing `clp_bands`).
- Pinned parser root cause (real extracted Section 3 lines): `.artifacts/sds-cache/slice-6-6-h2o2-scl-snippet.json`
  - The SDS **does** contain SCL lines, but PDF text extraction splits some ranges across lines (missing max/% on the
    same line), so the current line-based parser fails to match them.

#### Slice 6.7 (DONE): CLP SCL line-wrapping normalization (H2O2 partial → ok)

Root cause pinned (Slice 6.6):

- The H2O2 SDS contains SCL lines, but some concentration ranges are split across lines and some trailing `%` symbols
  appear on their own line after PDF text extraction.

Implementation:

- Add a small “continuation line” stitcher for SCL tables (only merges obvious cases; fail-closed):
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/clp_bands.py`
- Treat “Specific concentration limit:” (singular) as an SCL section hint for default percent basis inference:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/clp_bands.py`
- Pin the failure mode with a unit test derived from the real extracted line shape:
  - `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_clp_bands_parser.py`

Evidence (unit):

```bash
PYTHONPATH=src pdm run pytest -q \\
  tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_clp_bands_parser.py
```

Evidence (real data, fresh cache root; extended truthy sample set):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-7-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'KOH' --only 'H2SO4' --only 'H2O2' \\
  --report .artifacts/sds-cache/slice-6-7-report.json
```

- Report: `.artifacts/sds-cache/slice-6-7-report.json`
- Log: `.artifacts/sds-cache/slice-6-7-seed.log`
- Result: `ok=3 partial=0 fail=0` (H2O2 moved `partial → ok`).
- Pinned extracted SCL lines + parsed hazard codes: `.artifacts/sds-cache/slice-6-7-h2o2-scl-snippet.json`

#### Slice 6.8 (DONE): Seed “truthy sample set v1” with fresh cache root + pin root causes (no CLP parser work yet)

Goal: validate the PR-0062 “truthy sample set v1” (from the 2026-02-18 baseline report) against a **fresh**
`ARTIFACTS_ROOT`, then pin why each `fail` / `partial` happened.

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-8-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 2 \\
  --only 'Na2CO3' --only 'Ca(OH)2' --only 'C7H6O3' \\
  --only 'HF' --only 'H2SO4' --only 'H2O2' --only 'C2H6O' --only 'C7H6O2' \\
  --only 'CaCl2' --only 'CaC2' --only 'Cu2O' --only 'CuO' --only 'SrCl2' \\
  --only 'K2Cr2O7' --only 'KOH' --only 'NH4NO3' --only 'NH4Cl' --only 'S' \\
  --only 'C3H6O' --only 'AlCl3' --only 'Al2O3' \\
  --report .artifacts/sds-cache/slice-6-8-report.json | tee .artifacts/sds-cache/slice-6-8-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-8-report.json` (summary: `ok=6 partial=4 fail=11 total=21`)
- Log: `.artifacts/sds-cache/slice-6-8-seed.log`
- FAIL root causes (structured from log; candidates tried + rejected as non-SDS): `.artifacts/sds-cache/slice-6-8-fail-attempts.json`
- PARTIAL CLP root causes (SCL scan): `.artifacts/sds-cache/slice-6-8-snippets/*-scl-snippet.json`
  - All `partial` keys with `missing=['clp_bands']` had **no SCL content** in Section 2/3 (`scl_hint_lines=[]`,
    `scl_row_candidate_lines=[]`), i.e. not a parser failure-mode.

#### Slice 6.8.1 (DONE): Curate SCL-bearing SDS PDFs for NaOH/HCl/HF (make fresh-cache seeding deterministic)

Root cause (Slice 6.8):

- For `NaOH` / `HCl` / `HF`, PubChem “Safety and Hazards” candidate URLs were dominated by non-SDS PDFs
  (CAS “terms”, NJ RTK Act, EPA fact sheets). With a fresh cache root, this causes `fail` and blocks CLP parsing work.

Implementation:

- Add curated SDS linkouts (truthy PDFs) for:
  - `NaOH` (CID `14798`)
  - `HCl` (CID `313`)
  - `HF` (CID `14917`)
  - File: `data/sds_linkouts/curated.json`

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-8-scl-v1-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'NaOH' --only 'HCl' --only 'HF' --only 'KOH' --only 'H2SO4' --only 'H2O2' \\
  --report .artifacts/sds-cache/slice-6-8-scl-v1-report.json | tee .artifacts/sds-cache/slice-6-8-scl-v1-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-8-scl-v1-report.json` (summary: `ok=5 partial=1 fail=0`)
- Snippets (SCL rows + parsed hazard codes): `.artifacts/sds-cache/slice-6-8-scl-v1-snippets/*-scl-snippet.json`

#### Slice 6.8.2 (DONE): Prefer SDS PDF density when present (fix gas-phase PubChem density for HCl/HF)

Root cause pinned (real data):

- For `HCl`/`HF`, PubChem density can be present but represent gas-phase density (e.g. `g/L`), which is wrong for
  aqueous stock solutions described by the SDS PDFs.
- On the curated Roth SDS PDFs, Section 9 density is parseable (`extract_density_g_ml_from_sds_text`) and yields the
  expected liquid density (e.g. `HCl ~1.19 g/mL`, `HF ~1.18 g/mL`).

Implementation:

- Fetcher now prefers `density_from_pdf` over PubChem density when the PDF contains a density line:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`
- Unit tests pin the selection behavior:
  - `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_fetcher_density_selection.py`

Evidence (unit):

```bash
PYTHONPATH=src pdm run pytest -q \\
  tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_fetcher_density_selection.py
```

Evidence (real data; fresh cache root; verifies index density values):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-8-scl-v2-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'NaOH' --only 'HCl' --only 'HF' --only 'KOH' --only 'H2SO4' --only 'H2O2' \\
  --report .artifacts/sds-cache/slice-6-8-scl-v2-report.json | tee .artifacts/sds-cache/slice-6-8-scl-v2-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-8-scl-v2-report.json` (summary: `ok=5 partial=1 fail=0`)
- Snippets (density + SCL rows): `.artifacts/sds-cache/slice-6-8-scl-v2-snippets/*-scl-snippet.json`
  - `HCl` density now `1.19` (was `0.001639` in v1 run)
  - `HF` density now `1.18` (was `0.29` in v1 run)

#### Slice 6.9 (DONE): Curate SDS linkouts for top fresh-cache FAILs (CaCl2/Na2CO3/NH4Cl)

Root cause pinned (Slice 6.8):

- For these keys, PubChem candidates are either missing entirely (`candidates_missing=true`) or dominated by non-SDS PDFs
  (CAS terms / NJ RTK Act). With a fresh `ARTIFACTS_ROOT`, the pipeline fail-closes before any parsing work can start.
- Evidence: `.artifacts/sds-cache/slice-6-8-fail-attempts.json` (see `fail_keys` + per-key candidate lists).

Implementation:

- Add curated SDS linkouts (truthy PDFs) for:
  - `CaCl2` (CID `5284359`)
  - `Na2CO3` (CID `10340`)
  - `NH4Cl` (CID `25517`)
  - File: `data/sds_linkouts/curated.json`
- Validate via the seed loop on a fresh cache root and require `fail → partial|ok` (SDS bytes present; PDF passes
  `is_sds_document`).

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-9-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'CaCl2' --only 'Na2CO3' --only 'NH4Cl' \\
  --report .artifacts/sds-cache/slice-6-9-report.json | tee .artifacts/sds-cache/slice-6-9-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-9-report.json` (summary: `ok=0 partial=3 fail=0 total=3`)
- Log: `.artifacts/sds-cache/slice-6-9-seed.log`

Root causes pinned (best-effort missing `clp_bands`):

- SCL scan snippets (Section 2/3): `.artifacts/sds-cache/slice-6-9-scl-snippets/*-scl-snippet.json`
  - All 3 entries have `parsed_band_count=0` with no `scl_row_candidate_lines` (i.e. not a CLP parser bug).
  - `NH4Cl` includes Section 3 “Specific Conc. Limits” **headings** but no actual `C ...` SCL rows.

#### Slice 6.10 (DONE): Re-run “truthy sample set v1” with fresh cache root (measure fail-count delta)

Goal: measure how much fresh-cache `fail` decreases after Slice 6.8.1–6.9 curated several high-impact CIDs.

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-10-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 2 \\
  --only 'Na2CO3' --only 'Ca(OH)2' --only 'C7H6O3' \\
  --only 'HF' --only 'H2SO4' --only 'H2O2' --only 'C2H6O' --only 'C7H6O2' \\
  --only 'CaCl2' --only 'CaC2' --only 'Cu2O' --only 'CuO' --only 'SrCl2' \\
  --only 'K2Cr2O7' --only 'KOH' --only 'NH4NO3' --only 'NH4Cl' --only 'S' \\
  --only 'C3H6O' --only 'AlCl3' --only 'Al2O3' \\
  --report .artifacts/sds-cache/slice-6-10-report.json | tee .artifacts/sds-cache/slice-6-10-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-10-report.json` (summary: `ok=6 partial=8 fail=7 total=21`)
- Log: `.artifacts/sds-cache/slice-6-10-seed.log`
- Delta vs Slice 6.8 (fresh-cache): `fail 11 → 7` (the curated keys `HF`/`CaCl2`/`Na2CO3`/`NH4Cl` moved `fail → partial`).

Remaining fresh-cache `fail` keys (after Slice 6.9): `NH4NO3`, `C2H6O`, `C7H6O2`, `Ca(OH)2`, `K2Cr2O7`,
`C7H6O3`, `S`.

#### Slice 6.11 (DONE): Curate Roth SDS linkouts for 3 remaining FAIL keys (C2H6O/C7H6O2/K2Cr2O7)

Root cause pinned (Slice 6.8):

- PubChem “Safety and Hazards” candidates can be missing or dominated by non-SDS PDFs (CAS terms / NJ RTK Act),
  causing fresh-cache `fail` due to `is_sds_document` fail-closed behavior.
- Evidence: `.artifacts/sds-cache/slice-6-8-fail-attempts.json`

Implementation:

- Add curated SDS linkouts (truthy PDFs) for:
  - `C2H6O` (CID `702`) — Ethanol (Roth MT-EN)
  - `C7H6O2` (CID `243`) — Benzoic acid (Roth MT-EN)
  - `K2Cr2O7` (CID `24502`) — Potassium dichromate (Roth MT-EN)
  - File: `data/sds_linkouts/curated.json`

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-11-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'C2H6O' --only 'C7H6O2' --only 'K2Cr2O7' \\
  --report .artifacts/sds-cache/slice-6-11-report.json | tee .artifacts/sds-cache/slice-6-11-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-11-report.json` (summary: `ok=1 partial=2 fail=0 total=3`)
- Log: `.artifacts/sds-cache/slice-6-11-seed.log`

Root causes pinned (best-effort missing `clp_bands`):

- SCL scan snippets (Sections 2/3): `.artifacts/sds-cache/slice-6-11-scl-snippets/*-scl-snippet.json`
  - `C2H6O` and `C7H6O2` have no SCL hint lines or SCL row candidates in Sections 2/3 (`parsed_band_count=0`),
    i.e. not a CLP parser bug.
  - `K2Cr2O7` contains an SCL row and parses `parsed_band_count=1` (now `ok`).

#### Slice 6.12 (DONE): Re-run “truthy sample set v1” after Slice 6.11 (measure new fail-count)

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-12-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 2 \\
  --only 'Na2CO3' --only 'Ca(OH)2' --only 'C7H6O3' \\
  --only 'HF' --only 'H2SO4' --only 'H2O2' --only 'C2H6O' --only 'C7H6O2' \\
  --only 'CaCl2' --only 'CaC2' --only 'Cu2O' --only 'CuO' --only 'SrCl2' \\
  --only 'K2Cr2O7' --only 'KOH' --only 'NH4NO3' --only 'NH4Cl' --only 'S' \\
  --only 'C3H6O' --only 'AlCl3' --only 'Al2O3' \\
  --report .artifacts/sds-cache/slice-6-12-report.json | tee .artifacts/sds-cache/slice-6-12-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-12-report.json` (summary: `ok=7 partial=10 fail=4 total=21`)
- Log: `.artifacts/sds-cache/slice-6-12-seed.log`
- Delta vs Slice 6.10: `fail 7 → 4` (`C2H6O`/`C7H6O2` moved `fail → partial`; `K2Cr2O7` moved `fail → ok`).

Remaining fresh-cache `fail` keys (after Slice 6.11): `NH4NO3`, `Ca(OH)2`, `C7H6O3`, `S`.

#### Slice 6.13 (DONE): Option B — allow best-effort export when SCL/CLP bands are missing

Goal: stop blocking export on SDS PDFs that are “truthy” but do not contain SCL rows (or do not cover the selected
target concentration). Instead, fall back to SDS-level GHS/CLP signals (`hazard_codes` + `pictograms` +
`signal_word`) with explicit notes + warnings.

Decision:

- Keep `missing_flags` explicit (`sds_clp_bands_missing`, `clp_unavailable_for_target`) so the UI/PDF can surface
  “best effort” semantics.
- Remove `sds_clp_bands_missing` and `clp_unavailable_for_target` from the export-blocking set.
- When we cannot select a concentration band, populate `draft.clp` from the SDS snapshot and add a pinned note:
  - `SCL saknas i SDS; visar SDS-koder (best effort).`
  - `SCL saknas för vald koncentration; visar SDS-koder (best effort).`

Implementation:

- Best-effort CLP fallback + export gating update:
  - `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`
- Unit tests pin the new contract:
  - `tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py`

Evidence (unit):

```bash
PYTHONPATH=src pdm run pytest -q \\
  tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py
```

#### Slice 6.14 (DONE): Curate SDS linkouts for remaining fresh-cache FAIL keys (NH4NO3/Ca(OH)2/C7H6O3/S)

Root cause (Slice 6.12 → Slice 6.8 fail-attempts taxonomy):

- Remaining FAIL keys were dominated by non-SDS PDFs (CAS “terms”, NJ RTK Act) or had no PubChem “Safety and Hazards”
  candidates at all (`candidates_missing=true`).
- Evidence: `.artifacts/sds-cache/slice-6-8-fail-attempts.json` (per-key candidate lists for `NH4NO3`, `Ca(OH)2`,
  `C7H6O3`, `S`).

Implementation:

- Add curated SDS linkouts (truthy PDFs) for:
  - `NH4NO3` (CID `22985`)
  - `Ca(OH)2` (CID `6093208`)
  - `C7H6O3` (CID `338`)
  - `S` (CID `5362487`)
- File: `data/sds_linkouts/curated.json`

Evidence (real data; fresh cache root; verify `fail → partial` for all 4 keys):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-14-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 1 \\
  --only 'NH4NO3' --only 'Ca(OH)2' --only 'C7H6O3' --only 'S' \\
  --report .artifacts/sds-cache/slice-6-14-report.json | tee .artifacts/sds-cache/slice-6-14-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-14-report.json` (summary: `ok=0 partial=4 fail=0 total=4`)
- Log: `.artifacts/sds-cache/slice-6-14-seed.log`

Root causes pinned (best-effort missing `clp_bands`):

- SCL scan snippets (Sections 2/3): `.artifacts/sds-cache/slice-6-14-scl-snippets/*-scl-snippet.json`
  - All 4 entries have `parsed_band_count=0` with no `section_2_scl_row_candidate_lines` or
    `section_3_scl_row_candidate_lines` (i.e. not a CLP parser bug).

#### Slice 6.15 (DONE): Re-run “truthy sample set v1” after Slice 6.14 (measure new fail-count)

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-15-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 2 \\
  --only 'Na2CO3' --only 'Ca(OH)2' --only 'C7H6O3' \\
  --only 'HF' --only 'H2SO4' --only 'H2O2' --only 'C2H6O' --only 'C7H6O2' \\
  --only 'CaCl2' --only 'CaC2' --only 'Cu2O' --only 'CuO' --only 'SrCl2' \\
  --only 'K2Cr2O7' --only 'KOH' --only 'NH4NO3' --only 'NH4Cl' --only 'S' \\
  --only 'C3H6O' --only 'AlCl3' --only 'Al2O3' \\
  --report .artifacts/sds-cache/slice-6-15-report.json | tee .artifacts/sds-cache/slice-6-15-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-15-report.json` (summary: `ok=7 partial=14 fail=0 total=21`)
- Log: `.artifacts/sds-cache/slice-6-15-seed.log`
- Delta vs Slice 6.12: `fail 4 → 0` (all 4 remaining FAIL keys moved `fail → partial` after curation).

Remaining PARTIAL keys (truthy PDFs, but missing `clp_bands`):

- All PARTIAL keys are `missing=['clp_bands']` except `SrCl2` which is `missing=['clp_bands', 'density_g_ml']`.

#### Slice 6.16 (DONE): Full seed run (164 hazards) with fresh cache root (baseline + failure taxonomy)

Goal: re-run the full hazard set with a **fresh** `ARTIFACTS_ROOT` to quantify how much of the data problem is:

- “we fetched an SDS but our parsers/heuristics are incomplete” vs
- “we never get a usable SDS PDF candidate at all”.

Evidence (real data; fresh cache root):

```bash
ARTIFACTS_ROOT=/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/sds-cache/slice-6-16-cache-root \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 2 \\
  --report .artifacts/sds-cache/slice-6-16-report.json | tee .artifacts/sds-cache/slice-6-16-seed.log
```

- Report: `.artifacts/sds-cache/slice-6-16-report.json` (summary: `ok=11 partial=14 fail=139 total=164`)
- Log: `.artifacts/sds-cache/slice-6-16-seed.log`
- FAIL root causes (structured from log; per-key candidate lists + verdict): `.artifacts/sds-cache/slice-6-16-fail-attempts.json`
  - Taxonomy (from `summary.mode_counts`):
    - `no_candidates=79` (provider registry returned no PDF candidates)
    - `non_sds_candidates=59` (candidates fetched but rejected by `is_sds_document`)
    - `pdf_no_hazard_codes=1` (candidate fetched, but hazard codes could not be extracted)
  - Non-SDS dominance (from `summary.top_non_sds_urls`): NJ “RTK Act” PDF + CAS “chemical safety library terms”.

Interpretation:

- This output **does not** mean PR-0062 is “blocked” or “not working”; it means our *current* SDS PDF candidate
  discovery (curated linkouts + PubChem linkout/safety/LCSS URLs) cannot produce a usable SDS PDF for most hazards.
- The dominant problem in the full set is therefore **upstream coverage**, not CLP-band parsing. Parser work only moves
  the needle for the subset where we actually get an SDS PDF and extract hazard signals from it.
- PR-0062’s path out of the historical “ok=10 fail=154” prefetch state is the **best-effort draft contract**
  (`missing_flags` + server-driven `export_gate`) so the app remains usable while SDS coverage is improved
  incrementally where it matters most.

#### Repeatable validation loop (avoid stale cache masking parser changes)

Important: in best-effort mode, the SDS index store returns cached partial entries (`require_complete=false`). To
ensure parser improvements are validated against **fresh derivation**, run the slice using a **fresh cache root**
(`ARTIFACTS_ROOT`) per iteration.

Example (one-off validation run for the sample set):

```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts-pr-0062-slice-6 \\
PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache \\
  --best-effort --no-fail-fast --concurrency 2 \\
  --only 'Na2CO3' --only 'Ca(OH)2' --only 'C7H6O3' \\
  --only 'HF' --only 'H2SO4' --only 'H2O2' --only 'C2H6O' --only 'C7H6O2' \\
  --only 'CaCl2' --only 'CaC2' --only 'Cu2O' --only 'CuO' --only 'SrCl2' \\
  --only 'K2Cr2O7' --only 'KOH' --only 'NH4NO3' --only 'NH4Cl' --only 'S' \\
  --only 'C3H6O' --only 'AlCl3' --only 'Al2O3' \\
  --report .artifacts/sds-cache/slice-6-sample-report.json
```

Interpretation: treat `partial → ok` moves for these keys as the minimum evidence threshold before broadening to a
larger set.

## Test plan

- Unit tests for missing-flag derivation (SDS missing / density missing / CLP bands missing / heuristics missing).
- Handler tests for:
  - draft endpoint returns 200 with best-effort payload when SDS is incomplete
  - export-risk-pdf is offline (no fetch) and best-effort when confirmations + context are complete
- SPA tests (Vitest):
  - buttons are gated by `export_gate.ready` and `sds.pdf_available`
  - missing blockers render in UI

## Rollback plan

- Revert contract additions and restore strict draft gating (`require_complete=true`).
- Restore strict export behavior (offline + fail-closed) if we decide best-effort export is too permissive.
