---
type: review
id: REVIEW-PR-0071-2026-03-04
title: "Ruthless review — PR-0071 riskunderlag alignment"
status: completed
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
---

## Scope

### Files reviewed

- `src/skriptoteket/application/curated_apps/reagent_prep_chef_risk_contract.py`
- `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`
- `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_export_risk_pdf.py`
- `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_save_risk_pdf.py`
- `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_helpers.py`
- `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`
- `frontend/apps/skriptoteket/src/composables/reagentPrepChef/riskExportGate.ts`
- `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefRisk.ts`
- `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue`
- `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefStepRisk.vue`
- `tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_contract.py`
- `tests/unit/web/reagent_prep_chef/test_risk_routes.py`
- `frontend/apps/skriptoteket/src/composables/reagentPrepChef/riskExportGate.spec.ts`
- `docs/reference/ref-reagent-prep-chef-riskunderlag-skolpraxis.md`
- `docs/backlog/prs/pr-0071-reagent-prep-chef-riskbedomning-form-skolpraxis.md`

### Public surfaces affected

- HTTP response header filename for `POST /api/v1/apps/chemistry.reagent_prep_chef/export-risk-pdf`.
- App export vault filename convention for risk PDFs.
- PDF title/copy for risk document (`Riskbedömning` -> `Underlag till riskbedömning`).
- SPA export button/copy and required-field guidance text.
- Backend risk context required-field contract shared across draft + export.

### Compatibility posture

- **Partially breaking** for clients/tests that assert exact previous filename `riskbedomning.pdf`.
- Breaking change is intentional and documented by PR-0071 decision checkpoint.

## Findings

### 1) low — Frontend/backend filename literal can drift

- **File**: `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefRisk.ts:28`
- **What**: Frontend defines `RISK_SUPPORT_PDF_FILENAME` locally, while backend defines the same concept in
  `reagent_prep_chef_risk_contract.py`.
- **Why it matters**: Future rename can diverge (header filename vs browser download filename), causing inconsistent UX.
- **Fix**: Optional follow-up: parse filename from `Content-Disposition` when present, fallback to local constant.
- **Proof requirement**: Add frontend test around filename selection path and run
  `pdm run fe-test -- src/composables/reagentPrepChef/*.spec.ts`.

### 2) low — No direct unit test for save-handler filename generation

- **File**: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_save_risk_pdf.py:77`
- **What**: Current tests assert route-level JSON through stubs, but do not exercise real handler naming logic.
- **Why it matters**: A future refactor can silently regress `underlag-riskbedomning-<formula>.pdf`.
- **Fix**: Add unit test for `ReagentPrepChefSaveRiskPdfHandler` with stubbed export/vault protocols.
- **Proof requirement**: New test command under `tests/unit/application/curated_apps/handlers/` and run
  `pdm run pytest -q tests/unit/application/curated_apps/handlers/...`.

## Decision

`approved`

No blocker/high issues found. Architecture boundaries, contract alignment, typing, docs updates, and verification
evidence are all acceptable.

## Validation evidence reviewed

- `pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_contract.py tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py tests/unit/web/reagent_prep_chef/test_risk_routes.py`
- `pdm run fe-test -- src/composables/reagentPrepChef/riskExportGate.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_st_11_09_curated_app_e2e --base-url http://127.0.0.1:5173`
