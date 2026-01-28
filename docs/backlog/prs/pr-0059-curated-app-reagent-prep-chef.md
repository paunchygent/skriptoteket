---
type: pr
id: PR-0059
title: "Curated app: Reagent Prep Chef (implementation)"
status: ready
owners: "agents"
created: 2026-01-26
updated: 2026-01-28
stories:
  - "ST-20-01"
tags: ["curated-apps", "backend"]
acceptance_criteria:
  - "Curated app appears in Katalog with correct role gate and placement."
  - "App is bespoke-required: /apps/:appId renders a dedicated Reagent Prep Chef SPA view (generic AppDetailView is not used for this app)."
  - "SPA uses app-specific endpoints only (no /api/v1/start_action or tool session orchestration in the primary UX)."
  - "App supports solid + liquid_stock flows with deterministic outputs and teacher-friendly Swedish validation errors."
  - "Safety output is curated-only with explicit SDS fallback on misses (never heuristics)."
  - "Export produces a downloadable PDF via an app-specific endpoint."
---

## Problem

Teachers need quick, accurate solution prep calculations. Common mistakes include hydrate state ambiguity, purity
assumptions, and dilution math errors when scaling for multiple student groups.

## Goal

Ship **Reagent Prep Chef** as a first-class curated app (ADR-0023) with a modern, low-friction bespoke UX and an
**app-specific API contract**. Curated apps are shipped application modules (not tools); runner/tool infrastructure is
allowed only as an internal implementation detail (not exposed to the SPA as the primary contract).

## Non-goals

- No chemistry heuristics (exothermicity, incompatibilities, etc.).
- No online SDS fetching or external chemistry APIs.
- No multi-solute “recipes” (single-solute prep per run).

## API contract (app-specific)

Primary endpoints (exact routes):

- `GET /api/v1/apps/{app_id}`
  - Use existing curated apps endpoint for metadata + role gating.
- `POST /api/v1/apps/chemistry.reagent_prep_chef/prep`
  - Validates inputs strictly and returns a prep sheet response optimized for rendering (no tool/run orchestration).
- `POST /api/v1/apps/chemistry.reagent_prep_chef/export-pdf`
  - Returns `application/pdf` with `Content-Disposition: attachment; filename="reagensberedning.pdf"`.

Optional (UX enhancement):

- `GET /api/v1/apps/chemistry.reagent_prep_chef/chemicals`
  - Returns curated chemical list (key + display_name + aliases) for a typeahead picker.

## Implementation plan

Backend wiring

- Add curated app entry to `InMemoryCuratedAppRegistry`:
  - `app_id=chemistry.reagent_prep_chef`
  - sensible Swedish title/summary
  - `min_role` agreed (teacher vs user)
  - initial placement (e.g. `larare/ovrigt`)
- Curated app definition MUST be `ui_mode=bespoke_required` (fail closed if bespoke view is missing).

Registry/UI policy plumbing

- Extend curated app metadata with `ui_mode: "bespoke_required" | "generic_ok"` (or equivalent `spa_view_id`).
- For Reagent Prep Chef, set `ui_mode="bespoke_required"` in the curated app registry.
- Expose `ui_mode` in:
  - curated app detail response (`GET /api/v1/apps/:appId`) and
  - any curated app catalog list payload where the SPA needs to decide routing/UX.

Core domain/service code (pure + testable; no HTTP/tool concepts)

- Add formula normalization module (separator-only normalization; preserve chemical meaning).
  - Add molar mass wrapper:
  - decide dependency (recommended: `molmass`) and add to `pyproject.toml`
  - validate support for hydrates + parentheses
- Implement deterministic calculations with `Decimal`:
  - group logistics (ceil groups, safety factor)
  - solid solute mass (purity-adjusted)
  - liquid stock dilution volumes (reject impossible dilution)
  - minimum mass warning threshold (configurable, default 0.01 g)

Curated hazards data

- Add repo-owned hazards dataset:
  - define record schema + canonical formula keys (+ optional aliases)
  - implement `HazardLookupProtocol` + in-memory loader (Scope.APP)
  - explicit SDS fallback payload on miss (no guessing)

Backend app service + endpoints (no tool/run orchestration in the public contract)

- Implement an application service that produces a “Prep Sheet” response object for the SPA.
- Implement `POST /api/v1/apps/chemistry.reagent_prep_chef/prep`:
  - strict validation
  - deterministic rounding (round only at the boundary / for presentation)
  - teacher-friendly Swedish error messages + stable error codes
- Implement `POST /api/v1/apps/chemistry.reagent_prep_chef/export-pdf`:
  - recompute from request and render a print-friendly PDF (WeasyPrint)
  - return as `application/pdf` with download headers
- Keep any shared runner/tool infrastructure internal-only (FORBIDDEN to expose as required client orchestration).

Export

- Export is app-specific and must not require the SPA to coordinate tool runs or artifacts panels.

Frontend (bespoke app UI)

- Replace `AppDetailView` with an app host view:
  - If bespoke view exists for `app_id`, render it.
  - If `ui_mode="generic_ok"` and no bespoke view exists, render the generic fallback.
  - If `ui_mode="bespoke_required"` and no bespoke view exists, show a blocking “UI update required” screen.
- Implement `ReagentPrepChefView`:
  - stepper/wizard: Reagent → Class setup → Source (solid/stock) → Result
  - reagent picker (curated hazards dataset) + manual formula input
  - live-derived logistics (groups, total volume) and clear unit copy
  - result ledger (mass/volumes) + safety side panel + “Export PDF”
  - persist draft inputs locally (optional) for low-friction iteration
  - MUST call app-specific endpoints (no `start_action`, no tool sessions/state rev as primary contract)

## Test plan

Automated

- Unit tests for:
  - formula normalization (`CuSO4.5H2O`, `CuSO4*5H2O`, `CuSO4·5H2O`)
  - solid solute math (purity factor, safety factor)
  - dilution math (reject `stock_molarity <= target_molarity`)
  - curated hazards lookup hit/miss behavior
  - API contract shape for:
    - `POST /api/v1/apps/chemistry.reagent_prep_chef/prep`
    - `POST /api/v1/apps/chemistry.reagent_prep_chef/export-pdf`
- SPA view selection:
  - bespoke-known app renders bespoke view
  - bespoke_required without view shows blocking state
  - generic_ok without view falls back to generic renderer (if applicable)

Manual smoke (local)

1. Open the curated app from Katalog.
2. Submit `prep` for a curated reagent → verify prep sheet response renders + safety is curated.
3. Submit `prep` for an unknown reagent → verify explicit SDS warning and no guessed hazards.
4. Export PDF via `export-pdf` → download PDF and verify content.

## Rollback plan

- Remove the curated app registry entry (hide from catalog) and redeploy.
- Keep code paths isolated so the demo curated app and normal tools remain unaffected.
