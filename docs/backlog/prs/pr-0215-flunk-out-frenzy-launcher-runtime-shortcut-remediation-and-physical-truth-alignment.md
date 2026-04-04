---
type: pr
id: PR-0215
title: "Flunk-Out Frenzy: launcher runtime shortcut remediation and physical-truth alignment"
status: in_progress
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "physics", "runtime", "proof-first", "mechanics", "truth"]
dependencies:
  - "PR-0209"
  - "PR-0212"
  - "PR-0213"
  - "PR-0214"
  - "PR-0216"
acceptance_criteria:
  - "Given route admission currently promotes speed from inferred charge and a hard floor, when this task is complete, then accepted route travel derives from directly observed launcher contact/release state and does not upgrade velocity beyond what runtime evidence supports."
  - "Given route progression currently advances the ball by direct `setTranslation(...)` and `setLinvel(...)` writes along authored route points, when this checkpoint is complete, then any remaining transport shortcut is treated as explicit blocked debt rather than being narrated as a completed physical rail."
  - "Given `handoffVelocity` is the only acceptable declared bounded heuristic from `PR-0212`, when this task is complete, then any remaining non-simulated behavior is isolated to the terminal board handoff and is never overstated as continuous route physics."
  - "Given the proof surface is now truthful and operational through `PR-0213` and `PR-0214`, when this task is complete, then the canonical focused tests and live Playwright trace continue to serve as the decision gate for whether runtime remediation actually improved physical truth."
  - "Given automated traces can still mask the known inert-launch false-green risk, when this task is complete, then acceptance remains blocked until a manual launcher matrix check for `rest`, `short`, `medium`, `full`, and `relaunch` is recorded in `.agents/handoff.md` alongside the automated evidence."
  - "Given this slice is now a bounded runtime-honesty checkpoint rather than the physical-carrier cut-over itself, when this task is complete, then no new carrier-role schema, donor overhead collider cut-over, or baseline repin is smuggled into the slice."
---

## Problem

`PR-0212` made three launcher-runtime truth gaps explicit:

1. route entry can be accepted with speed promoted from inferred charge rather
   than fully observed contact outcome
2. route travel is advanced by direct body writes along authored route points
3. the terminal `handoffVelocity` heuristic is acceptable only if it remains a
   bounded declared seam rather than cover for earlier non-physical transport

`PR-0213` and `PR-0214` fixed the proof surface around those gaps. They did not
remove the mechanics debt itself. The launcher can therefore look fully proven
while still depending on speed amplification and kinematic corridor transport.

## Goal

Reduce the launcher-runtime shortcuts enough to expose honest drift and preserve
the truthful proof stack, without pretending that this slice can complete the
full physical-carrier conversion on current foundations.

This slice is now explicitly a **runtime-honesty checkpoint**:

1. accepted route energy comes from observed runtime state, not inferred speed
   promotion
2. remaining route transport debt is surfaced honestly and kept blocked, not
   renamed into physical truth
3. the only remaining bounded heuristic is the terminal board handoff already
   declared in the donor spec

## Checkpoint definition

`PR-0215` is a bounded checkpoint whose purpose is to stabilize the current
truth surface and keep the remaining runtime shortcuts visible.

That means this slice may:

- remove or reduce launcher-runtime overclaim when direct runtime evidence can
  support the change
- preserve the `PR-0213` / `PR-0214` proof stack as the canonical decision
  surface
- convert unresolved transport behavior into explicit blocked debt instead of
  renaming it into carrier truth

That also means this slice must stop once it has made the current truth surface
honest enough to show what still remains unresolved.

## Non-goals

- No proof-surface weakening or telemetry reconstruction.
- No physical carrier graph implementation.
- No new carrier-role schema or launcher-world ownership model work; that now
  belongs to `EPIC-33` / `ST-33-01`.
- No donor overhead collider cut-over.
- No baseline repin.
- No broad Playwright/summary rewrite beyond what runtime remediation forces the
  truthful trace to report.
- No donor-map redraw or speculative new launcher topology.
- No relaxation of existing seam tolerances or invariant thresholds.
- No attempt to hide unresolved runtime debt by renaming it as "derived truth."

## Scope lock (bounded)

