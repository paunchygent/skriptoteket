---
type: pr
id: PR-0059
title: "Curated app: Reagent Prep Chef (implementation)"
status: ready
owners: "agents"
created: 2026-01-26
updated: 2026-01-26
stories:
  - "ST-20-01"
tags: ["curated-apps", "backend"]
acceptance_criteria:
  - "Curated app appears in Katalog with correct role gate and placement."
  - "App is bespoke-required: /apps/:appId renders a dedicated Reagent Prep Chef SPA view (generic AppDetailView is not used for this app)."
  - "App supports solid + liquid_stock flows with deterministic outputs and teacher-friendly validation errors."
  - "Safety output is curated-only with SDS fallback on misses."
  - "Export produces a downloadable PDF artifact."
---

## Problem

Teachers need quick, accurate solution prep calculations. Common mistakes include hydrate state ambiguity, purity
assumptions, and dilution math errors when scaling for multiple student groups.

## Goal

Ship **Reagent Prep Chef** as a first-class curated app (ADR-0023) with a modern, low-friction UX using Tool UI contract
v2 (ADR-0022) and persisted session state + ui_payload (ADR-0024).

## Non-goals

- No chemistry heuristics (exothermicity, incompatibilities, etc.).
- No online SDS fetching or external chemistry APIs.
- No multi-solute “recipes” (single-solute prep per run).

## Implementation plan

Backend wiring

- Add curated app entry to `InMemoryCuratedAppRegistry`:
  - `app_id=chemistry.reagent_prep_chef`
  - sensible Swedish title/summary
  - `min_role` agreed (teacher vs user)
  - initial placement (e.g. `larare/ovrigt`)
- Refactor curated app executor to dispatch by `app_id` (avoid growing `if app_id == ...` blocks).

Registry/UI policy plumbing

- Extend curated app metadata with `ui_mode: "bespoke_required" | "generic_ok"` (or equivalent `spa_view_id`).
- For Reagent Prep Chef, set `ui_mode="bespoke_required"` in the curated app registry.
- Expose `ui_mode` in:
  - curated app detail response (`GET /api/v1/apps/:appId`) and
  - any curated app catalog list payload where the SPA needs to decide routing/UX.

Core domain/service code (pure + testable)

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

Curated app UI payload (Tool UI contract v2)

- Implement actions: `start`, `calculate`, `export_pdf`, `reset`.
- Use typed outputs only (`notice`, `markdown`, `table`, `json`), with clear Swedish copy.
- Use action `prefill` so iterating doesn’t require retyping.

Export

- Implement `export_pdf`:
  - generate PDF artifact from the current prep sheet
  - write to `output/*.pdf` with path safety checks

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
  - preserve/restore state via tool session state + action prefill

## Test plan

Automated

- Unit tests for:
  - formula normalization (`CuSO4.5H2O`, `CuSO4*5H2O`, `CuSO4·5H2O`)
  - solid solute math (purity factor, safety factor)
  - dilution math (reject `stock_molarity <= target_molarity`)
  - curated hazards lookup hit/miss behavior
  - UI contract shape for each action (outputs/actions/state)
  - SPA view selection:
    - bespoke-known app renders bespoke view
    - bespoke_required without view shows blocking state
    - generic_ok without view falls back to generic renderer

Manual smoke (local)

1. Open the curated app from Katalog.
2. Run `start` → verify the form renders with defaults.
3. Run `calculate` with a curated reagent → verify prep sheet + safety outputs.
4. Run `calculate` with an unknown reagent → verify explicit SDS warning and no guessed hazards.
5. Run `export_pdf` → download PDF artifact and verify content.

## Rollback plan

- Remove the curated app registry entry (hide from catalog) and redeploy.
- Keep code paths isolated so the demo curated app and normal tools remain unaffected.
