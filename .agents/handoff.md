# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `docs/`.

## Snapshot

- Date: 2026-03-29
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`, `PR-0147`, `PR-0148`, `PR-0150`, `PR-0151`, `PR-0152`, `PR-0153`, `PR-0154`, `PR-0155`

## Status

- Hemma checkout is Git-aligned on current `main`, but the latest redeploy exposed a production web crash loop from removed FastAPI lifecycle APIs; `skriptoteket-worker` stays healthy, production seating-export smoke succeeded inside the worker image on the new local WeasyPrint path, and the exported PDF was pulled to `.artifacts/production-pdf-check/hemma-seating-export-smoke.pdf` for logo inspection.
- EPIC-26 export baseline is in place locally:
  - grouping + seating PDF rendering is local in Skriptoteket
  - grouping + seating XLSX delivery shipped
  - keep using host `dev-local` for real planner/export proof, not container logs alone
- Conversion Hub `PR-0148` is done locally:
  - local job ledger is authoritative at the product boundary
  - upstream Sir Convert job ids stay internal
  - live proof on `http://127.0.0.1:5173` passed with the real `wait_seconds <= 20` constraint
- Smart-assignment docs are approved and aligned across `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`, `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` through `story-27-06`, and `docs/backlog/prs/pr-0152-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md`.
- Smart-assignment docs are aligned for the current lane:
  - rerun diversity belongs to the core smart-run contract in `ADR-0074`, `ST-27-03`, `ST-27-04`, and `PR-0154`
  - `ST-27-05` now covers explanation/rerun messaging only
  - `PR-0155` is now implemented locally: `Regler` is the dedicated rules workspace, `Planeringskarta` / `Sittschema` share one authoring model, `Sittplatser` / `Grupper` keep compact summaries plus the small settings affordance near `Smart`, and `Närmare läraren` now has inspector edit/remove parity
- `ST-27-01` is done:
  - `PR-0147` reset the seating smart-rule contract to `seating_preferences[].near_teacher`
  - `PR-0149` delivered the visible seating smart-rule toolbar and V1 interaction model
- `PR-0151` is done:
  - smart rules are roster-global and persist through `/rosters/{roster_id}/smart-rules`
  - draft PATCH/workspace payloads now own only arrangement state, notes, toggles, and history
  - optimistic concurrency, split autosave-lane retry safety, hydration hardening, and late-response invalidation are in place
  - forward repair migration `7d4c1a2b9e6f_repair_roster_smart_rule_root_contract.py` fixes impossible local drift states
- `PR-0152` is done:
  - planner uses one session controller, one draft lane, one smart-rule lane, one smart-rule UI bucket, and explicit transition policies
  - route-shell workspace/export/exit flows use explicit transition APIs
  - `abandonDraft` is smart-lane-first, `exitPlanner` timeout returns confirm-discard, and `clearWorkspace()` is teardown-only
  - smart-rule hydration failure is lane-local with retry UI and no planner-wide save truth remains
