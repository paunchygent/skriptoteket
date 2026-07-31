---
type: task
id: TASK-SKRIPT-25-06-13
title: 'Flunk-Out Frenzy: launcher shortcut breach inventory and truth-gate audit'
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
- Given no-shortcuts is a hard rule, when this task is complete, then the launcher
  shortcut inventory is explicit, evidence-locked, and file-referenced with exact
  path:line anchors.
- Given policy compliance is currently disputed, when this task is complete, then
  each shortcut/cheat is classified by violation type, failure mode, and scope impact
  (runtime, proof layer, or both).
- Given current tests should assume board-mechanics truth, when this task is complete,
  then every focused gate is mapped to what it proves, what it does not prove, and
  where false-green risk exists.
- Given gameplay-fidelity claims are currently overstated, when this task is complete,
  then the exact dishonest/not-yet-validated gameplay segments are declared explicitly.
- Given root-cause claims must be non-speculative, when this task is complete, then
  probable failed assumptions are listed as hypotheses tied to evidence, not treated
  as facts.
- Given governance requires independent scrutiny, when this task is complete, then
  a full ruthless review/audit document is produced and approved before any further
  production launcher behavior edits.
- Given this is an audit gate, when this task is complete, then no production geometry/runtime
  behavior changes are merged in this PR.
---

## Context

The source does not provide a separate context section; no additional context is recorded.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Story Contract Slice

### Source: Goal

Create an explicit, reviewable breach inventory and truth-gate audit so the team can separate:

1. hard evidence,
2. bounded heuristics that are declared and acceptable,
3. hidden shortcuts/cheats that invalidate gameplay-fidelity claims.

## Contract Inputs

### Source: Hard definitions and invariants

1. `truthy-mechanics evidence`
   A claim is truthy only if it is directly observed from runtime state/events without reconstruction or post-hoc phase insertion.
2. `shortcut`
   Any runtime or proof behavior that replaces physical causal flow with forced state transitions, teleportation, synthetic speed floors, or inferred events/phases.
3. `dishonest gameplay claim`
   Any claim that says a seam is physically validated while the proving path depends on shortcuts.
4. `policy invariant`
   `no-shortcuts`, strict seam contract, donor-authored seam continuity, and explicit `swplunger` vs `sw16` semantics.

## Plan

The source does not provide a separate plan section; no additional plan is recorded.

## Implementation Steps

The source does not provide a separate implementation steps section; no additional implementation steps is recorded.

## Proof

### Source: Evidence-locked shortcut and policy-violation inventory



### Source: Accessible output evidence snapshot (2026-04-04)

- Source artifact A (live Playwright trace run):
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
  - file timestamp/size observed: `2026-04-04 01:52` / `3,002,423 bytes`
  - metadata:
    - `generated_at_utc=2026-04-03T23:52:27.696954+00:00`
    - `engine_version_marker=pr-0209-launch-to-drop-trace`
