---
type: pr
id: PR-0197
title: "ST-29-11: editor/site adoption proof and segmented-toggle contract completion"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "editor", "site", "segmented-toggle"]
dependencies:
  - "EPIC-29"
  - "PR-0195"
  - "PR-0196"
acceptance_criteria:
  - "Given dense controls are meant to be shared beyond the planner, when this slice ships, then editor and adjacent SPA surfaces prove the tightened primitives are genuinely cross-app rather than planner-local."
  - "Given `UiSegmentedToggle` is still used across planner and non-planner surfaces, when this slice ships, then its semantics and usage contract are complete enough that consumers act as thin adapters instead of reinterpreting it per surface."
  - "Given editor and non-planner tool surfaces use dense buttons and menus, when this slice is complete, then their behavior and rhythm stay aligned with the same primitive contract proven in the planner."
---

## Problem

After the primitive contract and planner wrappers are tightened, the remaining architectural proof
is whether the same contract still holds in the editor and other site/app surfaces. Without that
proof, the "shared" dense-control layer is still mostly a planner story.

## Goal

Complete `ST-29-11` by proving and finishing adoption across editor and adjacent non-planner
surfaces, with `UiSegmentedToggle` as the main cross-app contract seam.

## Non-goals

- Custom tooltip implementation from `ST-29-08`.
- Symbol-language completion from `ST-29-12`.
- Planner layout or workflow redesign.

## Implementation plan

1. Complete the segmented-toggle contract.
   - Tighten `UiSegmentedToggle.vue` semantics and consumer expectations where needed.

2. Prove editor adoption.
   - Align `EditorWorkspaceToolbar.vue` and `EditorToolMenu.vue` with the tightened primitive
     contract from `PR-0195`.

3. Prove site/app adoption beyond planner and editor.
   - Revisit current `UiSegmentedToggle` consumers such as vault/tool-run surfaces so they use the
     component through one stable contract instead of local interpretation drift.

4. Lock the cross-app contract with focused tests and live checks.

## Proposed module focus

- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.spec.ts`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.spec.ts`
- `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceModeSelector.vue`
- `frontend/apps/skriptoteket/src/components/vault/VaultPanel.vue`
- `frontend/apps/skriptoteket/src/components/tool-run/ToolFileFieldPicker.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`

## Test plan

- `pdm run fe-test -- --run src/components/ui/UiSegmentedToggle.spec.ts src/components/editor/EditorWorkspaceToolbar.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/admin/tools/:toolId`

## Rollback plan

- Revert the editor/site adoption proof as one slice if non-planner consumers reveal a broken
  primitive contract.
- Keep the earlier primitive and planner cleanup slices unless the issue proves the shared contract
  itself is wrong.
