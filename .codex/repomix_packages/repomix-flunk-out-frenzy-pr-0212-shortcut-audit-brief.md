# Repomix Brief: PR-0212 Launcher Shortcut Breach Inventory and Truth-Gate Audit

## Package

- XML: `.agents/repomix_packages/repomix-flunk-out-frenzy-pr-0212-shortcut-audit-review.xml`
- Include list: `.agents/repomix_packages/repomix-flunk-out-frenzy-pr-0212-shortcut-audit-files.txt`

## Purpose

Enable an external offline reviewer to audit:

1. exact launcher shortcut/policy-breach evidence,
2. proof-layer inference vs direct-observation gaps,
3. current test-gate truth coverage vs false-green risk,
4. declared dishonest/not-yet-validated gameplay scope.

## Primary governing docs (read first)

1. `docs/backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md`
2. `docs/backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md`
3. `AGENTS.md`
4. `.agents/rules/000-rule-index.md`
5. `.agents/rules/070-testing-standards.md`
6. `.agents/rules/075-browser-automation.md`
7. `.agents/rules/096-review-workflow.md`

## Core implementation evidence

- Launcher seam/runtime:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
- Authoring/compiler seam contracts:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorMap.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorDevices.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.ts`

## Proof + observability evidence

- Focused specs:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
- Playwright live-trace tooling:
  - `scripts/playwright_flunk_out_frenzy_launch_trace_check.py`
  - `scripts/playwright_flunk_out_frenzy_route_check.py`
  - `scripts/_playwright_flunk_out_frenzy.py`
  - `scripts/_playwright_browser.py`
  - `scripts/_playwright_config.py`
- Trace artifacts:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
  - `frontend/apps/skriptoteket/.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`

## Reviewer note

The package intentionally includes both live and focused-trace artifacts because `PR-0212` requires evaluating where matrix pass-state depends on direct observations vs inferred/reconstructed markers.
