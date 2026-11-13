---
type: reference
id: REF-SKRIPT-GENERAL-reference-reagent-prep-chef-hazards-shortcards-alignment-policy
title: 'Reference: Reagent Prep Chef — hazards ↔ shortcards alignment policy'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-reagent-prep-chef-hazard-shortcard-alignment-policy
summary: 'Reference: Reagent Prep Chef — hazards ↔ shortcards alignment policy'
---

## Overview

### Source: Purpose

Define a strict drift policy between:

- runtime hazards dataset: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`
- offline SDS shortcards: `data/reagent_prep_chef/sds/shortcards.json`

The objective is deterministic risk-text generation without silent data skew.

## Facts And Semantics

### Source: H/P policy

### H-codes (blocking contract)

- H-codes are part of runtime risk semantics.
- H-code drift is a hard failure in CI/pre-commit.

### P-codes (non-blocking for now)

- P-codes are currently consumed as shortcard metadata, not runtime hazards contract.
- P-code drift is therefore not a blocking guard condition yet.
- If hazards contract later introduces `p_codes`, the guard must be extended to make P-codes blocking too.

### Source: Remediation workflow

1. Rebuild shortcards:
   - `pdm run sds-build-shortcards`
2. Align hazards from shortcards:
   - `pdm run python -m scripts.align_reagent_prep_chef_hazard_codes_from_shortcards --apply`
3. Re-run guard:
   - `pdm run sds-check-hazard-alignment`
4. Run quality gates:
   - `pdm run lint && pdm run typecheck && pdm run docs-validate`

### Source: Notes

- The alignment report is written to:
  - `.artifacts/reagent_prep_chef/hazard-sds-alignment-report.json`
- Manual validation invariant remains in force from shortcards builder:
  parser output is never ground truth, and manual validation governs dataset trust.

## Decisions And Interpretation

### Source: Contracts and ownership

1. Runtime risk drafting reads hazard codes from `hazards.json`.
2. Shortcards are derived offline from repo-owned SDS markdown and are not legal ground truth.
3. CI/pre-commit guard enforces synchronization rules before merge.

### Source: Guard rules (blocking)

Command:

```bash
pdm run sds-check-hazard-alignment
```

The guard fails when any of the following hold:

1. `shortcards.manual_validation.required` is `true`.
2. A hazards entry has empty `hazard_codes` while shortcard has non-empty H-codes (backfill candidate).
3. Hazards and shortcards both have non-empty H-codes but values differ.
4. A hazards key has no corresponding shortcard entry.
