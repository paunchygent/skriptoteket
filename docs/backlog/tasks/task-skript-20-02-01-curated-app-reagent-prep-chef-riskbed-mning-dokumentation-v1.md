---
type: task
id: TASK-SKRIPT-20-02-01
title: 'Curated app: Reagent Prep Chef — Riskbedömning + dokumentation (v1)'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-20-02-01#closeout'
story: ST-SKRIPT-20-02
task_kind: story
acceptance_criteria:
  - Riskbedömning tab exists in the bespoke Reagent Prep Chef view and is only available after a successful prep calculation.
  - Risk assessment draft is generated deterministically from the prep sheet + curated repo data and is restorable via tool_sessions with optimistic concurrency (state_rev).
  - SDS is available for curated chemicals as backend-hosted **markdown** (ADR-0067). The SPA renders the markdown in-app and does not open external vendor URLs.
  - Draft state is persisted via tool_sessions with optimistic concurrency (state_rev) and can be restored on reload.
  - Export-risk-pdf returns a downloadable PDF with stable filename and includes the AFS-aligned documentation fields (scope, risks, measures, participants, approver, date, next review date).
  - Save-risk-pdf stores the PDF in Vault with source_kind=APP_EXPORT and returns a Vault file ref to the SPA.
  - OpenAPI types are regenerated and the SPA compiles/type-checks against the updated schema.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0056 D2 on code and type-check evidence. The user dropped the seriousness rating from criterion 5 because no field supports it: the risk contract has no seriousness field and the exported PDF does not render one. The Goal and Plan below name a teacher-confirmed seriousness rating and are kept as history; see Closeout for the evidence and the checks that were not run.

## Context

### Source: Problem

Teachers need to document risk assessments for chemical work in a way that is practical, reproducible, and tied to what was actually prepared (formula, concentration, volume, steps). Today, Reagent Prep Chef exports the prep sheet as PDF, but there is no integrated risk assessment workflow or documentation artifact.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

### Source: Goal

Add a first-class **Riskbedömning** workflow to the existing curated app:

- Deterministic draft generation based on computed prep sheet + curated repo data.
- Teacher-owned completion of local context and confirmation/modification of seriousness/rating.
- PDF export + Save to Vault.
- Draft persistence via `tool_sessions`.
- Full SDS access for curated chemicals via offline backend-hosted **markdown** (ADR-SKRIPT-0067).
- Keep Riskbedömning teacher-first and maintainable: no SDS-derived signal extraction pipeline.

### Source: API contract (app-specific)

New endpoints (exact routes):

- `POST /api/v1/apps/chemistry.reagent_prep_chef/risk-assessment`

  - Returns `draft` + warnings + `state_rev`.

- `POST /api/v1/apps/chemistry.reagent_prep_chef/export-risk-pdf`

  - Returns `application/pdf` with `Content-Disposition: attachment`.

- `POST /api/v1/apps/chemistry.reagent_prep_chef/save-risk-pdf`

  - Saves to Vault and returns Vault file info.

- `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/{sds_ref}`

  - Returns full SDS content (e.g. PDF) served from backend-hosted curated storage.

## Contract Inputs

No separate contract inputs were recorded in the source snapshot.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

### Source: Implementation plan

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

Curated data + SDS (ADR-SKRIPT-0067)

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

## Implementation Steps

The source records no separate implementation steps.

## Proof

### Source: Test plan

- Backend:
  - Unit tests for SDS corpus lookup + risk draft gating.
  - Integration tests for the endpoints.
- Frontend:
  - Vitest tests for gating logic + required-field gating for export.
- Manual:
  - Run the app, generate a prep sheet, open Riskbedömning, open SDS, fill context, confirm checklist, export PDF, save to Vault, reload and verify draft restoration.

## Validation

Validation follows the focused test and verification material recorded above.

## Stop Conditions

### Source: Rollback plan

- Remove the new endpoints and tab.
- Keep existing prep sheet export behavior unchanged.
- Remove any new repo-owned risk template data files.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                         |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on code and type-check evidence (TASK-SKRIPT-REP-0056 D2). The criterion on a teacher-confirmed seriousness rating is dropped because no field supports it (user decision 2026-10-28); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

No separate lessons learned were recorded in the source snapshot.

## Notes

No additional task-local notes were recorded in the source snapshot.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Implementation Review

### Source: Implementation status (as of 2026-03-04)

Delivered so far:

