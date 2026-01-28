---
type: reference
id: REF-curated-app-reagent-prep-chef
title: "Reference: Curated app — Reagent Prep Chef"
status: active
owners: "agents"
created: 2026-01-26
topic: "curated-apps"
links:
  - ADR-0022
  - ADR-0023
  - ADR-0024
  - ADR-0036
  - EPIC-20
  - ST-20-01
  - REV-EPIC-20
---

This document adapts **“The Reagent Prep Chef”** into a **Skriptoteket Curated App** (ADR-0023) implemented in the
FastAPI backend, rendered through **Tool UI contract v2** (ADR-0022), and persisted via **tool sessions + ui_payload**
(ADR-0024).

The goal is a teacher-first, SOTA-feeling prep calculator without “scripts fighting the UI”: the platform renders a
typed form and a structured prep sheet, while the backend stays deterministic and audit-friendly.

## Safety position (non-negotiable)

- This app **does not** replace an SDS, local lab rules, or supervision requirements.
- The app **must not** “guess” hazards. It only returns **curated** safety entries for known reagents and otherwise
  returns a **Consult SDS** response.
- The app is scoped to **classroom lab prep for aqueous solutions** (no synthesis guidance).

## Product goals

- **Zero ambiguity** around hydrate states and purity.
- **Fast**: instant results, no runner container roundtrip.
- **Friendly**: guided form, prefilled defaults, and a printable prep sheet.
- **Deterministic**: same input → same output, with explicit rounding rules.
- **Safe confidence**: curated safety lookup only, with SDS fallback on unknowns.

## Non-goals (v1)

- Predicting reaction heat / chemistry outcomes (no heuristics).
- Mixing multiple reagents into recipes (single-solute prep per run).
- Concentration-dependent hazard classification beyond curated entries.
- Direct SDS fetching from the SPA. Backend fetch + cache is allowed, but the SPA must only open backend-hosted SDS copies.

## App identity and catalog placement

### Proposed curated app identity

- `app_id`: `chemistry.reagent_prep_chef`
- `title` (SV): `Reagensberedning: Reagent Prep Chef`
- `summary` (SV): `Räkna ut massa/volym för lösningar med hydrat- och renhetsstöd + kuraterade skyddsråd.`
- `min_role`: `teacher` (or `user` if Skriptoteket users are already teachers)
- `placements` (initial, using existing taxonomy): `profession_slug="larare"`, `category_slug="ovrigt"`

If/when taxonomy grows, add a dedicated category (e.g. `kemi`) and update placements.

## Interaction model (Tool UI contract v2)

The app is interactive and runs via `POST /api/v1/start_action` (ADR-0024).

## Bespoke UI policy (no “generic UI” for this app)

Curated apps are allowed to ship bespoke UX. Tool UI contract v2 is the **safe transport + persistence boundary**, not a
UX ceiling.

### Policy

- This app is **bespoke-required**: the SPA must render a dedicated view (not the generic action/output renderer).
- Other curated apps may be **generic-ok** and use the generic `AppDetailView` as a fallback.

### Recommended plumbing

- Extend the curated apps registry metadata with either:
  - `ui_mode: "bespoke_required" | "generic_ok"`, or
  - `spa_view_id: string` (e.g. `reagent_prep_chef_v1`) plus an implicit fallback policy.
- The `/apps/:appId` route becomes an “app host”:
  - If a bespoke view is registered for the app, render it.
  - If `ui_mode=generic_ok` and no bespoke view exists, fall back to the generic `AppDetailView`.
  - If `ui_mode=bespoke_required` and no bespoke view exists, show a blocking “UI update required” screen.

### Actions (minimal set)

1. `start` — returns the form + “how it works” intro, with prefilled defaults from session state.
2. `calculate` — validates inputs, computes results, returns a prep sheet + safety + export actions.
3. `export_pdf` — generates a PDF artifact of the prep sheet for printing.
4. `reset` — clears session state and returns to defaults.

### Outputs (typed)

The result view uses platform primitives:

- `markdown`: human-readable prep sheet (steps + warnings).
- `table`: logistics summary and safety table.
- `json`: machine-readable “prep_result” object for debugging/traceability.
- `notice`: explicit SDS fallback warning when reagent safety is unknown.

## Input contract (UI fields + backend model)

Even though Tool UI contract actions carry untyped JSON, the curated app should validate the payload with Pydantic v2
and return a **recoverable** UI error (do not rely on HTTP 422 for normal user mistakes).

### Form fields (recommended)

Core:

- `chemical_formula` (`string`): e.g. `CuSO4·5H2O` or `CuSO4.5H2O` (normalized).
- `target_molarity` (`number`): mol/L (must be `> 0`).
- `vol_per_group_ml` (`number`): mL per workstation (must be `> 0`).
- `student_count` (`integer`): total students (must be `> 0`).
- `students_per_group` (`integer`, default `2`): must be `> 0`.
- `safety_factor` (`number`, default `0.10`): `0.0–0.5`.

Source selection:

- `source_type` (`enum`): `solid` or `liquid_stock` (default `solid`).
- `stock_molarity` (`number`): required when `source_type=liquid_stock`.
- `solute_purity` (`number`, default `1.0`): `> 0` and `<= 1.0`.

UX improvements (optional but recommended):

- `reagent_picker` (`enum`) backed by curated hazards data (common classroom reagents).
  - If set, it pre-fills `chemical_formula` and displays the canonical name + safety entry.
  - Still allow manual formula input for advanced use.

### Backend Pydantic model (shape)

Implement a strict model and validate cross-field logic:

- When `source_type=liquid_stock`: `stock_molarity` is required and must be `> target_molarity`.
- Reject volumes that imply unrealistic precision (warn, don’t fail) and enforce minimum measurable mass thresholds.

