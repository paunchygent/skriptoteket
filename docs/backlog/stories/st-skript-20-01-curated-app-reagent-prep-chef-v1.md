---
type: story
id: ST-SKRIPT-20-01
title: 'Curated app: Reagent Prep Chef (v1)'
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
  approval_evidence: 'ST-SKRIPT-20-01#closeout'
epic: EPIC-SKRIPT-20
acceptance_criteria:
  - Given a teacher opens the curated app, when the app is started, then the UI shows a typed form with safe defaults and clear Swedish guidance.
  - Given the app is marked bespoke-required, when the user opens /apps/:appId, then the SPA renders a dedicated Reagent Prep Chef view (and does not fall back to the generic AppDetailView).
  - Given a valid solid-solute input (including hydrate notation), when the user runs Calculate, then the app returns a deterministic prep sheet with (a) total groups/volume, (b) molar mass + moles required, (c) required mass adjusted for purity, and (d) step-by-step instructions.
  - Given a valid liquid_stock input, when the user runs Calculate, then the app returns a deterministic dilution plan (stock volume + diluent volume) and rejects impossible dilution with an actionable error.
  - Given the chemical is present in curated hazards data, when results are returned, then the UI includes curated PPE/disposal/hazard codes; and given it is missing, then the UI includes an explicit 'Consult SDS' warning without guessed hazards.
  - Given the user requests export, when export runs, then the app produces a PDF artifact of the prep sheet that is downloadable via the existing artifact endpoints.
retired_ids:
  - ST-20-01
backlog_document_profile: contract-derived
---

## Slice Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0056 D5, because its acceptance holds on main. The original story text below is kept as history; see Closeout.

## Context

Teachers frequently need quick, accurate solution prep calculations. Common classroom failure modes include hydrate
state mistakes, purity assumptions, and mis-scaling volumes for group counts.

This story implements the app as **trusted backend code** (curated app path) to deliver a “real app” UX without runner
containers and without exposing an editor workflow.

## Epic Contract Slice

No separate material is recorded in the source snapshot.

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Tasks

- TASK-SKRIPT-20-01-01 (done)

## Verification

The source record did not define a separate section for this package heading.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 because the story's acceptance holds on main (orchestrator decision 2026-10-28, TASK-SKRIPT-REP-0056 D5); the Closeout section lists the evidence and the checks that were not run. |

## Live Verification Plan

No separate material is recorded in the source snapshot.

## Non-Goals

No separate material is recorded in the source snapshot.

## Notes

### Context

Teachers frequently need quick, accurate solution prep calculations. Common classroom failure modes include hydrate
state mistakes, purity assumptions, and mis-scaling volumes for group counts.

This story implements the app as **trusted backend code** (curated app path) to deliver a “real app” UX without runner
containers and without exposing an editor workflow.

### Notes

- Implementation reference: `docs/reference/ref-curated-app-reagent-prep-chef.md`
- UX principle: no chemical heuristics; curated-only safety; deterministic math with explicit rounding/warnings.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Story Closeout Review

No separate material is recorded in the source snapshot.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0056 D5 (orchestrator closeout on code evidence). Its only child, TASK-SKRIPT-20-01-01, is done. Acceptance on main:

1. Typed form with safe defaults and Swedish guidance: defaults in `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefForm.ts:36-45`, guidance in `views/apps/reagent-prep-chef/ReagentPrepChefStepSource.vue:29-31`.
2. Dedicated view, no generic fallback: the app is `BESPOKE_REQUIRED` (`src/skriptoteket/infrastructure/curated_apps/registry.py:56`) and `curatedAppHostRegistry.ts:32-35` maps it to `ReagentPrepChefView.vue`.
3. Solid solute with hydrates and purity: `src/skriptoteket/domain/curated_apps/reagent_prep_chef/calculator.py:21-31`, `formulas.py:24-45` and `handlers/reagent_prep_chef_prep.py:110-153`. A probe for CuSO4·5H2O gave 15 groups, 825 mL, molar mass 249.685, 20.60 g at purity 1.0 and 21.68 g at purity 0.95.
4. Liquid stock dilution: `reagent_prep_chef_prep.py:52-68` rejects a stock molarity at or below the target with `ERR_IMPOSSIBLE_DILUTION`, and the SPA shows an actionable message (`calculationErrorMessage.ts:11,18`). A probe with stock 1.0 for NaCl gave 82.5 mL stock and 742.5 mL diluent.
5. Curated hazards or an SDS warning: `reagent_prep_chef_prep.py:94-108`; unknown chemicals get "Okänt ämne: konsultera SDS innan användning." The result step shows PPE, disposal and the SDS warning (`ReagentPrepChefStepResult.vue:113-141`); H-codes appear in the risk step (`ReagentPrepChefStepRisk.vue:182, 219-222`) and the PDF, not in the result step.
6. PDF export through the artifact endpoints: `handlers/reagent_prep_chef_export_pdf.py:78-159` records a run whose output archive holds `output/reagensberedning.pdf`, and `/api/v1/runs/{run_id}/artifacts/{artifact_id}` serves it (`web/routes/interactive_tools.py:160-185`). The SPA downloads the PDF from `/export-pdf` directly and does not show the artifact URL.

Not checked: no walk of the app and no HTTP download of the artifact. Test gaps: no test uses a purity other than 1.0, none asserts `ERR_IMPOSSIBLE_DILUTION` or covers artifact recording. Roughly 60 of 164 entries in `hazards.json` have empty `hazard_codes` (for example NaCl); I did not check whether that data is right.
