# Offline Planning Task: PR-0060 — Reagent Prep Chef Risk Assessment (Riskbedömning)

## Context Package

**Repomix XML**: `repomix-pr0060-reagent-prep-chef-risk-assessment-planning.xml`

This package contains the authoritative scope docs (ST-20-02 + PR-0060) and the key backend/frontend touchpoints you’ll need to plan the implementation end-to-end.

Note: the package is intentionally large (includes `frontend/apps/skriptoteket/openapi.json` and generated TS types) because the goal is to let you reason about API/type generation and existing conventions without access to the repo.

## Objective

Produce a **detailed, gap-free implementation plan** for the Risk Assessment feature in the existing curated app **ReagentPrepChef**.

The plan must be good enough that a developer with repo access can implement PR-0060 with minimal re-discovery.

## Scope (must follow PR-0060 “as law”)

- Offline/curated **SDS hosting** (no runtime external fetching).
- **Full chemistry heuristics** for lab prep (reaction/incompatibility/exothermicity/etc.) appropriate for the curated dataset.
- **Concentration-dependent CLP classification** (mixtures/solutions must classify based on concentration).
- **Automatic risk scoring** with explicit **teacher confirmation** (teacher must accept/override before “final”).
- Draft persistence (teacher should not lose work; autosave / restore).
- PDF export and save-to-vault flows (aligned with existing export/save patterns).

## Deliverable

Return a written plan containing:

1. **Domain model proposal** (Pydantic/dataclasses boundary decisions) for:
   - Risk assessment draft state (persisted in tool sessions).
   - Computed risk assessment result (derived from sheet + heuristics + CLP).
   - SDS references (stable IDs + metadata).
2. **Curated data requirements**:
   - What must be added to/alongside `hazards.json` (or replaced) to support concentration-dependent CLP and heuristics.
   - How SDS PDFs are stored, indexed, and served offline.
3. **Backend API contract**:
   - Exact endpoints, request/response shapes, error cases (incl. optimistic concurrency via `state_rev`).
   - How the risk assessment endpoints integrate with existing ReagentPrepChef endpoints.
4. **Backend implementation touchpoints**:
   - Where to add protocols, handlers, DI wiring, and routes.
   - Where the CLP engine + heuristics + scoring live (domain vs application).
5. **Frontend UX flow**:
   - UI layout within `ReagentPrepChefView.vue`.
   - Teacher confirmation/override flow.
   - Autosave/restore behavior.
   - SDS viewing UX.
6. **PDF + Vault plan**:
   - HTML generation strategy and how to keep it maintainable.
   - Vault file metadata expectations.
7. **Test plan**:
   - Unit tests for CLP classification engine.
   - Unit tests for heuristics rules.
   - API route tests.
   - (Optional) frontend tests for state transitions.
8. **OpenAPI/types update plan**:
   - How to regenerate `openapi.json` and `openapi.d.ts` after adding endpoints.

No code is required in your deliverable, but it must name files and describe concrete changes.

## Architectural Constraints (must follow repo rules)

- Domain is pure (no FastAPI, no DB, no HTTP errors).
- Web/API layer is thin.
- Protocol-first DI (depend on `typing.Protocol`).
- Unit of Work owns transactions (repos don’t commit).
- Raise `DomainError` in domain/application; map to HTTP in web layer.
- Use existing patterns for tool sessions and vault.

## Reading Map (start here)

- Scope docs:
  - `docs/backlog/stories/story-20-02-curated-app-reagent-prep-chef-risk-assessment.md`
  - `docs/backlog/prs/pr-0060-curated-app-reagent-prep-chef-risk-assessment.md`

- Existing ReagentPrepChef handlers and patterns:
  - Prep calculation: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_prep.py`
  - HTML for PDF export: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_helpers.py`
  - Export PDF handler: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_export_pdf.py`
  - Save PDF to Vault: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_save_pdf.py`
  - Tool session persistence pattern (defaults): `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_defaults.py`

- Curated hazard data store:
  - Store implementation: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards_store.py`
  - Data file: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`

- API surface + DI:
  - FastAPI routes: `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`
  - Curated apps DI wiring: `src/skriptoteket/di/curated_apps.py`
  - Protocols: `src/skriptoteket/protocols/reagent_prep_chef.py`

