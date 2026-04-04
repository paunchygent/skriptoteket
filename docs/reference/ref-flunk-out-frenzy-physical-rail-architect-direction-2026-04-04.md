---
type: reference
id: REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04
title: "Reference: Flunk-Out Frenzy physical rail architect direction (2026-04-04)"
status: active
owners: "agents"
created: 2026-04-04
topic: "launcher-physics-architecture"
links:
  - EPIC-25
  - REV-EPIC-25
  - PR-0212
  - PR-0213
  - PR-0214
  - PR-0215
  - PR-0216
  - REF-curated-app-flunk-out-frenzy-architecture-and-foundational-code
---

## Purpose

This reference captures the lead architect's direction for replacing the
current **route-driven launcher transport** with a **physical carrier graph**
inside the launcher Rapier world while preserving the strict proof surface
introduced through [PR-0213](../backlog/prs/pr-0213-flunk-out-frenzy-live-trace-contract-parity-remediation.md)
and [PR-0214](../backlog/prs/pr-0214-flunk-out-frenzy-launch-trace-operational-summary-and-decision-gate.md).

It is the architectural source of truth for the physical-rail follow-on after:

- [PR-0212](../backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md)
  identified the shortcut classes and truth-gate breaches
- [PR-0215](../backlog/prs/pr-0215-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment.md)
  showed that removing shortcut energy materially changes live timing and peak
  speed
- [PR-0216](../backlog/prs/pr-0216-flunk-out-frenzy-physical-rail-carrier-semantics-and-architect-guidance-packet.md)
  prepared the design-and-review packet for the physical carrier model

This document complements, and does not replace,
[ref-curated-app-flunk-out-frenzy-architecture-and-foundational-code.md](./ref-curated-app-flunk-out-frenzy-architecture-and-foundational-code.md).

## Architectural direction

The recommended model is:

- replace the current route-driven transport with a **physical carrier graph**
  inside the launcher Rapier world
- keep a separate **observation-spine layer** for proof, phase naming, and
  progress measurement
- preserve **one explicit terminal board handoff seam**

The lower shooter corridor is already physically real in the launcher world.
The model stops being physical at route capture, where the accepted ball is
snapped to the route start and then advanced by repeated body writes in
`LauncherTravelRoute.ts`, while the overhead donor wireforms remain render-only
with `physics: false`.

