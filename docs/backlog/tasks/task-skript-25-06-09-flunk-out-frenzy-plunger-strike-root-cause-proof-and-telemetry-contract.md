---
type: task
id: TASK-SKRIPT-25-06-09
title: 'Flunk-Out Frenzy: plunger-strike root-cause proof and telemetry contract'
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
story: ST-SKRIPT-25-06
task_kind: story
acceptance_criteria:
- Given live evidence remains authoritative, when this task is complete, then launcher
  root-cause claims are backed by deterministic red tests plus retained telemetry
  artifacts, not by implementation guesses.
- Given production geometry/runtime behavior is frozen in this lane, when this task
  is complete, then no donor path/topology edits are made and no launch-behavior tuning
  is merged under this PR.
- Given architect seam invariants are hard requirements, when this task is complete,
  then strict seam continuity `xy<=1/z<=1`, no helper rails/freehand seam geometry,
  terminal-route-only handoff semantics, and real `sw16` exit semantics remain unchanged.
- Given user-reported inert launch is unresolved, when this task is complete, then
  at least one deterministic red test fails on current code and encodes the observed
  failure signature.
- Given observability is currently insufficient, when this task is complete, then
  launcher telemetry contract fields are explicit, typed, and captured in a retained
  artifact for each launch matrix case.
- Given governance requires review before implementation, when this task is complete,
  then independent reviewer approval is recorded before any production geometry/runtime
  behavior fixes begin.
dependencies:
- TASK-SKRIPT-25-06-03
- TASK-SKRIPT-25-06-07
- TASK-SKRIPT-25-06-08
- ST-SKRIPT-25-06
---

## Context

### Source: Problem

Live verification shows input and plunger motion updates are visible in runtime state, but the ball can remain inert after release. Current green tests do not reliably expose that live failure signature.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Story Contract Slice

The source does not provide a separate contract slice.

## Contract Inputs

The source does not record separate contract inputs.

## Plan

### Source: Implementation plan (proof lane only)

1. Add deterministic red test coverage for launch-effect contract:
   - target surface:
     - `src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
     - `src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
   - fixed deterministic test parameters:
     - simulation step: `dtMs = 16`
     - pre-release stability window: `10` steps
     - release-observation window: `60` steps
     - hold profiles:
       - short: `holdMs = 128`, `holdSteps = 8`
       - medium: `holdMs = 416`, `holdSteps = 26`
       - full: `holdMs = 896`, `holdSteps = 56`
       - relaunch gap: `relaunchGapMs = 256`, `relaunchGapSteps = 16`
   - required red/green launch-effect assertions:
     - from fixed pre-release baseline, each release case asserts both:
       - `ballDisplacementPx >= thresholdPx`
       - `minVy <= thresholdVy`
     - thresholds:
       - short: `thresholdPx = 2`, `thresholdVy = -8`
       - medium: `thresholdPx = 4`, `thresholdVy = -20`
       - full: `thresholdPx = 8`, `thresholdVy = -40`
       - relaunch second release: same as medium
   - required failing signature on current baseline:
     - at least one full-hold case fails with:
       - `ballDisplacementPx < 8` and/or `minVy > -40`
     - failure output must include per-case telemetry snapshot (`plunger`, `ball`, `route_capture`, `contact`)
   - include matrix cases at minimum:
     - rest
     - short hold
     - medium hold
     - full hold
     - relaunch

2. Add launcher telemetry contract (non-behavioral observability):
   - target surface:
     - `src/components/apps/flunk-out-frenzy/game/core/runtimeTypes.ts`
     - `src/components/apps/flunk-out-frenzy/game/core/GameRuntime.ts`
     - `src/components/apps/flunk-out-frenzy/GameHost.vue` (`__FOF_DEBUG__` extension)
   - required telemetry fields:
     - `input`: launch pressed state and last transition time
     - `plunger`: current Y, target Y, charge ratio, phase
     - `ball`: owner (`launcher_chain|main_world`), position, velocity
     - `route`: pending release ratio, active route tag, capture-window remaining
     - `route_capture`: last decision (`accepted|rejected`) and reject reason (`distance_xy|distance_z|vy_gate|window_expired|no_route`)
     - `sensors`: feed/exit inside flags and last `sw16` transition timestamp
     - `contact`:
       - `plungerBallContactActive` (boolean)
       - `contactEnteredThisStep` (boolean)
       - `contactExitedThisStep` (boolean)
       - `separationPx` (signed; negative indicates overlap)
       - `overlapPx` (max with `0`)
       - `relativeVyAtContact`
       - `lastContactAtStep`
       - `impulseTransferMarker` (normalized readonly scalar in `[0,1]`)
   - telemetry output must remain read-only and must not modify simulation behavior.
   - deterministic strike-evidence rule (no manual interpretation):
     - `strikeEvidencePresent = (maxOverlapPx >= 0.5) OR (relativeVyAtContact <= -5) OR (impulseTransferMarker >= 0.1)`
     - `maxOverlapPx` is computed across the release-observation window for the active case
     - `relativeVyAtContact` uses the most-negative observed contact sample in the window
   - deterministic strike classification:
     - `no_effective_strike` when `strikeEvidencePresent = false`
     - `post_strike_route_rejection` when `strikeEvidencePresent = true` and route decision is `rejected`
     - `strike_and_route_accepted` when `strikeEvidencePresent = true` and route decision is `accepted`

