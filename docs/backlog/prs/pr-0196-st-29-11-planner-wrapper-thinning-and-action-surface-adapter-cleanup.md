---
type: pr
id: PR-0196
title: "ST-29-11: planner wrapper thinning and action-surface adapter cleanup"
status: canceled
owners: "agents"
created: 2026-04-01
updated: 2026-06-18
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "klassrumskartan", "planner", "refactor"]
dependencies:
  - "EPIC-29"
  - "PR-0195"
  - "ST-29-05"
acceptance_criteria:
  - "Given planner-facing dense controls already render through shared primitives, when this slice ships, then planner wrappers are thin usage adapters rather than secondary sources of density, spacing, or interaction behavior."
  - "Given planner action surfaces still carry toolbar-owned styling and wrapper-specific behavior, when this slice is complete, then the shared action-bar and wrapper layer delegates visual/interactive rules downward into the primitives instead of re-owning them."
  - "Given grouping, seating, and rules tool surfaces already have a shipped layout, when this slice ships, then they keep the same teacher-facing composition while their wrapper stack becomes simpler and less redundant."
---

## Problem

The planner now uses the shared dense-control family heavily, but several planner-facing wrappers
still do more than adapt labels and test hooks. That keeps planner-owned styling and interaction
logic alive in exactly the places `ST-29-11` is supposed to simplify.

## Goal

Thin the planner wrapper layer so the shared primitives own behavior and the planner wrappers mainly
map planner-specific copy, events, and test ids.

## Non-goals

- Re-cutting planner layout or toolbar zoning.
- New teacher-facing planner capabilities.
- Editor/site-wide adoption proof work; that belongs to `PR-0197`.
- Canonical symbol/discoverability completion from `ST-29-12`.

## Implementation plan

1. Thin planner-specific wrappers.
   - Revisit `PlannerToolbarIconButton.vue`, `PlannerToolbarOverflowMenu.vue`, and
     `PlannerExportActionGroup.vue` after `PR-0195`.

2. Tighten the planner action-surface seam.
   - Update `PlannerWorkspaceActionBar.vue` and the grouping/seating/rules toolbar consumers so
     they stop owning dense-control presentation details that belong in the primitives.

3. Keep planner behavior stable.
   - Preserve the current shipped grouping/seating/rules composition and ordering.
   - Focus on adapter cleanup, not visible workflow redesign.

4. Add focused planner coverage plus live desktop-proof checks.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesToolRail.vue`

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceActionBar.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`

## Rollback plan

- Revert the planner-wrapper cleanup pass if adapter thinning destabilizes shipped planner controls.
- Keep the shared primitive tightening from `PR-0195` intact unless the bug is truly in the
  primitive contract itself.

## Supersession Note (2026-06-18)

Canceled during `PR-0359` as absorbed by the later shipped `ST-29-11` planner
hardening set. Shared planner wrapper and action-surface work now lives in the
implemented later slices rather than in this older generic cleanup draft.