- Tool sessions + Vault infrastructure:
  - Tool session protocols: `src/skriptoteket/protocols/tool_sessions.py`
  - Tool session repo (state_rev): `src/skriptoteket/infrastructure/repositories/tool_session_repository.py`
  - Vault protocols: `src/skriptoteket/protocols/vault.py`
  - Vault routes + helpers: `src/skriptoteket/web/api/v1/vault.py`, `src/skriptoteket/application/scripting/handlers/_vault_helpers.py`

- Frontend:
  - Main view: `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue`
  - API client/types: `frontend/apps/skriptoteket/src/api/client.ts`, `frontend/apps/skriptoteket/src/api/openapi.d.ts`
  - Vault composable: `frontend/apps/skriptoteket/src/composables/vault/useVaultFiles.ts`

## Implementation Checklist (what your plan must cover)

### 1) Curated data model + storage

- Define the **minimum curated dataset** required to support:
  - Concentration-dependent CLP classification.
  - Heuristics (incompatibilities, reactive groups, exothermic dissolution, gas evolution, etc.).
  - Offline SDS lookup.
- Decide whether to:
  - Extend `hazards.json` into a richer schema, or
  - Split into multiple curated files (recommended for maintainability).

Your plan must include:

- A stable chemical identifier strategy (e.g., normalized formula key + aliases, as used today).
- How concentration is represented (mass fraction, molarity, w/v) and converted.
- How to attach:
  - “substance hazards” (pure chemical classification), and
  - “solution/mixture hazards” (computed classification from concentration).

### 2) Offline SDS hosting (backend-served)

Plan a concrete solution that works offline and is simple to operate.

At minimum:

- SDS must be stored server-side (curated; shipped with the app) and served through an authenticated API.
- Hazards data must reference SDS via an `sds_ref` (or similar stable ID).
- The API must allow the frontend to open/download the SDS PDF.

Non-trivial aspects you must solve in your plan:

- Where SDS PDFs live (e.g., under `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds/`).
- How you index them (e.g., `sds_index.json` mapping `sds_ref` -> relative path, filename, language, revision date).
- How you serve them:
  - Use FastAPI `FileResponse`/`StreamingResponse`.
  - Set `Content-Type: application/pdf`.
  - Decide on caching headers and filename handling.

### 3) CLP classification engine (concentration-dependent)

Plan an implementation that is deterministic and testable.

Your plan must specify:

- Inputs (chemical identity + concentration + amount + any procedure metadata you need).
- Outputs (hazard classes, H-statements, pictograms, signal word, precautionary statements if included).
- How curated data represents thresholds/cutoffs.
- How mixture classification is computed (high level), including edge cases.

Guidance (not code, but structure):

- Keep the CLP engine in **domain** (pure functions), with curated data as input (loaded by infrastructure).
- Represent “hazard rules” as data + small rule evaluators, not ad-hoc conditionals scattered in handlers.
- Include unit tests for:
  - Threshold boundaries.
  - Multiple hazards contributing.
  - Unknown/insufficient data.

### 4) Chemistry heuristics (reaction/incompatibility)

Plan a heuristics subsystem that can be extended over time and is explainable to teachers.

Your plan must define:

- A rule representation (e.g., “reactive groups” + “pair incompatibilities” + “procedure-based hazards”).
- How you attach **explanations and sources** to each warning (teacher trust).
- How you avoid false certainty:
  - Provide confidence/assumptions.
  - Make warnings reviewable and editable by the teacher.

Include a concrete set of “first iteration” heuristics categories (the plan can phase them, but must cover the full scope):

- Acid/base incompatibilities.
- Oxidizer/reducer.
- Water-reactive.
- Gas evolution risks.
- Exothermic dissolution and mixing order.
- Incompatible waste/disposal combinations.

### 5) Automatic risk scoring + teacher confirmation

Plan the scoring model and the teacher confirmation UX.

Your plan must include:

- A risk matrix definition (e.g., likelihood x severity) and its scale.
- How severity is derived (from CLP classification + procedure context).
- How likelihood is derived (from procedure steps, quantities, concentration, known heuristics triggers).
- How “overall risk score” is aggregated from multiple hazards.
- Explicit teacher confirmation requirements:
  - What constitutes “confirmed”.
  - What happens if the teacher edits scores.
  - How that is represented in persisted draft state.

### 6) Draft persistence (tool sessions)

Plan persistence using the existing `tool_sessions` mechanism.

Your plan must specify:

- A stable tool session key namespace for this feature (separate from defaults).
- `state_rev` concurrency strategy:
  - Client sends current `state_rev` on update.
  - Backend returns 409/Conflict on mismatch with server copy.
  - UI conflict resolution flow (simple and safe).

