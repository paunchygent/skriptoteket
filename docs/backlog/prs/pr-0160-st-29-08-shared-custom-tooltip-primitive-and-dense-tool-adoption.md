---
type: pr
id: PR-0160
title: "ST-29-08: shared custom tooltip primitive and dense-tool adoption"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-29-08"
tags: ["frontend", "klassrumskartan", "design-system", "tooltip", "ux"]
dependencies:
  - "EPIC-29"
  - "ST-29-08"
  - "PR-0157"
acceptance_criteria:
  - "Given dense planner/editor controls still depend on browser-native `title` tooltips, when this slice ships, then the SPA exposes one shared custom tooltip primitive/composable that those controls can consume instead of leaving timing and chrome to the browser."
  - "Given tooltip timing should be tunable globally, when this slice ships, then the default hover/focus open delay and close behavior live in one shared frontend contract rather than being duplicated in local components."
  - "Given the enhancement should stay bounded, when this slice ships, then first adoption is limited to shared dense planner/editor controls and does not attempt a repo-wide tooltip migration."
  - "Given the tooltip system is part of the shared UI contract, when this slice ships, then keyboard and accessibility behavior (`role=\"tooltip\"`, `aria-describedby`, focus entry, escape/dismiss behavior) are tested and consistent across the adopted controls."
---

## Problem

The dense-tool control layer now exists, but its hover discoverability still depends mainly on
browser-native `title` behavior. That prevents product-owned timing, visual consistency, and future
global tuning.

## Goal

Introduce a shared custom tooltip primitive for dense planner/editor controls and migrate the first
adoption surfaces away from browser-native `title` handling.

## Non-goals

- Migrating every tooltip or hover-help surface in the repository.
- Reworking CodeMirror lint hovers or rich instructional popovers.
- Reopening the core EPIC-29 sequencing or blocking `ST-29-01` through `ST-29-07`.
- Using the tooltip upgrade as cover for broader toolbar/layout surgery.

## Implementation plan

1. Add the shared tooltip substrate.
   - Create a shared tooltip primitive/composable under `frontend/apps/skriptoteket/src/components/ui/`.
   - Keep the API small and compatible with the dense-tool primitive layer from `PR-0157`.

2. Freeze the global hover contract.
   - Define one shared delay/timing contract for hover and focus-triggered tooltips.
   - Keep the values centrally owned so later tuning is global rather than per-surface.

3. Integrate with shared dense controls.
   - Update shared dense action/icon/menu/toggle primitives to opt into the custom tooltip path.
   - Remove browser-native `title` dependence from the first adopted dense controls where the new
     tooltip is active.

4. Migrate first proving-ground surfaces.
   - Planner dense toolbars in `Grupper` / `Sittplatser`.
   - Editor dense toolbar controls that already share the same primitive layer.

5. Verify behavior end to end.
   - Add focused component tests for hover/focus/escape behavior.
   - Run live proof on planner/editor surfaces at the canonical desktop review widths.

## PR-sized execution checklist

- [ ] Add a shared tooltip primitive/composable under `src/components/ui/`
- [ ] Freeze global tooltip timing/dismiss behavior in one shared contract
- [ ] Integrate the custom tooltip path into shared dense primitives
- [ ] Adopt the tooltip system on planner/editor dense-toolbar controls first
- [ ] Add Vitest coverage for accessibility and dismissal behavior
- [ ] Run live planner/editor proof and record it in `.agents/handoff.md`

## Test plan

- `pdm run fe-test -- --run src/components/ui`
- `pdm run fe-test -- --run src/components/editor/EditorWorkspaceToolbar.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/admin/tools/:toolId`

## Rollback plan

- Revert the tooltip primitive/adoption slice as one unit if the shared contract proves unstable.
- Do not leave a half-migrated mix of custom and native dense-tool tooltip behavior behind.
