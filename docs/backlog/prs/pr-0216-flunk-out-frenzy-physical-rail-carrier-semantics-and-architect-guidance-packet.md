---
type: pr
id: PR-0216
title: "Flunk-Out Frenzy: physical rail carrier semantics and architect guidance packet"
status: ready
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "physics", "planning", "architecture", "rapier", "proof-first"]
dependencies:
  - "PR-0212"
  - "PR-0213"
  - "PR-0214"
  - "PR-0215"
acceptance_criteria:
  - "Given the current launcher overhead path still depends on authored travel routes plus direct body writes, when this task is complete, then the repo contains an explicit analysis of which launcher surfaces are physically real today, which are render-only or proof-only, and where the current corridor cannot support truthful rail travel."
  - "Given the next slice must be grounded in engine reality rather than aspiration, when this task is complete, then the plan explicitly identifies which Rapier 3D constraints, collider patterns, stability risks, CCD/substep concerns, and seam-continuity limits must be satisfied before deterministic transport can be replaced by physical carrier motion."
  - "Given the lead architect needs a careful independent analysis rather than an open-ended request for opinions, when this task is complete, then a targeted repomix package and architect brief exist with the exact files, evidence, and questions needed to advise on carrier semantics, heuristic boundaries, runtime responsibilities, and verification strategy."
  - "Given one independent architect pass has already produced concrete candidate recommendations, when this task is complete, then the offline architect packet presents those recommendations as explicit hypotheses to validate, modify, or reject instead of forcing a blind first-principles rediscovery."
  - "Given `PR-0215` already proved that removing shortcut energy changes live timing and peak-speed signatures, when this task is complete, then the proposed physical-rail follow-on defines production-ready success without weakening the truthful proof surface or silently normalizing drift."
---

## Problem

`PR-0215` has already shown that removing shortcut speed promotion changes the
observed launcher behavior in meaningful ways. The live route still completes,
but the ball now traverses the overhead path much more slowly and the `PR-0214`
gate correctly flags large drift in handoff timing, first board collision, and
peak speed.

That exposed a deeper problem: the current launcher "route" is still a
hybrid of authored proof semantics and kinematic transport. The ball is not yet
traveling a truly physical overhead wireform/rail whose motion is governed by
real colliders, contact, and game mechanics.

We therefore need one careful planning-and-analysis slice before attempting more
runtime remediation. That slice must map the current launcher corridor as it
actually exists in code, determine what Rapier can and cannot do for this
problem, and ask the lead architect for targeted implementation advice instead
of letting the next runtime changes become guesswork.

## Goal

Create the design contract and review packet for converting the launcher
overhead route from deterministic transport into a real physical carrier/rail.

This slice should answer, in repo-grounded terms:

1. what "map the current launcher-corridor physics surfaces" means in practice
2. what Rapier capabilities and limits matter for this specific wireform/ball
   problem
3. which new authored/compiled carrier semantics are required before runtime
   work can be honest
4. what the lead architect must advise on before further physical-rail
   implementation begins

## Non-goals

- No further runtime behavior edits beyond the already-started `PR-0215`
  checkpoint.
- No proof-contract weakening, baseline normalization, or telemetry softening.
- No speculative donor redraw or freehand geometry invention.
- No pretending that render-only wire rails are already physical carriers.
- No implementation of a new rail model before the architectural questions are
  answered explicitly.

## What the analysis means in practice

### A. Map the current launcher-corridor physics surfaces

This is not a vague "understand the code better" task. In this repo it means
producing a concrete inventory of the current launcher corridor and classifying
each surface by role:

1. support surfaces
   - which colliders can actually carry the ball's weight and motion today
2. retention/guard surfaces
   - which colliders keep the ball inside the corridor once elevated
3. seam surfaces
   - which surfaces or boundaries govern the transition from lower shooter lane
     to overhead path and from overhead path back to board
4. trigger/proof surfaces
   - which shapes exist only to classify phases or emit telemetry
5. render-only surfaces
   - which donor-backed rails or polygons look like wireforms but do not create
     physics at all
6. path-only semantics
   - which authored route points currently exist only so runtime can move the
     ball along them

For this slice, that mapping must explicitly reconcile:

- `specPlayfieldGeometry.ts`
- `specLauncher.ts`
- `tableDefinitionTypes.ts`
- `LauncherWorldGeometry.ts`
- `launcherChain3d.ts`
- `LauncherTravelRoute.ts`
- the current focused/live proof artifacts from `PR-0214`

The output must make it obvious where truthful physical carrier travel is
possible today and where the current corridor still depends on a transport
fiction.

### B. Check Rapier's relevant constraints for this exact problem

This also needs to be concrete. The question is not "can Rapier do physics?"
but "can Rapier 3D represent this donor-backed launcher wireform honestly
enough for our correctness bar without reintroducing hidden shortcuts?"

The analysis must therefore check the implications of:

1. dynamic ball on segmented 3D support geometry
   - capsule/box/tube approximations versus spline-like ideal paths
2. high-speed narrow-body contact stability
   - tunneling risk, CCD reliance, seam gaps, and jitter on thin rails
3. support plus guard geometry requirements
   - whether a single centerline rail is insufficient and a cradle/guide
     profile is needed
4. gravity direction and slope-driven travel
   - whether the authored z/y profile can generate donor-like motion or needs
     additional mechanical constraints