- Source artifact B (focused test-run artifact):
  - `frontend/apps/skriptoteket/.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
  - file timestamp/size observed: `2026-04-04 00:36` / `2,899,872 bytes`
- Artifact A matrix summary extraction (`case_id | hold_profile | sw16_exit_observed | handoff_to_board_step | first_board_collision_step | invariant_violations_count`):
  - `K-REST-STEADY | rest | false | null | null | 0`
  - `K-SHORT-STEADY | short | true | 512 | 513 | 0`
  - `K-MEDIUM-STEADY | medium | true | 782 | 783 | 0`
  - `K-FULL-STEADY | full | true | 1232 | 1233 | 0`
  - `K-RELAUNCH-MEDIUM | relaunch | true | 782 | 783 | 0`
- Artifact A direct transition-event extraction (`case_id | gate-passed(sw16) event count in raw trace steps | any sensors.lastSw16ExitStep marker`):
  - `K-REST-STEADY | 0 | false`
  - `K-SHORT-STEADY | 0 | true`
  - `K-MEDIUM-STEADY | 0 | true`
  - `K-FULL-STEADY | 0 | true`
  - `K-RELAUNCH-MEDIUM | 0 | true`
- Artifact A raw shape/cadence inspection (`K-MEDIUM-STEADY` representative facts from raw trace rows):
  - raw row keys are camelCase (`stepIndex`, `dtMs`, `seamTransition`, `handoffToBoardStep`)
  - sampled raw rows report `dtMs=8.333333333333334`
  - no sampled raw row exposed `phase=route_endpoint_bridge`
  - no sampled raw row exposed non-null `seamTransition`
- Artifact B matrix summary extraction:
  - `K-REST-STEADY | rest | false | null | null | 0`
  - `K-SHORT-STEADY | short | true | 87 | null | 0`
  - `K-MEDIUM-STEADY | medium | true | 149 | 150 | 0`
  - `K-FULL-STEADY | full | true | 173 | 174 | 0`
  - `K-RELAUNCH-MEDIUM | relaunch | true | 149 | 150 | 0`
- Artifact B raw shape/cadence inspection (`K-MEDIUM-STEADY` representative facts from raw trace rows):
  - raw row keys are snake_case (`step_index`, `dt_ms`, `seam_transition`, `handoff_to_board_step`)
  - raw rows report `dt_ms=16`
  - direct `phase=route_endpoint_bridge` row present
  - direct non-null `seam_transition` rows present:
    - `overhead -> endpoint-bridge`
    - `endpoint-bridge -> descent`
- Latest focused verification outputs recorded in `.codex/handoff.md` for the same lane:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts` -> `pass`
  - `pdm run fe-type-check` -> `pass`
  - `pdm run fe-build` -> `pass`
  - `pdm run docs-validate` -> `pass`
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop` -> `ok` (artifact generated)
- Audit relevance of this evidence:
  - Green matrix summaries coexist with zero direct `gate-passed(sw16)` raw-trace events in artifact A.
  - `sw16_exit_observed=true` is still satisfied via durable sensor marker (`lastSw16ExitStep`) even when direct event sampling is absent.
  - Artifact A (live) is a weaker, translated proof surface than artifact B (focused runtime): its raw rows are camelCase, report `dtMs=8.333333333333334`, and did not directly expose the `route_endpoint_bridge`/`seamTransition` evidence that artifact B exposes directly.
  - Because of that mismatch, artifact A and artifact B must not be treated as contract-equivalent evidence for PR-0209 seam proof.
  - This is exactly why `PR-0212` treats proof-layer inference/reconstruction as an explicit truth-gate risk, not a hidden implementation detail.

### Source: Current gate-truth matrix

| Gate | Directly proven behavior | Explicitly not proven | False-green risk | Key evidence anchors |
| --- | --- | --- | --- | --- |
| `compilePinballTable.spec.ts` | Donor `swplunger` vs `sw16` separation, authored route topology, strict seam continuity, and terminal-only handoff contract. | Runtime strike energy transfer, live event observation, or free-simulation corridor truth. | Compile green can be mistaken for gameplay-fidelity approval. | `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts:75`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts:101`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts:542`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts:600`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts:625` |
| `plungerLaneState.spec.ts` | Launcher feed/charge/release/relaunch state sequencing before Rapier motion applies. | Whether the released charge produces physically honest plunger contact or route-entry continuity. | State-machine green can be over-read as proof of physical launch honesty. | `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts:28`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts:64` |
| `PhysicsWorld.launcher.spec.ts` | Runtime launcher emits feed/charge events, keeps the served ball inside the shooter lane, blocks synthetic `sw16` before accepted route capture, and records a deterministic launch-to-drop artifact. | That accepted route speed came from truthful contact transfer rather than speed promotion/flooring; that every reported phase was directly observed in live cadence. | Runtime green can still coexist with kinematic route steering and artifact-level inference. | `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts:531`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts:571`, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts:601` |
| `playwright_flunk_out_frenzy_launch_trace_check.py` | Live browser execution can sample matrix cases, retain artifacts, and enforce PR-0209 invariant checks on the produced summaries. | That `sw16_exit_observed`, `route_endpoint_bridge`, `handoff_to_board`, and `board_drop_preimpact` always came from direct observation rather than reconstruction; that the live artifact exposes the same per-step seam fields/cadence as the focused artifact. | A fully green live matrix can still hide proof-layer inference because the script inserts/derives missing truthy markers, and the live artifact currently overstates parity with the focused artifact on `route_endpoint_bridge`, `seamTransition`, and `dt_ms`. | `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:256`, `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:262`, `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:269`, `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:275`, `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:288`, `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:295`, `docs/backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md:82` |
| `pdm run fe-type-check` | Typed surface consistency for the current frontend/runtime/test contracts. | Any behavioral truth about physics, seams, or live launcher fidelity. | Type safety can be mistaken for proof completeness. | Build-system gate only; no direct mechanics evidence. |
| `pdm run fe-build` | Production bundle integrity for the current SPA/frontend code. | Any runtime-causal truth about launcher mechanics or proof honesty. | Successful bundling can mask dishonest physics claims. | Build-system gate only; no direct mechanics evidence. |
| `pdm run docs-validate` | Docs-as-code contract compliance for the planning/audit artifacts. | Whether the audit claims themselves are correct in runtime terms. | A valid document can still contain a bad or incomplete audit. | Planning gate only; no direct mechanics evidence. |

