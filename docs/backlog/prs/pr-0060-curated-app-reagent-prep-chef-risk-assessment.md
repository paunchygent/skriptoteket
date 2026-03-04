---
type: pr
id: PR-0060
title: "Curated app: Reagent Prep Chef — Riskbedömning + dokumentation (v1)"
status: in_progress
owners: "agents"
created: 2026-01-28
updated: 2026-03-04
stories:
  - "ST-20-02"
tags: ["curated-apps", "backend", "frontend"]
adrs: ["ADR-0067"]
acceptance_criteria:
  - "Riskbedömning tab exists in the bespoke Reagent Prep Chef view and is only available after a successful prep calculation."
  - "Risk assessment draft is generated deterministically from the prep sheet + curated repo data and is restorable via tool_sessions with optimistic concurrency (state_rev)."
  - "SDS is available for curated chemicals as backend-hosted **markdown** (ADR-0067). The SPA renders the markdown in-app and does not open external vendor URLs."
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
- Full SDS access for curated chemicals via offline backend-hosted **markdown** (ADR-0067).
- Keep Riskbedömning teacher-first and maintainable: no SDS-derived signal extraction pipeline.

## Implementation status (as of 2026-03-04)

Delivered so far:

- Riskbedömning endpoints wired (draft/export/save) and SPA tab uses tool_sessions with optimistic concurrency.
- PDF export + Vault save follow existing patterns (WeasyPrint + run recording + Vault quota checks).
- SDS pipeline is being replaced by the repo-owned SDS markdown corpus (ADR-0067).

Remaining to close for acceptance:

- Wire Riskbedömning to the new SDS corpus contracts (markdown-first).
- Remove the PubChem/SDS fetch + derived-data surface from the production path.

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

Curated data + SDS (ADR-0067)

- SDS is a **repo-owned markdown corpus** served offline by the backend:
  - `data/reagent_prep_chef/sds/markdown/` (committed)
  - `data/reagent_prep_chef/sds/index.json` (committed; generated)
  - `data/reagent_prep_chef/sds/files/` (optional PDFs; gitignored)
- The backend does **not** fetch SDS content over HTTP at runtime.
- Riskbedömning uses curated hazards + risk templates; SDS is presented to the teacher as a document (no derived-signal engines).

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
  - Unit tests for SDS corpus lookup + risk draft gating.
  - Integration tests for the endpoints.
- Frontend:
  - Vitest tests for gating logic + required-field gating for export.
- Manual:
  - Run the app, generate a prep sheet, open Riskbedömning, open SDS, fill context, confirm checklist, export PDF, save to Vault, reload and verify draft restoration.

## Rollback plan

- Remove the new endpoints and tab.
- Keep existing prep sheet export behavior unchanged.
- Remove any new repo-owned risk template data files.