- `PR-0152` follow-up SRP cleanup is also done locally:
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` is now 404 LoC and planner-private helpers now live in `classroomPlannerStatus.ts`, `classroomPlannerStateSupport.ts`, `classroomPlannerSmartRuleActions.ts`, and `classroomPlannerLifecycle.ts`
- `PR-0153` planner export-flow cleanup is also done locally:
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts` now owns the shared export state machine; `useSeatingExportFlow.ts` and `useGroupingExportFlow.ts` are each 126 LoC
- `PR-0154` smart seating implementation is now in place locally and live-proofed:
  - backend-owned smart seating ships through `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating.py`, `src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_seating.py`, and `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`
  - the checkpoint seam now reads the strict last-12 eligible history window for the same roster plus normalized room context
  - seating `Use history` persists draft-locally, and `Slumpa` now branches honestly between local random and backend smart run
  - `src/skriptoteket/domain/curated_apps/classroom_planner/seat_topology.py` now normalizes real room geometry into teacher-facing ranks, contiguous local zones, and spread-oriented seating blocks, and `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_scoring.py` now rotates `Närmare läraren` inside the valid teacher pool plus `Keep near` across compact row/column/diagonal relation modes
  - real-room simulation coverage replaced toy solver-outcome cases:
    - `tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py` covers `SA24D` / `G20` with `6` keep-apart, `2` keep-near, and `2` near-teacher rules
    - `tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver_bf25_g104.py` covers `BF25` / `G104`, including overlapping `Närmare läraren` + `Keep apart` membership for `Felix Persson`
  - live semantics proof now runs through `scripts/live_st_27_03_smart_seating_semantics_check.py`; on `2026-03-28` it passed on a fresh host backend at `http://127.0.0.1:8002` with 120 history-enabled reruns, 120 unique valid layouts, min distinct seat count `6`, a 12-seat valid teacher pool with 11 occupied seats, 10 distinct seats for each near-teacher student, and keep-near row/column/diagonal mode rotation
  - independent `skriptoteket_reviewer` found and the implementation fixed two follow-up issues:
    - route-level FastAPI contract coverage for smart-run `404` / `409` / `422`
    - strict last-12 checkpoint-history seam with no caller-configurable limit
  - final post-fix `skriptoteket_reviewer` rerun returned no actionable findings; residual risk is now limited to missing stress/property testing beyond the shipped real-room scenario suites
  - note: if the live semantics proof still reports the old tiny teacher pool or misses diagonal keep-near rotation, you are likely hitting a stale hot-reload backend on `:8000`; use a fresh host backend on `:8002` or similar for canonical semantics verification
- `PR-0150` is done:
  - seating export checkpoints persist through a dedicated backend seam with normalized seating snapshots and room-context hashes
  - unchanged exports dedupe by roster plus normalized room-context identity; template id is stored provenance, and copied seat/fixture ids, seat zones, and fixture labels do not fork identical room layouts into separate checkpoint lanes
  - checkpoint recording remains wired only to successful seating export completion; draft handlers do not depend on the checkpoint write seam
- `PR-0155` rules-workspace cut-over is now in place locally and live-proofed:
  - `Regler` is a top-level workspace, bootstraps an explicit seating host from the overview-selected classroom when needed, defaults to `Planeringskarta`, keeps the local `Planeringskarta` / `Sittschema` toggle in the map-field header, and leaves `Sittplatser` / `Grupper` with compact smart summaries plus the small settings affordance near `Smart`
  - the rules layout now uses a compact global tool rail plus a stable top summary panel for active rules, so the right-side inspector column is gone and the map lane can use most of the workspace width
  - active rule creation/edit confirmation lives in the tool rail for all rule kinds, `Nära läraren` now uses the same pending count/chip/save feedback as the relation rules while still persisting as one consolidated rule, and the top summary panel stays reserved for existing rules
  - the active-rule cards no longer show pointless totals, `Nära läraren` is the shorter workspace label, summary actions are now tiny icon controls, and map markers stay single-row instead of wrapping down across student names
