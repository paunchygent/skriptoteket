---
type: pr
id: PR-0192
title: "Flunk-Out Frenzy: flipper contact model and explicit launcher state"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "physics", "controls"]
dependencies:
  - "PR-0191"
acceptance_criteria:
  - "Flipper-ball interaction is no longer modeled only through the current assist-impulse shortcut; the physics layer has an explicit flipper contact model with bounded configuration."
  - "The launcher or plunger flow is represented as explicit feed, charge, release, and relaunch state rather than inferred from a minimal pressed-or-not input flag."
  - "The resulting physics state remains behind the `PhysicsWorld` boundary and continues to emit semantic lifecycle events instead of Rapier details."
---

## Problem

The current flipper and launcher behavior is good enough for a first playable
slice, but it is still an approximation. The donor repo's most valuable physics
idea for us is not its whole solver, but its more explicit handling of flipper
contact and launcher timing.

## Goal

Strengthen the physical feel of the table before adding capture and ramp
devices:

- more faithful flipper contact behavior
- explicit launcher or plunger state
- clearer ball-lifecycle events around feed and release

## Non-goals

- No capture devices in this PR.
- No ramps or force zones in this PR.
- No attempt to port the donor engine's broadphase or collision system.

## Implementation plan

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

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/*.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify flippers can still cradle and strike the ball consistently
- verify launcher press, release, and relaunch behavior stays stable over a full
  3-ball run

## Rollback plan

- Remove the dedicated flipper and launcher helper modules.
- Restore the existing assist-impulse and simple charge-release flow.
- Keep the expanded event contract and tranche-one rule seams intact if
  downstream slices already depend on them.
