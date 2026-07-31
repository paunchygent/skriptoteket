---
type: task
id: TASK-SKRIPT-25-06-02
title: 'Flunk-Out Frenzy: donor semantic representation and trigger-shape fidelity'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-25-06
task_kind: story
acceptance_criteria:
- Given VPW donor triggers, gates, and wire rollovers carry richer shape or phase
  semantics than the current schema, when this task is complete, then the authored
  and compiled table model represents those semantics directly instead of flattening
  them into local bounding boxes or undocumented remaps.
- Given the donor map must stay inspectable, when this task is complete, then donor-backed
  trigger and gate definitions in `prototypeAlphaVpwDonorDevices.ts` and `prototypeAlphaTableSpec.ts`
  cite the intended donor source objects explicitly.
- Given launcher lanes and other donor lane corridors are shaped semantic regions,
  when this task is complete, then every remaining `laneBounds` or AABB-style lane
  containment seam is replaced with donor-shaped lane-region semantics instead of
  approximate local bounds.
- Focused compile and physics regressions prove the donor right-return footprint keeps
  donor rotation, the launch-lane donor trigger maps to the intended shooter/plunger
  donor objects, and a served ball does not self-fire launch semantics while resting
  in the lane.
- The donor reference docs, pinball authoring skill, and `.codex/handoff.md` explicitly
  forbid semantic flattening or 'good enough' vibe-porting when a richer donor representation
  exists.
---

## Context

### Problem

`PR-0198` gets the board back onto donor-backed topology, but it does not close
the remaining donor-semantic gap. Richer donor objects such as rotated gates,
wire rollovers, and shooter/plunger triggers are still at risk of being forced
into simpler local sensor shapes just because the current schema is easier to
fit around rectangles and circles.

That is not donor fidelity. It is representation loss.

### Goal

Extend the authored and compiled pinball-table system so donor-backed trigger
and gate semantics can be represented honestly:

- richer sensor shapes where donor devices need them
- explicit trigger phase semantics where donor behavior depends on enter vs exit
- donor-source traceability for every donor-backed semantic device
- donor-shaped lane-region semantics for launcher containment, lane membership,
  recharge/feed logic, and lane exits

### Non-goals

- No broad board-topology redraw; `PR-0198` owns the donor geometry cutover.
- No donor plunger-hardware or launcher wall-face release-model expansion;
  `PR-0200` owns that launcher/right-side representation gap.
- No VPX or ROM rule-code import.
- No `PR-0193` through `PR-0195` gameplay expansion in this task.
- No undocumented "temporary" flattening that quietly becomes the final model.

### Implementation plan

- Extend the authored/compiled table contracts to support richer donor-backed
  trigger shapes, for example `capsule`, donor wire-rollover equivalents, or
  another explicit representation that preserves the donor device semantics.
- Extend trigger semantics so donor-backed devices can declare the correct
  firing phase instead of assuming every sensor is a plain `enter` rectangle.
- Replace `laneBounds` and other coarse lane-containment shortcuts with
  donor-shaped lane-region semantics wherever the donor defines a real lane or
  launcher corridor footprint.
- Update the compiler and `PhysicsWorld.ts` so those richer donor-backed shapes
  compile into stable colliders and trigger behavior without losing donor
  provenance.
- Replace any flattened or remapped launch-lane semantics with direct
  donor-faithful mapping from the intended shooter/plunger donor objects.
- Preserve donor-measured rotation and footprint where the donor device is
  rotated, including the right-return path.
- Add focused regression coverage for compile output, donor-source provenance,
  and launcher-lane behavior.

### Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Manual/live:

- user-owned browser inspection of the launch lane and return-lane behavior once
  the deterministic proof is green

### Rollback plan

- Remove the richer donor-semantic shape contracts and restore the previous
  sensor union only if the new representation cannot be stabilized quickly.
- Keep `PR-0198` donor topology artifacts and provenance docs intact so the
  semantic follow-up can be resumed without rediscovery.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