- Planner UI-doctrine alignment is now documented for the upcoming overhaul:
  - added `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
  - tightened `.claude/skills/skriptoteket-frontend-specialist/SKILL.md`, `.claude/skills/brutalist-academic-ui/SKILL.md`, and `.agents/rules/045-huleedu-design-system.md` so future frontend work favors canvas-first, dense multi-workspace layouts over stacked panel chrome
  - doctrine now also states that workspace-heavy curated apps are desktop-first and that repeated operations should use a canonical symbol system before long text-button copy
- Proposed redesign planning package is now drafted: `EPIC-29`, `REV-EPIC-29`, and `ST-29-01`..`ST-29-08`; status is planning-only (`proposed` / `pending` / `ready`), with `ST-29-08` reserved as a post-core tooltip enhancement
- `PR-0157` dense-tool primitive implementation is now in progress locally:
  - canonical icons now include `IconAdjustments`, `IconPlus`, `IconZoomIn`, `IconZoomOut`, and `IconFitView`
  - shared SPA dense primitives now live under `frontend/apps/skriptoteket/src/components/ui/` (`UiDenseActionButton`, `UiDenseIconButton`, `UiDenseMenuButton`, `UiDenseSplitButton`, `UiDenseStatusPill`, `UiDenseToggle`, `UiDenseCompoundToggle`, `useDenseMenuSurface`, `denseToolPrimitives.ts`)
  - planner seating/grouping and editor toolbar/menu now read from that primitive layer, `Smart + Regler` is a compound control, editor AI undo/redo now use the canonical icon components, editor CRUD/status badges now use the shared dense status-pill contract, the shared `UiSegmentedToggle` now also carries the smaller secondary `subrail` treatment for local sort/view rails plus a taller `workspace` variant for equal-weight planner workspaces, now keeps one explicit column/divider per option instead of implicit multi-option wrapping, Klassrumskartan now reads repeated button recipes from shared `main.css` planner classes instead of scattered inline button styling, the planner shell/header chrome is quieter (`Curated App`, overview sales copy, panel-eyebrow labels, and visible `version N` shell text removed) with route hero vs active-workspace hierarchy encoded through shared `page-title` and `planner-shell-title` tiers, Mina filer no longer repeats the pointless `Filer` / `Aktiva filer och papperskorg` / `Sortera` / `Sök` chrome above controls, overview/pool/canvas surfaces are now denser with the duplicate overview resume CTA cards removed, shared overview panel tracks aligned, quieter overview footer actions, both gear-led overview edit buttons shortened to `Redigera`, and grouping cards now keep the rename field plus move/remove controls on one equal-height row with no redundant `Gruppnamn` label

## Verification

- 2026-03-27 `PR-0148` Conversion Hub:
  - `pdm run db-upgrade`
  - `pdm run pytest tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/web/conversion_hub/test_apps_conversion_hub_job_spec.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py`
  - `pdm run python -m scripts.check_migration_test_coverage`
  - `pdm run docs-validate`
  - live proof against `http://127.0.0.1:5173` via bootstrap-superuser API script; artifacts under `.artifacts/pr0148-live-check/`
- 2026-03-27 `PR-0151` roster-global smart rules:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rules.py tests/unit/web/apps/classroom_planner/test_smart_rules_api.py tests/unit/infrastructure/repositories/test_classroom_planner_smart_rules.py tests/unit/application/apps/classroom_planner/test_grouping_exports.py tests/unit/application/apps/classroom_planner/test_seating_exports.py tests/unit/web/test_startup_checks.py -q`
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run typecheck`
  - `pdm run db-upgrade`
  - `pdm run dev-db-upgrade`
  - live proof: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
- 2026-03-27 `PR-0152` planner session lanes:
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/usePlannerSessionController.spec.ts src/views/apps/useDraftPersistenceLane.spec.ts src/views/apps/useRosterSmartRuleLane.spec.ts src/views/apps/useSmartRuleUiState.spec.ts src/views/apps/plannerTransitionPolicies.spec.ts`
  - `pdm run fe-test -- --run src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run docs-validate`
  - live proof:
    - `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local`
    - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
    - artifacts under `.artifacts/classroom-planner-smoke`
- 2026-03-27 `PR-0152` follow-up SRP refactor:
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/usePlannerSessionController.spec.ts src/views/apps/useDraftPersistenceLane.spec.ts src/views/apps/useRosterSmartRuleLane.spec.ts src/views/apps/useSmartRuleUiState.spec.ts src/views/apps/plannerTransitionPolicies.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
  - `pdm run fe-type-check`
  - live proof: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
- 2026-03-27 `PR-0153` shared export-flow refactor:
  - `pdm run fe-test -- --run src/views/apps/useSeatingExportFlow.spec.ts src/views/apps/useGroupingExportFlow.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run docs-validate`
  - live proof: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
- 2026-03-27 `PR-0150` seating export checkpoints:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/ -q`
  - `pdm run pytest tests/unit/infrastructure/repositories/ -q`
  - `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[3e8b5c1a7d4f]' -q`
  - `pdm run docs-validate`
  - note: `pdm run pytest tests/integration/migration_schema_assertions.py -q` currently collects `0` tests because that module is a schema-assertion registry used by the docker idempotency runner, not a standalone pytest file
  - backend-only close-out; no planner UI/route smoke was required because no UI behavior changed in this session