3. Add deterministic artifact contract for live matrix:
   - artifact path:
     - `.artifacts/flunk-out-frenzy-launcher-root-cause-proof/launch-root-cause-matrix.json`
   - each case record must include:
     - fixed case id
     - input mode
     - hold profile
     - `dt_ms`
     - `hold_ms`
     - `hold_steps`
     - `relaunch_gap_ms`
     - `relaunch_gap_steps`
     - `observation_steps`
     - plunger delta
     - ball displacement magnitude
     - max/min `vy`
     - route capture decision + reason
     - `sw16` exit observed (boolean)
     - contact diagnostics (`contactActive`, `maxOverlapPx`, `lastContactAtStep`, `impulseTransferMarker`)
     - `strike_classification` (`no_effective_strike|post_strike_route_rejection|strike_and_route_accepted`)
   - forbidden artifact fields:
     - no `gate-passed` property in this artifact schema
   - required schema assertion in focused specs:
     - artifact parser/spec must hard-fail if `gate-passed` appears in case payloads

4. Keep implementation blocked:
   - geometry/runtime behavior fixes start only after:
     - red baseline is proven
     - telemetry artifacts are retained
     - independent reviewer approves this proof lane

## Implementation Steps

### Source: Reviewer checklist (required before fix implementation)

- Red test reproduces the live inert-launch signature without manual interpretation.
- Telemetry contract is explicit, typed, and sufficient to explain route-capture decisions.
- No topology/geometry/seam-relaxation edits are included in this proof lane.
- Artifact schema is deterministic and fully reproducible.

## Proof

### Source: Current observed failure signature (authoritative baseline)

- Input path responds (`launchActive` toggles true/false).
- Plunger position updates during hold/release.
- Ball position can stay unchanged across full-hold release window in live route checks.
- Therefore, root cause is still unresolved at the plunger-strike/route-entry seam.

### Source: Implementation plan (proof lane only)

1. Add deterministic red test coverage for launch-effect contract:
   - target surface:
     - `src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
     - `src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
   - fixed deterministic test parameters:
     - simulation step: `dtMs = 16`
     - pre-release stability window: `10` steps
     - release-observation window: `60` steps
     - hold profiles:
       - short: `holdMs = 128`, `holdSteps = 8`
       - medium: `holdMs = 416`, `holdSteps = 26`
       - full: `holdMs = 896`, `holdSteps = 56`
       - relaunch gap: `relaunchGapMs = 256`, `relaunchGapSteps = 16`
   - required red/green launch-effect assertions:
     - from fixed pre-release baseline, each release case asserts both:
       - `ballDisplacementPx >= thresholdPx`
       - `minVy <= thresholdVy`
     - thresholds:
       - short: `thresholdPx = 2`, `thresholdVy = -8`
       - medium: `thresholdPx = 4`, `thresholdVy = -20`
       - full: `thresholdPx = 8`, `thresholdVy = -40`
       - relaunch second release: same as medium
   - required failing signature on current baseline:
     - at least one full-hold case fails with:
       - `ballDisplacementPx < 8` and/or `minVy > -40`
     - failure output must include per-case telemetry snapshot (`plunger`, `ball`, `route_capture`, `contact`)
   - include matrix cases at minimum:
     - rest
     - short hold
     - medium hold
     - full hold
     - relaunch

