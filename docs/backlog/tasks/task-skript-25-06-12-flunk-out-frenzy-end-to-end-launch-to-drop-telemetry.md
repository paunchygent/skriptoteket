---
type: task
id: TASK-SKRIPT-25-06-12
title: 'Flunk-Out Frenzy: end-to-end launch-to-drop telemetry contract and deterministic
  trace matrix'
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
- Given launcher behavior is now test-green but still sensitive at seams, when this
  task is complete, then telemetry captures the full launch-to-drop path as deterministic,
  step-indexed phase traces rather than point-in-time snapshots only.
- Given gameplay-fidelity decisions must be evidence-backed, when this task is complete,
  then each launch matrix case emits retained artifacts that explain the full causal
  chain from `swplunger` rest to board-drop collision.
- Given no-shortcuts and donor-seam invariants are non-negotiable, when this task
  is complete, then telemetry/proof additions do not relax seam tolerance (`xy<=1`,
  `z<=1`), do not alter endpoint-bridge authoring, do not add helper/freehand geometry,
  and do not introduce synthetic launcher behavior.
- Given semantic separation is hard-required, when this task is complete, then traces
  keep `swplunger` feed/rest and `sw16` exit semantics explicit and independently
  testable.
- Given route-chain correctness is the seam contract, when this task is complete,
  then artifacts and tests prove the path order `overhead -> endpoint-bridge -> descent
  -> board handoff -> board drop` for qualifying launch cases.
- Given this is an observability/proof slice, when this task is complete, then production
  gameplay tuning/geometry edits are out of scope and any new behavior fix is blocked
  until this telemetry contract is green and reviewed.
- Given workflow requires auditable evidence, when this task is complete, then focused
  command results plus live route-check outputs are recorded in `.codex/handoff.md`
  with artifact paths.
---

## Context

Source: `docs/backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md`. Flunk-Out Frenzy: end-to-end launch-to-drop telemetry contract and deterministic trace matrix.