- 2026-03-27 smart-assignment docs scope refinement:
  - `pdm run docs-validate`
  - updated `ADR-0074`, `EPIC-27`, `REV-EPIC-27`, `ST-27-03`, `ST-27-04`, `ST-27-05`, `PR-0154`, and the decision memo so smart reruns prefer different good candidates on repeated `Slumpa` runs and `ST-27-05` no longer adds a separate alternate-result control
- 2026-03-27 smart-assignment UI docs refinement:
  - `pdm run docs-validate`
  - updated `ADR-0074`, `EPIC-27`, `REV-EPIC-27`, `ST-27-03`, `ST-27-04`, `ST-27-05`, `PR-0154`, `docs/index.md`, and the decision memo
  - added `ST-27-07` plus `PR-0155` so `Regler` is the dedicated rule-editing workspace with
    `Planeringskarta` / `Sittschema`, while `Sittplatser` / `Grupper` keep compact summaries and a
    settings-link affordance near `Smart`
- 2026-03-28 `PR-0155` rules workspace cut-over:
  - `pdm run fe-test -- --run src/views/apps/useSmartRuleUiState.spec.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
  - `pdm run fe-type-check`; `pdm run docs-validate`
  - live proof: `pdm run python -m scripts.playwright_pr_0155_rules_workspace_check --base-url http://127.0.0.1:5173`
  - artifacts under `.artifacts/pr-0155-rules-workspace-check/`; proof covered top-level `Regler`, explicit overview-template bootstrap, the map-field `Planeringskarta`/`Sittschema` switch (and its absence from the rail), the unified rail-owned pending/create-save flow for all rule kinds, compact summary-only smart panes, wider map real estate, single-row map markers, and the removed rules helper copy
- 2026-03-28 auth-cutover planning package:
  - `pdm run docs-validate`
  - added `ADR-0076`, `EPIC-28`, `REV-EPIC-28`, `ST-28-01`..`ST-28-04`, and updated `docs/index.md`
- 2026-03-28 planner UI-doctrine alignment:
  - `pdm run docs-validate`
  - updated `docs/index.md`, `.agents/rules/045-huleedu-design-system.md`, `.claude/skills/skriptoteket-frontend-specialist/SKILL.md`, and `.claude/skills/brutalist-academic-ui/SKILL.md`
  - refined the doctrine around desktop-first workspace composition and symbol-first repeated operations
- 2026-03-28 planner redesign planning package:
  - `pdm run docs-validate`
  - `REV-EPIC-29` fixes landed: `EPIC-29` is the canonical UI-overhaul hub, `PR-0127`..`PR-0132` now hang under `ST-29-03`/`ST-29-04`, the conflicting EPIC-26 story docs were removed, `REF-shared-tool-control-language-v1` now defines the first minimal cross-app control matrix, and `ST-29-08` / `PR-0160` now reserve the custom tooltip enhancement as a separate post-core lane