## Chemistry and calculations (deterministic)

### Group logistics

- `total_groups = ceil(student_count / students_per_group)`
- `base_total_volume_ml = total_groups * vol_per_group_ml`
- `total_volume_ml = base_total_volume_ml * (1 + safety_factor)`

Rounding:

- Round volumes for display only (e.g. 1 mL resolution); keep internal computation in `Decimal`.

### Solid solute case

- `moles_required = target_molarity * (total_volume_ml / 1000)`
- `mass_g = (moles_required * molar_mass_g_mol) / solute_purity`

### Liquid stock case (dilution)

- `stock_volume_L = (target_molarity * total_volume_L) / stock_molarity`
- `diluent_volume_L = total_volume_L - stock_volume_L`

If `stock_molarity <= target_molarity`: return a validation result (“impossible dilution”).

### Minimum mass guardrail

If `mass_g < 0.01` (configurable), return a warning output recommending preparing an intermediate stock first. This is
not a chemical heuristic; it’s a measurement/UX constraint.

## Formula parsing and molar mass strategy

### Normalization rules (input hygiene)

Normalize only separators and whitespace; do not “correct” chemistry:

- Replace `*` with `·`.
- Replace `.` with `·` only when it is used as a hydrate separator (e.g. `CuSO4.5H2O` → `CuSO4·5H2O`).
- Collapse whitespace and standardize `·` usage for display.

### Recommended dependency

Add a single, focused dependency for formula mass parsing:

- `molmass` (preferred) for robust molar mass calculation (supports parentheses and element counts).

If `molmass` is adopted, add it to `pyproject.toml` runtime dependencies and let PDM lock it in `pdm.lock`.

## Curated safety lookup (“no-slop”)

### Data source

Ship a repo-owned `hazards.json` (or `hazards.yaml`) with a curated list of common classroom reagents.

Recommended record shape:

```json
{
  "key": "CuSO4·5H2O",
  "display_name": "Kopparsulfat (pentahydrat)",
  "hazard_codes": ["H302", "H315", "H319"],
  "ppe": ["Skyddsglasögon", "Handskar"],
  "disposal": "Tungmetallavfall",
  "notes": ["Undvik inandning av damm."]
}
```

Lookup strategy:

- Key by **normalized formula** for deterministic matching.
- Optionally include `aliases[]` (common spellings) but still normalize to a single canonical key.
- On miss: return `{ level: "unknown", message: "Konsultera SDS innan användning." }`.

### Safety in UI

Safety outputs must be explicit about confidence:

- `notice` (warning): shown when `level="unknown"`.
- `table`: PPE/hazards/disposal for curated hits.

## Error handling (Skriptoteket-aligned)

Avoid throwing HTTP-layer errors for normal user mistakes. Prefer returning a failed UI result with actionable messages.

### App-level (preferred UX)

Return `ToolExecutionResult(status=FAILED)` with:

- `ui_result.status="failed"`
- `error_summary`: short Swedish message
- `outputs`: at least one `notice` explaining what to fix
- `next_actions`: keep the form action available with `prefill` set to the last valid values

### Platform-level (DomainError)

Use `DomainError` only for:

- unknown `action_id`
- contract violations (invalid payload types the app cannot interpret safely)
- internal execution failures (unexpected exceptions)

## Suggested backend structure (modular, protocol-first)

The existing curated app executor is a demo; for multiple apps, refactor to avoid a growing `if app_id == ...` block.

Recommended structure:

```text
src/skriptoteket/infrastructure/curated_apps/
  registry.py
  executor.py                 # dispatch-only
  apps/
    demo_counter.py
    reagent_prep_chef/
      __init__.py
      handler.py              # execute_action() -> ToolExecutionResult
      models.py               # Pydantic input/output models
      formula.py              # normalization + molar mass wrapper
      calc.py                 # pure calculations (Decimal)
      safety.py               # hazards lookup (IO behind a Protocol)
      data/hazards.json
tests/
  curated_apps/
    test_reagent_prep_chef.py
```

Protocols:

- `HazardLookupProtocol` (domain-facing): `get_by_formula(formula) -> HazardInfo | None`
- Infrastructure implementation reads `hazards.json` once at app startup (Scope.APP) and serves lookups from memory.

## Implementation plan (phased)

### Phase 0 — Design hardening (½ day)

- Finalize `hazards.json` record schema + canonical formula normalization.
- Decide the formula parser dependency (`molmass` recommended).

### Phase 1 — Core engine + tests (1–2 days)

- Implement formula normalization + molar mass calculation.
- Implement `solid` + `liquid_stock` math with `Decimal`.
- Unit tests: hydrates, dilution edge cases, rounding, minimum mass warning.

### Phase 2 — Curated app wiring (1 day)

- Add curated app definition to `InMemoryCuratedAppRegistry`.
- Implement `ReagentPrepChef` handler and dispatch via curated app executor.
- Implement `export_pdf` artifact generation (reuse existing PDF patterns).

### Phase 3 — UX polish (1 day)

- Provide Swedish copy for outputs and errors.
- Add “reagent picker” enum sourced from hazards data (optional).
- Ensure action `prefill` makes iteration fast (no retyping).

## Test plan (repo)

- `pytest -k reagent_prep_chef` (unit/integration tests for executor output)
- Manual smoke:
  1. Open app from Katalog.
  2. Run `start` → see form.
  3. Run `calculate` with a known reagent → see prep sheet + safety.
  4. Run `export_pdf` → download artifact and verify content.

## Deployment notes

- This is backend-only code shipped with the repo: deploy via the standard Skriptoteket Docker build/restart pipeline.
- No DB migrations required unless you later add app-specific persistence beyond `tool_sessions`.
