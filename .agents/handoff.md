# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `docs/`.
## Snapshot
- Date: 2026-04-02
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0127`, `PR-0128`, `PR-0129`, `PR-0130`, `PR-0131`, `PR-0132`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`, `PR-0147`, `PR-0148`, `PR-0149`, `PR-0150`, `PR-0151`, `PR-0152`, `PR-0153`, `PR-0154`, `PR-0155`, `PR-0156`, `PR-0157`, `PR-0161`, `PR-0162`, `PR-0163`, `PR-0164`, `PR-0165`, `PR-0166`, `PR-0169`, `PR-0170`, `PR-0171`, `PR-0173`, `PR-0174`, `PR-0176`, `PR-0177`, `PR-0179`, `PR-0180`, `PR-0181`, `PR-0182`, `PR-0183`, `PR-0184`, `PR-0185`, `PR-0186`, `PR-0187`
## Status
- `ST-25-05` / `PR-0192` is now migrated onto the compiled pinball-table system locally: `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts` is the authored source of truth, `pinballTablePlanTypes.ts` and `compilePinballTable.ts` now produce the compiled physics/render plan, `prototypeAlphaTable.ts` exports that compiled table directly, `PhysicsWorld.ts` now builds the Rapier world from compiled bodies/colliders instead of the removed `createLaneDevices.ts` / `createTargetDevices.ts` path, and `staticBoardUnderlay.ts` now renders compiled render nodes instead of the removed authored-table primitives. The old authored-table stack (`authoredTableTypes.ts`, `boardGeometryPrimitives.ts`, `prototypeAlphaAuthoredTable.ts`, `compileAuthoredTable.ts`) is deleted. Post-review fixes are included: default serve spawns now honor compiled `launchVelocity`, and the compiler now rejects duplicate semantic device tags.
- `ST-25-06` / `PR-0198` are now in progress as the corrective donor-topology slice: `data/pinball_resources_and_repos/vpw-rom-example-table-donor-map.md` captures the borrowed VPW boundary grammar and source files, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorMap.ts` now carries donor drag-point chains for the outer boundary, inner guides, outlanes, inlanes, drain guides, shooter walls, sling faces, flipper proportions, and measured gate footprints, `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorDevices.ts` now carries donor-derived anchors for the visible rollovers, left drop bank, middle scoop marker, shooter exit, and drain footprint, and `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts` now consumes those donor carriers directly instead of mixing them with locally-authored lane-fill polygons or hand-placed device coordinates. `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/render/staticBoardUnderlay.ts` also dropped the hard-coded orbit sketch so the visible board is closer to the donor grammar. The donor corrective task was renumbered from `PR-0196` to `PR-0198` to avoid colliding with an existing `EPIC-29` PR id.
- `EPIC-31` is now proposed in `docs/backlog/epics/epic-31-flappy-birds-curated-app.md`, with the required pending review in `docs/backlog/reviews/review-epic-31-flappy-birds-curated-app.md`. The scope fixes `games.flappy_birds` as a real bespoke curated app from day one, keeps the browser-owned runtime plus backend-owned leaderboard split, and explicitly narrows highscores to a lightweight teacher-fun feature with simple server-owned leaderboard state.
- The older competitive-games planning family has now been rewritten around lightweight leaderboard support rather than heavyweight submission-promotion assumptions: `docs/adr/adr-0073-competitive-games-and-official-high-scores.md`, `docs/reference/ref-competitive-games-cross-cutting-programme.md`, `docs/reference/ref-curated-app-flunk-out-frenzy-architecture-and-foundational-code.md`, `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md`, `docs/backlog/reviews/review-epic-25-competitive-games-and-flunk-out-frenzy.md`, `docs/backlog/stories/story-25-02-flunk-out-frenzy-local-runtime-vertical-slice.md`, `docs/backlog/stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md`, `docs/backlog/stories/story-25-04-competitive-play-leaderboard-hardening-and-ruleset-scoping.md`, and `docs/backlog/stories/story-25-05-flunk-out-frenzy-mechanics-port-foundation.md`. `ST-25-04` was renamed from the old promotion framing to the new leaderboard-hardening/ruleset-scoping framing, and `docs/index.md` now points at the renamed story.
- `ST-25-05` / `PR-0190` are now implemented locally: `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.ts` is now an orchestrator over the new `ruleTypes.ts`, `scoreState.ts`, `bonusJackpotState.ts`, and `ballLifecycleState.ts` helpers; the runtime seam now carries nested `bonus`, `jackpot`, and `ballLifecycle` HUD state through `runtimeEngineTypes.ts`, `runtimeTypes.ts`, `GameRuntime.ts`, `GameHost.vue`, and `FlunkOutFrenzyView.vue`; `PrototypeAlphaGameEngine.ts`, `gameEffectTypes.ts`, `PixiRenderer.ts`, and `AudioDirector.ts` now surface semantic bonus/jackpot/shoot-again effects; and the post-review rollover exploit fix now gates rollover bonus accrual to newly lit lanes only, with a regression added in `RuleEngine.spec.ts`.
- The `PR-0190` review loop is now documented: the preflight `skriptoteket_reviewer` pass raised no actionable blockers on the planned split, the first post-implementation review found the duplicate-lit-rollover bonus exploit, `skriptoteket_implementation_specialist` fixed that narrow slice plus the regression test, and the final reviewer verdict for the post-fix diff is clean from the lead-review pass in this session.
- `ST-25-05` / `PR-0189` are now implemented locally: `tableDefinitionTypes.ts` owns the shared Flunk-Out Frenzy authored geometry contracts, `prototypeAlphaTable.ts` now includes grouped rollover metadata plus the first tripwire, gate, standup-target, and popup-target definitions, `createLaneDevices.ts` and `createTargetDevices.ts` build those authored devices into Rapier sensors/colliders, and the new events are surfaced through `PrototypeAlphaGameEngine.ts`, `gameEffectTypes.ts`, `PixiRenderer.ts`, and `AudioDirector.ts` so the device slice has end-to-end feedback without pulling rule complexity forward.
- `ST-25-05` / `PR-0188` are now implemented locally: `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts` now exposes the widened future-facing `MachineEvent` union, `colliderMeta.ts` and `machineEventEmitter.ts` own collider semantics and Rapier contact translation, and `PhysicsWorld.ts` is reduced to 420 lines so the world class is back to orchestration rather than inline event plumbing.
- `EPIC-25` now includes the next local gameplay-planning slice: `docs/backlog/stories/story-25-05-flunk-out-frenzy-mechanics-port-foundation.md` defines the post-vertical-slice mechanics-port foundation, anchored to the local `.artifacts/SpaceCadetPinball` donor analysis, and now treats `PR-0188` through `PR-0190` as the first gated tranche, `PR-0191` as the formal reassessment and go/no-go checkpoint, and `PR-0192` through `PR-0195` as the higher-risk physical-fidelity and advanced-device follow-on work.
- `ST-29-06` / `PR-0187` are now implemented locally: `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPayloadNormalization.ts`, `classroomPlannerStateSupport.ts`, `classroomPlannerLifecycle.ts`, `useClassroomPlannerRouteShell.ts`, and `classroomPlannerRouteShellErrors.ts` keep the planner boundary hardening for thin no-classroom payloads and suppress raw runtime/framework text; the canonical local `5173` repro is now known to use the backend-served static SPA bundle until `pdm run fe-build` realigns it; `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue` now renders the approved no-classroom empty-state copy in default `Planeringsvy` while keeping the planning eyebrow on the class name and reserving `Ej på karta` for `Klassrumsvy`; `scripts/playwright_pr_0185_rules_no_classroom_fallback_check.py` now proves that live header contract; and `.codex/agents/skriptoteket-reviewer.toml` now explicitly states that `skriptoteket_reviewer` is the sole reviewer and must not delegate.
- The sole-reviewer loop is now closed for `PR-0187`: the first `skriptoteket_reviewer` pass found a stale draft-save acknowledgement normalization gap in `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`, `skriptoteket_implementation_specialist` fixed that slice plus added coverage in `classroomPlannerStateSupport.spec.ts`, and the final sole-reviewer rerun returned no actionable findings.
- `main` and Hemma are now aligned through the post-`PR-0187` deploy: `ssh hemma 'cd ~/apps/skriptoteket && ./scripts/hemma_deploy_and_verify_seating_export.sh'` completed successfully, and stale dangling Docker images were pruned afterward on Hemma.
- Backlog reconciliation is now current for `EPIC-29`: `ST-29-01`, `ST-29-04`, `ST-29-05`, and `ST-29-10` are now written as done to match the shipped desktop-first planner behavior; `PR-0127`, `PR-0131`, `PR-0132`, `PR-0156`, `PR-0182`, `PR-0183`, and `PR-0184` are marked done; `PR-0158` is canceled as stale seating-first planning; and the remaining follow-on primitive/symbol lane is now isolated in `ST-29-11` and `ST-29-12`, with `ST-29-08` positioned as the later custom-tooltip enhancement on top of that baseline.
- `ST-29-11` now has an explicit three-slice execution path: `PR-0195` for shared primitive-contract normalization plus generic menu/split behavior, `PR-0196` for planner wrapper thinning and action-surface adapter cleanup, and `PR-0197` for editor/site adoption proof plus segmented-toggle contract completion.
## Verification
- 2026-04-02 `ST-25-05` / `PR-0192` compiled pinball-table migration:
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - independent `skriptoteket_reviewer` pass found two actionable `P2` issues in the first post-migration review: default serve spawns were not honoring compiled `launchVelocity`, and semantic tag uniqueness was not validated even though compiled ids are derived from those tags
  - one `skriptoteket_implementation_specialist` iteration fixed those two slices in `PhysicsWorld.ts` and `compilePinballTable.ts`
  - post-fix deterministic rerun on the merged state: `pdm run fe-type-check`, `pdm run fe-build`
  - no browser proof was run in this slice; the remaining honest visual risk is that `staticBoardUnderlay.ts` still keeps a decorative hard-coded top orbit glow outside the compiled render-node path
- 2026-04-02 `ST-25-06` / `PR-0198` VPW donor-topology corrective cutover:
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run docs-validate`
  - donor strictness pass: `prototypeAlphaVpwDonorMap.ts` now uses donor drag-point chains for wall/lane carriers, donor-derived sling faces, donor-measured flipper proportions, donor-measured shooter-lane bounds, and donor-measured right-return gate footprint; `prototypeAlphaVpwDonorDevices.ts` now ports the visible rollover, drop-target, scoop, shooter-exit, and drain anchors from donor objects; `prototypeAlphaTableSpec.ts` no longer overlays locally-authored lane `renderSurfaces` or hand-placed visible board devices, and `staticBoardUnderlay.ts` no longer draws the hard-coded orbit arc
  - post-fix deterministic reruns: `pdm run fe-type-check`, `pdm run fe-build`, then `pdm run fe-type-check`, `pdm run fe-build`, then `pdm run fe-type-check`, `pdm run fe-build`
  - attempted independent `skriptoteket_reviewer` passes and one fallback explorer review, but the subagents stalled without returning a verdict before shutdown; no review findings were captured from tooling in this session
  - manual browser inspection is intentionally pending user on `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- 2026-04-01 `EPIC-31` Flappy Birds curated-app epic and review scaffolding:
  - `pdm run docs-validate`
- 2026-04-01 competitive-games docs rewrite for lightweight leaderboard support:
  - `pdm run docs-validate`
- 2026-04-01 `ST-25-05` / `PR-0190` bonus, jackpot, and ball-lifecycle rule state:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.spec.ts src/components/apps/flunk-out-frenzy/game/rules/scoreState.spec.ts src/components/apps/flunk-out-frenzy/game/rules/bonusJackpotState.spec.ts src/components/apps/flunk-out-frenzy/game/rules/ballLifecycleState.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/GameHost.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts`
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
  - `pdm run fe-test -- --run src/views/apps/FlunkOutFrenzyView.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:8000` -> `playwright-flunk-out-frenzy: ok -> .artifacts/flunk-out-frenzy-route-check`
  - one-off `pdm run python - <<'PY' ... PY` live check against `http://127.0.0.1:5173/apps/games.flunk_out_frenzy` -> `playwright-flunk-out-frenzy-live-5173: ok -> .artifacts/flunk-out-frenzy-live-check`; it logged in via the bootstrap superuser, started the live route, verified jackpot light/award, shoot-again light/consume, and drained through the 3-ball loop to `game-over` using the dev-only `window.__FOF_DEBUG__` seam
