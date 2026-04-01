---
type: pr
id: PR-0193
title: "Flunk-Out Frenzy: capture, eject, and save devices"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "physics", "rules"]
dependencies:
  - "PR-0192"
acceptance_criteria:
  - "Typed table definitions exist for capture-style devices such as kickout, hole, sink, or kickback, and the physics layer can build them from authored data."
  - "The physics boundary can represent capture, hold, eject, and save behavior through semantic machine events instead of leaking Rapier constraints or timers."
  - "The rules layer can react to those events with bounded lifecycle and award logic without collapsing back into one large controller."
---

## Problem

Targets and lanes create better progression, but real pinball-style gameplay
opens up when the ball can be captured, held, saved, and ejected. Those
behaviors also create the most obvious bridge from simple score accumulation to
jackpot and objective-driven rules.

## Goal

Add the first capture-style device family:

- kickout or scoop-style capture
- sink or hole-style hold and release
- kickback or save behavior

## Non-goals

- No ramps or field zones yet.
- No full mission tree yet.
- No backend persistence or score submission work.

## Implementation plan

- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTable.ts`
  with typed definitions for kickout, hole, sink, and kickback devices.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/createCaptureDevices.ts`
  for capture, hold, eject, and save device construction.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  to emit semantic capture and eject events.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/captureAwardsState.ts`
  or equivalent bounded helper if the rules layer needs a dedicated module for
  capture-driven awards and save handling.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.ts`,
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.ts`,
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/presentation/gameEffectTypes.ts`
  so the new device events can drive rule state and presentation effects.
- Extend focused specs in the physics, rules, and engine folders.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/*.spec.ts src/components/apps/flunk-out-frenzy/game/rules/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify the ball can be captured and ejected without getting lost or duplicating
  the active-ball state
- verify kickback or save behavior can preserve a run without corrupting ball
  count

## Rollback plan

- Remove the authored capture devices from the prototype table.
- Drop the capture-device factory and rule helper module.
- Restore the simpler drain-only lifecycle if the new capture flow proves too
  unstable.
