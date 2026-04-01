---
type: pr
id: PR-0183
title: "ST-29-10: overview prerequisite guidance and help-affordance copy"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-04-01
stories:
  - "ST-29-10"
tags: ["frontend", "ux", "klassrumskartan", "overview", "swedish"]
dependencies:
  - "EPIC-29"
  - "PR-0184"
  - "PR-0182"
  - "ST-08-34"
acceptance_criteria:
  - "Given no class is selected or available, when `Översikt` renders the prerequisite guidance, then the exact overview copy reads `Börja med att skapa en klasslista.`"
  - "Given a class exists but no classroom is selected or available, when `Översikt` renders the prerequisite guidance, then the exact overview copy reads `Nu har du skapat din klass. Skapa eller välj ett klassrum för att använda Sittplatser.`"
  - "Given the prerequisite guidance surface is visible, when the teacher needs more help, then the exact help-affordance copy reads `Behöver du mer vägledning kan du trycka på Hjälp.`"
  - "Given the copy slice ships, when focused frontend tests and a live local browser proof run, then the compact guidance remains calm, obvious, and free of new banner/modal/walkthrough chrome."
---

## Problem

Even after the selector itself is made honest, the teacher still needs one short, immediate message
that explains what to do next. The current planner surface does not carry that first-run guidance.

## Goal

Add one compact prerequisite-guidance line in `Översikt` using the exact approved Swedish copy and
one small pointer to `Hjälp`, without turning the planner into a larger onboarding experience.

## Locked copy

- No class overview guidance:
  - `Börja med att skapa en klasslista.`
- Class exists, no classroom overview guidance:
  - `Nu har du skapat din klass. Skapa eller välj ett klassrum för att använda Sittplatser.`
- Help-affordance line:
  - `Behöver du mer vägledning kan du trycka på Hjälp.`

## Non-goals

- Rewriting the existing `Hjälp` drawer content or the getting-started guide.
- Adding a walkthrough, coach marks, animation, or a second help surface.
- Changing which workspaces are reachable; that is handled in `PR-0182`.

## Implementation plan

1. Reuse the existing compact planner shell language rather than adding a new full-width helper
   panel.
2. Render the exact locked copy above for the no-class and class-without-classroom states.
3. Keep the guidance line scoped to first-run prerequisite states; once the prerequisite is met,
   the temporary guidance should disappear.
4. Add focused tests that lock the exact strings and confirm the copy only appears in the intended
   prerequisite states.
5. Run one live local browser proof at `http://127.0.0.1:5173` covering the two prerequisite
   states.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts`

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - verify no-class state
  - verify class-without-classroom state
  - verify the exact approved copy and the `Hjälp` affordance line

## Rollback plan

- Remove the new compact guidance line and keep the selector gating from `PR-0182` if later review
  finds a better planner-surface location for the same locked copy.
