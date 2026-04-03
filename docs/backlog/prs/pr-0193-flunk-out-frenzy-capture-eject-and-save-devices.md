---
type: pr
id: PR-0193
title: "Flunk-Out Frenzy: capture, eject, and save devices"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-02
stories:
  - "ST-25-05"
tags: ["frontend", "games", "physics", "rules"]
dependencies:
  - "PR-0192"
acceptance_criteria:
  - "Typed table and compiled-plan definitions exist for capture and save devices (kickout/hole/sink + kickback/save-post), and invalid authored data fails fast at compile time."
  - "The physics boundary represents capture, hold, eject, and save behavior through deterministic semantic machine events (`ball-captured`, `ball-ejected`, `ball-saved`) without leaking Rapier internals."
  - "Ball lifecycle invariants hold under capture and save flows: one active ball, no duplicate drains/ejects for the same contact window, and stable restart/game-over reset behavior."
  - "The rules layer reacts to capture/save events through bounded helper modules and keeps `RuleEngine.ts` as orchestration rather than a monolithic controller."
---

## Problem

Targets and lanes create better progression, but real pinball-style gameplay
opens up when the ball can be captured, held, saved, and ejected. Those
behaviors also create the most obvious bridge from simple score accumulation to
jackpot and objective-driven rules. Right now, semantic event contracts already
mention capture/eject/save, but the authored-table -> compiler -> physics
path is not fully checkpointed for deterministic behavior.

## Goal

Add the first capture-style device family:

- kickout or scoop-style capture
- sink or hole-style hold and release
- kickback or save behavior

## Non-goals

- No ramps or field zones yet.
- No full mission tree yet.
- No backend persistence or score submission work.

## Checkpoint model

This PR is executed as one task with three mandatory checkpoints:

- `PR-0193a` -> contract and compiler wiring
- `PR-0193b` -> physics lifecycle and machine-event emission
- `PR-0193c` -> rules/effects integration and reset correctness

No checkpoint is marked done unless its exit criteria and checkpoint-specific
tests pass.

## Implementation plan by checkpoint

### Checkpoint A (`PR-0193a`): contracts + compiler wiring

Scope:

- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  with typed capture/save device definitions.
- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/pinballTablePlanTypes.ts`
  so compiled collider semantics can represent capture/save triggers.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.ts`
  to compile capture/save device colliders and validate required authored
  fields (tags, hold/eject params, cooldown windows).
- Author at least one capture device and one save device in
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`.

Exit criteria:

- Invalid authored capture/save configuration fails at compile time.
- Compiled plan includes deterministic semantic tags for all capture/save
  sensors.

### Checkpoint B (`PR-0193b`): physics lifecycle + semantic machine events

Scope:

- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/colliderMeta.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/machineEventEmitter.ts`
  so contact translation stays pure and deterministic.
- Add bounded capture lifecycle state in physics (hold timer, eject trigger,
  per-device cooldown), implemented in dedicated helper module(s) under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/`.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  to emit `ball-captured`, `ball-ejected`, and `ball-saved` exactly once per
  eligible lifecycle transition.

Exit criteria:

- Capture -> hold -> eject flow is deterministic and repeatable.
- Save behavior does not duplicate or delete the active ball state.
- No Rapier internals leak into runtime/rules seams.

### Checkpoint C (`PR-0193c`): rules/effects integration + reset safety

Scope:

- Add bounded rule helper(s) for capture/save awards and lifecycle reactions
  under
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/`.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.ts`,
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.ts`,
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/presentation/gameEffectTypes.ts`
  to surface capture/eject/save outcomes through rule events and presentation
  effects.
- Ensure restart/game-over/start transitions reset capture/save state cleanly.

Exit criteria:

- Capture/save events drive bounded rule outcomes without re-monolithing
  `RuleEngine.ts`.
- Restart and next-ball transitions clear capture/save state reliably.

## Acceptance criteria mapping by checkpoint

- Checkpoint A covers acceptance criterion 1.
- Checkpoint B covers acceptance criteria 2 and 3.
- Checkpoint C covers acceptance criterion 4 and re-validates criteria 2 and 3
  through the full runtime path.

## Test plan

Automated:

- Checkpoint A:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/*.spec.ts`
- Checkpoint B:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/*.spec.ts`
- Checkpoint C:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/rules/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- Final integrated rerun:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/*.spec.ts src/components/apps/flunk-out-frenzy/game/rules/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- Verify capture -> hold -> eject works repeatedly for the authored capture
  device without losing the active ball.
- Verify save behavior can preserve a run without corrupting ball count.
- Verify restart after an in-progress capture flow does not leave stale hold or
  cooldown state.

## Rollback plan

- Roll back checkpoint C by removing capture/save rule helpers and effect wiring
  while keeping checkpoint A/B contracts intact.
- Roll back checkpoint B by disabling capture/save physics lifecycle handling
  and restoring drain-only semantics.
- Roll back checkpoint A by removing authored capture/save devices and compiler
  support if the device contracts prove too unstable in this sprint.
