---
type: pr
id: PR-0194
title: "Flunk-Out Frenzy: ramps, gates, and field-zone semantics"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "physics", "table"]
dependencies:
  - "PR-0193"
acceptance_criteria:
  - "Typed table definitions exist for authored ramps, gates, and field-zone style path semantics needed by the expanded local table."
  - "The physics layer can model ramp and gate transitions inside Rapier without porting the donor repo's custom broadphase or edge manager."
  - "Ramp, gate, and path-transition events are exposed as semantic machine events that future objective rules can consume."
---

## Problem

Capture devices and targets still leave the table mostly flat. To make the
local runtime feel closer to a richer pinball table, we need authored path
changes such as ramps, one-way gates, and controlled force or guidance zones.
This is also where it becomes especially important not to copy the donor
repo's engine architecture blindly.

## Goal

Add the authored path semantics needed for richer table choreography:

- ramps
- gates
- bounded field or guidance zones

## Non-goals

- No direct port of `TEdgeManager`.
- No generic level editor.
- No full mission system yet.

## Implementation plan

- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTable.ts`
  with typed ramp, gate, and field-zone definitions.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/fieldZones.ts`
  for bounded guidance or attraction semantics that stay inside the current
  Rapier world.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/createRampDevices.ts`
  for ramp and gate construction.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  so ramp and gate transitions emit semantic events.
- Extend the split Flunk-Out Frenzy physics spec surface under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.*.spec.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
  with path-transition coverage.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify a local run can enter and exit the authored ramp path consistently
- verify gate behavior is one-way where intended and does not trap the ball

## Rollback plan

- Remove the ramp, gate, and field-zone table definitions.
- Drop the new physics helper modules.
- Restore the flatter prototype table pathing if ramp behavior is not yet
  stable enough.
