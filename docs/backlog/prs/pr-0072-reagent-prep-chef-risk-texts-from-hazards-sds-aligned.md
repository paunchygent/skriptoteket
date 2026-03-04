---
type: pr
id: PR-0072
title: "Reagent Prep Chef — Risk texts derived from hazards (SDS-aligned data)"
status: ready
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-20-02"
tags: ["curated-apps", "backend", "data"]
adrs: ["ADR-0067"]
acceptance_criteria:
  - "Riskbedömning risk draft uses complete, subject-specific hazard codes (H/P) for each curated chemical (no generic fallbacks caused by missing codes)."
  - "The hazards dataset is validated/backfilled offline against the SDS markdown corpus (no runtime parsing)."
  - "A gap report is produced for hazards entries that still cannot be validated against SDS markdown."
  - "A school-MVP SDS shortcard dataset is built offline from repo-owned markdown and committed for deterministic portal autofill."
  - "Invariant: parser output is never treated as ground truth; when parser/structure issues arise, all SDS markdown files require manual validation."
---

## Problem

Risk texts are currently driven by the hazards dataset. If hazard codes are missing/incorrect for a chemical, the risk
draft becomes generic or misleading (even when SDS markdown clearly contains the hazard codes).

## Goal

- Make hazard-driven risk drafts reliable by ensuring hazards data is complete and SDS-aligned.
- Keep ADR-0067: no runtime HTTP, no runtime SDS scraping; alignment happens via offline scripts.

## Non-goals

- No runtime parsing of SDS markdown during risk draft generation.
- No CLP “classification engine” based on molarity; stick to curated data.

## Implementation plan

1. Add an offline validator/backfill script:
   - Extract hazard codes from SDS markdown (best-effort regex + section heuristics).
   - Compare to hazards dataset; report gaps and optionally backfill missing hazard codes.
2. Update `hazards.json` (repo-owned) and ensure the risk handler uses the updated codes deterministically.
3. Add a small unit test surface around extraction and matching for a known chemical where the current dataset is wrong.

## Test plan

- `pdm run test`
- `pdm run lint && pdm run typecheck`
- Manual: verify that an affected chemical now shows the correct risk codes in the risk draft.

## Implementation notes (2026-03-04)

1. Added offline shortcard builder:
   - `scripts/build_reagent_prep_chef_sds_shortcards.py`
   - Extracts school-MVP fields (identity, CLP, PPE hints, spill/incompatibility/waste notes).
2. Added parser trust invariant enforcement:
   - `parser_ground_truth=false` in output.
   - If any parser/structure issue appears, report marks manual validation scope as `all_files`.
   - Manual checklist for all SDS markdown files is emitted under `.artifacts/`.
3. Added tests for extraction + invariant behavior:
   - `tests/unit/scripts/test_build_reagent_prep_chef_sds_shortcards.py`

## Rollback plan

- Revert hazards dataset changes and the script; keep reports as artifacts for follow-up.
