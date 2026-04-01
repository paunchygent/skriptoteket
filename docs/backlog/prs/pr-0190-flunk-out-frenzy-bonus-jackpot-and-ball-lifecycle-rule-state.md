---
type: pr
id: PR-0190
title: "Flunk-Out Frenzy: bonus, jackpot, and ball-lifecycle rule state"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "rules", "hud"]
dependencies:
  - "PR-0189"
acceptance_criteria:
  - "The rule engine no longer keeps all scoring and progression logic in one file; score, bonus or jackpot, and ball-lifecycle state are split into small focused modules."
  - "Bonus, jackpot, multiplier, and shoot-again or ball-save state are derived from semantic machine events instead of from Rapier-facing conditionals."
  - "The runtime and HUD contracts can expose richer rule state without giving Vue ownership of simulation data."
---

## Problem

The current `RuleEngine.ts` is intentionally tiny, but it only supports bumper,
sling, rollover, and drain scoring. If we keep layering richer scoring on top
of that shape, we will recreate a TypeScript version of the monolithic donor
controller that we explicitly do not want.

## Goal

Refactor the rule layer into a reusable foundation for:

- bonus and jackpot accumulation
- ball-save or shoot-again lifecycle
- richer multiplier and bank-completion handling

## Non-goals

- No capture-device physics yet.
- No ramp-specific semantics yet.
- No backend score submission or replay logic.

## Implementation plan

- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/ruleTypes.ts`
  for typed rule-state contracts and step-result boundaries.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/scoreState.ts`
  for point-award helpers and multiplier application.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/bonusJackpotState.ts`
  for bonus, jackpot, and award-arm state.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/ballLifecycleState.ts`
  for drain settlement, respawn decisions, and shoot-again handling.
- Slim
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.ts`
  into an orchestrator over the new helpers.
- Extend
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/runtimeTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/runtimeEngineTypes.ts`
  so read-only runtime state can carry bonus, jackpot, and shoot-again signals.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/presentation/gameEffectTypes.ts`
  so those state changes can surface as semantic effects.
- Add focused tests beside the new rule modules plus updated coverage in
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.spec.ts`.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/rules/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify a local run can visibly accumulate and settle bonus or jackpot state
  without corrupting the existing 3-ball game loop

## Rollback plan

- Collapse the new rule helper modules back into `RuleEngine.ts`.
- Remove HUD-facing bonus or jackpot fields if the shell cannot yet render them
  safely.
- Restore the previous score and multiplier-only rule snapshot.
