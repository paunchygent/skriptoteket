---
type: task
id: TASK-SKRIPT-29-11-01
title: 'ST-29-11: desktop-first planner toolbar priority and overflow hardening'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-29-11-01#closeout'
story: ST-SKRIPT-29-11
task_kind: story
acceptance_criteria:
  - Given grouping and seating action rows are dense desktop command surfaces, when width pressure increases at the canonical `laptop` and `desktop` review widths, then lower-priority actions collapse intentionally into overflow before any toolbar cluster detaches, spills visibly, or forces ugly catch-all wrapping.
  - Given the current planner action bar still uses rigid zone wrappers, when this slice ships, then the width/overflow contract is explicit and priority-driven rather than relying on `overflow-visible`, unbounded `shrink-0` zones, or accidental spill behavior.
  - Given this is a desktop-first hardening slice, when review proof is run, then grouping and seating keep one-row desktop command strips without ugly wrap fallbacks or detached right-edge controls.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

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

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

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

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

The planner toolbar priority and overflow ladder shipped in `usePlannerToolbarOverflow.ts` (commit 7eace6443, parity fixes cf0c20c1f and c2f606f92), consumed by the grouping and seating toolbars with the order context, `Börja om`, share/export, and no `overflow-visible` left in the toolbars. The one-row behaviour at laptop and desktop widths was not checkable offline; TASK-SKRIPT-29-11-02 carries the exact-cutoff browser proof and the undo/redo overflow step. Closed on code under D1; TASK-SKRIPT-29-11-02 owns the exact-cutoff live proof and the undo/redo overflow step. The ladder registers context, reset and distribution (`useGroupingToolbarOverflow.ts:75-88`); undo-redo and new-draft stay inline.
