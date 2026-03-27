# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `docs/`.

## Snapshot

- Date: 2026-03-27
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`, `PR-0147`, `PR-0148`, `PR-0151`, `PR-0152`, `PR-0153`

## Status

- Hemma is clean and Git-aligned; `sir_convert_a_lot_prod`, `skriptoteket-web`, and `skriptoteket-worker` are healthy.
- EPIC-26 export baseline is in place locally:
  - grouping + seating PDF rendering is local in Skriptoteket
  - grouping + seating XLSX delivery shipped
  - keep using host `dev-local` for real planner/export proof, not container logs alone
- Conversion Hub `PR-0148` is done locally:
  - local job ledger is authoritative at the product boundary
  - upstream Sir Convert job ids stay internal
  - live proof on `http://127.0.0.1:5173` passed with the real `wait_seconds <= 20` constraint
- Smart-assignment docs are approved and aligned across `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`, `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` through `story-27-06`, and `docs/backlog/prs/pr-0152-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md`.
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
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` is now 404 LoC
  - new planner-private support modules:
    - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStatus.ts`
    - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`
    - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts`
    - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerLifecycle.ts`
- `PR-0153` planner export-flow cleanup is also done locally:
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts` now owns the shared export state machine
  - `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts` is now 126 LoC
  - `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts` is now 126 LoC
- Current frontend god-file hotspots after the export-flow cleanup:
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
  - `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
  - then editor/vault/profile hotspots outside the planner lane

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

- Host dev export smoke now matches the local Klassrumskartan PDF boundary, but keep using the host `dev-local` lane because container-only logs can hide real planner/export failures.
- `pdm.lock` still has local, uncommitted follow-up changes after the `pdfplumber` runtime fix; do not lose or silently overwrite that diff.
- Keep the `7d4c1a2b9e6f` repair migration in mind if a long-lived local DB reports Alembic head but misses the roster smart-rule root contract.
- Smart-assignment sequencing is still strict:
  - `PR-0150` / `ST-27-02` remains next
  - `ST-27-03` / `ST-27-04` should build on the shipped `PR-0152` session/lane split, not on older planner-wide save assumptions

## Next Steps

- Continue the smart-assignment lane in the corrected order:
  - execute `PR-0150` next for seating checkpoint registry + normalized assignment-hash dedupe under `ST-27-02`
  - then continue with `ST-27-03` / `ST-27-04` on top of the shipped `PR-0152` session-controller + lane split
  - keep relation rules as non-overlapping visible clusters in V1 and keep smart controls near workspace/top-panel surfaces; do not add a global smart-settings drawer
- If cleanup continues before new feature work, start with:
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
  - `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
