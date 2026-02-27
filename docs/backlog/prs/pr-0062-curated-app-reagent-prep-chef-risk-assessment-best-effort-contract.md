---
type: pr
id: PR-0062
title: "Curated app: Reagent Prep Chef — Riskbedömning best effort contract (SDS missing flags + UI gating)"
status: in_progress
owners: "agents"
created: 2026-02-18
updated: 2026-02-19
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
  - export-risk-pdf remains strict + offline and fails closed with clear validation errors
- SPA tests (Vitest):
  - buttons are gated by `export_gate.ready` and `sds.pdf_available`
  - missing blockers render in UI

## Rollback plan

- Revert contract additions and restore strict draft gating (`require_complete=true`).
- Keep export behavior unchanged (strict/offline) throughout.