- Riskbedömning endpoints wired (draft/export/save) and SPA tab uses tool_sessions with optimistic concurrency.
- PDF export + Vault save follow existing patterns (WeasyPrint + run recording + Vault quota checks).
- SDS pipeline is being replaced by the repo-owned SDS markdown corpus (ADR-SKRIPT-0067).

Remaining to close for acceptance:

- Wire Riskbedömning to the new SDS corpus contracts (markdown-first).
- Remove the PubChem/SDS fetch + derived-data surface from the production path.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0056 D2 (orchestrator closeout on code and type-check evidence).

D2 dropped the seriousness rating: criterion 5 no longer lists "seriousness" among the PDF fields. Each remaining criterion was checked on main:

- Criterion 1 (tab after a successful calculation): the "5. Riskbedömning" button is disabled while `prep` is `null` (`frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue:354-360`), and `prep` is set only after a successful `/prep` call (`composables/reagentPrepChef/useReagentPrepChefPrep.ts:53-58`).
- Criteria 2 and 4 (draft from the prep sheet, `tool_sessions`, `state_rev`): the draft is built from the calculated sheet and the curated hazard and template data (`src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py:153-269`). Inputs and a fingerprint of the prep payload are stored in `tool_sessions` (`:165-196`), and the update is `UPDATE ... WHERE state_rev = expected` (`infrastructure/repositories/tool_session_repository.py:83-117`). The SPA saves with a 600 ms debounce and `expected_state_rev` and maps a 409 to a reload message (`useReagentPrepChefRisk.ts:194-229`). After a page reload only the calculation form comes back from local storage; the stored risk inputs return when the teacher recalculates and opens the Riskbedömning tab again (`ReagentPrepChefView.vue:233-238, 264-267`). I read "can be restored on reload" as that.
- Criterion 3 (SDS markdown): `GET /sds/{sds_ref}/markdown` serves the repo-owned corpus under `data/reagent_prep_chef/sds` (`src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py:204-218`; the index holds 164 entries and all 164 files exist). The SPA renders it in the SDS modal through `UiMarkdown` (`views/apps/reagent-prep-chef/ReagentPrepChefSdsModal.vue:97-100`). The only `target="_blank"` there opens the backend PDF route, and the reagent view has no `window.open`. Two corpus files carry 10 outbound reference links that render as ordinary links (`data/reagent_prep_chef/sds/markdown/FeS__fishersci__undated.md:548`, `SrSO4__chemicalbook__2026-01-17.md:526-547`); I did not count them as vendor URLs opened by the SPA.
- Criterion 5 (export PDF): the route returns `Content-Disposition: attachment` with the constant name `underlag-riskbedomning.pdf` (`apps_reagent_prep_chef.py:107-120`; `application/curated_apps/reagent_prep_chef_risk_contract.py:19`). `build_risk_export_html` in `application/curated_apps/handlers/reagent_prep_chef_helpers.py` renders scope, risks, measures, participants, approver, date and next review date, and export is refused while a required context field is empty.
- Criterion 6 (save to Vault): `reagent_prep_chef_save_risk_pdf.py:103` stores with `source_kind=APP_EXPORT`, and the response carries a `VaultFileInfo` with a `vault:` ref (`reagent_prep_chef.py:187-190`).
- Criterion 7 (OpenAPI types and type-check): `frontend/apps/skriptoteket/src/api/openapi.d.ts` holds the `export-risk-pdf` and `save-risk-pdf` paths, and `pdm run fe-type-check` exited 0 on 2026-10-28. No script compares the committed types with a fresh export, and I did not regenerate them.

Focused tests ran on 2026-10-28: 28 backend tests passed (`tests/unit/web/reagent_prep_chef`, the risk contract, risk assessment, risk template store and domain risk tests) and 2 frontend tests passed (`ReagentPrepChefView.spec.ts`).

Not checked: no walk of the app (prep sheet, Riskbedömning, SDS, export, save, reload), no PDF rendered or opened, and the test coverage is thin. No test builds the risk export HTML or runs the save handler to check `APP_EXPORT`, and the SPA risk composable has no spec. The two items the Implementation Review below listed as remaining on 2026-03-04 are done in code: Riskbedömning reads the SDS corpus, and the request path makes no PubChem or other HTTP fetch. Static residue remains: `pubchem_cid` in `hazards.json`, an empty `ClpBand` model, and the unread directories `data/pubchem_payloads/` and `data/sds_linkouts/`.
