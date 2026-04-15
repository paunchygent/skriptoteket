---
type: pr
id: PR-0129
title: "Klassrumskartan: shared planner action-bar zoning contract and grouping/seating remap"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-31
stories:
  - "ST-29-03"
tags: ["frontend", "ux", "klassrumskartan", "toolbar", "refactor"]
dependencies:
  - "PR-0114"
  - "PR-0128"
acceptance_criteria:
  - "The shared planner action-bar seam supports explicit reusable zones for context/setup, primary workflow actions, and secondary/overflow actions instead of only exposing one left slot plus one catch-all right slot."
  - "Grouping and seating both adopt that zoned action-bar contract without regressing their shipped teacher-facing behavior, control ordering, or export/history/settings affordances."
  - "The resulting zone model is documented and proven general enough that `ST-29-06` can reuse it later instead of inventing a one-off `Regler` toolbar layout."
---

## Problem

The current planner shell already ships user-facing grouping and seating toolbars that are denser,
stickier, and calmer than the old planner rows. What is still missing is the reusable primitive
contract underneath them.

[PlannerWorkspaceActionBar.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue)
still behaves as a thin visual wrapper with one `leading` slot and one catch-all right slot. That
means the actual zoning rules now live implicitly inside the grouping and seating toolbar
implementations rather than in a shared API that later `EPIC-29` stories can safely reuse.

## Goal

Codify the already-shipped grouping/seating toolbar behavior into one real shared action-bar zoning
contract, then remap both toolbars onto that contract without changing what teachers already see.

## Status note (2026-03-31)

This slice is now implemented locally through the shared planner toolbar seam:

- [PlannerWorkspaceActionBar.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue) now exposes explicit `primary`, `context`, and `secondary` slots and renders stable zone wrappers with `data-zone` hooks instead of only `leading` plus one catch-all slot.
- [PlannerGroupingWorkspaceToolbar.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue) and [PlannerSeatingWorkspaceToolbar.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue) now remap their existing teacher-facing controls onto those zones without changing control order, export/history/settings affordances, or the detached sticky-shell behavior.
- Focused frontend coverage now freezes the zone contract and toolbar adoption through [PlannerWorkspaceActionBar.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.spec.ts), [PlannerGroupingWorkspacePane.export.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts), and [PlannerSeatingWorkspacePane.export.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts).

## Locked design decisions

- Use the shared planner action-bar seam instead of creating a second unrelated toolbar primitive.
- Preserve the current shipped teacher-facing grouping and seating toolbar behavior; this is a
  contract-extraction pass, not a redesign.
- Prefer explicit semantic zones over width-driven wrap order.
- Keep clearly secondary actions eligible for overflow instead of competing with main workflow
  controls.
- Keep the resulting contract broad enough for later `ST-29-06` reuse without hard-coding it to
  either grouping or seating.

## Non-goals

- No new grouping or seating capabilities.
- No overview hierarchy work in this PR.
- No visible toolbar churn just for the sake of abstraction purity.
- No `Regler`-workspace redesign in this slice; that remains `ST-29-06`.

## Implementation plan

- Extend `PlannerWorkspaceActionBar.vue` into a real zoned API for:
  - context/setup
  - primary workflow actions
  - secondary actions / export / overflow
- Remap [PlannerGroupingWorkspaceToolbar.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue) onto that API while keeping the current grouping control order and overflow behavior intact.
- Remap [PlannerSeatingWorkspaceToolbar.vue](../../../frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue) onto the same API while preserving the current classroom selector, export cluster, and overflow behavior.
- Add focused coverage that proves grouping and seating still match the shipped layout grammar after the primitive extraction.
- Update `ST-29-03` notes so the remaining `EPIC-29` work clearly points at this contract rather than at already-shipped toolbar behavior.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`

## Test plan

- Focused frontend tests for zoned action-bar rendering plus grouping/seating toolbar adoption.
- Browser verification at `laptop` and `desktop` widths that grouping and seating remain ordered,
  legible, and behaviorally unchanged.
- `pdm run docs-validate`

## Rollback plan

- Revert the shared action-bar zoning API and restore the current grouping action row while keeping
  the broader shell decomposition from `PR-0114`.

## References

- Story parent: [ST-29-03](../stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- Planner shell/shared primitive baseline: [PR-0114](pr-0114-klassrumskartan-planner-shell-decomposition-and-shared-ui-primitives.md)
- Overview/shell simplification baseline: [PR-0112](pr-0112-klassrumskartan-overview-design-simplification-and-seamless-workspace-transitions.md)
- Rules-workspace follow-up consumer: [ST-29-06](../stories/story-29-06-klassrumskartan-rules-workspace-rail-map-inspector-rebalance.md)
- Frontend skill: [integrated-frontend-stack](/Users/olofs_mba/Documents/Repos/skill-repository/skills/integrated-frontend-stack/SKILL.md)
- Design-system rule: [045-huleedu-design-system](../../../.codex/rules/045-huleedu-design-system.md)
