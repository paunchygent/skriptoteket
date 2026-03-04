---
type: pr
id: PR-0071
title: "Reagent Prep Chef — Riskbedömning form aligned with Swedish school praxis"
status: ready
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

1. Produce a reference note under `docs/reference/` that lists authoritative sources and extracts the minimum required
   documentation fields for chemical risk assessments in school settings.
2. Update the SPA form fields and helper copy based on that reference.
3. Update backend required-field validation for export/save to match.
4. Add a small UI/handler test surface to prevent drift.

## Test plan

- `pdm run docs-validate`
- Frontend: `pdm run fe-test` (required-field gating)
- Backend: `pdm run test` (export validation)

## Rollback plan

- Revert to the previous form and validations; keep the reference doc for later iteration.