### Source: Verification plan

- `pdm run docs-validate`
- Reviewer sign-off recorded in the `PR-0212` supplemental section inside `review-epic-25-competitive-games-and-flunk-out-frenzy.md`.

## Validation

The source does not provide a separate validation section; no additional validation is recorded.

## Stop Conditions

### Source: Non-goals

- No geometry edits.
- No launcher runtime behavior edits.
- No seam tolerance changes.
- No test-threshold relaxation.
- No artifact schema softening.

### Source: Rollback plan

- Revert the audit-planning updates only; do not treat rollback as permission to reopen launcher behavior work without an explicit approved supplemental review verdict.

## Lessons Learned

The source does not provide a separate lessons learned section; no additional lessons learned is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: Problem

Current launcher artifacts can pass focused gates while still masking non-physical seams and inference-heavy proof behavior. The unresolved risk is not only one bug; it is trust drift between what tests claim and what gameplay actually proves.

### Source: A. Route-speed amplification detached from measured contact outcome

- Evidence:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:512`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:514`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:39`
- Nature of violation:
  - Route capture can promote speed by `max(measuredSpeed, resolvedChargeSpeed)` and then apply a hard route-speed floor (`Math.max(releaseSpeed * 0.85, 850)`), which can dominate observed plunger-contact velocity.
- Why this is a policy breach:
  - It can make downstream route behavior appear physically valid even when plunger-strike transfer was weak.
- Test-gate impact:
  - Qualifying-route assertions can go green while plunger-to-route energy continuity is still not truthy.

### Source: B. Kinematic route transport that bypasses free simulation of that segment

- Evidence:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:530`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts:531`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:135`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:136`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:167`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts:168`
- Nature of violation:
  - Route attachment and route progression use direct `setTranslation(...)`/`setLinvel(...)` writes at attach, per-step route sample, and chain seam transitions.
- Why this is a policy breach:
  - This can hide seam-physics truth in that corridor by replacing free physical evolution with deterministic steering.
- Test-gate impact:
  - Route-order checks can pass even if the same seam would fail under fully physical traversal.

### Source: C. Live trace proof-layer event/phase inference instead of strict direct observation

- Evidence:
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:262`
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:269`
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:275`
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:278`
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:288`
- Nature of violation:
  - `sw16_exit_observed` can be inferred from `lastSw16ExitStep`, and missing phases can be inserted (`route_endpoint_bridge`, `handoff_to_board`, `board_drop_preimpact`) when direct observation is incomplete.
- Why this is a policy breach:
  - Live proof can become reconstruction-first instead of observation-first, which undermines trust in reported sequence truth.
- Test-gate impact:
  - Live matrix artifacts can report a complete chain without sampling each transition directly.

### Source: E. Live artifact summary can overstate per-step seam proof

- Evidence:
  - `docs/backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md:82`
  - `docs/backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md:97`
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:269`
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py:275`
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json` (`K-MEDIUM-STEADY` raw trace inspected: no `route_endpoint_bridge` rows, no non-null `seamTransition`, raw `dtMs=8.333333333333334`)
  - `frontend/apps/skriptoteket/.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json` (`K-MEDIUM-STEADY` raw trace inspected: direct `route_endpoint_bridge`, non-null `seam_transition`, raw `dt_ms=16`)
- Nature of violation:
  - The live Playwright artifact summary can satisfy the required phase chain by reconstruction even when the raw live trace does not expose the per-step `route_endpoint_bridge` or `seam_transition` evidence that `PR-0209` requires.
- Why this is a policy breach:
  - This is a stronger false-green mode than generic inference alone: the summary can look PR-0209-complete while the raw live artifact remains weaker than the focused artifact on the exact seam-proof fields the contract calls out.
- Test-gate impact:
  - Reviewers can over-credit live proof as contract-equivalent to the focused runtime artifact when it currently is not.

### Source: D. Bounded synthetic board handoff contract (declared heuristic, not hidden)

- Evidence:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts:304`
- Nature of behavior:
  - Terminal descent route still declares explicit `handoffVelocity`.
- Status:
  - This is acceptable only if explicitly documented as a bounded seam contract and never represented as full physical continuity.
