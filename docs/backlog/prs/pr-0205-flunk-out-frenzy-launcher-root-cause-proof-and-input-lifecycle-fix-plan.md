---
type: pr
id: PR-0205
title: "Flunk-Out Frenzy: launcher root-cause proof and input lifecycle fix plan"
status: ready
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "ux", "input", "root-cause", "proof-first"]
dependencies:
  - "PR-0204"
acceptance_criteria:
  - "Given the user-reported live issue remains authoritative, when this task is complete, then root-cause assumptions are documented with explicit evidence and do not rely on unproven implementation guesses."
  - "Given production-code changes are blocked until root cause is proven, when this task is complete, then the proof lane consists of tests/docs only and no additional production behavior changes."
  - "Given launcher seam contracts were already tightened, when this task is complete, then proof explicitly separates physics-seam behavior from browser input/interaction behavior."
  - "Given current findings show a pointer lifecycle defect, when this task is complete, then a failing test captures the defect and is linked as the required implementation target for the next slice."
  - "Given architect invariants are non-negotiable, when this task is complete, then proof explicitly preserves seam continuity `xy<=1/z<=1`, no helper rails/freehand seam geometry, terminal-route-only `handoffVelocity` semantics, and `gate-passed` semantics from real `sw16` exit."
  - "Given the issue is user-observed in live browser behavior, when this task is complete, then a retained live launcher matrix artifact proves keyboard + pointer behavior with overlay/focus transitions and captures current failing behavior."
  - "Given review governance is required, when this task is complete, then an independent reviewer approves this proof-targeted fix plan before implementation starts."
---

## Problem

Live user verification still reports no observable launcher effect. A prior
input/overlay patch was implemented, but it did not change the observed browser
behavior. We need proof-first root-cause isolation before more production
changes.

## Goal

Lock a proof-first plan that demonstrates:

1. what currently works
2. what currently fails
3. why the previous fix did not solve the reported issue
4. what implementation target is approved next

## Non-goals

- No new launcher behavior changes in production code in this task.
- No seam-tolerance relaxation, no helper rails, no freehand seam geometry.
- No reclassification of unresolved live behavior as "accepted."

## Root-cause assumptions and evidence

- Assumption A (physics seam path is active under direct commands):
  - Evidence: `PhysicsWorld` charged-release tests show plunger displacement and
    ball advancement under direct launch commands, including explicit launcher
    lifecycle events.
  - Current proof surface:
    - `src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`

- Assumption B (previous fix did not prove pointer lifecycle correctness):
  - Evidence: focused input-path test currently fails because pointer capture is
    not released after pointer-up in the current controller behavior.
  - Current failing proof surface:
    - `src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`

- Why the previous fix did not close the root issue:
  - It improved command wiring but did not establish and verify a complete
    pointer interaction lifecycle contract.
  - It was not accepted against authoritative live behavior and lacked a strict
    failing proof target tied to the observed launcher issue.

## Required comparison baseline (previous fix vs current proof lane)

- Prior patch/review surface:
  - `PR-0204` and the associated launcher input/overlay patch in
    `KeyboardInputController.ts` + `GameHost.vue`.
- Intended prior behavior:
  - improved launcher input routing and reduced overlay interaction interference.
- Live behavior that still failed afterward:
  - user-reported no observable plunger movement/effect in five independent
    browser runs.
- Missing proof contract now added in this task:
  - explicit red/green proof surfaces for physics baseline vs pointer lifecycle
    defect baseline plus required retained live matrix artifacts.

## Implementation plan

- Keep this task proof-only:
  - maintain the failing input lifecycle test as the red baseline
  - keep direct-physics launcher test coverage explicit as the control baseline
- Keep invariant controls in the proof run:
  - include compiler/runtime contract control surface for terminal-route-only
    `handoffVelocity` semantics and sw16/route seam invariants.
- Define next implementation target precisely (for follow-up task):
  - fix pointer lifecycle so capture/press/release/blur/visibility transitions
    are consistent and test-proven
  - rerun live launcher matrix with keyboard + pointer proof artifacts
- Require independent review sign-off on this plan before writing production
  launcher behavior changes.

## Test plan

- Proof command set for this task:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
  - `pdm run docs-validate`
- Invariant to proof-surface map (must stay explicit):
  - seam contracts, route ownership/provenance, and terminal-route handoff
    semantics:
    - `src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
  - launcher feed/charge/release/rerun lifecycle contract:
    - `src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
  - runtime launcher behavior, real `sw16` semantics, and no synthetic route-start
    gate event behavior:
    - `src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
  - input lifecycle red baseline and pointer/keyboard path contract:
    - `src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
- Live matrix prerequisites (must be satisfied before running cases):
  1. backend dependencies installed and DB prepared
     - `pdm install -G monorepo-tools`
     - `pdm run fe-install`
     - `docker compose up -d db`
     - `pdm run db-upgrade`
  2. bootstrap local auth user exists
     - `pdm run bootstrap-superuser`
  3. runtime processes started in separate terminals
     - `pdm run dev`
     - `pdm run fe-dev`
  4. artifact directory exists
     - `mkdir -p .artifacts/flunk-out-frenzy-live-launch-matrix`
