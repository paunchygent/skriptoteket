---
type: pr
id: PR-0071
title: "Reagent Prep Chef — Riskbedömning form aligned with Swedish school praxis"
status: done
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-20-02"
tags: ["curated-apps", "product", "docs", "frontend", "backend"]
acceptance_criteria:
  - "Riskbedömning form fields and required validation are backed by named authoritative sources (Skolverket and/or Arbetsmiljöverket + applicable AFS)."
  - "The form avoids unnecessary documentation and matches common school workflows for teachers."
  - "Frontend required-field gating and backend export validation match the same field set."
  - "UI + exported PDF use the correct document naming (Riskbedömning vs Underlag) based on the researched sources."
---

## Problem

The current Riskbedömning form is an early draft and has not been validated against Swedish school praxis. Teachers are
very sensitive to unnecessary documentation.

## Goal

- Produce a source-backed, teacher-friendly Riskbedömning form that matches real school expectations.
- Update frontend + backend validation to match the researched field set.

## Non-goals

- No “best guess” form requirements.
- No internationalization; Swedish-first only.

## Implementation plan

1. Research + source capture:
   - Produce a reference note under `docs/reference/` with **named sources** and the extracted *minimum required* fields
     for chemical risk documentation in Swedish schools (Skolverket + Arbetsmiljöverket + relevant AFS).
   - Include a mapping table: `current_field` → `required_by_source` → `keep/merge/drop` → `why`.
2. Decision checkpoint (must be explicit in the reference note):
   - Confirm whether the app should produce a **full “Riskbedömning”** or an **“Underlag till riskbedömning”** export.
   - Update all UI copy + PDF titles accordingly (teachers should not be forced into “extra paperwork” wording).
3. Contract + validation alignment:
   - Define the final field set in the backend request model (single source of truth for required/optional).
   - Ensure frontend required-field gating matches the backend export/save validation (no drift).
   - Update `ST-20-02` acceptance criteria if the final field set changes.
4. Implement UX + PDF:
   - Update the SPA form fields, defaults, and helper copy to match the researched minimum.
   - Ensure the exported PDF mirrors the same field set (and does not introduce extra required fields).
5. Tests:
   - Frontend: required-field gating (unit tests).
   - Backend: export/save validation for the same required fields (unit tests).

## Test plan

- `pdm run docs-validate`
- Frontend: `pdm run fe-test` (required-field gating)
- Backend: `pdm run test` (export validation)

## Rollback plan

- Revert to the previous form and validations; keep the reference doc for later iteration.

## Implementation notes (2026-03-04)

1. Source-backed reference and decision checkpoint added:
   - `docs/reference/ref-reagent-prep-chef-riskunderlag-skolpraxis.md`
   - Named sources captured (Skolverket + Arbetsmiljöverket AFS 2023:1 / AFS 2023:10).
   - Explicit decision: exported artifact is named **Underlag till riskbedömning**.
2. Backend single source of truth for required risk-context fields:
   - `src/skriptoteket/application/curated_apps/reagent_prep_chef_risk_contract.py`
   - Both draft gating and export validation now use the same `missing_risk_context_fields(...)` contract.
3. Frontend gating copy now follows backend `draft.export_gate.missing_context_fields`:
   - `frontend/apps/skriptoteket/src/composables/reagentPrepChef/riskExportGate.ts`
   - Removed hardcoded “saknas”-text in `ReagentPrepChefStepRisk.vue`.
4. Naming alignment (UI + export/save):
   - Export filename/content-disposition/save filename changed to `underlag-riskbedomning*.pdf`.
