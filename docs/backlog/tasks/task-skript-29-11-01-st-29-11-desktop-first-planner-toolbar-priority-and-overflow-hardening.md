---
type: task
id: TASK-SKRIPT-29-11-01
title: 'ST-29-11: desktop-first planner toolbar priority and overflow hardening'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-29-11
task_kind: story
acceptance_criteria:
- Given grouping and seating action rows are dense desktop command surfaces, when
  width pressure increases at the canonical `laptop` and `desktop` review widths,
  then lower-priority actions collapse intentionally into overflow before any toolbar
  cluster detaches, spills visibly, or forces ugly catch-all wrapping.
- Given the current planner action bar still uses rigid zone wrappers, when this slice
  ships, then the width/overflow contract is explicit and priority-driven rather than
  relying on `overflow-visible`, unbounded `shrink-0` zones, or accidental spill behavior.
- Given this is a desktop-first hardening slice, when review proof is run, then grouping
  and seating keep one-row desktop command strips without ugly wrap fallbacks or detached
  right-edge controls.
---

## Context

### Problem

`PR-0224` fixed the planner-shell width regression, but it did not finish the
dense toolbar hardening. Grouping and seating still rely on a brittle
fixed-budget action-row contract, where rigid zones can misbehave under tighter
desktop widths even after the shell itself stays stable.

### Goal

Finish the remaining desktop-first toolbar hardening:

- define explicit priority tiers for grouping and seating actions
- collapse low-priority controls intentionally before the row degrades
- keep one-row desktop command strips intact at canonical laptop/desktop widths
- prevent detached export/overflow clusters and spill-driven layout breakage

### Non-goals

- Reopening planner-shell width stability.
- Reintroducing mobile-first wrap behavior as the default answer.
- Changing teacher-facing workflow semantics without a new product decision.

### Module focus

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`

### Test plan

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceActionBar.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live desktop proof:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - verify no detached export/overflow cluster appears in grouping or seating
  - verify grouping and seating stay composed at the canonical laptop/desktop review widths

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
