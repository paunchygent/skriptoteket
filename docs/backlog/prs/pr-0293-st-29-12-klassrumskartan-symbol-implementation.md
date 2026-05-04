---
type: pr
id: PR-0293
title: "ST-29-12: Klassrumskartan symbol implementation"
status: done
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-12"
tags: ["frontend", "components", "design-system", "icons", "klassrumskartan"]
dependencies:
  - "EPIC-29"
  - "PR-0292"
acceptance_criteria:
  - "Given the accepted symbol matrix, when Klassrumskartan renders its workspace modes, rules tools, share/export controls, and management actions, then each repeated concept uses the approved symbol."
  - "Given share links render, when users see link/copy/share affordances, then link symbols are reserved for actual links rather than relationship rules."
  - "Given shared icon wrappers currently use hand-authored SVGs, when this implementation ships, then `IconAdjustments`, `IconFitView`, `IconMinus`, `IconZoomIn`, and `IconZoomOut` are backed by the locked Lucide replacements from `PR-0292` without changing visible labels or layout."
  - "Given a symbol changes visually, when tests and browser proof run, then no layout regression or button text overflow is introduced."
---

## Problem

Klassrumskartan needs the approved symbol language applied in runtime UI without
reopening layout, color, or workflow decisions.

## Goal

Apply the `PR-0292` semantic symbol decisions to Klassrumskartan.

The implementation should focus on:

- workspace mode symbols
- rules-tool symbols
- Dela/share/export/file symbols
- common management actions inside Klassrumskartan
- student/classroom/class-list symbols

## Non-goals

- Reworking toolbar priority or overflow placement.
- Reopening small-screen layouts.
- Changing share/export behavior.
- Changing rule semantics or smart-placement behavior.

## Implementation Plan

1. Add or update canonical icon wrappers under
   `frontend/apps/skriptoteket/src/components/icons/`.
2. Replace direct feature-local Lucide imports where the decision matrix calls
   for a wrapper.
3. Replace the current custom SVG wrapper internals with their locked Lucide
   counterparts:
   - `IconAdjustments` -> `SlidersHorizontal`
   - `IconFitView` -> `Fullscreen` behind the existing fit-view wrapper name
   - `IconMinus` -> `Minus`
   - `IconZoomIn` -> `ZoomIn`
   - `IconZoomOut` -> `ZoomOut`
4. Replace overloaded symbols such as non-link `IconLink2` usage.
5. Preserve existing accessible names and visible labels unless the decision
   matrix explicitly changes label language.
6. Add focused component tests for the highest-risk semantic swaps.
7. Run live Klassrumskartan browser proof at the EPIC-29 viewports when visible
   workspace symbols change.

## Test Plan

- `pdm run fe-type-check`
- `pdm run fe-lint`
- focused Vitest specs for touched components
- live Playwright proof across EPIC-29 viewport names for touched
  Klassrumskartan surfaces
- `git diff --check`

## Rollback Plan

Revert the runtime icon swaps while keeping the approved docs matrix so the
implementation can be re-applied in smaller component slices.

## Implementation Summary

- Added the approved code-facing icon wrappers under
  `frontend/apps/skriptoteket/src/components/icons/`, including the Tabler-backed
  `IconGroupsWorkspace` and `IconClassroom` exceptions from `PR-0292`.
- Replaced the old hand-authored SVG wrapper internals for adjustments, fit-view,
  minus, zoom-in, and zoom-out with their locked Lucide counterparts.
- Updated Klassrumskartan workspace mode, rules-tool, share/copy/file, student,
  and rule-management icon usage without changing visible labels, toolbar
  priority, or share/export behavior.
- Kept `IconLink2` usage on actual share/link surfaces and removed it from
  relationship-rule semantics.

## Verification

- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-test -- --run PlannerTopPanel PlannerRulesWorkspacePane PlannerShareExportPanel PlannerShareLinksPanel PlannerSeatingWorkspacePane.smart-rules`
- `pdm run python -m scripts.playwright_st_29_small_screen_remaining_workspaces --start-backend --start-vite`
