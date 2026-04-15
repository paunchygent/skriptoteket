# Flunk-Out Frenzy Physical Rail Architect Context

## Why you are receiving this packet

We are preparing the next launcher architecture slice after `PR-0215` exposed
that removing runtime shortcut energy materially changes live launcher timing
and peak speed.

This note is intentionally compact. Its job is to orient you to the exact
problem, the strongest evidence, and the proposed design hypotheses you should
validate, modify, or reject.

## Current verified state

1. The proof surface is now truthful and operational through `PR-0213` and
   `PR-0214`.
2. `PR-0215` removed key runtime shortcuts:
   - no charge-derived route-speed promotion
   - no old route-speed floor
   - non-zero chained seam velocity preserved
3. Focused tests are green, but the canonical live launcher trace gate is
   blocked on real drift against the pinned baseline.

## Current blocked live evidence

From `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`:

- run verdict: `blocked`
- blocked cases:
  - `K-MEDIUM-STEADY`
  - `K-FULL-STEADY`
  - `K-RELAUNCH-MEDIUM`
- blocking flags:
  - `first_board_collision_step_drift`
  - `handoff_to_board_step_drift`
  - `peak_speed_drift`

Current observed values:

- `K-MEDIUM-STEADY`
  - handoff: `668`
  - collision: `669`
  - peak drift: `50.0%`
- `K-FULL-STEADY`
  - handoff: `704`
  - collision: `705`
  - peak drift: `58.6%`
- `K-RELAUNCH-MEDIUM`
  - handoff: `668`
  - collision: `669`
  - peak drift: `50.0%`

The route still completes the expected phase chain. What changed is timing and
energy, which strongly suggests the previous green behavior was materially
shaped by transport shortcuts.

## Current architectural facts

1. The current overhead donor wireform is still render-only in
   `specPlayfieldGeometry.ts` (`physics: false`).
2. `LauncherWorldGeometry.ts` builds the launcher seam world from:
   - floor
   - walls
   - guide rails
   It does not create physical overhead carrier geometry from `travelRoutes`.
3. `LauncherTravelRoute.ts` still advances the ball with direct:
   - `setTranslation(...)`
   - `setLinvel(...)`
4. `travelRoutes` therefore still mix two roles:
   - proof/phase semantics
   - de facto transport rails

## Candidate recommendations from the first architect pass

Please treat each of these as something to evaluate, not as accepted truth.

1. Do **not** physicalize the current `travelRoutes`.
   They should become observation/proof spines only.

2. Introduce new explicit carrier semantics:
   - `wireformCarrier3D`
   - `wireformGuard3D`
   - `carrierReceiver3D`
   - `carrierSeamBridge3D`
   - `carrierObservationSpine3D`

3. Turn the current overhead donor wireforms into real colliders:
   - `RampS3`
   - `RampS001`
   - `RampS002`
   - `RampS4`

4. Permit only terminal `handoffVelocity` as a production mechanics heuristic.

5. Forbid route-start snaps, per-step transport writes, speed floors, and any
   seam correction that can add energy.

6. Keep the separate launcher Rapier 3D seam only if it owns the full elevated
   route through one late board handoff. Otherwise redesign the boundary.

## What we need from you

Please provide:

1. `accept` / `modify` / `reject` guidance for each candidate recommendation
2. your preferred authored/compiler/runtime split
3. any Rapier-specific caveats we must treat as blockers up front
4. a staged implementation strategy that preserves the strict `PR-0214` truth
   gate rather than weakening it
