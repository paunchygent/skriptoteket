---
type: pr
id: PR-0195
title: "Flunk-Out Frenzy: objective controllers and bank progression"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "rules", "progression"]
dependencies:
  - "PR-0194"
acceptance_criteria:
  - "The rule layer keeps a slim orchestration surface while target banks, skill-shot logic, and objective progression live in dedicated controller modules."
  - "Bank completion, jackpot progression, and objective state changes are driven by semantic machine events and surfaced as deliberate game effects."
  - "The resulting local runtime remains compatible with future replay, ruleset, and official-score work instead of hardcoding one opaque local-only flow."
---

## Problem

By the time richer devices, bonus or jackpot state, and ramp semantics exist,
the remaining risk is orchestration. If all progression logic ends up back in
`RuleEngine.ts`, the earlier decomposition work will only postpone the monolith
rather than prevent it.

## Goal

Finish the mechanics-port foundation with bounded rule controllers for:

- target-bank completion
- skill-shot progression
- objective or mission-style local progression

## Non-goals

- No backend leaderboard or replay work.
- No multiball rewrite unless it fits naturally inside the controller seams.
- No attempt to recreate every donor mode one-for-one.

## Implementation plan

- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/controllers/skillShotController.ts`
  for launch-lane and early-ball progression.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/controllers/targetBankController.ts`
  for bank-completion and reset logic.
- Create
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/controllers/objectiveController.ts`
  for higher-level local progression that composes bank, ramp, and capture
  events.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/ruleTypes.ts`
  and
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.ts`
  so the engine orchestrates controller outputs instead of owning every rule
  branch directly.
- Update
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.ts`,
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/presentation/gameEffectTypes.ts`,
  and any read-only runtime state contracts that need to surface controller
  outcomes to the HUD or effects layer.
- Add focused controller specs plus updated end-to-end engine coverage.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/rules/**/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify bank-completion and objective state can be advanced and reset across a
  full local run
- verify game-over and restart still clear progression state correctly

## Rollback plan

- Remove the new controller modules and fold only the minimum stable rule logic
  back into `RuleEngine.ts`.
- Remove any half-complete objective-specific HUD or effect hooks.
- Keep the underlying event and device work from earlier PRs intact if it is
  already stable.
