---
type: pr
id: PR-0185
title: "ST-29-06: rules no-classroom fallback, organized off-map roster, and grouping hint copy alignment"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-03-31
stories:
  - "ST-29-06"
tags: ["frontend", "ux", "klassrumskartan", "rules", "copy"]
dependencies:
  - "EPIC-29"
  - "PR-0155"
  - "PR-0129"
  - "ST-29-10"
acceptance_criteria:
  - "The no-classroom `Regler` planning-map state uses the exact approved empty-map copy."
  - "Students who are not currently shown on the map render in one compact organized actionable roster surface instead of a loose wrapping chip cloud."
  - "Selection from that off-map roster preserves the current rules workflow: active tool, ordered selection, and pending create/save feedback."
  - "The `Grupper` workspace supporting hint uses the exact approved copy `Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.`"
  - "Focused browser proof confirms the no-classroom `Regler` state stays legible and organized at `1366x768` and `1440x900`."
---

## Problem

The current `Regler` no-classroom state still looks like fallback UI: the map area explains the
missing classroom, but the student list below is presented as a loose chip cloud. That makes the
primary interaction surface feel unstructured precisely when the teacher may want to start from
rules first rather than from a classroom layout.

At the same time, the current `Grupper` supporting hint under-describes the actual teacher task
because it ignores both randomization and deliberate placement.

## Goal

Refine the remaining teacher-facing planner guidance so:

- the no-classroom `Regler` state feels intentional and usable
- off-map students remain easy to scan and select for rule authoring
- grouping guidance matches the real teacher workflow in calm Swedish copy

## Locked copy

- No-classroom `Regler` planning-map guidance:
  - `Välj ett klassrum i arbetsytan Sittplatser och placera ut eleverna om du vill arbeta med regler direkt utifrån klassrummets möblering.`
- `Grupper` supporting hint:
  - `Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.`

## Non-goals

- No smart-rule contract changes.
- No changes to rule persistence, export behavior, or planner routing.
- No new rule-editing capabilities.
- No redesign of the rules tool rail or map interaction model beyond the no-classroom state.

## Implementation plan

1. Update the no-classroom empty-map copy in `PlannerRulesMapCanvas.vue`.
2. Replace the loose off-map student chip cloud with a more organized actionable roster
   presentation that still supports rule selection.
3. Preserve existing selection-order and pending-rule feedback semantics while using the organized
   roster surface.
4. Update the `Grupper` workspace supporting hint in `PlannerWorkspaceShell.vue`.
5. Extend focused Vitest coverage for the no-classroom rules state and the updated grouping hint.

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/assets/main.css`
- `docs/mockups/st-29-06-rules-no-classroom-fallback/index.html`

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live proof against `http://127.0.0.1:5173`:
  - `laptop` `1366x768`
  - `desktop` `1440x900`
  - verify `Regler` with class selected but no classroom selected
  - verify the off-map student surface reads as organized and remains selectable
  - verify the updated `Grupper` hint renders exactly

## Rollback plan

- Revert the organized off-map roster presentation to the current chip cloud if it causes
  selection regressions.
- Keep the existing rules tool rail, map, and persistence seams intact while rolling back only the
  no-classroom presentation and helper copy changes.
