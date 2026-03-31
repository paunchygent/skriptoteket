---
type: pr
id: PR-0157
title: "ST-29-01: shared dense-tool primitives and canonical symbol assets"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-03-31
stories:
  - "ST-29-01"
tags: ["frontend", "design-system", "components", "klassrumskartan", "editor"]
dependencies:
  - "EPIC-29"
  - "PR-0156"
acceptance_criteria:
  - "Given the frozen shared operation inventory, when this slice ships, then the canonical symbols for undo, redo, history, configure context, create, close, export/download, zoom in, zoom out, fit view, and overflow live in one shared icon surface instead of being redefined per tool."
  - "Given dense tool controls need a stable primitive contract, when this slice ships, then the SPA exposes shared primitive components for icon button, icon-led button, split button, menu button, toggle, and segmented mode switch using the shared role and behavior language from `REF-shared-tool-control-language-v1`."
  - "Given icon-only or icon-led controls render through these primitives, when they ship, then they expose accessible names, focus states, and discoverability rules consistently rather than relying on per-surface ad hoc markup."
  - "Given the repository still lacks a dedicated `frontend/packages/huleedu-ui` package, when this slice ships, then the canonical primitive implementation lives in one shared SPA location that later stories can consume without duplicating planner/editor-specific variants."
  - "Given `configure_context` routes to a destination that needs disambiguation such as `Regler` or `Inställningar`, when this slice ships, then the control does not render as a bare mystery gear and instead uses the shared adjustments/sliders symbol with icon-led or text-visible labeling."
  - "Given dense-action primitives are introduced, when this slice ships, then primitive size, spacing, disclosure width, hover, focus, active, and disabled behavior live in the primitives themselves rather than in toolbar-level descendant overrides."
  - "Given dense-tool buttons share one primitive family, when this slice ships, then corner treatment is harmonized as one hard small-radius (`4px`) shape language for standalone controls, with grouped controls keeping the same radius only on their outer edges instead of mixing square and rounded buttons casually on one toolbar."
  - "Given split and menu behavior are frozen in this slice, when shared components ship, then their APIs are generic enough for planner and editor reuse and include keyboard rules for open, navigate, escape, and focus return."
  - "Given undo and redo are frozen shared operations, when this slice ships, then editor and planner both render them through the canonical icon components rather than mixing icons with unicode glyphs."
  - "Given the segmented mode switch is introduced as a shared primitive, when this slice ships, then it freezes as a single-choice mode switch with the correct semantics rather than as an ambiguous pressed-button group."
---

## Problem

The control language is now defined, but the implementation substrate is still fragmented. Planner
and editor surfaces both use repeated operations, yet the reusable primitive layer for those
controls is not formalized.

## Goal

Implement the first shared dense-tool primitive layer for the SPA:

- canonical symbol assets
- shared role-aware control primitives
- shared accessibility and tooltip contract
- shared size tiers and disabled-state contract
- one stable primitive home for planner and editor reuse

## Non-goals

- Full workspace redesign.
- Rewriting all planner/editor controls in the same PR.
- Moving primitives into a separate package.
- Solving every future action category beyond the frozen v1 set.

## Implementation plan

1. Finalize the shared symbol inventory in code.
   - Consolidate and extend `frontend/apps/skriptoteket/src/components/icons/`.
   - Ensure one canonical icon export surface exists.
   - Add the missing shared plus/create, zoom in, zoom out, and fit-view icons.
   - Replace editor-local undo/redo unicode glyphs with the canonical icon components.

2. Add shared primitive components.
   - Create or refactor shared controls in `frontend/apps/skriptoteket/src/components/ui/`.
   - Cover:
     - icon-first toolbar action
     - icon-led action
     - split button
     - menu trigger
     - toggle
     - dense status pill
     - segmented mode switcher
     - compound toggle cluster for `toggle + configure_context child`

3. Encode the shared behavioral contract.
   - Tooltips / titles
   - `aria-label` / accessible-name rules
   - hover / focus / disabled / active states
   - compact dense-tool sizing and spacing
   - disabled-state opacity tiers
   - menu and split keyboard behavior
   - focus return after menu dismissal

4. Remove app-shaped APIs from candidate shared controls.
   - Refactor current split/menu candidates so they accept generic item models instead of
     planner-specific unions and hardcoded labels.
   - Resolve `configure_context` so it can disambiguate `Regler` / `Inställningar` instead of
     collapsing to a bare icon.

