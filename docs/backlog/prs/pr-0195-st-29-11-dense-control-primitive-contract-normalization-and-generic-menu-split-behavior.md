---
type: pr
id: PR-0195
title: "ST-29-11: dense-control primitive contract normalization and generic menu/split behavior"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "components", "klassrumskartan", "editor"]
dependencies:
  - "EPIC-29"
  - "PR-0157"
acceptance_criteria:
  - "Given the shared dense-control layer already exists, when this slice ships, then spacing, radius, hover, focus, active, disabled, and disclosure behavior live in the shared primitive contract rather than in toolbar-owned overrides."
  - "Given split-button and menu-button behavior is shared across planner and editor surfaces, when this slice ships, then those primitives expose generic item models and shared keyboard/focus-return behavior instead of planner-shaped APIs."
  - "Given dense controls are reused across the SPA, when this slice is complete, then the shared primitive helpers and exported components are the primary source of truth for dense control rhythm instead of local wrapper CSS."
---

## Problem

The first shared dense-control pass shipped the right primitives, but some of the real behavior
contract still leaks out into surface-owned CSS and wrapper assumptions. That makes the shared layer
look canonical on paper while still behaving like an adapter over local toolbar rules.

## Goal

Normalize the dense-control contract in the shared `components/ui` layer before touching another
wave of surface adoption:

- make shared primitive styling and interaction the source of truth
- finish generic menu/split behavior for cross-surface reuse
- reduce the need for toolbar-owned descendant selectors and local behavior patches

## Non-goals

- Full planner/editor adoption sweep.
- Canonical symbol audit/completion work from `ST-29-12`.
- Custom tooltip work from `ST-29-08`.
- Reopening workspace layout composition.

## Implementation plan

1. Normalize the shared dense-control contract in `src/components/ui/`.
   - Tighten `denseToolPrimitives.ts`.
   - Ensure radius, size tiers, hover, focus, active, disabled, and grouped disclosure behavior are
     owned by the shared primitive layer.

2. Finish generic menu/split behavior.
   - Refine `UiDenseMenuButton.vue`, `UiDenseSplitButton.vue`, and `useDenseMenuSurface.ts` so item
     models and focus-return behavior are shared and generic rather than planner-shaped.

3. Remove primitive-level drift in the export surface.
   - Update `PlannerExportActionGroup.vue` only as needed to consume the generic split contract,
     without widening into a full planner-wrapper cleanup pass.

4. Lock the contract with focused UI tests.

## Proposed module focus

- `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts`
- `frontend/apps/skriptoteket/src/components/ui/useDenseMenuSurface.ts`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseMenuButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseSplitButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/index.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`

## Test plan

- `pdm run fe-test -- --run src/components/ui/UiDenseSplitButton.spec.ts src/components/ui/UiDenseStatusPill.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Revert the shared primitive contract tightening as one unit if generic menu/split behavior proves
  unstable.
- Do not keep half-migrated split/menu APIs in both shared and planner-local forms.
