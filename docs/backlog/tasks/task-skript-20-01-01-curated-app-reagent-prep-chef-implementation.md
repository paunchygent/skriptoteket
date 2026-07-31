---
type: task
id: TASK-SKRIPT-20-01-01
title: 'Curated app: Reagent Prep Chef (implementation)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-20-01
task_kind: story
acceptance_criteria:
- Curated app appears in Katalog with correct role gate and placement.
- 'App is bespoke-required: /apps/:appId renders a dedicated Reagent Prep Chef SPA
  view (generic AppDetailView is not used for this app).'
- SPA uses app-specific endpoints only (no /api/v1/start_action or tool session orchestration
  in the primary UX).
- App supports solid + liquid_stock flows with deterministic outputs and teacher-friendly
  Swedish validation errors.
- Safety output is curated-only with explicit SDS fallback on misses (never heuristics).
- Export produces a downloadable PDF via an app-specific endpoint.
- Users can save/export PDFs to Mina filer (Vault) and download them from the vault
  UI.
- Users can save/load standardinställningar per-user, plus export/import defaults
  via Mina filer.
- Riskbedömning tab generates a deterministic draft, supports confirmation/override,
  and exports/saves a PDF.
---

## Context

### Problem

Teachers need quick, accurate solution prep calculations. Common mistakes include hydrate state ambiguity, purity
assumptions, and dilution math errors when scaling for multiple student groups.

### Goal

Ship **Reagent Prep Chef** as a first-class curated app (ADR-0023) with a modern, low-friction bespoke UX and an
**app-specific API contract**. Curated apps are shipped application modules (not tools); runner/tool infrastructure is
allowed only as an internal implementation detail (not exposed to the SPA as the primary contract).

### Non-goals

- No uncurated heuristics: any CLP/heuristics/risk templates must be repo-owned data (no guessing).
- No online SDS fetching or external chemistry APIs.
- No multi-solute “recipes” (single-solute prep per run).

### API contract (app-specific)

Primary endpoints (exact routes):

- `GET /api/v1/apps/{app_id}`
  - Use existing curated apps endpoint for metadata + role gating.
- `GET /api/v1/apps/chemistry.reagent_prep_chef/chemicals`
  - Returns curated chemical list (key + display_name + aliases) for the typeahead picker.
- `POST /api/v1/apps/chemistry.reagent_prep_chef/prep`
  - Validates inputs strictly and returns a prep sheet response optimized for rendering (no tool/run orchestration).
- `POST /api/v1/apps/chemistry.reagent_prep_chef/export-pdf`
  - Returns `application/pdf` with `Content-Disposition: attachment; filename="reagensberedning.pdf"`.
- `POST /api/v1/apps/chemistry.reagent_prep_chef/save-pdf`
  - Saves the prep PDF to Vault and returns `VaultFileInfo`.
- `GET /api/v1/apps/chemistry.reagent_prep_chef/defaults`
- `PUT /api/v1/apps/chemistry.reagent_prep_chef/defaults`
  - Per-user defaults persisted via tool_sessions with `state_rev` optimistic concurrency.
- `POST /api/v1/apps/chemistry.reagent_prep_chef/save-defaults`
  - Exports defaults JSON to Vault and returns `VaultFileInfo`.
- `POST /api/v1/apps/chemistry.reagent_prep_chef/load-defaults`
  - Loads defaults JSON from Vault, validates it, and updates per-user defaults.
- `POST /api/v1/apps/chemistry.reagent_prep_chef/risk-assessment`
  - Generates/restores a deterministic risk draft and persists it via tool_sessions (`state_rev`).
- `POST /api/v1/apps/chemistry.reagent_prep_chef/export-risk-pdf`
- `POST /api/v1/apps/chemistry.reagent_prep_chef/save-risk-pdf`
  - Exports/saves a deterministic PDF riskbedömning document (requires confirmations + required context fields).
- `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/{sds_ref}`
  - Serves curated SDS attachments (offline-hosted; no runtime external fetch).

### Implementation plan

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
- Molar mass + normalization is implemented in-domain (no external chemistry API calls).
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

### Test plan

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

### Code review (as of 2026-01-28)

### Backend (DDD / Clean Architecture)

✅ **Strong points**

- **Domain stays pure:** calculation/normalization logic is isolated under
  `src/skriptoteket/domain/curated_apps/reagent_prep_chef/` and is testable without web/DB.
- **Thin web layer:** `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py` is access-gate + delegation only.
- **Stable errors:** app-specific error codes are surfaced via `DomainError.details.app_error_code`, enabling the SPA to
  show friendly, localized errors without tying domain code to HTTP.
- **No-slope safety:** curated hazard lookup with explicit SDS disclaimer on misses (no heuristics).
- **PDF generation via protocol:** renderer behind `ReagentPrepChefPdfRendererProtocol` keeps infra swappable; WeasyPrint
  dependencies are present in Dockerfile.

⚠️ **Issues / risks**

- **Export HTML styling:** `build_export_html()` embeds hard-coded CSS colors. It’s acceptable for PDF output, but it
  drifts from the HuleEdu token system; consider aligning palette/typography with tokens if PDF branding matters.
- **Hazards dataset grounding:** hazards list is expanded to ~160+ entries with Swedish names sourced from Wikidata
  (plus a small manual override map) via `scripts/generate_reagent_prep_chef_hazards_wikidata.py`. Hazard codes/CLP
  bands are still sparse and should be curated further for the most common classroom reagents.

🧪 **Test coverage notes**

- Domain unit tests cover formula normalization + calculation; hazards store has lookup tests; web API has route tests.
- Missing: an explicit unit test for “unknown chemical → SDS disclaimer payload” and “stock dilution invalid →
  app_error_code=ERR_IMPOSSIBLE_DILUTION” at the handler level (API tests cover some of this indirectly).

### Frontend (SPA / tokens-first)

✅ **Strong points**

- **Fail-closed routing policy:** `frontend/apps/skriptoteket/src/views/AppHostView.vue` blocks when
  `ui_mode=bespoke_required` and no bespoke view exists (no generic fallback for curated apps that require bespoke UX).
- **Chemicals search UX:** curated chemical search renders a live results list while typing, selectable via click, and
  selection mirrors into the dropdown.
- **App-specific API usage:** UI uses app endpoints (`/api/v1/apps/...`) for prep/export/defaults (no tool runner
  orchestration in the primary UX).

⚠️ **Issues / risks**

- **SRP/LoC:** `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue` is ~1300 LoC and mixes routing, state,
  storage, UI rendering, and interaction logic. Split into smaller components/composables (stepper, chemical picker,
  defaults/settings, result panel, export actions).
- **Tokens-first styling drift:** view still contains bespoke scoped CSS for the settings popover/trigger. Prefer Tailwind
  utilities + shared primitives (`btn-*`, token colors/shadows) to stay aligned with the design rules.

### Rollback plan

- Remove the curated app registry entry (hide from catalog) and redeploy.
- Keep code paths isolated so the demo curated app and normal tools remain unaffected.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
