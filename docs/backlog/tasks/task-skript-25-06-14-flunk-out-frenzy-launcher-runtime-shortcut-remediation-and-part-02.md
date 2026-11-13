---
type: task
id: TASK-SKRIPT-25-06-14-PART-02
title: 'Flunk-Out Frenzy: launcher runtime shortcut remediation and physical-truth
  alignment — part 02'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: TASK-SKRIPT-25-06-14
part: 2
---

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

### Planned module shape

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

### Test plan

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
  - record the outcome in `.codex/handoff.md`
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

### Rollback plan

- Roll back only the runtime-shortcut remediation if it makes launcher behavior
  worse while preserving the truthful proof surface from `PR-0213` and
  `PR-0214`.
- Do not reintroduce speed promotion, in-route speed floors, or per-step route
  teleports as a quick way to make tests green again.
- If truthful runtime remediation proves blocked by geometry or topology that
  this slice cannot change safely, stop and open a separate follow-up PR rather
  than weakening the contract or restoring hidden shortcuts.

### Definition of done

`PR-0215` is done when all of the following are true:

- the current truth surface still reports launcher behavior honestly through the
  focused tests, canonical live trace, and manual launcher matrix gate
- any remaining shortcut or transport debt is named explicitly as blocked debt
  instead of being narrated as a finished physical rail
- the work has stopped short of carrier schema, donor collider, ownership, and
  cut-over governance concerns now assigned to `EPIC-33` / `ST-33-01`

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
