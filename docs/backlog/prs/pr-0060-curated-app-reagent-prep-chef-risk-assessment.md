---
type: pr
id: PR-0060
title: "Curated app: Reagent Prep Chef — Riskbedömning + dokumentation (v1)"
status: in_progress
owners: "agents"
created: 2026-01-28
updated: 2026-02-01
stories:
  - "ST-20-02"
tags: ["curated-apps", "backend", "frontend"]
acceptance_criteria:
  - "Riskbedömning tab exists in the bespoke Reagent Prep Chef view and is only available after a successful prep calculation."
  - "Risk assessment draft is generated deterministically from the prep sheet + offline SDS/curated inputs and includes: (a) full chemistry heuristics (reaction prediction, incompatibilities, exothermicity), (b) a concentration-dependent CLP classification engine output, and (c) automatic risk scoring where the teacher must explicitly confirm or modify seriousness/rating."
  - "Full SDS is available for curated chemicals as backend-hosted content. Runtime SDS fetching is allowed, but the SPA must only open backend-hosted copies (cached offline after fetch) and never call external SDS URLs directly."
  - "Draft state is persisted via tool_sessions with optimistic concurrency (state_rev) and can be restored on reload."
  - "Export-risk-pdf returns a downloadable PDF with stable filename and includes the AFS-aligned documentation fields (scope, risks + seriousness, measures, participants, approver, date, next review date)."
  - "Save-risk-pdf stores the PDF in Vault with source_kind=APP_EXPORT and returns a Vault file ref to the SPA."
  - "OpenAPI types are regenerated and the SPA compiles/type-checks against the updated schema."
---

## Problem

Teachers need to document risk assessments for chemical work in a way that is practical, reproducible, and tied to what was actually prepared (formula, concentration, volume, steps). Today, Reagent Prep Chef exports the prep sheet as PDF, but there is no integrated risk assessment workflow or documentation artifact.

## Goal

Add a first-class **Riskbedömning** workflow to the existing curated app:

- Deterministic draft generation based on computed prep sheet + curated repo data.
- Teacher-owned completion of local context and confirmation/modification of seriousness/rating.
- PDF export + Save to Vault.
- Draft persistence via `tool_sessions`.
- Full SDS access for curated chemicals via offline backend-hosted storage.
- Full chemistry heuristics (reaction prediction, incompatibilities, exothermicity, etc.).
- Concentration-dependent CLP classification engine.
- Automatic risk scoring + teacher must explicitly confirm or modify seriousness/rating.

## Implementation status (as of 2026-02-01)

Delivered so far:

- Riskbedömning endpoints wired (draft/export/save) and SPA tab uses tool_sessions with optimistic concurrency.
- PDF export + Vault save follow existing patterns (WeasyPrint + run recording + Vault quota checks).
- SDS fetch/cache pipeline stores and serves **PDF** SDS (backend-hosted), keeping LCSS JSON for structured GHS.
- Multi-source SDS provider registry wired (curated linkouts + PubChem LinkOut + safety URLs + LCSS URL scan).
- Curated SDS meta store added; curated density/CLP bands are now loaded and used when present.
- Seed SDS cache supports parallel fetches and strict validation; sample batch (C3H6O/Al/AlCl3/AlCl3·6H2O/Al2O3) now completes cleanly with curated meta.

Remaining to close for acceptance:

- **Full dataset prefetch validation**: ran `seed-sds-cache` on 2026-02-01 → ok=10, fail=154 (see `.artifacts/sds-cache/full-report.json` and `.artifacts/sds-cache/missing-hazards.txt`). All misses must be resolved.
- Populate curated SDS linkouts + curated meta (density + CLP bands) for every hazard; no gaps.
- Confirm the remaining CLP/heuristics outputs match acceptance criteria across the full hazard list.

## API contract (app-specific)

New endpoints (exact routes):

- `POST /api/v1/apps/chemistry.reagent_prep_chef/risk-assessment`
  - Returns `draft` + warnings + `state_rev`.

- `POST /api/v1/apps/chemistry.reagent_prep_chef/export-risk-pdf`
  - Returns `application/pdf` with `Content-Disposition: attachment`.

- `POST /api/v1/apps/chemistry.reagent_prep_chef/save-risk-pdf`
  - Saves to Vault and returns Vault file info.

- `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/{sds_ref}`
  - Returns full SDS content (e.g. PDF) served from backend-hosted curated storage.

## Implementation plan

Backend

- Add new request/response models in `src/skriptoteket/application/curated_apps/reagent_prep_chef/`:
  - `ReagentPrepChefRiskAssessmentRequest`
  - `ReagentPrepChefRiskAssessmentDraft`
  - `ReagentPrepChefRiskAssessmentResult`
- Add protocols in `src/skriptoteket/protocols/reagent_prep_chef.py`:
  - `ReagentPrepChefRiskAssessmentHandlerProtocol`
  - `ReagentPrepChefExportRiskPdfHandlerProtocol`
  - `ReagentPrepChefSaveRiskPdfHandlerProtocol`
- Implement handlers in `src/skriptoteket/application/curated_apps/handlers/` following existing patterns:
  - Use `tool_sessions` with a new context key (e.g. `curated-app-risk-assessment:v1`) for draft persistence.
  - Reuse the existing PDF renderer (`WeasyPrintPdfRenderer`).
  - Reuse the existing Vault save pattern (compare `reagent_prep_chef_save_pdf.py`).

Curated data + SDS

- SDS must be stored in backend-hosted storage; runtime may fetch from external sources, but must cache and serve from backend storage (no direct vendor URLs in the SPA).
- Implement SDS ingestion + parsing to derive structured inputs for:
  - chemistry heuristics (reaction prediction, incompatibilities, exothermicity)
  - concentration-dependent CLP classification
  - automatic risk scoring
- Add repo-owned data under `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/`:
  - `risk_templates.json` (used as a presentation/normalization layer on top of computed CLP + scoring)
- Extend hazard model/data with fields needed by the new engines (e.g. `sds_ref`, extracted SDS fields, and any curated overrides).
- Ingestion path can be a repo/tooling concern (e.g. maintainer CLI or runner job) that fetches SDS from an approved source and stores it; the app only serves stored SDS.

FastAPI wiring

- Add endpoints in `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`.

Frontend

- Extend `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue`:
  - Add a tab/section: `Riskbedömning`.
  - Gate it on an existing computed prep result.
  - Add a context form and a risk-item list with required seriousness/rating.
  - Add buttons:
    - Export PDF
    - Save PDF to Vault
    - Open SDS (if `sds_ref` is present)

## Test plan

- Backend:
  - Unit tests for SDS parsing, chemistry heuristics, concentration-dependent CLP classification, and automatic risk scoring.
  - Integration tests for the endpoints.
- Frontend:
  - Vitest tests for gating logic + required-field gating for export.
- Manual:
  - Run the app, generate a prep sheet, verify computed heuristics + CLP + scoring are present, confirm/modify ratings, open SDS, export PDF, save to Vault, reload and verify draft restoration.

## Rollback plan

- Remove the new endpoints and tab.
- Keep existing prep sheet export behavior unchanged.
- Remove any new repo-owned risk template data files.
