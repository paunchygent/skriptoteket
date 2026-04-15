# Flunk-Out Frenzy Physical Rail Architect Brief

## Role

You are the lead architect performing an independent design analysis of the
Flunk-Out Frenzy launcher overhead corridor.

## Purpose

We need implementation advice and strategy for replacing the current
deterministic launcher travel transport with a truly physical overhead rail or
wireform, without relaxing assertions, weakening telemetry truth, or inventing
new hidden shortcuts.

This brief accompanies:

- planning scope:
  `docs/backlog/prs/pr-0216-flunk-out-frenzy-physical-rail-carrier-semantics-and-architect-guidance-packet.md`
- review package:
  `.agents/repomix_packages/repomix-flunk-out-frenzy-physical-rail-architect-guidance.xml`

## Current state summary

1. `PR-0212` audited the runtime shortcuts and proof-layer shortcuts around the
   launcher corridor.
2. `PR-0213` and `PR-0214` made the live/focused trace surface truthful and
   operational:
   - canonical live gate:
     `scripts/playwright_flunk_out_frenzy_launch_trace_parity_check.py`
   - canonical artifacts:
     `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
     `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.json`
     `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`
3. `PR-0215` has started removing shortcut energy:
   - no charge-derived route-speed promotion
   - no old route speed floor
   - non-zero route-direction seam velocity preserved
4. Focused proof is green, but the live `PR-0214` gate now blocks on real drift:
   - `first_board_collision_step_drift_blocked`
   - `handoff_to_board_step_drift_blocked`
   - `peak_speed_drift_blocked`
5. The route still completes, but the runtime is much slower than the pinned
   baseline. This indicates that transport shortcuts were materially shaping the
   previous behavior.

## How to use the first architect pass

This packet now includes one independent architect pre-analysis. Do not treat it
as authoritative. Treat it as a refined starting point.

Your task is to:

1. validate, modify, or reject the proposed recommendations
2. identify where they are incomplete or too optimistic
3. replace them with a better design if needed

The candidate recommendations are summarized in:

- `.agents/repomix_packages/repomix-flunk-out-frenzy-physical-rail-architect-context.md`

## Important current architectural facts

1. The current route is still path-driven in runtime:
   - `launcher/LauncherTravelRoute.ts` advances the ball with direct
     `setTranslation(...)` and `setLinvel(...)`
2. The donor overhead rails in `specPlayfieldGeometry.ts` are still
   `physics: false`
3. `LauncherWorldGeometry.ts` currently builds the launcher seam world from:
   - floor
   - walls
   - guide rails
   It does not compile physical overhead carrier geometry from `travelRoutes`
4. `travelRoutes` therefore still serve as both:
   - proof/phase semantics
   - de facto transport rails
5. The separate Rapier 3D launcher seam may itself be part of the constraint.

## Decision questions requiring your guidance

1. What should the new authored carrier model be?
   - support rail segments
   - guard/retention rails
   - seam funnels/receivers
   - other carrier primitives?

2. What may remain heuristic, if anything?
   - is terminal `handoffVelocity` still acceptable?
   - are bounded position-only seam corrections acceptable?
   - what should be forbidden outright?

3. What is the correct runtime responsibility split?
   - authored spec
   - compiler
   - geometry builder
   - runtime observation/classification
   - telemetry/proof

4. Which donor assets should become real colliders?
   - current `guideRails`
   - current render-only overhead wire rails
   - additional inferred carrier surfaces
   - none of the above without seam redesign?

5. Is the current Rapier seam architecture sufficient?
   - can the separate launcher 3D world support production-ready physical
     travel?
   - or does truthful rail travel require a deeper physics/world-boundary
     redesign?

6. How should we define production-ready success?
   - which invariants must stay strict
   - what live-trace drift remains acceptable if the runtime becomes more
     truthful
   - how should manual matrix behavior and trace evidence interact in the final
     gate

## Candidate recommendations to validate, modify, or reject

Please give an explicit judgment on each:

1. Do not physicalize the current `travelRoutes`; demote them to
   observation/proof spines only.
2. Add explicit carrier types instead of overloading `guideRails`:
   - `wireformCarrier3D`
   - `wireformGuard3D`
   - `carrierReceiver3D`
   - `carrierSeamBridge3D`
   - `carrierObservationSpine3D`
3. Convert the current overhead donor wireforms (`RampS3`, `RampS001`,
   `RampS002`, `RampS4`) into real colliders.
4. Keep only terminal `handoffVelocity` as a production mechanics heuristic.
5. Forbid all route-start snaps, per-step transport writes, speed floors, and
   hidden seam nudges in production.
6. Keep the separate launcher Rapier 3D seam only if it owns the entire
   elevated route through one late board handoff.

## Requested output

Please provide:

1. a recommended physical carrier model for this launcher corridor
2. a recommended authored/compiler/runtime split
3. a shortlist of acceptable versus forbidden heuristics
4. Rapier-specific implementation risks we must design around
5. a staged implementation strategy for the follow-on PR
6. verification guidance that keeps the `PR-0214` truth surface strict
7. an `accept` / `modify` / `reject` judgment for each candidate
   recommendation above

## High-value evidence paths

- `docs/backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md`
- `docs/backlog/prs/pr-0213-flunk-out-frenzy-live-trace-contract-parity-remediation.md`
- `docs/backlog/prs/pr-0214-flunk-out-frenzy-launch-trace-operational-summary-and-decision-gate.md`
- `docs/backlog/prs/pr-0215-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment.md`
- `docs/backlog/prs/pr-0216-flunk-out-frenzy-physical-rail-carrier-semantics-and-architect-guidance-packet.md`
- `.agents/repomix_packages/repomix-flunk-out-frenzy-physical-rail-architect-context.md`
- `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherWorldGeometry.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/spec/specLauncher.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/spec/specPlayfieldGeometry.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