- Reproducible live launcher matrix procedure (retain artifacts):
  1. Open:
     - `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
  2. If login is required, authenticate with `BOOTSTRAP_SUPERUSER_EMAIL` and
     `BOOTSTRAP_SUPERUSER_PASSWORD` from `.env`.
  3. Reach playable state:
     - app route loaded
     - table canvas visible
     - game has left initial loading state
  4. Use fixed hold timings:
     - `short = 120ms`
     - `medium = 420ms`
     - `full = 900ms`
     - `relaunch gap = 250ms` after first release
  5. Use fixed overlay/focus actions:
     - overlay reopen: press `Escape` once (open), then `Escape` once (close)
     - blur/refocus: switch to another browser tab for ~1 second, then return
       to the game tab and click inside canvas once
  6. Execute this exact case matrix in order (no substitutions):
     - `K-CLOSED-STEADY`: keyboard, closed, steady, rest
       action: press launcher key once (`Space`) with no hold
     - `K-REOPEN-STEADY`: keyboard, reopened, steady, rest
       action: reopen overlay via `Escape` open/close, then press `Space` once
     - `K-CLOSED-BLUR`: keyboard, closed, blur_refocus, rest
       action: perform blur/refocus sequence, then press `Space` once
     - `P-CLOSED-STEADY`: pointer, closed, steady, rest
       action: pointer down/up once on launcher input area without hold
     - `P-REOPEN-STEADY`: pointer, reopened, steady, rest
       action: overlay reopen sequence, then pointer down/up once
     - `P-CLOSED-BLUR`: pointer, closed, blur_refocus, rest
       action: blur/refocus sequence, then pointer down/up once
     - `P-REOPEN-BLUR`: pointer, reopened, blur_refocus, rest
       action: overlay reopen + blur/refocus, then pointer down/up once
     - `K-SHORT-TAP`: keyboard, closed, steady, short
       action: hold `Space` 120ms, then release
     - `K-MEDIUM-HOLD`: keyboard, closed, steady, medium
       action: hold `Space` 420ms, then release
     - `K-FULL-AND-RELAUNCH`: keyboard, closed, steady, relaunch
       action: hold `Space` 900ms release, wait 250ms, hold `Space` 900ms
       release
  7. Save one final post-run screenshot:
     - `.artifacts/flunk-out-frenzy-live-launch-matrix/launch-matrix-after.png`
  8. Write:
     - `.artifacts/flunk-out-frenzy-live-launch-matrix/launch-matrix-summary.json`
- Required artifact schema (`launch-matrix-summary.json`):
  - `run_at_utc`: ISO timestamp
  - `url`: must equal `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
  - `cases`: array with all 10 exact case ids above (no omissions)
  - each case object must include:
    - `case_id`: one of the fixed ids above
    - `input_mode`: `keyboard` or `pointer`
    - `overlay_state`: `closed` or `reopened`
    - `focus_state`: `steady` or `blur_refocus`
    - `hold_profile`: `rest`, `short`, `medium`, `full`, or `relaunch`
    - `plunger_visible_motion`: boolean
    - `ball_visible_response`: boolean
    - `sw16_exit_observed`: boolean
    - `gate_passed_observed`: boolean
    - `notes`: short free text
- Fixed case-to-field mapping (no inferred values allowed):
  - `K-CLOSED-STEADY`: `keyboard`, `closed`, `steady`, `rest`
  - `K-REOPEN-STEADY`: `keyboard`, `reopened`, `steady`, `rest`
  - `K-CLOSED-BLUR`: `keyboard`, `closed`, `blur_refocus`, `rest`
  - `P-CLOSED-STEADY`: `pointer`, `closed`, `steady`, `rest`
  - `P-REOPEN-STEADY`: `pointer`, `reopened`, `steady`, `rest`
  - `P-CLOSED-BLUR`: `pointer`, `closed`, `blur_refocus`, `rest`
  - `P-REOPEN-BLUR`: `pointer`, `reopened`, `blur_refocus`, `rest`
  - `K-SHORT-TAP`: `keyboard`, `closed`, `steady`, `short`
  - `K-MEDIUM-HOLD`: `keyboard`, `closed`, `steady`, `medium`
  - `K-FULL-AND-RELAUNCH`: `keyboard`, `closed`, `steady`, `relaunch`
- Required complete summary template (all 10 cases, no inferred fields):
  - `{"run_at_utc":"<iso>","url":"http://127.0.0.1:5173/apps/games.flunk_out_frenzy","cases":[{"case_id":"K-CLOSED-STEADY","input_mode":"keyboard","overlay_state":"closed","focus_state":"steady","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"K-REOPEN-STEADY","input_mode":"keyboard","overlay_state":"reopened","focus_state":"steady","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"K-CLOSED-BLUR","input_mode":"keyboard","overlay_state":"closed","focus_state":"blur_refocus","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"P-CLOSED-STEADY","input_mode":"pointer","overlay_state":"closed","focus_state":"steady","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"P-REOPEN-STEADY","input_mode":"pointer","overlay_state":"reopened","focus_state":"steady","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"P-CLOSED-BLUR","input_mode":"pointer","overlay_state":"closed","focus_state":"blur_refocus","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"P-REOPEN-BLUR","input_mode":"pointer","overlay_state":"reopened","focus_state":"blur_refocus","hold_profile":"rest","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"K-SHORT-TAP","input_mode":"keyboard","overlay_state":"closed","focus_state":"steady","hold_profile":"short","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"K-MEDIUM-HOLD","input_mode":"keyboard","overlay_state":"closed","focus_state":"steady","hold_profile":"medium","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"},{"case_id":"K-FULL-AND-RELAUNCH","input_mode":"keyboard","overlay_state":"closed","focus_state":"steady","hold_profile":"relaunch","plunger_visible_motion":false,"ball_visible_response":false,"sw16_exit_observed":false,"gate_passed_observed":false,"notes":"replace with observation"}]}`
- Expected result profile for this task:
  - compiler + seam/runtime invariant controls stay green
  - pointer lifecycle red test fails and remains the implementation target

## Rollback plan

- If this proof lane is rejected, keep launcher implementation blocked and
  remove any claim that root cause is known.