- 2026-04-01 `ST-25-05` / `PR-0189` lanes, targets, and tripwire devices:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:8000` -> `playwright-flunk-out-frenzy: ok -> .artifacts/flunk-out-frenzy-route-check`
- 2026-04-01 `ST-25-05` / `PR-0188` machine-event and PhysicsWorld foundation:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:8000` -> `playwright-flunk-out-frenzy: ok -> .artifacts/flunk-out-frenzy-route-check`
- 2026-04-01 `EPIC-25` mechanics-port tranche gating update:
  - `pdm run docs-validate`
- 2026-04-01 `EPIC-25` mechanics-port backlog docs:
  - `pdm run docs-validate`
- 2026-04-01 `ST-29-06` / `PR-0187` no-classroom remediation:
  - local API payloads for the no-classroom path returned `200` for `workspace-summary`, `drafts/resolve`, `draft workspace`, and `smart-rules`, and focused diagnostics confirmed the canonical `5173` repro lands on the backend-served static SPA bundle from `:8000`, so `pdm run fe-build` is required before trusting the browser proof
  - `pdm run fe-test -- --run src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
  - `pdm run fe-test -- --run src/views/apps/classroomPlannerPayloadNormalization.spec.ts src/views/apps/classroomPlannerRouteShellErrors.spec.ts src/views/apps/classroomPlannerStateSupport.spec.ts src/views/apps/classroomPlannerRouteShellOverviewCrud.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run python -m scripts.playwright_pr_0185_rules_no_classroom_fallback_check --base-url http://127.0.0.1:5173` -> `playwright-pr-0185: ok`
  - `pdm run docs-validate`
  - live functional check on `http://127.0.0.1:5173/apps/classroom.group-seating-studio` via the real bootstrap-superuser browser flow now reaches `Regler` without raw JS text, shows the approved no-classroom empty-state copy in `Planeringsvy`, keeps the planning eyebrow on the class name, and leaves the off-map roster actionable
