---
type: task
id: TASK-SKRIPT-25-05-02
title: 'Flunk-Out Frenzy: flipper contact model and explicit launcher state'
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
story: ST-SKRIPT-25-05
task_kind: story
acceptance_criteria:
- Flipper-ball interaction is no longer modeled only through the current assist-impulse
  shortcut; the physics layer has an explicit flipper contact model with bounded configuration.
- The launcher or plunger flow is represented as explicit feed, charge, release, and
  relaunch state rather than inferred from a minimal pressed-or-not input flag.
- The resulting physics state remains behind the `PhysicsWorld` boundary and continues
  to emit semantic lifecycle events instead of Rapier details.
---

## Context

Source: `docs/backlog/prs/pr-0192-flunk-out-frenzy-flipper-contact-model-and-explicit-launcher-state.md`. Flunk-Out Frenzy: flipper contact model and explicit launcher state.

The current flipper and launcher behavior is good enough for a first playable slice, but it is still an approximation. The donor repo's most valuable physics idea for us is not its whole solver, but its more explicit handling of flipper contact and launcher timing. Strengthen the physical feel of the table before adding capture and ramp devices: - more faithful flipper contact behavior - explicit launcher or plunger state - clearer ball-lifecycle events around feed and release - No capture devices in this PR. - No ramps or force zones in this PR. - No attempt to port the donor engine's broadphase or collision system. - Create `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/g

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-25-05-02 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

The current flipper and launcher behavior is good enough for a first playable
slice, but it is still an approximation. The donor repo's most valuable physics
idea for us is not its whole solver, but its more explicit handling of flipper
contact and launcher timing.

### Goal

Strengthen the physical feel of the table before adding capture and ramp
devices:

- more faithful flipper contact behavior
- explicit launcher or plunger state
- clearer ball-lifecycle events around feed and release

### Non-goals

- No capture devices in this PR.
- No ramps or force zones in this PR.
- No attempt to port the donor engine's broadphase or collision system.

### Implementation plan

- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/flipperContactModel.ts`
  to own angle-aware flipper impulse transfer and contact heuristics.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.ts`
  to own launcher feed, charge, release, and relaunch timing.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  to delegate flipper and launcher behavior to those modules instead of keeping
  the logic inline.
- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTable.ts`
  with the authored launcher or feed parameters needed by the new model.
- Add focused specs for the new flipper and launcher modules plus updated
  coverage in
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`.

### Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/*.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify flippers can still cradle and strike the ball consistently
- verify launcher press, release, and relaunch behavior stays stable over a full
  3-ball run

### Rollback plan

- Remove the dedicated flipper and launcher helper modules.
- Restore the existing assist-impulse and simple charge-release flow.
- Keep the expanded event contract and tranche-one rule seams intact if
  downstream slices already depend on them.

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