Relevant code surfaces:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherWorldGeometry.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/spec/specLauncher.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/spec/specPlayfieldGeometry.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`

## 1. Recommended physical carrier model

Treat the overhead corridor as a **carrier graph**, not as a path.

Use five authored roles:

1. **Support carriers**
   These are the load-bearing fixed colliders that carry the ball through the
   elevated route.

2. **Guard / retention carriers**
   These prevent escape, suppress lateral fall-off, and stabilize travel
   through turns, crown changes, and descent.

3. **Receiver / funnel carriers**
   These own the hard seams: release capture, endpoint mouth, descent
   confinement, and the final pre-board receiver.

4. **Observation spines**
   These replace the current transport meaning of `travelRoutes`. They keep
   route tags, donor provenance, phase names, and progress measurement, but
   they never move the ball.

5. **One terminal handoff seam**
   This is the only mechanics seam that may still inject declared board-entry
   state via `handoffVelocity` / `handoffZ`.

Do **not** overload everything into `guideRails`. The current launcher 3D
schema only knows `walls`, `guideRails`, `sensors`, and optional `travelRoutes`,
which is too coarse for a truthful overhead carrier. The current `guideRails`
also cover only the lower shoulder / upper-guide region, not the full elevated
corridor.

Preferred data-model shape:

- one tagged `carriers[]` union with
  `kind: "support" | "guard" | "receiver" | "observation_spine" | "handoff_seam"`

This is preferred over wireform-specific naming because not every critical
element is literally a wireform. The receive mouth and seam funnels are
surfaces or volumes, not just rails.

## 2. Recommended authored / compiler / runtime split

### Authored spec

- Keep donor provenance explicit.
- Author physical carrier roles separately from proof roles.
- Keep charge ratio only as a legality / eligibility input for which
  observation spine is relevant.
- Preserve strict seam continuity checks, but apply them to the
  observation-spine graph and carrier graph anchors, not to a transport rail.

The current compiler rule enforcing `xy<=1` and `z<=1` continuity is valuable
and should survive in the next model.

### Compiler

- Compile donor-backed overhead sources `RampS3`, `RampS001`, `RampS002`, and
  `RampS4` into launcher-world carrier colliders.
- Validate graph continuity, ownership, receiver coverage, and one-late-handoff
  topology.
- Derive any additional support / guard / receiver surfaces as declared
  compiler output with donor provenance, not as opaque runtime invention.

### Geometry builder

`LauncherWorldGeometry.ts` should build support, guard, and receiver colliders
in the launcher world. It should remain geometry-only. No phase logic should be
added there.

### Runtime observation / classification

- Admit route occupancy from observed release/contact state plus spatial
  eligibility.
- Infer active phase from physical ball position relative to support / receiver
  occupancy and the nearest observation spine.
- Measure progress by projection onto the observation spine.
- Arm terminal handoff only when the ball physically enters the handoff
  receiver.

### Telemetry / proof

- Keep the existing phase vocabulary if possible:
  `route_overhead`, `route_endpoint_bridge`, `route_descent`,
  `handoff_to_board`, `board_drop_preimpact`, `board_drop_postimpact`
- Change the *cause*, not the naming.
- Add explicit counters for any seam correction or non-simulated intervention.
- Preserve the `PR-0213` / `PR-0214` rule: summary claims must remain
  raw-row-backed, never reconstructed.

## 3. Acceptable vs forbidden heuristics

### Acceptable

- Terminal `handoffVelocity` and `handoffZ`, declared as a bounded board-entry
  seam.
- Observation heuristics that do not move the ball:
  - nearest-spine progress
  - occupancy classification
  - route legality by charge band
- A temporary bring-up entry alignment correction only if all of these hold:
  - one-shot, not per-step
  - position-only
  - never increases velocity magnitude
  - emitted in telemetry
  - blocked from production acceptance until the counter is driven to `0`

This keeps the repo aligned with the terminal-only bounded-heuristic direction
set by [PR-0212](../backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md)
and [PR-0215](../backlog/prs/pr-0215-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment.md).

### Forbidden

- Route-start snap in production
- Any per-step transport write during carrier occupancy
- Speed floors
- Charge-derived speed fabrication
- Hidden seam nudges
- Any correction that can add energy
- Any proof-layer insertion of phases/events that were not directly observed

These remain the exact shortcut classes identified as breaches in
[PR-0212](../backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md).

## 4. Rapier-specific implementation risks

Rapier can support this design, but only if the implementation is built for its
contact model instead of treating it like a spline mover.

### CCD changes timing

Rapier's CCD uses motion-clamping to stop a fast body at first contact, which
can produce legitimate timing loss. A more truthful rail can therefore arrive
later than the shortcut baseline. The response must be to keep the gate strict
until the physical model is stabilized, not to hide the drift.

Reference:

- [Rapier CCD guide](https://rapier.rs/docs/user_guides/bevy_plugin/rigid_body_ccd)

### Scale matters

Rapier recommends setting `length_unit` to match world-units-per-meter, and its
internal tolerances scale with that choice. With pixel-like coordinates, this
is a stability concern, not optional tuning trivia.

Reference:

- [Rapier World API](https://rapier.rs/javascript3d/classes/World.html)

### Default solver budget is modest

Rapier's `IntegrationParameters` control timestep, solver iterations, and CCD
substeps. The defaults are a pragmatic game balance, not a guarantee that thin,
fast wireform travel will be stable enough for this lane.

Prefer targeted per-body additional solver iterations on the ball / critical
launcher contacts before globally inflating the whole simulation.

Reference:

- [Rapier simulation structures](https://rapier.rs/docs/user_guides/javascript/simulation_structures/)

### Do not model the carrier as a thin mesh shortcut

Rapier supports triangle meshes for fixed environment geometry, but meshes and
polylines are zero-thickness and bring internal-edge / ghost-collision risks.
For this lane, thick segment, capsule, or compound-collider assemblies are
safer than one "perfect" mesh rail.

Reference:

- [Rapier collider guide](https://rapier.rs/docs/user_guides/javascript/colliders/)

### Kinematic plunger motion should follow Rapier's interaction model

If plunger interaction is revisited during the refactor, use Rapier's kinematic
interaction model consciously. Rapier recommends
`setNextKinematicTranslation(...)` over direct `setTranslation(...)` for
position-based kinematic bodies so dynamic-body interaction gets a computed
kinematic velocity.

Reference:

- [Rapier RigidBody API](https://rapier.rs/javascript2d/classes/RigidBody.html)

### World ownership is the core architectural risk

The launcher currently runs in its own 3D Rapier world and hands the ball back
to the main world only at board handoff. That is viable only if every causal
elevated-route surface lives in that same launcher world. Mid-route cross-world
causality is not truthful.

## 5. Staged implementation strategy

1. **Freeze the current evidence surface.**
   Keep the current `PR-0214` raw artifact, machine summary, human summary, and
   manual matrix as the pre-change decision surface. The blocked result is
   useful truth, not noise.

2. **Add carrier semantics without deleting the proof layer.**
   Introduce support / guard / receiver / observation / handoff roles in the
   launcher 3D schema. Keep the current route tags alive as observation spines.

3. **Compile overhead donor geometry into launcher-world colliders.**
   Use `RampS3`, `RampS001`, `RampS002`, and `RampS4` as source geometry, but
   compile them into launcher-owned carriers. Do not simply flip the current
   top-level playfield rails to `physics: true`.

4. **Shadow the observer before deleting transport.**
   Let the new observer infer occupancy / progress while old transport still
   exists behind debug evidence. Compare "where physics says the ball is" vs
   "where transport says it should be." Do not use the observer to fake green
   results.

5. **Delete route-start snap and per-step transport for the overhead segment
   first.**
   After this point, `activeTravelRoute` should become observation state, not
   motion state.

6. **Extend the same rule through endpoint-bridge and descent.**
   Keep one late handoff into the main world. After that handoff the main world
   is effectively planar again, so this remains a coherent seam.

7. **Drive any correction counter to zero.**
   If a temporary entry correction exists, make it visible, bounded, and
   removable. Production target: `0`.

8. **Only then repin the baseline.**
   Do not widen `PR-0214` drift thresholds to "accept truth." Hold the line,
   stabilize the physical version, confirm it in the manual matrix, then capture
   a new baseline intentionally.

## 6. Verification guidance that keeps PR-0214 strict

Keep the current truth surface strict. Do not normalize today's drift away. The
live summary is correctly blocked today because the runtime is no longer being
propped up by shortcut energy, and `PR-0214` makes those blocked thresholds
explicit.

Add focused tests that fail if:

- launcher carrier occupancy still causes direct body transport writes
- accepted carrier entry results in higher speed than the observed entry state
  can justify
- any seam correction increases energy
- any reported `route_*` phase appears without physical occupancy evidence
- the production correction counter is non-zero

Keep the manual launcher matrix as a blocking truth check alongside the
automated trace. `PR-0215` already states that acceptance must remain blocked
until `rest` / `short` / `medium` / `full` / `relaunch` are manually recorded,
and contradictory manual feel should overrule automation.

Drift policy should stay two-stage:

- **Against the current pinned baseline:** blocked is expected and should remain
  blocked during migration.
- **Against the future physical baseline:** keep the gate strict again. Repin
  only after focused proof, raw live trace, and manual matrix all agree the new
  mechanics are intentional and stable.

## 7. Candidate recommendation judgments

### 1. Do not physicalize the current `travelRoutes`; demote them to observation / proof spines only.

**Accept.**

This is the core move. The current `travelRoutes` already mix proof semantics
with transport, and the transport side is the debt. Preserve their tags,
provenance, and continuity role, but remove all motion ownership.

### 2. Add explicit carrier types instead of overloading `guideRails`.

**Modify.**

The explicit-semantics idea is correct. The exact first-pass names were too
wireform-specific and slightly too low-resolution. The preferred role set is:

- support
- guard
- receiver
- observation spine
- handoff seam

Some crucial elements are surfaces or funnels, not wireforms, and a "bridge" is
better treated as a role composed of support + guard than as a primitive.

### 3. Convert the current overhead donor wireforms into real colliders.

**Modify.**

Use the overhead donors `RampS3`, `RampS001`, `RampS002`, and `RampS4` as the
donor-backed source geometry for real colliders. Do **not** simply flip the
current top-level playfield rail assets from `physics: false` to `physics: true`
in place. In the current architecture that would target the wrong world and
risk duplicate ownership.

### 4. Keep only terminal `handoffVelocity` as a production mechanics heuristic.

**Modify.**

Keep terminal `handoffVelocity` as the only **production mechanics** heuristic.
Also allow observation heuristics that do not move the ball. A position-only
entry correction may exist during bring-up, but production acceptance should
treat any non-zero correction count as a blocker.

### 5. Forbid all route-start snaps, per-step transport writes, speed floors, and hidden seam nudges in production.

**Accept.**

This remains a hard rule. It is exactly the runtime shortcut class called out
by [PR-0212](../backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md)
and [PR-0215](../backlog/prs/pr-0215-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment.md).

### 6. Keep the separate launcher Rapier 3D seam only if it owns the entire elevated route through one late board handoff.

**Modify.**

The ownership rule is correct, but it should be stated more sharply: keep the
separate launcher world only if it owns **every causal surface from post-plunger
capture through descent receiver and final board handoff**.

The current split is already close: launcher 3D owns the lower shooter
walls/rails and elevated receive-mouth walls, while the playfield compiler keeps
the elevated mouth walls out of main-world colliders. That makes one-late-
handoff ownership plausible once the overhead carriers move into the launcher
world.

## Summary

The short version of the architect direction is:

- **physical carrier graph**
- **observation-spine overlay**
- **one terminal handoff seam**

That is the cleanest path to truthful launcher mechanics without weakening
`PR-0214` or smuggling route transport shortcuts back in under a new name.
