---
type: pr
id: PR-0188
title: "Flunk-Out Frenzy: machine-event contract expansion and PhysicsWorld decomposition"
status: done
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "physics", "architecture"]
dependencies:
  - "PR-0108"
acceptance_criteria:
  - "The Flunk-Out Frenzy physics layer no longer keeps collider metadata, event emission, and world orchestration collapsed into a single oversized `PhysicsWorld.ts` module."
  - "The `MachineEvent` contract can represent at least target, tripwire, launch-lane, gate, capture or eject, and save semantics without exposing Rapier internals to rules, runtime, or presentation code."
  - "Existing bumper, sling, rollover, drain, flipper, and launcher behavior keeps working after the decomposition."
---

## Problem

`PhysicsWorld.ts` is already above the repo size budget and its event surface is
still shaped for the first vertical slice. If we add targets, capture devices,
gates, and richer ball-lifecycle logic directly into the current file, the
physics boundary will become a monolith before the real mechanics even land.

## Goal

Create the narrow physics foundation for the mechanics-port story:

- broaden the semantic machine-event vocabulary
- split collider metadata and event emission into dedicated modules
- keep the public physics boundary stable for the runtime and rule engine

## Non-goals

- No new table devices yet.
- No bonus, jackpot, or objective logic yet.
- No visual redesign of the game shell.

## Implementation plan

- Expand
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
  so `MachineEvent` can express:
  - `tripwire-crossed`
  - `standup-target-hit`
  - `popup-target-hit`
  - `gate-passed`
  - `launch-lane-enter`
  - `ball-captured`
  - `ball-ejected`
  - `ball-saved`
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/colliderMeta.ts`
  for typed collider metadata and stable semantic tags.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/machineEventEmitter.ts`
  so contact-to-event translation no longer lives inline in `PhysicsWorld.ts`.
- Refactor
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  so it owns only world setup, stepping, command application, snapshot
  projection, and orchestration of the new helper modules.
- Update the split Flunk-Out Frenzy physics spec surface under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.*.spec.ts`
  to lock both legacy event behavior and the newly expanded event shapes.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- play one local run in `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
  and confirm the existing prototype-alpha session still launches, drains, and
  ends cleanly

## Rollback plan

- Remove the new physics helper modules.
- Collapse event translation back into `PhysicsWorld.ts`.
- Restore the previous `MachineEvent` union if downstream modules are not yet
  consuming the richer surface.

## Implementation summary

- Expanded
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
  so the machine-event contract can already represent tripwires, targets,
  gates, launch-lane entry, capture or eject, and save semantics without
  exposing Rapier details.
- Added
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/colliderMeta.ts`
  for typed collider metadata and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/machineEventEmitter.ts`
  for contact-to-event translation and authored impulse handling.
- Reduced
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  from 504 lines to 420 lines so the world class is back to orchestration,
  stepping, snapshots, and command handling.
- Updated the split Flunk-Out Frenzy physics spec surface under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.*.spec.ts`
  to keep the existing authored-zone behavior locked while also compile-checking
  the widened future-facing event surface.