2. Add launcher telemetry contract (non-behavioral observability):
   - target surface:
     - `src/components/apps/flunk-out-frenzy/game/core/runtimeTypes.ts`
     - `src/components/apps/flunk-out-frenzy/game/core/GameRuntime.ts`
     - `src/components/apps/flunk-out-frenzy/GameHost.vue` (`__FOF_DEBUG__` extension)
   - required telemetry fields:
     - `input`: launch pressed state and last transition time
     - `plunger`: current Y, target Y, charge ratio, phase
     - `ball`: owner (`launcher_chain|main_world`), position, velocity
     - `route`: pending release ratio, active route tag, capture-window remaining
     - `route_capture`: last decision (`accepted|rejected`) and reject reason (`distance_xy|distance_z|vy_gate|window_expired|no_route`)
     - `sensors`: feed/exit inside flags and last `sw16` transition timestamp
     - `contact`:
       - `plungerBallContactActive` (boolean)
       - `contactEnteredThisStep` (boolean)
       - `contactExitedThisStep` (boolean)
       - `separationPx` (signed; negative indicates overlap)
       - `overlapPx` (max with `0`)
       - `relativeVyAtContact`
       - `lastContactAtStep`
       - `impulseTransferMarker` (normalized readonly scalar in `[0,1]`)
   - telemetry output must remain read-only and must not modify simulation behavior.
   - deterministic strike-evidence rule (no manual interpretation):
     - `strikeEvidencePresent = (maxOverlapPx >= 0.5) OR (relativeVyAtContact <= -5) OR (impulseTransferMarker >= 0.1)`
     - `maxOverlapPx` is computed across the release-observation window for the active case
     - `relativeVyAtContact` uses the most-negative observed contact sample in the window
   - deterministic strike classification:
     - `no_effective_strike` when `strikeEvidencePresent = false`
     - `post_strike_route_rejection` when `strikeEvidencePresent = true` and route decision is `rejected`
     - `strike_and_route_accepted` when `strikeEvidencePresent = true` and route decision is `accepted`

3. Add deterministic artifact contract for live matrix:
   - artifact path:
     - `.artifacts/flunk-out-frenzy-launcher-root-cause-proof/launch-root-cause-matrix.json`
   - each case record must include:
     - fixed case id
     - input mode
     - hold profile
     - `dt_ms`
     - `hold_ms`
     - `hold_steps`
     - `relaunch_gap_ms`
     - `relaunch_gap_steps`
     - `observation_steps`
     - plunger delta
     - ball displacement magnitude
     - max/min `vy`
     - route capture decision + reason
     - `sw16` exit observed (boolean)
     - contact diagnostics (`contactActive`, `maxOverlapPx`, `lastContactAtStep`, `impulseTransferMarker`)
     - `strike_classification` (`no_effective_strike|post_strike_route_rejection|strike_and_route_accepted`)
   - forbidden artifact fields:
     - no `gate-passed` property in this artifact schema
   - required schema assertion in focused specs:
     - artifact parser/spec must hard-fail if `gate-passed` appears in case payloads

4. Keep implementation blocked:
   - geometry/runtime behavior fixes start only after:
     - red baseline is proven
     - telemetry artifacts are retained
     - independent reviewer approves this proof lane

### Source: Test plan

- Focused proof commands:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
  - `pdm run docs-validate`
- Expected profile for this task:
  - at least one new launch-effect test is red on current baseline
  - telemetry contract tests are green (schema/presence)
  - seam invariants remain green in existing focused specs

### Source: Reviewer checklist (required before fix implementation)

- Red test reproduces the live inert-launch signature without manual interpretation.
- Telemetry contract is explicit, typed, and sufficient to explain route-capture decisions.
- No topology/geometry/seam-relaxation edits are included in this proof lane.
- Artifact schema is deterministic and fully reproducible.

## Validation

### Source: Reviewer checklist (required before fix implementation)

- Red test reproduces the live inert-launch signature without manual interpretation.
- Telemetry contract is explicit, typed, and sufficient to explain route-capture decisions.
- No topology/geometry/seam-relaxation edits are included in this proof lane.
- Artifact schema is deterministic and fully reproducible.

## Stop Conditions

### Source: Scope lock

- This task is proof-first only:
  - define deterministic red tests for the inert-launch signature
  - define launcher telemetry contract and retained artifact format
  - retain existing seam and donor invariants unchanged
- Out of scope in this task:
  - no donor geometry edits (`prototypeAlphaVpwDonorMap.ts`, `prototypeAlphaTableSpec.ts`)
  - no seam-tolerance changes
  - no new helper rails/freehand join geometry
  - no runtime launch-behavior tuning as a “fix” before proof lane is approved

### Source: Non-negotiable stop conditions

Do not start production geometry/runtime behavior fixes if any remain true:

- no deterministic red launch-effect test exists
- telemetry contract lacks route-capture reject reason visibility
- artifacts cannot explain why a release did not become launch movement
- proof lane lacks independent reviewer approval

## Lessons Learned

### Source: Current observed failure signature (authoritative baseline)

- Input path responds (`launchActive` toggles true/false).
- Plunger position updates during hold/release.
- Ball position can stay unchanged across full-hold release window in live route checks.
- Therefore, root cause is still unresolved at the plunger-strike/route-entry seam.

## Notes

### Source: Root-cause hypotheses to prove/disprove

1. Plunger-body strike is not producing effective ball impulse in live flow.
2. Route-entry gates are not being satisfied after release despite charge and plunger motion.
3. Existing tests pass because they do not assert the same live launch-effect signature and do not expose route-capture rejection reasons.