Primary runtime scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherSensors.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherContext.ts`
- any new focused launcher helper modules needed to keep runtime responsibilities
  under the repo's file-size and SRP limits

Proof/verification scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
- `.agents/handoff.md`

Reference-but-not-rewrite scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/spec/specLauncher.ts`
- `scripts/playwright_flunk_out_frenzy_launch_trace_parity_check.py`
- `scripts/playwright_flunk_out_frenzy_launch_trace_check.py` as compatibility wrapper only, not the canonical decision gate
- `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
- `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.json`
- `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`

Out of scope:

- new route-contract weakening PR work
- broad table-compiler or launcher-schema changes unrelated to this checkpoint
- reauthoring donor rail geometry without first proving runtime code cannot use
  the existing donor-backed corridor
- physical cut-over work now governed by `EPIC-33` / `ST-33-01`

## Sequencing correction (2026-04-04)

The architect direction in
`docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`
made a broader structural point explicit:

- `PR-0215` is not the physical-carrier implementation vehicle
- `travelRoutes` should become observation/proof spines, not motion owners
- physical carrier schema/compiler/ownership work must land first under
  `EPIC-33` / `ST-33-01`

This PR therefore remains valid only as a bounded runtime-honesty checkpoint.
Any further cut-over continuation is blocked on `PR-0217` through `PR-0219`.

## Hard stop conditions

Stop `PR-0215` and route the work into `EPIC-33` / `ST-33-01` if truthful
runtime remediation requires any of the following:

- carrier-role schema or observation-spine contract changes
- launcher-world ownership redefinition
- donor overhead collider conversion or compiler-owned carrier output
- observer shadow-mode or cut-over readiness-gate work
- baseline repin, drift-threshold widening, or other `PR-0214` softening

If any of those become necessary, this PR has reached its intended checkpoint
boundary and should record the blocker rather than absorb the next lane.

## Evidence-locked shortcut targets

### A. Route speed amplification from inferred charge plus floor

- Current evidence:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:426`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:433`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:460`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:39`
- Current dishonest path:
  - route speed is promoted by `Math.max(measuredSpeed, resolveLaunchSpeedFromCharge(...))`
  - route speed is then floored again inside `buildActiveTravelRoute(..., 850)`
- Required end state:
  - accepted route speed must derive from directly observed release/contact
    state
  - if observed energy is insufficient for truthful route entry, the route must
    reject rather than silently upgrade the ball

### B. Kinematic route transport via direct body writes

- Current evidence:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:444`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:445`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:135`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:136`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:167`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:168`
- Current dishonest path:
  - route capture snaps the ball onto the route start
  - each step advances route progress by authored distance and writes body pose
    directly
  - seam transitions reset the body again at the next route start
- Required end state:
  - authored route definitions remain an observation/proof surface, not a
    kinematic transport rail
  - the live/focused trace must observe the ball traversing the donor-backed
    launcher corridor without claiming free-simulation truth while body writes
    still do the real work

### C. Remaining gap between bounded heuristic and claimed physical truth

- Current evidence:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/spec/specLauncher.ts:223`
- Constraint from `PR-0212`:
  - terminal `handoffVelocity` may remain as a declared bounded seam contract
  - earlier route travel may not depend on hidden shortcuts while still being
    narrated as physical continuity
- Required end state:
  - only the terminal descent-to-board seam may remain heuristic
  - all earlier launcher-to-route truth claims must be backed by actual runtime
    behavior rather than transport fiction

## Best-practice implementation plan

### Checkpoint A. Freeze the proof baseline before touching runtime

1. Rerun the current proof gates and retain the launcher raw/summary artifacts.
2. Treat those artifacts as the before-state decision surface, not just test
   exhaust.
3. Do not change the trace contract first; use the current truthful operator
   surface to tell us whether mechanics work helped or hurt.

### Checkpoint B. Separate route admission from route transport

1. Extract the current route-admission decision into a focused helper module so
   launcher admission can be reasoned about independently of corridor motion.
2. Replace inferred-charge speed promotion with observed entry-state
   calculations:
   - capture measured release/contact velocity at the acceptance moment
   - project that velocity onto the route-entry tangent
   - reject route entry when observed velocity is below the truthful threshold
     instead of lifting it with `resolveLaunchSpeedFromCharge(...)` or an
     in-route floor
3. Keep charge ratio only as an eligibility input for which routes are legal,
   not as permission to fabricate route energy after the fact.

### Checkpoint C. Turn the route into an observed corridor, not a transporter

1. Refactor `ActiveTravelRoute` so it tracks observed route occupancy/progress
   instead of owning the ball's physical motion.