5. Replace planner/editor primitive stopgaps where safe.
   - Reduce one-off wrappers such as planner-local icon button treatments when they can become thin
     adapters over the shared primitive layer.
   - Remove dense-action dependence on page-button primitives such as `btn-ghost` plus local
     overrides.
   - Move repeated Klassrumskartan button recipes out of inline template class strings and into
     shared planner-facing button classes in `frontend/apps/skriptoteket/src/assets/main.css` so
     the planner can tune shape and density globally instead of per surface.
   - Remove overview-owned duplicate resume CTAs once the segmented mode switch is the canonical
     task-entry surface, and compress oversized overview/pool/canvas panels onto the same dense
     control-language rhythm.

6. Add focused component tests and one live proof on the current dense-tool surfaces.

## Coding assessment (2026-03-28)

The current codebase confirms that the primitive freeze should ship as a shared SPA layer first,
not as planner-local cleanup:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
  currently forces dense sizing through descendant selectors such as
  `[&_.btn-ghost]:px-3 [&_.btn-ghost]:py-1.5`, which violates the primitive-owned spacing rule.
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`
  already expresses the quieter dense-toolbar direction and should become a thin adapter over the
  shared icon-button primitive rather than remain the source of truth.
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
  is visually close to the target split button, but its API is still planner-shaped because it
  bakes planner export unions, default labels, and test ids into the component.
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`,
  `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`, and
  `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue` each carry their own menu
  lifecycle instead of reading from one shared keyboard/focus contract.
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue` still renders
  unicode undo/redo glyphs and derives dense controls from `btn-ghost`, which is explicitly out of
  bounds for this slice.
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue` is visually close to the
  target mode switch, but it still exposes pressed-button semantics instead of a single-choice
  mode-switch contract.

## Touched-file scope

The first implementation pass should stay inside the following files.

Shared icon surface:

- `frontend/apps/skriptoteket/src/components/icons/index.ts`
- `frontend/apps/skriptoteket/src/components/icons/IconPlus.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconZoomIn.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconZoomOut.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconFitView.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconAdjustments.vue`

Shared dense-tool primitives:

- `frontend/apps/skriptoteket/src/components/ui/index.ts`
- `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts`
- `frontend/apps/skriptoteket/src/components/ui/useDenseMenuSurface.ts`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseIconButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseMenuButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseSplitButton.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseStatusPill.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseToggle.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseCompoundToggle.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`

Planner/editor adoption surfaces:

- `frontend/apps/skriptoteket/src/assets/main.css`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerConfirmationDialog.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerMetadataDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesInspector.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesToolRail.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTemplateOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateEditorSidebar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/SeatNode.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue`

Verification surface:

- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.spec.ts`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseStatusPill.spec.ts`
- `frontend/apps/skriptoteket/src/components/ui/UiDenseSplitButton.spec.ts`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.spec.ts`

## Explicit deferrals

This PR should still avoid:

- shell surgery and feedback-band removal
- rules-rail visual composition work
- editor save/publish workflow standardization beyond the menu/button primitive contract
- package extraction into `frontend/packages/huleedu-ui`

## PR-sized execution checklist

- [ ] Consolidate `src/components/icons/*` and `src/components/icons/index.ts`
- [ ] Add or refactor shared dense-tool controls under `src/components/ui/`
- [ ] Freeze size tiers and disabled-state rules in the shared primitives
- [ ] Make split/menu APIs generic rather than planner-shaped
- [ ] Normalize editor undo/redo to the canonical icon components
- [ ] Update the primitive contract docs if implementation reveals a mismatch
- [ ] Add Vitest coverage for the new shared controls
- [ ] Run a live check on the planner and editor toolbars
- [ ] Record verification in `.agents/handoff.md` if implementation proceeds

## Ship gate

Do not merge this slice until all of the following are true:

- `configure_context` is resolved without a bare ambiguous gear
- dense-action buttons no longer inherit page-button behavior as their base
- editor undo/redo uses the canonical shared icons
- split/menu APIs are generic shared primitives rather than planner-shaped widgets

## Test plan

- `pdm run fe-test -- --run src/components/ui`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/admin/tools/:toolId`
  - `pdm run python -m scripts.playwright_pr_0157_dense_toolbar_check --base-url http://127.0.0.1:5173`
  - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`

## Rollback plan

- Revert the primitive implementation as one unit if the contract proves too unstable.
- Do not keep partial duplicate planner/editor primitives if the shared layer is backed out.