### Source: Implementation plan (proof lane only)

1. Add deterministic red test coverage for launch-effect contract:
   - target surface:
     - `src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
     - `src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
   - fixed deterministic test parameters:
     - simulation step: `dtMs = 16`
     - pre-release stability window: `10` steps
     - release-observation window: `60` steps
     - hold profiles:
       - short: `holdMs = 128`, `holdSteps = 8`
       - medium: `holdMs = 416`, `holdSteps = 26`
       - full: `holdMs = 896`, `holdSteps = 56`
       - relaunch gap: `relaunchGapMs = 256`, `relaunchGapSteps = 16`
   - required red/green launch-effect assertions:
     - from fixed pre-release baseline, each release case asserts both:
       - `ballDisplacementPx >= thresholdPx`
       - `minVy <= thresholdVy`
     - thresholds:
       - short: `thresholdPx = 2`, `thresholdVy = -8`
       - medium: `thresholdPx = 4`, `thresholdVy = -20`
       - full: `thresholdPx = 8`, `thresholdVy = -40`
       - relaunch second release: same as medium
   - required failing signature on current baseline:
     - at least one full-hold case fails with:
       - `ballDisplacementPx < 8` and/or `minVy > -40`
     - failure output must include per-case telemetry snapshot (`plunger`, `ball`, `route_capture`, `contact`)
   - include matrix cases at minimum:
     - rest
     - short hold
     - medium hold
     - full hold
     - relaunch

2. Add launcher telemetry contract (non-behavioral observability):
   - target surface:
     - `src/components/apps/flunk-out-frenzy/game/core/runtimeTypes.ts`
     - `src/components/apps/flunk-out-frenzy/game/core/GameRuntime.ts`
     - `src/components/apps/flunk-out-frenzy/GameHost.vue` (`__FOF_DEBUG__` extension)
   - required telemetry fields:
     - `input`: launch pressed state and last transition time
     - `plunger`: current Y, target Y, charge ratio, phase
     - `ball`: owner (`launcher_chain|main_world`), position, velocity
     - `route`: pending release ratio, active route tag, capture-window remaining
     - `route_capture`: last decision (`accepted|rejected`) and reject reason (`distance_xy|distance_z|vy_gate|window_expired|no_route`)
     - `sensors`: feed/exit inside flags and last `sw16` transition timestamp
     - `contact`:
       - `plungerBallContactActive` (boolean)
       - `contactEnteredThisStep` (boolean)
       - `contactExitedThisStep` (boolean)
       - `separationPx` (signed; negative indicates overlap)
       - `overlapPx` (max with `0`)
       - `relativeVyAtContact`
       - `lastContactAtStep`
       - `impulseTransferMarker` (normalized readonly scalar in `[0,1]`)
   - telemetry output must remain read-only and must not modify simulation behavior.
   - deterministic strike-evidence rule (no manual interpretation):
     - `strikeEvidencePresent = (maxOverlapPx >= 0.5) OR (relativeVyAtContact <= -5) OR (impulseTransferMarker >= 0.1)`
     - `maxOverlapPx` is computed across the release-observation window for the active case
     - `relativeVyAtContact` uses the most-negative observed contact sample in the window
   - deterministic strike classification:
     - `no_effective_strike` when `strikeEvidencePresent = false`
     - `post_strike_route_rejection` when `strikeEvidencePresent = true` and route decision is `rejected`
     - `strike_and_route_accepted` when `strikeEvidencePresent = true` and route decision is `accepted`

3. Add deterministic artifact contract for live matrix:
   - artifact path:
     - `.artifacts/flunk-out-frenzy-launcher-root-cause-proof/launch-root-cause-matrix.json`
   - each case record must include:
     - fixed case id
     - input mode
     - hold profile
     - `dt_ms`
     - `hold_ms`
     - `hold_steps`
     - `relaunch_gap_ms`
     - `relaunch_gap_steps`
     - `observation_steps`
     - plunger delta
     - ball displacement magnitude
     - max/min `vy`
     - route capture decision + reason
     - `sw16` exit observed (boolean)
     - contact diagnostics (`contactActive`, `maxOverlapPx`, `lastContactAtStep`, `impulseTransferMarker`)
     - `strike_classification` (`no_effective_strike|post_strike_route_rejection|strike_and_route_accepted`)
   - forbidden artifact fields:
     - no `gate-passed` property in this artifact schema
   - required schema assertion in focused specs:
     - artifact parser/spec must hard-fail if `gate-passed` appears in case payloads

4. Keep implementation blocked:
   - geometry/runtime behavior fixes start only after:
     - red baseline is proven
     - telemetry artifacts are retained
     - independent reviewer approves this proof lane

## Plan Document Review

The source does not include a plan document review record.

## Implementation Review

The source does not include an implementation review record.