- 2026-04-01 `EPIC-29` backlog reconciliation:
  - `pdm run docs-validate`
- 2026-04-01 `ST-29-11` PR-slice planning:
  - `pdm run docs-validate`
## How to Run
```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173
ssh hemma 'cd ~/apps/skriptoteket && ./scripts/hemma_deploy_and_verify_seating_export.sh'
```
## Known Issues / Risks
- The donor corrective slice now uses donor drag-point carriers for the visible board boundary network plus donor-derived visible-device anchors; the remaining non-donor values in `prototypeAlphaTableSpec.ts` are mechanics-side tuning such as flipper swing angles, flipper contact impulse tuning, launcher charge/impulse values, and bumper sizing/impulses rather than visible lane or boundary coordinates.
- The canonical local browser proof for Klassrumskartan no-classroom flows depends on the backend-served static SPA bundle once auth redirects into `:8000`; rerun `pdm run fe-build` before trusting `http://127.0.0.1:5173` Playwright outcomes after frontend changes.
- The warnings-as-errors audit still surfaces a dependency-level Python 3.14 deprecation in `pytest-asyncio` (`asyncio.AbstractEventLoopPolicy`); repo-owned code is clean for the audited patterns, but the plugin likely needs a compatible bump.
- Keep the `7d4c1a2b9e6f` repair migration in mind if a long-lived local DB reports Alembic head but misses the roster smart-rule root contract.
- `tests/integration/test_migration_revision_coverage_idempotent.py` still has one pre-existing full-suite harness failure on merge revision `6a1e9d3c4b7f` because `tests/integration/migration_idempotency_support.py` assumes a linear `down_revision`; the new `b7f9c2d4e1a6` revision itself passes both targeted migration checks.
## Next Steps
- Do the manual browser read for `PR-0198` on the donor-backed compiled-table build and decide whether the next slice is still launcher/lane geometry cleanup inside `prototypeAlphaTableSpec.ts` or whether `PR-0193` can begin.
- Review `EPIC-31` / `REV-EPIC-31`, then scaffold the first `ST-31-0x` story stack for `games.flappy_birds` around substrate/bootstrap, local playable runtime, and lightweight leaderboard plumbing.
- `ST-25-05` remains in progress behind the donor corrective gate; do not continue `PR-0193` through `PR-0195` until the donor-backed board is accepted in the browser.
- Next planning choice inside `EPIC-29` is to implement `ST-29-11` in order through `PR-0195`, `PR-0196`, and `PR-0197`, then define the `ST-29-12` symbol/discoverability slice sequence before taking `ST-29-08`.
- If the no-classroom proof is rerun after more frontend changes, rebuild the backend-served SPA first with `pdm run fe-build`.
