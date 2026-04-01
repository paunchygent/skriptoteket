---
type: pr
id: PR-0182
title: "ST-29-10: workspace selector reachability and locked disabled-state copy"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-04-01
stories:
  - "ST-29-10"
tags: ["frontend", "ux", "klassrumskartan", "planner-shell", "swedish"]
dependencies:
  - "EPIC-29"
  - "PR-0184"
  - "ST-24-07"
  - "ST-27-07"
  - "PR-0114"
  - "PR-0115"
acceptance_criteria:
  - "Given no class is selected or available, when the shared planner workspace selector renders in `Översikt` or the live planner shell, then `Grupper`, `Sittplatser`, and `Regler` are visibly disabled, non-clickable, and use the exact locked disabled-state copy `Skapa först en klasslista.`"
  - "Given a class exists but no classroom is selected or available, when the shared planner workspace selector renders, then `Grupper` and `Regler` remain enabled, `Sittplatser` is visibly disabled and non-clickable, and the exact locked disabled-state copy reads `Skapa eller välj först ett klassrum.`"
  - "Given a disabled workspace option is shown, when the teacher interacts with it by mouse or keyboard, then the selector does not route into the old silent no-op path."
  - "Given the selector state is implemented, when focused frontend tests run, then the prerequisite matrix is locked in the planner top panel, overview shell, and live planner shell."
---

## Problem

The shared planner selector currently exposes unavailable workspaces as active options. That makes
the shell dishonest before the teacher has created the prerequisites needed to use those views.

## Goal

Make the shared workspace selector tell the truth about reachability:

- disable unavailable workspaces visibly and semantically
- keep `Regler` available once a class exists
- lock the disabled-state Swedish copy explicitly in the implementation task

## Locked copy

- No class disabled-state hint:
  - `Skapa först en klasslista.`
- No classroom disabled-state hint for `Sittplatser`:
  - `Skapa eller välj först ett klassrum.`

## Non-goals

- Adding the larger overview guidance line; that belongs to `PR-0183`.
- Changing the accepted product decision that `Regler` is available once a class exists.
- Adding a custom tooltip system, modal, toast, or walkthrough.

## Implementation plan

1. Add explicit prerequisite-state inputs to the shared planner selector path.
2. Thread disabled-state information through the overview shell and live planner shell into the
   shared segmented control.
3. Use the existing segmented-control disabled support; do not introduce a parallel workspace-nav
   primitive.
4. Lock the exact disabled-state copy above in the relevant view/component tests.
5. Verify that disabled options no longer fall through to the old silent route-shell early-return
   behavior.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellWorkspace.ts`

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Restore the selector's previous always-enabled presentation only if the disabled-state matrix
  proves technically incompatible with the current shell, while keeping the story-level product
  decision open for a corrected retry.