5. solver/substep sensitivity
   - what step cadence, damping, friction, restitution, and collider density are
     required for stable travel at current scale/speeds
6. world-boundary implications
   - whether the separate launcher Rapier 3D seam can carry the full physical
     route honestly or whether the seam architecture itself becomes the blocker

The output should identify not only what Rapier can do, but also which patterns
would still be disguised transport even if they looked more "physical" in code.

## Required design questions for the lead architect

The architect handoff must request concrete guidance on:

1. **Carrier semantics**
   Which new 3D authored/compiled carrier types should exist beyond today's
   `guideRails` and `travelRoutes`?

2. **Heuristic boundaries**
   What, if anything, may remain heuristic besides the already-declared
   terminal `handoffVelocity`, and how must those seams be named/tested?

3. **Runtime responsibility split**
   Which responsibilities belong to authored spec, compiler, geometry builder,
   runtime observation, and telemetry once route transport is removed?

4. **Donor-to-collider mapping**
   Which donor assets should become real colliders, and which donor shapes
   should remain render/proof-only?

5. **Rapier feasibility**
   Is the current separate launcher 3D world sufficient for a production-ready
   physical rail, or does the seam architecture need a deeper redesign?

6. **Truth-preserving verification**
   What counts as production-ready success in focused tests, live trace drift,
   and manual launcher-matrix behavior if the rail becomes physically honest but
   timing changes?

## Proposed hypotheses for architect validation

The offline architect should not start from a blank slate. The packet should
present the following as explicit candidate recommendations to validate,
modify, or reject:

1. **Do not physicalize the current `travelRoutes`.**
   They should become observation/proof spines only, not motion drivers.

2. **Introduce explicit carrier semantics.**
   Candidate new types:
   - `wireformCarrier3D`
   - `wireformGuard3D`
   - `carrierReceiver3D`
   - `carrierSeamBridge3D`
   - `carrierObservationSpine3D`

3. **Turn the donor overhead wireforms into real colliders.**
   The current `RampS3`, `RampS001`, `RampS002`, and `RampS4` overhead donors
   are the leading candidates to stop being `physics: false`.

4. **Keep only terminal `handoffVelocity` as a production heuristic.**
   Observation heuristics may remain acceptable, but transport heuristics may
   not.

5. **Require zero transport writes during carrier occupancy.**
   `setTranslation(...)` / `setLinvel(...)` must disappear from overhead route
   progression once physical carriers exist.

6. **Treat seam correction as temporary bring-up only.**
   If an entry correction is temporarily unavoidable, production-ready success
   should mean its debug counter is `0`.

7. **Keep the separate launcher 3D seam only if it owns the entire elevated
   route.**
   If descent confinement or receiver ownership leaks back into the main world,
   the seam boundary itself should be reconsidered before more runtime work.

## Implementation plan

### Checkpoint A. Freeze the current evidence

1. Record the exact current runtime/proof state from `PR-0215`:
   - focused tests green
   - live `PR-0214` gate blocked on timing/peak-speed drift
2. Treat the raw trace matrix and summary gate as the evidence surface for the
   architect review, not just local debugging exhaust.

### Checkpoint B. Write the physical-surface analysis

1. Inventory the current physical launcher surfaces and semantic-only surfaces.
2. Classify each authored/compiled surface as support, guard, seam, proof, or
   render-only.
3. Identify the exact points where the current launcher corridor ceases to be a
   physical model and becomes path-driven transport.

### Checkpoint C. Write the Rapier feasibility analysis

1. Ground the design discussion in the collider types and solver behavior
   available in the current engine/runtime stack.
2. Identify the stability and seam risks that must be addressed if the
   wireform becomes physical.
3. Call out any engine/architecture blockers that would make a truthful rail
   impossible inside the current seam model.

### Checkpoint D. Build the architect packet

1. Create a concise architect brief with:
   - current state summary
   - explicit blocked-drift evidence from `PR-0215`
   - the candidate recommendations above as reviewable hypotheses
   - exact evidence paths
   - required questions and required decisions
   - decisions needed before implementation
2. Build a targeted repomix package covering:
   - planning docs (`PR-0212` to `PR-0216`)
   - the concise architect context/evidence note
   - launcher runtime and geometry files
   - table spec/compiler files
   - focused launcher proof files
   - canonical live trace tooling and summary artifact

### Checkpoint E. Route the outcome into the next implementation slice

1. Do not continue the physical-rail conversion on intuition alone.
2. Wait for architect guidance.
3. Use that guidance to define the actual implementation PR that introduces new
   carrier semantics, runtime observation rules, and production-ready
   verification expectations.

## Test plan

- Docs/package validation:
  - `pdm run docs-validate`
- Repomix packaging validation:
  - `repomix --style xml --no-gitignore --output .agents/repomix_packages/repomix-flunk-out-frenzy-physical-rail-architect-guidance.xml --include "<targeted file list>"`
- Optional evidence refresh before external review:
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_parity_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`

## Rollback plan

This slice is documentation and review-packaging only.

If the framing proves wrong:

1. keep `PR-0215` as the active runtime checkpoint
2. replace or supersede `PR-0216` with a corrected planning doc
3. rebuild the architect package against the corrected scope rather than
   continuing runtime changes under a flawed design premise
