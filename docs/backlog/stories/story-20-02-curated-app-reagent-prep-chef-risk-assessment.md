---
type: story
id: ST-20-02
title: "Curated app: Reagent Prep Chef — Riskbedömning + dokumentation (v1)"
status: in_progress
owners: "agents"
created: 2026-01-28
updated: 2026-02-18
epic: "EPIC-20"
dependencies: ["ADR-0022", "ADR-0023", "ADR-0024", "REF-curated-app-reagent-prep-chef"]
acceptance_criteria:
  - "Given a teacher has computed a prep sheet, when the teacher opens the new Riskbedömning tab, then the UI shows a structured risk assessment draft prefilled from the computed prep (formula, molarity, volumes, instructions) and prefilled with concentration-dependent CLP classification, chemistry heuristics warnings, and automatic risk scores requiring explicit teacher confirmation/override for each risk item."
  - "Given the teacher confirms or modifies the prefilled data and fills required local context, when the teacher exports, then the backend generates a deterministic PDF risk assessment document (no external API calls during export) and the SPA downloads it."
  - "Given the teacher exports and chooses Save to Vault, when saving completes, then a Vault file is created with source_kind=APP_EXPORT and the user receives a Vault file reference."
  - "Given the teacher returns later, when the app is opened, then the last risk assessment draft can be restored from app-owned session state (tool_sessions) without data loss (or the teacher can start a fresh draft)."
  - "Given the chemical is not present in curated hazards data, when a risk draft is generated, then the risk assessment fails with an explicit error and requires a curated SDS before proceeding (no fallback)."
  - "Given the chemical is present in curated hazards data and has a curated SDS attachment, when the teacher opens Riskbedömning, then the UI can open the full SDS served by the backend (cached offline after any fetch) without any direct external fetch from the SPA."
ui_impact: "Yes (new tab + forms + export/save actions)"
data_impact: "Yes (repo-owned risk templates + extended curated hazards fields; stored drafts via tool_sessions)"
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
  - Repo-owned curated hazards data and repo-owned risk templates.
  - **Concentration-dependent CLP classification** for solutions/mixtures based on curated data.
  - **Chemistry heuristics** for lab prep (reaction/incompatibility/exothermicity/etc.) based on curated data.
  - **Automatic risk scoring** with explicit teacher confirmation/override for each risk item.
- Require explicit teacher-entered context (cannot be inferred):
  - school/unit, room, date, responsible teacher, approver, participants, and local controls.
- Export a deterministic PDF via WeasyPrint.
- Save the PDF to Vault (same pattern as existing export/save for prep sheet).
- Persist the draft in `tool_sessions` so the teacher can return later.

## Non-goals / Fail-safe constraints

- Runtime SDS fetching is allowed, but must be cached and served by the backend (no direct external SDS URLs in the SPA).
- No heuristics/CLP/scoring for chemicals not present in curated data; instead, show explicit 'cannot compute' and require teacher to consult SDS.
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
  - Output: full SDS content (e.g. `application/pdf`) served from backend-hosted curated storage.

## Data requirements

Curated-only data. No guessing.

- Extend hazards records with optional curated fields to support risk drafting:
  - `controls[]` (curated handling controls)
  - `first_aid[]` (optional)
  - `sources[]` (citations for curated content)
  - `sds_ref` (optional reference to a full SDS stored offline in backend storage)
  - **Concentration-dependent CLP data** (thresholds, hazard classes, H-statements, pictograms) for solutions/mixtures.
  - **Heuristics data** (reactive groups, incompatibility pairs, exothermic dissolution rules, gas evolution rules) with sources.

- SDS storage requirement:
  - Full SDS documents for curated chemicals must be available in full via backend-hosted storage (e.g. PDF bytes).
- The primary UX must not depend on calling external vendor URLs directly; backend fetch + cache is allowed.

- Add repo-owned risk template catalog (new JSON data):
  - hazard-code driven templates (e.g. H314 — frätande stänk)
  - a small set of generic lab risks (glass breakage, spills, etc.)
  - **Risk matrix definitions** (likelihood/severity scales) and scoring rules.

## PDF output requirements

The PDF must include AFS-aligned documentation fields:

- Scope/where it applies
- Identified risks + seriousness indication
- Measures/controls and preparedness
- Participants + approver
- Date + next planned review date
- Explicit SDS disclaimer for missing curated hazards
- **CLP classification output** (pictograms, signal word, H-statements) for each chemical/solution.
- **Heuristics warnings** with sources and explanations.
- **Risk matrix** with automatic scores and teacher confirmation/override indicators.

## Test plan

- Backend unit tests:
  - Risk template expansion, SDS fallback behavior, export validation.
  - Concentration-dependent CLP classification engine (threshold boundaries, multiple hazards).
  - Chemistry heuristics rules (incompatibilities, exothermicity, gas evolution).
  - Automatic risk scoring and teacher confirmation state.
- Backend integration tests: endpoints and auth.
- Frontend unit tests (Vitest): required fields gating export, error handling, confirmation flow.
- Assumption validation (data-first): pick a small “sample truthy” set from `.artifacts/sds-cache/full-report.json` spanning ok/fail/partial cases and validate missingness/gating against real shapes before building larger code paths.
- Manual: compute prep sheet — open risk tab — review prefilled CLP/heuristics/scores — confirm/override — export PDF — save to Vault — reopen app and confirm draft restore.

## Notes

- Build on ST-20-01 output model and export patterns.
- Follow the curated-app rule: bespoke UX + app-specific APIs; tool/runner infrastructure is internal-only.

## Implementation status (as of 2026-02-18)

Progress:

- Riskbedömning draft/export/save endpoints exist; tool_sessions state persistence is wired.
- SDS pipeline caches **PDF** SDS and serves PDF from backend (no direct external SDS links in SPA).
- Multi-source SDS provider registry wired (curated linkouts + PubChem LinkOut + safety URLs + LCSS URL scan).
- Curated SDS meta store added; curated density/CLP bands are used when present.
- Seed SDS cache supports parallel fetches + strict validation; sample batch with curated meta completes cleanly.

Outstanding gaps vs acceptance criteria:

- Full prefetch validation ran 2026-02-01 → ok=10, fail=154 (see `.artifacts/sds-cache/full-report.json` and `.artifacts/sds-cache/missing-hazards.txt`). To get out of the “strict completeness blocks everything” state, **PR-0062** defines a best-effort draft contract with explicit `missing_flags` and server-driven `export_gate` (draft tolerant, export fail-closed/offline).
- Curated SDS linkouts/meta coverage still incomplete for the full list (manual curation required).
