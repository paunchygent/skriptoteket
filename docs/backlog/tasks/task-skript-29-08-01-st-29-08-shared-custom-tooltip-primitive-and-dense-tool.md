---
type: task
id: TASK-SKRIPT-29-08-01
title: 'ST-29-08: shared custom tooltip primitive and dense-tool adoption'
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
story: ST-SKRIPT-29-08
task_kind: story
acceptance_criteria:
- Given dense planner/editor controls still depend on browser-native `title` tooltips,
  when this slice ships, then the SPA exposes one shared custom tooltip primitive/composable
  that those controls can consume instead of leaving timing and chrome to the browser.
- Given tooltip timing should be tunable globally, when this slice ships, then the
  default hover/focus open delay and close behavior live in one shared frontend contract
  rather than being duplicated in local components.
- Given the enhancement should stay bounded, when this slice ships, then first adoption
  is limited to shared dense planner/editor controls and does not attempt a repo-wide
  tooltip migration.
- Given the tooltip system is part of the shared UI contract, when this slice ships,
  then keyboard and accessibility behavior (`role="tooltip"`, `aria-describedby`,
  focus entry, escape/dismiss behavior) are tested and consistent across the adopted
  controls.
dependencies:
- EPIC-SKRIPT-29
- ST-SKRIPT-29-08
---

## Context

### Source: Problem

The dense-tool control layer now exists, but its hover discoverability still depends mainly on
browser-native `title` behavior. That prevents product-owned timing, visual consistency, and future
global tuning.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Story Contract Slice

### Source: Goal

Introduce a shared custom tooltip primitive for dense planner/editor controls and migrate the first
adoption surfaces away from browser-native `title` handling.

## Contract Inputs

The source does not record separate contract inputs.

## Plan

### Source: Implementation plan

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

## Implementation Steps

### Source: PR-sized execution checklist

- [ ] Add a shared tooltip primitive/composable under `src/components/ui/`
- [ ] Freeze global tooltip timing/dismiss behavior in one shared contract
- [ ] Integrate the custom tooltip path into shared dense primitives
- [ ] Adopt the tooltip system on planner/editor dense-toolbar controls first
- [ ] Add Vitest coverage for accessibility and dismissal behavior
- [ ] Run live planner/editor proof and record it in `.codex/handoff.md`

## Proof

### Source: Test plan

- `pdm run fe-test -- --run src/components/ui`
- `pdm run fe-test -- --run src/components/editor/EditorWorkspaceToolbar.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/admin/tools/:toolId`

## Validation

### Source: Test plan

- `pdm run fe-test -- --run src/components/ui`
- `pdm run fe-test -- --run src/components/editor/EditorWorkspaceToolbar.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/admin/tools/:toolId`

## Stop Conditions

### Source: Non-goals

- Migrating every tooltip or hover-help surface in the repository.
- Reworking CodeMirror lint hovers or rich instructional popovers.
- Reopening the core EPIC-SKRIPT-29 sequencing or blocking `ST-29-01` through `ST-29-07`.
- Using the tooltip upgrade as cover for broader toolbar/layout surgery.

## Lessons Learned

The source does not record separate lessons learned.

## Notes

### Source: PR-sized execution checklist

- [ ] Add a shared tooltip primitive/composable under `src/components/ui/`
- [ ] Freeze global tooltip timing/dismiss behavior in one shared contract
- [ ] Integrate the custom tooltip path into shared dense primitives
- [ ] Adopt the tooltip system on planner/editor dense-toolbar controls first
- [ ] Add Vitest coverage for accessibility and dismissal behavior
- [ ] Run live planner/editor proof and record it in `.codex/handoff.md`

### Source: Rollback plan

- Revert the tooltip primitive/adoption slice as one unit if the shared contract proves unstable.
- Do not leave a half-migrated mix of custom and native dense-tool tooltip behavior behind.

## Plan Document Review

The source does not include a plan document review record.

## Implementation Review

The source does not include an implementation review record.