Current proofs confirm pass/fail outcomes for launcher behavior, but we still lack one deterministic telemetry contract that explains the entire launch-to-drop chain in a single trace artifact. That gap makes it harder to diagnose future seam regressions quickly and unambiguously. Add an end-to-end, deterministic telemetry and artifact contract for the full launch-to-drop path, with focused tests that prove phase ordering, semantic correctness, and seam continuity visibility without changing gameplay behavior. - No launcher behavior tuning in this slice. - No donor geometry/path edits (`prototypeAlphaVpwDonorMap.ts`, `prototypeAlphaTableSpec.ts`). - No seam tolerance relaxation (`xy<=1`, `z<

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-25-06-12 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

Current proofs confirm pass/fail outcomes for launcher behavior, but we still lack one deterministic telemetry contract that explains the entire launch-to-drop chain in a single trace artifact. That gap makes it harder to diagnose future seam regressions quickly and unambiguously.

### Goal

Add an end-to-end, deterministic telemetry and artifact contract for the full launch-to-drop path, with focused tests that prove phase ordering, semantic correctness, and seam continuity visibility without changing gameplay behavior.

### Non-goals

- No launcher behavior tuning in this slice.
- No donor geometry/path edits (`prototypeAlphaVpwDonorMap.ts`, `prototypeAlphaTableSpec.ts`).
- No seam tolerance relaxation (`xy<=1`, `z<=1` stays strict).
- No helper rails, no freehand seam geometry, no invented bridge points.
- No new direct launch shortcut path (`setLinvel(...)` as release substitute).
- No synthetic `gate-passed` emission from route start.

### Scope lock (bounded)

Primary implementation scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/runtimeTypes.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/GameRuntime.ts`
- `scripts/playwright_flunk_out_frenzy_launch_trace_check.py` (new live-proof artifact script)

Proof/contract scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
- `.codex/handoff.md`

Out of scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorMap.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.ts`

### Telemetry contract (required)

### 1. Trace phases

Each case trace must label each recorded step with exactly one phase:

1. `feed_rest`
2. `charge_pull`
3. `release_strike_window`
4. `route_overhead`
5. `route_endpoint_bridge`
6. `route_descent`
7. `handoff_to_board`
8. `board_drop_preimpact`
9. `board_drop_postimpact`

### 2. Per-step record shape

Required fields for every recorded step:

- `step_index`
- `dt_ms`
- `phase`
- `ball_owner` (`launcher_chain|main_world|none`)
- `ball_position` (`x,y,z|null`)
- `ball_velocity` (`x,y,z|null`)
- `plunger` (`currentY,targetY,chargeRatio,phase`)
- `route` (`activeRouteTag,pendingReleaseChargeRatio,captureWindowMsRemaining,routeProgressDistancePx`)
- `route_capture` (`lastDecision,lastRejectReason`)
- `sensors` (`feedInside,exitInside,lastSw16ExitStep`)
- `contact` (`plungerBallContactActive,contactEnteredThisStep,contactExitedThisStep,separationPx,overlapPx,relativeVyAtContact,lastContactAtStep,impulseTransferMarker`)
- `seam_transition` (`fromRouteTag,toRouteTag,xyDeltaPx,zDeltaPx|null`)
- `events` (semantic machine events emitted this step)

### 3. Case-level summary fields

Each case summary must include:

- `case_id`
- `hold_profile` (`rest|short|medium|full|relaunch`)
- `dt_ms`
- `hold_steps`
- `relaunch_gap_steps`
- `observation_steps`
- `phase_order_observed` (ordered distinct phases)
- `sw16_exit_observed` (boolean)
- `handoff_to_board_step` (number|null)
- `first_board_collision_step` (number|null)
- `peak_speed`
- `min_vy`
- `max_displacement_px`
- `strike_classification` (`no_effective_strike|post_strike_route_rejection|strike_and_route_accepted`)
- `invariant_violations` (array; empty when pass)

### 4. Exact phase predicates (must be typed and deterministic)

Phase transitions must be derived from typed source-of-truth fields, not ad hoc inference:

- `handoff_to_board_step`:
  - first step where `ball_owner` transitions from `launcher_chain` to `main_world`
  - transition must be recorded from the `PhysicsWorld` board-handoff seam (`releaseToBoard` commit path)
  - `handoff_to_board_step` is `null` if no such transition occurs within the case observation budget

- `first_board_collision_step`:
  - first post-handoff step where a new typed telemetry marker confirms ball contact with a non-sensor board collider in the main world
  - launcher-chain wall/guide contacts and sensor transitions must not count
  - `first_board_collision_step` is `null` if no qualifying contact occurs within board-drop observation budget

- `board_drop_preimpact`:
  - steps after `handoff_to_board_step` and strictly before `first_board_collision_step`

- `board_drop_postimpact`:
  - steps at and after `first_board_collision_step`

Focused specs must assert:
- `first_board_collision_step === null` before handoff
- launcher-chain contacts do not classify as board-drop impact

### Deterministic matrix contract

Use unchanged PR-0206 matrix controls:

- `dtMs=16`
- `holdSteps=0/8/26/56` + relaunch second release profile
- `relaunchGapSteps=16`
- `observationSteps=60` (launcher proof window)
- `boardDropObservationSteps=300` (fixed additional board-drop window)

Required cases:

- `K-REST-STEADY`
- `K-SHORT-STEADY`
- `K-MEDIUM-STEADY`
- `K-FULL-STEADY`
- `K-RELAUNCH-MEDIUM`

No threshold, case-set, or schema relaxations allowed.

Frozen per-case obligations:

- `K-REST-STEADY`:
  - qualifying for full route/drop proof: `no`
  - required terminal expectations: no route chain required, `sw16_exit_observed=false`, `handoff_to_board_step=null`, `first_board_collision_step=null`

- `K-SHORT-STEADY`:
  - qualifying for full route/drop proof: `no`
  - required terminal expectations: route/drop phases not required, `handoff_to_board_step` and `first_board_collision_step` may remain `null`

- `K-MEDIUM-STEADY`:
  - qualifying for full route/drop proof: `yes`
  - required phase order includes: `route_overhead -> route_endpoint_bridge -> route_descent -> handoff_to_board -> board_drop_preimpact`
  - required outcomes: `sw16_exit_observed=true`, non-null `handoff_to_board_step`; `first_board_collision_step` may be non-null within board-drop budget

- `K-FULL-STEADY`:
  - qualifying for full route/drop proof: `yes`
  - required phase order includes: `route_overhead -> route_endpoint_bridge -> route_descent -> handoff_to_board -> board_drop_preimpact`
  - required outcomes: `sw16_exit_observed=true`, non-null `handoff_to_board_step`, non-null `first_board_collision_step` within board-drop budget

- `K-RELAUNCH-MEDIUM`:
  - qualifying for full route/drop proof: `yes`
  - required phase order includes full route/drop path for the second release window
  - required outcomes: at least one valid handoff/drop chain for relaunch phase, `sw16_exit_observed=true`

### Artifact contract

Primary output:

- `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`

Optional per-case detailed trace:

- `.artifacts/flunk-out-frenzy-launch-to-drop/traces/<case-id>.json`

Artifact must include:

- metadata (`generated_at_utc`, `repo_branch`, `engine_version_marker`)
- matrix summaries
- full step traces per case
- explicit `invariant_violations` list

Forbidden artifact behavior:

- missing phases silently omitted
- implicit route transitions without seam deltas
- synthetic `gate-passed` field aliases that bypass semantic event history

### Implementation plan

1. Add typed launch-to-drop trace models (physics + runtime debug surfaces).
2. Instrument launcher-chain and world transitions to emit per-step phase records.
3. Record route transition seam deltas (`xy`, `z`) at chain boundaries.
4. Capture board-handoff step and first board-impact step.
5. Expose trace capture through existing debug seam in a read-only way.
6. Add deterministic proof tests that assert:
   - required phase order for qualifying cases
   - distinct `swplunger`/`sw16` semantics
   - handoff occurs only after descent phase
   - first board-impact occurs only after handoff
   - no invariant violations in passing cases
7. Add retained artifact emission for matrix runs in test/debug flow.

### Test plan

- Focused regression commands:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run docs-validate`

- New required trace-proof checks:
  - matrix artifacts generated and schema-valid
  - each case has non-empty step records
  - qualifying hold cases include full route chain and board-drop phases
  - rest case does not synthesize `sw16` exit
  - no forbidden schema fields/aliases

### Live verification (required)

- URL:
  - `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Run executable telemetry-proof check and preserve artifacts:
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`
- Required live-proof artifact fields (machine-readable JSON):
  - `phase_order_observed`
  - `sw16_exit_observed`
  - `handoff_to_board_step`
  - `first_board_collision_step`
- Record in `.codex/handoff.md`:
  - exact command
  - artifact folder paths
  - summary of observed phase progression and `sw16` semantics

### Non-negotiable stop conditions

Do not mark complete if any remain true:

- trace contract cannot show full launch-to-drop phase sequence
- route chain phase order is ambiguous or missing for qualifying cases
- handoff and first board-impact steps are absent from traces
- `swplunger` and `sw16` semantics are conflated in artifacts/tests
- any seam tolerance/bridge contract is weakened
- focused verification or live evidence is not recorded in `.codex/handoff.md`

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