2. Remove per-step `setTranslation(...)` / `setLinvel(...)` stepping from the
   route runner.
3. Let the existing donor-backed launcher walls and guide rails in
   `LauncherWorldGeometry.ts` own corridor motion, while route logic becomes:
   - route-entry classification
   - route/phase observation
   - seam-transition observation
   - terminal handoff arming
4. If a tiny runtime nudge is still needed at the exact route-entry seam, it
   must obey a strict seam-alignment contract:
   - it may align position only within the existing route-entry tolerance band
   - it may preserve or reduce observed entry velocity, but it may never
     increase velocity magnitude
   - it must be emitted in telemetry and locked by focused tests proving that
     post-correction route energy never exceeds pre-correction observed entry
     energy
   - it may not become a recurring per-step corridor transport loop

### Checkpoint D. Isolate the only allowed heuristic

1. Keep `handoffVelocity` only at the final descent-to-board seam.
2. Document and test that earlier route segments no longer rely on hidden speed
   promotion or route teleports.
3. If the corridor still cannot carry truthful travel with existing donor
   geometry, stop and route that blocker into a new follow-up PR rather than
   broadening this slice into geometry-authoring or contract weakening.

### Checkpoint E. Lock behavior with proof-first tests

1. Expand the focused launcher runtime tests so they fail if:
   - accepted route speed exceeds what the observed release/contact state can
     justify
   - route success still depends on direct body teleports
   - seam telemetry claims route phases the runtime did not physically traverse
2. Keep `compilePinballTable.spec.ts` as the topology/contract guard and
   `plungerLaneState.spec.ts` as the launcher state-machine guard, but make
   `PhysicsWorld.launcher.spec.ts` the source of truth for runtime honesty.
3. Use the canonical live Playwright trace and PR-0214 summary gate after each
   checkpoint to confirm runtime changes improved truth rather than merely
   changing the shape of green output.
4. Do not accept the slice on automated output alone:
   - record a manual launcher matrix check for `rest`, `short`, `medium`,
     `full`, and `relaunch`
   - if the manual run still shows inert plunger/ball interaction while the
     automated trace is green, treat that as a blocking mismatch rather than a
     tolerable discrepancy

## Planned module shape

To stay under the repo's file-size and SRP constraints, prefer a split close to
this:

- `launcherChain3d.ts`
  - orchestration only
- `launcher/LauncherRouteAdmission.ts`
  - observed entry-state capture, tangent projection, truthful route acceptance
- `launcher/LauncherRouteObserver.ts`
  - route occupancy/progress inference from physical ball position
- `launcher/LauncherTravelRoute.ts`
  - reduced to route sampling/math helpers and terminal handoff resolution only

If the existing modules can absorb that split cleanly without extra files, that
is fine, but the implementation must avoid growing a single launcher file back
into an oversized mixed-responsibility class.

## Test plan

- Focused runtime proof:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
- Frontend quality gates:
  - `pdm run fe-type-check`
  - `pdm run fe-build`
- Docs gate:
  - `pdm run docs-validate`
- Live proof gate:
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_parity_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`
- Blocking manual gate:
  - run one headed local launcher matrix pass covering `rest`, `short`,
    `medium`, `full`, and `relaunch`
  - record the outcome in `.agents/handoff.md`
  - do not mark `PR-0215` accepted while this manual matrix remains pending or
    contradictory to the automated trace

Required artifact review after the live gate:

- raw trace:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
- machine summary:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.json`
- human summary:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`
- focused baseline for drift comparison:
  - `frontend/apps/skriptoteket/.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`

## Rollback plan

- Roll back only the runtime-shortcut remediation if it makes launcher behavior
  worse while preserving the truthful proof surface from `PR-0213` and
  `PR-0214`.
- Do not reintroduce speed promotion, in-route speed floors, or per-step route
  teleports as a quick way to make tests green again.
- If truthful runtime remediation proves blocked by geometry or topology that
  this slice cannot change safely, stop and open a separate follow-up PR rather
  than weakening the contract or restoring hidden shortcuts.

## Definition of done

`PR-0215` is done when all of the following are true:

- the current truth surface still reports launcher behavior honestly through the
  focused tests, canonical live trace, and manual launcher matrix gate
- any remaining shortcut or transport debt is named explicitly as blocked debt
  instead of being narrated as a finished physical rail
- the work has stopped short of carrier schema, donor collider, ownership, and
  cut-over governance concerns now assigned to `EPIC-33` / `ST-33-01`
