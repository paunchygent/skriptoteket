---
type: pr
id: PR-0157
title: "ST-29-01: shared dense-tool primitives and canonical symbol assets"
status: ready
owners: "agents"
created: 2026-03-28
updated: 2026-03-28
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

6. Add focused component tests and one live proof on the current dense-tool surfaces.

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

## Rollback plan

- Revert the primitive implementation as one unit if the contract proves too unstable.
- Do not keep partial duplicate planner/editor primitives if the shared layer is backed out.
