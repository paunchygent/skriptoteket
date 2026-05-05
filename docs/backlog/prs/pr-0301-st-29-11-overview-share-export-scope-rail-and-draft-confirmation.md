---
type: pr
id: PR-0301
title: "ST-29-11: overview share/export scope rail and draft confirmation"
status: done
owners: "agents"
created: 2026-05-06
updated: 2026-05-06
stories:
  - "ST-29-11"
  - "ST-26-06"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "overview", "sharing", "export"]
dependencies:
  - "PR-0286"
  - "PR-0295"
acceptance_criteria:
  - "Given the teacher opens `Dela och exportera` from `Översikt`, when both grouping and seating are available, then `Välj innehåll` uses the shared rail/toolbar toggle pattern instead of stacked large selectable rows."
  - "Given `Gruppindelning` or `Sittschema` is selected, when the panel renders, then an adjacent confirmation summary shows the selected draft context with class list and classroom, for example `SA24D · G20`, plus the selected content kind and update/create metadata."
  - "Given the selected content changes, when the teacher switches the rail toggle, then `Länk` and `Filer` update for the selected draft without visually shifting the panel columns or changing share/export state-machine ownership."
  - "Given a required class list or classroom is missing, when a disabled or unavailable scope is shown, then the rail and confirmation area state the missing prerequisite without silently selecting the wrong draft."
  - "Given the share/export panel is inspected at `1366x768`, `1440x900`, and phone width, then the left selector column stays balanced with the `Länk` and `Filer` columns, labels fit, and focus/selected states match the current Verdigris/action token contract."
---

## Problem

`PR-0286` correctly consolidated outward distribution into `Dela och exportera`,
but the overview panel's current `Välj innehåll` selector still reads as two
oversized stacked buttons. That makes the left column feel heavier than `Länk`
and `Filer`, and it does not confirm which class-list/classroom draft the
resulting link or file action will target.

Product-owner direction from the 2026-05-05 mockup review prefers the third
option in the selector alternatives: a compact rail/toolbar toggle plus a
selected-draft confirmation summary.

## Goal

Polish the overview `Dela och exportera` selector so it behaves like a familiar
Klassrumskartan rail control while giving teachers explicit draft confidence:

- use the compact rail/toggle pattern already established on adjacent planner
  screens
- keep the options as `Gruppindelning` and `Sittschema`
- show the active class list and classroom in the confirmation summary
- show the selected content kind and draft metadata below the rail
- preserve the existing `Länk` and `Filer` column contracts from `PR-0286`

## Non-goals

- No backend, API, share-artifact, export-job, or renderer changes.
- No change to generated PDF, poster, or Excel artifact formats.
- No change to share-link owner, TTL, revoke, expected-revision, or public-read
  contracts.
- No new global primitive unless the existing dense/segmented rail cannot meet
  the contract through a thin usage adapter.
- No redesign of the workspace toolbar `Dela` trigger.

## Implementation Plan

1. Update `PlannerShareExportScopeList.vue` so overview mode renders a compact
   two-option rail/toolbar selector rather than stacked large rows.
2. Extend the overview scope-option model in `PlannerOverviewDistributionPanel.vue`
   or `plannerShareExportActions.ts` with display-ready context metadata:
   class-list label, classroom label, content kind, and draft timestamp/count
   details already available in the overview shell.
3. Render a selected-draft confirmation summary below the rail. The summary
   should be information-only and must not introduce a second selector.
4. Preserve `PlannerShareExportPanel.vue`,
   `PlannerShareExportLinkSection.vue`, and `PlannerShareExportFileSection.vue`
   as separate composition seams so share and export flows remain independently
   testable.
5. Keep the desktop overview panel grid stable: the selector column should not
   push `Länk` or `Filer` vertically when the teacher switches scope.
6. Update focused component tests for selector rendering, selected-draft
   summary, disabled prerequisite states, and scope-switch events.
7. Capture browser proof against the existing `PR-0286` share/export proof lane,
   adding the overview selector state at `1366x768`, `1440x900`, and phone
   width.

## Test Plan

- `pdm run fe-test -- --run PlannerShareExportPanel PlannerClassWorkspace`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Retained or updated browser proof for `Dela och exportera` covering:
  - overview selector rail and selected `Sittschema` confirmation
  - overview selector rail and selected `Gruppindelning` confirmation
  - disabled/missing-prerequisite scope state
  - no column jump in `Länk` / `Filer` during scope switches

## Implementation Summary

Implemented as a frontend-only polish slice:

- `PlannerShareExportScopeList.vue` now renders `Gruppindelning` /
  `Sittschema` as a compact two-option rail with semantic icons instead of
  large stacked rows.
- `PlannerOverviewDistributionPanel.vue` now builds display-ready scope
  summaries with class-list label, classroom label, selected content kind,
  count metadata, and draft updated date when available.
- `PlannerClassWorkspace.vue` passes the selected roster/classroom context and
  active draft timestamps into the overview distribution panel.
- Disabled prerequisite states now show visible copy below the rail, not only a
  hidden/title tooltip.
- The desktop overview grid gives the selector column enough room for the rail
  and selected-draft confirmation while preserving the `Länk` and `Filer`
  column contracts.
- The retained `PR-0286` Playwright proof now also covers the overview selector
  rail at `390x844`, `1366x768`, and `1440x900`.

## Verification

- `pdm run fe-test -- --run PlannerShareExportPanel PlannerClassWorkspace`
  passed: 2 files / 20 tests.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run fe-build` passed; existing large chunk-size warnings remain.
- `pdm run ruff check scripts/_playwright_classroom_planner.py scripts/playwright_pr_0286_share_export_affordance.py tests/unit/scripts/test_playwright_script_surface.py`
  passed.
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
  passed: 3 tests.
- `pdm run python -m scripts.playwright_pr_0286_share_export_affordance --start-backend --start-vite`
  passed with rendered-height assertions for the overview scope rail, `Skapa
  länk`, and export buttons, and wrote overview selector screenshots at
  `.artifacts/playwright-pr-0286-share-export-affordance/overview-390x844-share-export-scope-selector.png`,
  `.artifacts/playwright-pr-0286-share-export-affordance/overview-1366x768-share-export-scope-selector.png`,
  and
  `.artifacts/playwright-pr-0286-share-export-affordance/overview-1440x900-share-export-scope-selector.png`.

## Rollback Plan

Restore the current stacked scope rows in `PlannerShareExportScopeList.vue` and
remove the selected-draft summary. Because this slice is frontend-only, rollback
must not require database, API, share, export, or renderer changes.

## References

- Parent primitive story:
  [ST-29-11](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Share/export contract story:
  [ST-26-06](../stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md)
- Prior share/export consolidation:
  [PR-0286](pr-0286-st-29-11-share-export-affordance-consolidation.md)
- Selector alternatives and preferred direction:
  [ST-29-11 share/export affordance consolidation mockup](../../mockups/st-29-11-share-export-affordance/README.md)