- 2026-03-28 `PR-0157` dense-tool primitives:
  - `pdm run fe-type-check`
  - `pdm run fe-test -- --run src/components/ui/UiDenseStatusPill.spec.ts src/components/editor/EditorWorkspaceToolbar.spec.ts src/components/ui/UiDenseSplitButton.spec.ts src/components/ui/UiSegmentedToggle.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.export.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/CreateRosterModal.spec.ts`
  - `pdm run docs-validate`
  - live proof: `pdm run python -m scripts.playwright_pr_0157_dense_toolbar_check --base-url http://127.0.0.1:5173`, `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`, `pdm run python -m scripts.playwright_vault_sort_subrail_check --base-url http://127.0.0.1:5173`, `pdm run python -m scripts.playwright_pr_0157_overview_alignment_check --base-url http://127.0.0.1:5173`, and `pdm run python -m scripts.playwright_pr_0157_group_card_alignment_check --base-url http://127.0.0.1:5173`
  - artifacts under `.artifacts/pr-0157-live-check/`, `.artifacts/classroom-planner-smoke`, `.artifacts/vault-sort-subrail-check`, and `.artifacts/pr-0157-overview-alignment-check`; proof covered planner seating/grouping dense-tool follow-ups, the planner-wide shared button-recipe sweep in modals/drawers/overview/template-editor surfaces, grouped undo/redo outer-edge `4px` corners, compact overflow, grouping count stepper, the updated grouping smoke selector for `Nytt utkast`, the quieter planner shell/header typography and chrome, the shared secondary subrail treatment across the rules map switch and Vault sort, the taller dedicated workspace mode selector for Klassrumskartan, the restored interior dividers between all segmented options, and the denser overview/student-pool/canvas surfaces without duplicate overview resume cards, with live-aligned overview panels, quieter footer actions, Vault sort/search height parity, and the shortened `Redigera` gear actions
- 2026-03-27 `PR-0154` smart seating:
  - backend semantics alignment verified with domain/application/web/repository pytest lanes plus `pdm run typecheck` and `pdm run docs-validate`
  - live proof against a fresh host backend: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run uvicorn --app-dir src skriptoteket.web.app:app --reload --host 127.0.0.1 --port 8002` and `pdm run python -m scripts.live_st_27_03_smart_seating_semantics_check --base-url http://127.0.0.1:8002 --runs 120`
  - artifacts under `.artifacts/st-27-03-smart-seating-semantics/summary.json`
- 2026-03-29 compatibility sweep:
  - `pdm run pytest tests/test_smoke.py tests/test_openapi_contracts.py tests/unit/web/test_startup_checks.py`
  - `PYTHONPATH=src pdm run python -c "from skriptoteket.web.app import create_app; app=create_app(); print(app.title); print(bool(app.openapi().get('info', {}).get('title')))"`
  - `pdm run fe-type-check`; `pdm run docs-validate`
  - live proof: `curl -sf http://127.0.0.1:8000/healthz` and `curl -I -sf http://127.0.0.1:5173/apps/classroom.group-seating-studio`

## How to Run
```bash
# Local dev
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Planner smoke
pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173

# Planner import browser proof
pdm run python -m scripts.playwright_pr_0137_class_list_import_check --base-url http://127.0.0.1:5173

# Hemma export deploy/readiness gate
ssh hemma 'cd ~/apps/skriptoteket && ./scripts/hemma_deploy_and_verify_seating_export.sh'
```

## Known Issues / Risks

- Hemma is on `c1993966` and the seating-export deploy gate passes, but the web container is still unhealthy because `/healthz` fails inside the repo-owned Dishka/FastAPI hybrid compat path with `KeyError: '___dishka_websocket'`.
- The warnings-as-errors audit still surfaces a dependency-level Python 3.14 deprecation in `pytest-asyncio` (`asyncio.AbstractEventLoopPolicy`); repo-owned code is clean for the audited patterns, but the plugin likely needs a compatible bump.
- Keep the `7d4c1a2b9e6f` repair migration in mind if a long-lived local DB reports Alembic head but misses the roster smart-rule root contract.
- Smart-assignment sequencing is still strict:
  - `ST-27-04` should build on the shipped `PR-0150` geometry-based checkpoint registry, the `PR-0152` session/lane split, and the new `PR-0154` smart seating run seam, not on older planner-wide save assumptions

## Next Steps

- Take `ST-07-07` next before more feature work: `PR-0162`..`PR-0164` now define the correct global fix for retiring `src/skriptoteket/web/dishka_compat.py`, moving HTTP DI onto FastAPI `Depends` + `request.state.dishka_container`, handling websockets explicitly, and re-proving Hemma health on the locked runtime.
- After the production DI cutover is healthy again, resume the planner lanes in order: `ST-29-02` shell compression, then the remaining `ST-29-*` workspace overhaul slices, while keeping the earlier smart-assignment/rules contracts intact.
