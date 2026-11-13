---
type: task
id: TASK-SKRIPT-20-02-02
title: Reagent Prep Chef — Risk texts derived from hazards (SDS-aligned data)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-20-02
task_kind: story
acceptance_criteria:
- Riskbedömning risk draft uses complete, subject-specific hazard codes (H/P) for
  each curated chemical (no generic fallbacks caused by missing codes).
- The hazards dataset is validated/backfilled offline against the SDS markdown corpus
  (no runtime parsing).
- A gap report is produced for hazards entries that still cannot be validated against
  SDS markdown.
- A school-MVP SDS shortcard dataset is built offline from repo-owned markdown and
  committed for deterministic portal autofill.
- 'Invariant: parser output is never treated as ground truth; when parser/structure
  issues arise, all SDS markdown files require manual validation.'
---

## Context

Source: `docs/backlog/prs/pr-0072-reagent-prep-chef-risk-texts-from-hazards-sds-aligned.md`. Reagent Prep Chef — Risk texts derived from hazards (SDS-aligned data).

Risk texts are currently driven by the hazards dataset. If hazard codes are missing/incorrect for a chemical, the risk draft becomes generic or misleading (even when SDS markdown clearly contains the hazard codes). - Make hazard-driven risk drafts reliable by ensuring hazards data is complete and SDS-aligned. - Keep ADR-0067: no runtime HTTP, no runtime SDS scraping; alignment happens via offline scripts. - No runtime parsing of SDS markdown during risk draft generation. - No CLP “classification engine” based on molarity; stick to curated data. 1. Add an offline validator/backfill script: - Extract hazard codes from SDS markdown (best-effort regex + section heuristics). - Compare to hazards

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-20-02-02 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

Risk texts are currently driven by the hazards dataset. If hazard codes are missing/incorrect for a chemical, the risk
draft becomes generic or misleading (even when SDS markdown clearly contains the hazard codes).

### Goal

- Make hazard-driven risk drafts reliable by ensuring hazards data is complete and SDS-aligned.
- Keep ADR-0067: no runtime HTTP, no runtime SDS scraping; alignment happens via offline scripts.

### Non-goals

- No runtime parsing of SDS markdown during risk draft generation.
- No CLP “classification engine” based on molarity; stick to curated data.

### Implementation plan

1. Add an offline validator/backfill script:
   - Extract hazard codes from SDS markdown (best-effort regex + section heuristics).
   - Compare to hazards dataset; report gaps and optionally backfill missing hazard codes.
2. Update `hazards.json` (repo-owned) and ensure the risk handler uses the updated codes deterministically.
3. Add a small unit test surface around extraction and matching for a known chemical where the current dataset is wrong.

### Test plan

- `pdm run test`
- `pdm run lint && pdm run typecheck`
- Manual: verify that an affected chemical now shows the correct risk codes in the risk draft.
- `pdm run sds-check-hazard-alignment`

### Implementation notes (2026-03-04)

1. Added offline shortcard builder:
   - `scripts/build_reagent_prep_chef_sds_shortcards.py`
   - Extracts school-MVP fields (identity, CLP, PPE hints, spill/incompatibility/waste notes).
2. Added parser trust invariant enforcement:
   - `parser_ground_truth=false` in output.
   - If any parser/structure issue appears, report marks manual validation scope as `all_files`.
   - Manual checklist for all SDS markdown files is emitted under `.artifacts/`.
3. Added tests for extraction + invariant behavior:
   - `tests/unit/scripts/test_build_reagent_prep_chef_sds_shortcards.py`

4. Added offline hazards↔shortcards alignment script and applied deterministic backfill:
   - `scripts/align_reagent_prep_chef_hazard_codes_from_shortcards.py`
   - Backfill scope this run: 108 entries with empty `hazard_codes` got SDS shortcard H-codes.
   - Report artifact: `.artifacts/reagent_prep_chef/hazard-sds-alignment-report.json`

5. Added invariant test so hazards cannot drift behind shortcards:
   - `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_hazards_store.py`
   - Rule asserted: if shortcard has H-codes for an `sds_ref`, hazards entry for same `key` must not be empty.

6. Added blocking CI/pre-commit guard + policy doc:
   - Guard script: `scripts/check_reagent_prep_chef_hazard_shortcard_alignment.py`
   - Quality wiring: `pyproject.toml` (`lint`) + `.pre-commit-config.yaml`
   - Policy reference: `docs/reference/ref-reagent-prep-chef-hazard-shortcard-alignment-policy.md`

### Rollback plan

- Revert hazards dataset changes and the script; keep reports as artifacts for follow-up.

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
