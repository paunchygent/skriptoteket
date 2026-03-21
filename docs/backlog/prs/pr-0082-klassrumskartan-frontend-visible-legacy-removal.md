---
type: pr
id: PR-0082
title: "Klassrumskartan: frontend visible legacy removal and surface decoupling"
status: ready
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-05"
tags: ["frontend", "ux"]
acceptance_criteria:
  - "The default planner UI no longer exposes superseded advanced planner surfaces or opposite-axis context leaks."
  - "Dead or unwired solver-era UI components are removed instead of left in the codebase."
  - "The default grouping and seating surfaces teach one task at a time and follow current design-system expectations."
---

## Problem

The current frontend still contains visible remnants of the superseded planner direction:

- `Placeringprofil` remains part of the default planner shell
- grouping still leaks seat context and seating still leaks group context
- the old suggestions/finalize panel still exists in the codebase
- static room-canvas presentation still lives partly in inline styles

These are not harmless leftovers. They keep teaching the wrong mental model.

## Goal

Remove the visible old-direction planner surface so the shipped UI only reflects approved
fundamentals.

## Non-goals

- Full class-first workspace implementation from `ST-24-02`
- Backend/public API cleanup
- Draft-kind lifecycle refactoring

## Checklist

- [ ] Remove `PlannerSuggestionsPanel.vue` and any unused imports, references, or dead tests connected to it.
- [ ] Remove the default-shell `Placeringprofil` entry point and any other prominently visible advanced planner controls that are not part of the approved near-term workflow.
- [ ] Remove seat-context leakage from grouping surfaces.
- [ ] Remove group-context leakage from seating surfaces.
- [ ] Keep grouping and seating focused on their own task language and default affordances.
- [ ] Move static room-grid presentation out of inline strings and into design-system-aligned class or CSS-variable-backed styling.
- [ ] Update frontend tests so they assert the cleaned default surface instead of preserving old planner controls.

## Implementation plan

- Prune dead or superseded planner UI components first.
- Simplify the active shell so it only exposes approved fundamentals.
- Make grouping/seating components task-pure by removing default opposite-axis hints.
- Tighten canvas presentation so static styling does not remain hard-coded inline.

## Test plan

- Frontend unit/component tests for the planner shell, grouping board, and room canvas
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run ...`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- Manual live check that the default planner no longer shows solver-era controls or cross-mode leakage

## Rollback plan

- Revert the frontend cleanup PR if it breaks manual grouping/seating, then re-land it in narrower UI-only slices without restoring dead components or old planner affordances.
