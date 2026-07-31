---
type: task
id: TASK-SKRIPT-25-05-05
title: 'Flunk-Out Frenzy: objective controllers and bank progression'
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
- The rule layer keeps a slim orchestration surface while target banks, skill-shot
  logic, and objective progression live in dedicated controller modules.
- Bank completion, jackpot progression, and objective state changes are driven by
  semantic machine events and surfaced as deliberate game effects.
- The resulting local runtime remains compatible with future replay, ruleset, and
  official-score work instead of hardcoding one opaque local-only flow.
---

## Context


By the time richer devices, bonus or jackpot state, and ramp semantics exist,
the remaining risk is orchestration. If all progression logic ends up back in
`RuleEngine.ts`, the earlier decomposition work will only postpone the monolith
rather than prevent it.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Story Contract Slice


Finish the mechanics-port foundation with bounded rule controllers for:

- target-bank completion
- skill-shot progression
- objective or mission-style local progression

## Contract Inputs

No separate contract inputs is stated in the source.

## Plan


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

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/rules/**/*.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- verify bank-completion and objective state can be advanced and reset across a
  full local run
- verify game-over and restart still clear progression state correctly

## Validation

No separate validation is stated in the source.

## Stop Conditions


- Remove the new controller modules and fold only the minimum stable rule logic
  back into `RuleEngine.ts`.
- Remove any half-complete objective-specific HUD or effect hooks.
- Keep the underlying event and device work from earlier PRs intact if it is
  already stable.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Non-goals


- No backend leaderboard or replay work.
- No multiball rewrite unless it fits naturally inside the controller seams.
- No attempt to recreate every donor mode one-for-one.

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Implementation Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
