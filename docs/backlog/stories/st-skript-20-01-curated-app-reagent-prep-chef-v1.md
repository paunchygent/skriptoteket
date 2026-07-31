---
type: story
id: ST-SKRIPT-20-01
title: 'Curated app: Reagent Prep Chef (v1)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-20
acceptance_criteria:
- Given a teacher opens the curated app, when the app is started, then the UI shows
  a typed form with safe defaults and clear Swedish guidance.
- Given the app is marked bespoke-required, when the user opens /apps/:appId, then
  the SPA renders a dedicated Reagent Prep Chef view (and does not fall back to the
  generic AppDetailView).
- Given a valid solid-solute input (including hydrate notation), when the user runs
  Calculate, then the app returns a deterministic prep sheet with (a) total groups/volume,
  (b) molar mass + moles required, (c) required mass adjusted for purity, and (d)
  step-by-step instructions.
- Given a valid liquid_stock input, when the user runs Calculate, then the app returns
  a deterministic dilution plan (stock volume + diluent volume) and rejects impossible
  dilution with an actionable error.
- Given the chemical is present in curated hazards data, when results are returned,
  then the UI includes curated PPE/disposal/hazard codes; and given it is missing,
  then the UI includes an explicit 'Consult SDS' warning without guessed hazards.
- Given the user requests export, when export runs, then the app produces a PDF artifact
  of the prep sheet that is downloadable via the existing artifact endpoints.
retired_ids:
- ST-20-01
---

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
