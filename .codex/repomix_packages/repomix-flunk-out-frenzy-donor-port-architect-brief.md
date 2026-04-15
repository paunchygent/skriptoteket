# Flunk-Out Frenzy Donor Port Architect Brief

## Purpose

Provide an architecture-level review package for the final donor-faithful port of the VPW reference board into the Flunk-Out Frenzy runtime, with focus on launcher-to-playfield continuity, seam correctness, and behavior fidelity under repeated launch/collision cycles.

## Snapshot

- Date: 2026-04-03
- Last milestone commit referenced by team: `319735cb` (on `main`)
- Scope focus: right-side launcher corridor, swplunger/sw16 semantics, 3D launcher-chain route handoff, donor wall/rail provenance
- Confidence state: integration plumbing is strong; behavioral fidelity in narrow seam transitions is not fully closed

## Current Implementation Status (careful summary)

1. Donor topology and provenance are explicit in authored map/spec contracts.
2. Launcher contract semantics are richer than earlier slices:
   - explicit `donor-corridor` lane regions
   - explicit trigger shape variants (`rect`, `capsule`, `donor-wire-rollover`)
   - explicit 3D launcher walls/sensors/guide rails/travel routes
3. Runtime includes dedicated 3D launcher-chain handling:
   - separate Rapier 3D world for launcher/plunger/handoff seam
   - route-based release handoff into board simulation
   - explicit gate/event emission along launch exit seam
4. Compiler/runtime/test seams now carry donor-aware semantics instead of simplified fallback geometry.

## What is Working (as currently evidenced)

1. Donor map/spec alignment for launcher/right-side artifacts is explicit in:
   - `prototypeAlphaVpwDonorMap.ts`
   - `prototypeAlphaVpwDonorDevices.ts`
   - `prototypeAlphaTableSpec.ts`
2. Compile contracts enforce launcher lane + 3D launcher completeness in:
   - `compilePinballTable.ts`
   - `compilePinballTable.spec.ts`
3. Runtime has dedicated launcher-chain integration and event wiring in:
   - `launcherChain3d.ts`
   - `PhysicsWorld.ts`
   - `plungerLaneState.ts`
4. Team-reported targeted regression suite is green for this slice:
   - `pdm run fe-lint`
   - `pdm run fe-type-check`
   - `pdm run fe-build`
   - `pdm run docs-validate`
   - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`

## Open Gaps / Residual Risk

1. Full donor-fidelity launch behavior is not fully behaviorally proven yet.
2. Narrow right-side corridor seam remains high-risk for small geometry/join mismatches.
3. Elevated rail intent is represented but multi-height traversal and transition continuity are not yet fully stabilized under repeated live interactions.
4. Some architecture is present and test-covered, but realistic launch timing + repeated collision edge cases remain only partially validated.

## Why the Remaining Work is Critical

- Schema-correct geometry can still be trajectory-wrong at seam scale.
- Small px-level angle/gap mismatches can produce:
  - false rebounds
  - incorrect corridor loops
  - premature/late trigger firings
  - non-donor blocker behavior in upper-right handoff region

## Completion Estimate (current team assessment)

- Donor topology representation for targeted shooter/right flow: ~80%
- Donor-accurate live behavior verification: ~40-50%
- Remaining acceptance distance: seam closure + deterministic launcher-to-left-playfield trajectory verification

## Desired End State (architect target)

1. Fully donor-faithful board/resource port for launcher/right-side path and connecting flow.
2. Deterministic launch progression from rest through corridor into gameplay without seam lock loops.
3. Donor trigger semantics preserved:
   - `swplunger` = launch anchor/feed band
   - `sw16` = launch-lane exit semantic source
   - right-return gate geometry/angle preserved where applicable
4. Transition surfaces/walls/rails represented without hidden flattening fallbacks.
5. Behavioral acceptance proven with repeatable launch-cycle examples across variable hold/release timing.

## Architect Guidance Requested

1. Confirm whether current launcher-chain + 2D world handoff design is sufficient for full donor fidelity, or should move to a unified multi-height collision representation.
2. Propose the canonical seam modeling strategy for corridor joints:
   - edge continuity requirements
   - tolerance strategy
   - accepted decomposition rules for non-convex donor regions
3. Recommend acceptance criteria for "faithful enough to ship" vs "still heuristic."
4. Prioritize next implementation sequence to close remaining behavioral uncertainty fastest with minimal regression risk.

## Verification Expectations for Next Slice

1. Static contract checks:
   - donor-backed wall/wire/route nodes remain provenance-explicit
   - no fallback flattening of launcher handoff semantics
2. Runtime checks:
   - at least 10 launch cycles with varied hold/release timing
   - collect examples for rest, short tap, medium hold, full charge, repeated relaunch
3. Seam geometry checks:
   - no wedge lock at corridor mouth
   - continuous wall joins through handoff
   - path stays in intended lane arc until exit
4. Event checks:
   - no stationary/rest false-positive launch-exit events
   - sw16/swplunger semantic separation remains intact

## Package Note

This package intentionally includes code, tests, donor assets, and planning docs so an external architect can evaluate both representation and behavior risk, then prescribe the final donor-faithful closure plan.
