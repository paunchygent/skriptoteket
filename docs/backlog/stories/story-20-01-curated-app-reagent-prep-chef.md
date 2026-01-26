---
type: story
id: ST-20-01
title: "Curated app: Reagent Prep Chef (v1)"
status: ready
owners: "agents"
created: 2026-01-26
epic: "EPIC-20"
dependencies: ["ADR-0022", "ADR-0023", "ADR-0024", "REF-curated-app-reagent-prep-chef"]
acceptance_criteria:
  - "Given a teacher opens the curated app, when the app is started, then the UI shows a typed form with safe defaults and clear Swedish guidance."
  - "Given the app is marked bespoke-required, when the user opens /apps/:appId, then the SPA renders a dedicated Reagent Prep Chef view (and does not fall back to the generic AppDetailView)."
  - "Given a valid solid-solute input (including hydrate notation), when the user runs Calculate, then the app returns a deterministic prep sheet with (a) total groups/volume, (b) molar mass + moles required, (c) required mass adjusted for purity, and (d) step-by-step instructions."
  - "Given a valid liquid_stock input, when the user runs Calculate, then the app returns a deterministic dilution plan (stock volume + diluent volume) and rejects impossible dilution with an actionable error."
  - "Given the chemical is present in curated hazards data, when results are returned, then the UI includes curated PPE/disposal/hazard codes; and given it is missing, then the UI includes an explicit 'Consult SDS' warning without guessed hazards."
  - "Given the user requests export, when export runs, then the app produces a PDF artifact of the prep sheet that is downloadable via the existing artifact endpoints."
ui_impact: "Yes (interactive curated app UI)"
data_impact: "No (uses existing curated apps + tool_sessions/tool_runs; hazards data is repo-owned)"
---

## Context

Teachers frequently need quick, accurate solution prep calculations. Common classroom failure modes include hydrate
state mistakes, purity assumptions, and mis-scaling volumes for group counts.

This story implements the app as **trusted backend code** (curated app path) to deliver a “real app” UX without runner
containers and without exposing an editor workflow.

## Notes

- Implementation reference: `docs/reference/ref-curated-app-reagent-prep-chef.md`
- UX principle: no chemical heuristics; curated-only safety; deterministic math with explicit rounding/warnings.
