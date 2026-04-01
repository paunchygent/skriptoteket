---
type: pr
id: PR-0189
title: "Flunk-Out Frenzy: lanes, targets, and tripwire devices"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "physics", "table"]
dependencies:
  - "PR-0188"
acceptance_criteria:
  - "Typed table definitions exist for richer lane and target devices, including grouped rollovers, standup targets, popup targets, and tripwire or gate-style pass-through sensors."
  - "The Rapier-backed physics layer can build those devices from authored table data and emit semantic machine events without leaking engine details into rules or presentation code."
  - "The runtime can surface the resulting target and lane events as stable game effects without forcing Vue to own machine state."
---

## Problem

After `PR-0188`, the event contract is ready for more device types, but the
table authoring and physics factory surface still only knows about the narrow
prototype-alpha subset. We need the first real device expansion before bonus,
jackpot, or mission-style rules make sense.

## Goal

Introduce the first new device families from the donor mechanics:

- richer lanes
- standup and popup targets
- tripwires or pass-through sensors

## Non-goals

- No capture devices yet.
- No ramp or force-zone work yet.
- No mission controller logic yet.

## Implementation plan

- Extract shared table schemas into
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  so `prototypeAlphaTable.ts` can grow without becoming the next oversized
  module.
- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTable.ts`
  with typed definitions for:
  - grouped rollover lanes
  - standup targets
  - popup targets
  - tripwires
  - simple gates where useful for authored paths
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/createLaneDevices.ts`
  for rollover, tripwire, and gate sensor construction.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/createTargetDevices.ts`
  for standup and popup target construction plus cooldown or reset handling.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
  to wire the new devices into the expanded event surface.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/presentation/gameEffectTypes.ts`
  so target and lane events can become semantic game effects.
- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
  with target-bank and tripwire coverage.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify the new target and lane devices can be triggered in a local run and
  produce stable game feedback without breaking the existing bumper or drain
  loop

## Rollback plan

- Remove the added table definition types and device factories.
- Revert the authored prototype table to the pre-target layout.
- Drop the new target or lane game-effect mappings if downstream handling is
  not yet ready.