- Risk if undocumented:
  - Teams can misread speed jumps as validated physics rather than declared handoff contract behavior.

### Source: Shortcut classification matrix

| ID | Violation type | Failure mode | Scope impact | Evidence-locked audit conclusion |
| --- | --- | --- | --- | --- |
| A | Runtime shortcut | Route speed can be promoted from inferred charge and then floored independent of observed contact outcome. | Runtime and proof layer | A green route outcome does not by itself prove strike-to-route energy continuity. |
| B | Runtime shortcut | Route travel is advanced by direct body writes instead of free simulation across the route corridor. | Runtime and proof layer | Route order can look deterministic while corridor physics truth remains unproven. |
| C | Proof-layer shortcut | The live trace script upgrades markers into `sw16_exit_observed` and inserts missing phases post hoc. | Proof layer | The artifact can read as a complete causal chain even when direct observation is incomplete. |
| D | Declared bounded heuristic | Terminal descent uses explicit `handoffVelocity` rather than claiming full physical continuity into board space. | Runtime only, acceptable when declared | This is not a hidden cheat if treated as a terminal seam contract and never overstated as full physics. |
| E | Proof-layer shortcut | The live artifact summary can appear PR-0209-complete even when raw live rows do not expose `route_endpoint_bridge`, `seamTransition`, or matching `dt_ms` cadence/shape. | Proof layer | Live and focused artifacts are not currently contract-equivalent proof surfaces and must not be treated as such. |

### Source: Secondary corroborating gates

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts:191`
  proves pointer hold/release maps to launch commands, but it does not prove gameplay overlays/focus states in the live app are transparent.
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts:228`
  proves blur clears stuck launch input, but it does not prove the launcher seam is physically honest.
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts:651`
  proves runtime debug telemetry exposes launch proof records without legacy aliases such as `gate-passed`, but it does not prove live trace observations are inference-free.

### Source: Dishonest/not-yet-validated gameplay declaration (must be explicit)

Until this task is closed, these segments are non-truthy:

1. Plunger-strike energy continuity into captured route speed.
2. Live direct observation of ephemeral transition events/phases at full matrix cadence.
3. Claim that qualifying-route success alone proves full seam physical fidelity.

These segments remain truthy:

1. Compiler-level seam contracts (`xy<=1`, `z<=1`, terminal-only handoff, cycle checks, feed/exit uniqueness).
2. Distinct authored semantics of `swplunger` and `sw16` at definition level.

### Source: Most probable failed assumptions to audit (hypotheses, not conclusions)

1. Deterministic route steering was treated as equivalent to physical seam proof.
2. Post-hoc phase reconstruction was treated as acceptable live-proof evidence.
3. Speed-floor heuristics were treated as harmless stabilization rather than fidelity debt.
4. Green focused gates were over-interpreted beyond their actual proof surface.

### Source: Required ruthless review and audit deliverables

1. Record the audit verdict in the existing epic review artifact:
   - `docs/backlog/reviews/review-epic-25-competitive-games-and-flunk-out-frenzy.md`
   - use a dedicated supplemental section titled `PR-0212 Launcher Shortcut Breach Inventory and Truth-Gate Audit`
   - do **not** create `review-pr-0212-...`; `docs/_meta/docs-contract.yaml` only permits `review-epic-XX-...` review files
2. Reviewer must enumerate findings by severity with exact `path:line` evidence.
3. Reviewer must produce a gate-truth matrix:
   - `gate`
   - `directly proven behavior`
   - `inferred behavior`
   - `false-green risk`
   - `required remediation`
4. Reviewer must explicitly approve/reject each of:
   - breach inventory completeness
   - dishonest-gameplay declaration accuracy
   - root-cause hypothesis framing quality (non-speculative discipline)
5. No production launcher behavior changes may start before this review status is `approved`.

### Source: Implementation plan (bounded)

1. Author and freeze this breach inventory task (`PR-0212`).
2. Add a pending `PR-0212` supplemental review record under `review-epic-25-competitive-games-and-flunk-out-frenzy.md`, then move that supplemental verdict to `approved` only after independent review.
3. Convert approved audit findings into the next bounded proof-first implementation PR (separate slice).

### Source: Non-negotiable stop conditions

Do not mark this slice complete if any remain true:

- any shortcut listed above remains undocumented or unclassified,
- gate-truth matrix does not separate direct evidence from inference,
- dishonest gameplay declaration is missing or vague,
- independent ruthless review is missing or not approved.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Implementation Review

The source does not provide a separate implementation review section; no additional implementation review is recorded.