### 7) Backend endpoints + handlers

Plan endpoints and where they live.

Minimum endpoints expected by ST-20-02/PR-0060 include:

- Get draft (or get-or-create).
- Update draft (with optimistic concurrency).
- Export risk assessment PDF.
- Save risk assessment PDF to Vault.
- Get SDS (by `sds_ref`).

Your plan must map each endpoint to:

- A handler in `src/skriptoteket/application/curated_apps/handlers/`.
- Protocol additions in `src/skriptoteket/protocols/reagent_prep_chef.py`.
- DI wiring in `src/skriptoteket/di/curated_apps.py`.
- Route additions in `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`.

### 8) PDF generation + Vault save

Plan how risk assessment content becomes HTML and then PDF.

- Reuse `WeasyPrintPdfRenderer` (`src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/pdf_renderer.py`).
- Avoid bloating `build_export_html`; instead propose a maintainable structure (e.g., separate builder function/module for risk assessment HTML).
- Define the PDF structure:
  - Identification (school, teacher, date, activity).
  - Chemical list + concentrations.
  - CLP outputs (pictograms, H-statements).
  - Heuristics warnings.
  - Risk matrix + teacher confirmation fields.
  - SDS references (IDs/links).

Vault save:

- Mirror the existing save pattern from `reagent_prep_chef_save_pdf.py`.
- Define naming conventions and metadata.

### 9) Frontend integration

Plan the UI changes in `ReagentPrepChefView.vue`.

Your plan must cover:

- Where the Risk Assessment UI lives (tab/section).
- When auto-generation runs (e.g., after prep calculation, and whenever inputs change).
- How teacher confirmation is enforced.
- How autosave is triggered (debounced) and how errors are shown.
- SDS open/download UX.
- PDF export/save UX (and Vault feedback using `useVaultFiles` patterns).

### 10) Tests

Plan tests in the repo style.

- Backend unit tests:
  - CLP engine.
  - Heuristics rules.
  - Hazard/SDS store loading.
- Web/API tests:
  - Extend `tests/unit/web/test_apps_reagent_prep_chef_api_routes.py` for new endpoints.
- Keep tests focused on behavior and protocols; avoid patching implementation details.

### 11) OpenAPI + generated types

Plan the update workflow:

- Update FastAPI routes.
- Run OpenAPI export script: `scripts/export_openapi_v1.py`.
- Regenerate frontend types using the existing script in `frontend/apps/skriptoteket/package.json`.

Your plan must mention what changes are expected in:

- `frontend/apps/skriptoteket/openapi.json`
- `frontend/apps/skriptoteket/src/api/openapi.d.ts`

## Non-trivial Solutions (you must explicitly address these)

### A) SDS ingestion workflow (curated operations)

Propose a maintainable ingestion workflow for curators:

- Where curated PDFs are added.
- How `sds_ref` is chosen and kept stable.
- How metadata is updated.

You may propose a simple script (plan only) that validates:

- Every `sds_ref` referenced by hazards exists.
- Every indexed SDS file exists and is a PDF.

### B) Concentration conversions

Risk/CLP depends on concentration.

Plan how to derive comparable concentration measures from existing prep inputs:

- Solid dissolved into final volume.
- Liquid stock solution diluted into final volume.

Specify whether you’ll compute:

- Mass fraction (w/w),
- w/v, or
- molarity,

and how you’ll handle density assumptions (curated density table vs explicit “assumed density”).

### C) Explainability and teacher trust

Every computed warning/score must have an explanation.

Plan:

- A structured “evidence” object on warnings/scores.
- How to include sources (SDS section refs, curated notes, rule IDs).

### D) Failure modes

Plan safe degradation:

- Missing hazard data.
- Missing SDS.
- Unknown concentration.
- Conflicting draft updates.

Define how these appear in the UI and in exported PDFs.

## Questions you should explicitly resolve or flag

- What is the minimum required content in a Swedish school chemical risk assessment for this app’s context (as per the referenced regulations in ST-20-02).
- Whether SDS should be served to all authenticated teachers or restricted further.
- How to version/track updates to curated hazard + SDS datasets.
- Whether risk assessment drafts are per “prep sheet instance”, per “tool session”, or both.

## Expected Output Format

Return your deliverable as:

- A structured document with headings matching this task, plus
- A proposed file-by-file change list (by path), and
- A phased implementation plan (milestones) with dependencies.
