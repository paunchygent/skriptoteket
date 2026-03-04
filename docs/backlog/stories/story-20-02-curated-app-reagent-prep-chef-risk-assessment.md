---
type: story
id: ST-20-02
title: "Curated app: Reagent Prep Chef — Riskbedömning + dokumentation (v1)"
status: in_progress
owners: "agents"
created: 2026-01-28
updated: 2026-03-04
epic: "EPIC-20"
dependencies: ["ADR-0022", "ADR-0023", "ADR-0024", "ADR-0067", "REF-curated-app-reagent-prep-chef"]
acceptance_criteria:
  - "Given a teacher has computed a prep sheet, when the teacher opens the Riskbedömning tab, then the UI shows a structured draft prefilled from the computed prep (formula, molarity, volumes, instructions) plus a teacher-editable local context form."
  - "Given the chemical is present in curated hazards data, when the risk draft is generated, then the UI includes curated safety guidance (PPE/avfall/H-koder when available) and an 'Öppna SDS' action."
  - "Given an SDS markdown exists for the current chemical, when the teacher clicks 'Öppna SDS', then the SPA renders the SDS markdown served by the backend with no external fetch and no direct vendor URLs."
  - "Given the SDS markdown is missing, when the teacher clicks 'Öppna SDS', then the UI blocks the action with a clear 'SDS saknas' message."
  - "Given the teacher fills required local context and confirms the checklist items, when the teacher exports, then the backend generates a deterministic PDF risk assessment document (no external API calls during export) and the SPA downloads it."
  - "Given the teacher exports and chooses Save to Vault, when saving completes, then a Vault file is created with source_kind=APP_EXPORT and the user receives a Vault file reference."
  - "Given the teacher returns later, when the app is opened, then the last risk assessment draft can be restored from app-owned session state (tool_sessions) without data loss (or the teacher can start a fresh draft)."
  - "Given the chemical is not present in curated hazards data, when a risk draft is generated, then the risk assessment fails with an explicit error (no guessing/fallback)."
ui_impact: "Yes (new tab + forms + export/save actions)"
data_impact: "Yes (repo-owned risk templates + SDS corpus index; stored drafts via tool_sessions)"
---

## Context

Teachers need to document risk assessments for chemical work. Reagent Prep Chef already produces deterministic, teacher-friendly prep sheets; this story adds a first-class riskbedömning flow that is tied to the exact concentration/volume/handling steps used.

The value proposition is to remove the repetitive “paperwork assembly” part of riskbedömning:

- Prefill risks/measures from curated data and deterministic prep outputs.
- Keep a reusable, restorable draft per teacher (tool_sessions).
- Generate a ready-to-file PDF + optionally store it in Vault.
- Provide full SDS access for curated chemicals directly in the app (offline-hosted).

Regulatory basis and practical expectations:

- Arbetsmiljöverket: risk assessments should be documented in writing.
- AFS 2023:1 (SAM): riskbedömningar ska dokumenteras skriftligt och ange vilka riskerna är, och om de är allvarliga.
- AFS 2011:19 (Kemiska arbetsmiljörisker): defines what risk assessment documentation must contain for chemical risk sources.

## Scope

- Add a bespoke UX tab: Riskbedömning.
- Generate a structured risk assessment draft from:
  - `ReagentPrepChefPrepRequest` + computed prep sheet.
  - Repo-owned curated hazards data (best-effort; no guessing).
  - Repo-owned risk templates (simple checklist + measures).
- Require explicit teacher-entered context (cannot be inferred):
  - school/unit, room, date, responsible teacher, approver, participants, and local controls.
- Export a deterministic PDF via WeasyPrint.
- Save the PDF to Vault (same pattern as existing export/save for prep sheet).
- Persist the draft in `tool_sessions` so the teacher can return later.
- Provide offline SDS access via the backend-hosted markdown corpus (ADR-0067).

## Non-goals / Fail-safe constraints

- No runtime SDS fetching from external sources (SDS must be backend-hosted; ADR-0067).
- No concentration-dependent CLP classification engine.
- No chemistry heuristics / reaction prediction.
- No automatic risk scoring. The draft is a structured template that the teacher confirms/completes.
- No guessing or extrapolation beyond curated data structures.

## API contract (app-specific)

New endpoints (exact routes):

- `POST /api/v1/apps/chemistry.reagent_prep_chef/risk-assessment`
  - Input: prep request + optional context + expected_state_rev
  - Output: structured draft + warnings + state_rev

- `POST /api/v1/apps/chemistry.reagent_prep_chef/export-risk-pdf`
  - Input: risk assessment draft
  - Output: `application/pdf` download

- `POST /api/v1/apps/chemistry.reagent_prep_chef/save-risk-pdf`
  - Input: risk assessment draft + filename
  - Output: Vault file info

- `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/{sds_ref}`
  - Output: full SDS PDF content (optional; when available).

- `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/{sds_ref}/markdown`
  - Output: SDS markdown payload served from repo-owned corpus (ADR-0067).

## Data requirements

Curated-only data. No guessing.

- Hazards dataset (repo-owned): PPE/disposal/notes and best-effort hazard codes.
- SDS corpus (repo-owned markdown): `data/reagent_prep_chef/sds/markdown/` + `data/reagent_prep_chef/sds/index.json`.
- Risk template catalog (repo-owned): a small set of generic lab risks and measures (no scoring engine).

## PDF output requirements

The PDF must include AFS-aligned documentation fields:

- Scope/where it applies
- Identified risks + seriousness indication
- Measures/controls and preparedness
- Participants + approver
- Date + next planned review date
- Explicit SDS disclaimer for missing curated hazards
- SDS reference and a note that the teacher must consult the full SDS.

## Test plan

- Backend unit tests:
  - Risk template expansion, SDS availability flags, export validation.
  - Teacher confirmation state and required-context gating.
- Backend integration tests: endpoints and auth.
- Frontend unit tests (Vitest): required fields gating export, error handling, confirmation flow.
- Manual: compute prep sheet — open risk tab — open SDS — fill context — confirm checklist — export PDF — save to Vault — reopen app and confirm draft restore.

## Notes

- Build on ST-20-01 output model and export patterns.
- Follow the curated-app rule: bespoke UX + app-specific APIs; tool/runner infrastructure is internal-only.

## Implementation status (as of 2026-03-04)

This story is being re-scoped to align with ADR-0067 (markdown-first offline SDS corpus) and a teacher-first,
maintainable Riskbedömning workflow.

The goal is to ship a reliable draft + export/save flow that depends on curated hazards + SDS documents, not on brittle
web fetches or heavy SDS-derived signal extraction.
