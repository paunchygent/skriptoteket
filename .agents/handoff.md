# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `docs/`.
## Snapshot
- Date: 2026-03-30
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`, `PR-0147`, `PR-0148`, `PR-0150`, `PR-0151`, `PR-0152`, `PR-0153`, `PR-0154`, `PR-0155`, `PR-0157`, `PR-0161`, `PR-0162`, `PR-0163`, `PR-0164`, `PR-0165`, `PR-0166`, `PR-0169`, `PR-0170`, `PR-0171`
## Status
- `ST-07-07` is now shipped locally and live on Hemma: `src/skriptoteket/web/dishka_compat.py` is removed, HTTP DI now resolves through `request.state.dishka_container`, websocket resolution is explicit via `src/skriptoteket/web/dishka_dependencies.py`, `skriptoteket_reviewer` approved the final tree with no actionable findings, and Hemma `skriptoteket-web` / `skriptoteket-worker` are healthy again after the `2026-03-29` seating-export deploy gate.
- Hemma is now back on the current published `main` commit with a clean `git status --short`; the canonical deploy gate now fast-forwards a clean checkout to `origin/main` before it rebuilds.
- `ST-09-06` / `PR-0169` are done:
  - `src/skriptoteket/config.py` and `src/skriptoteket/infrastructure/curated_apps/registry.py` now apply a production-only curated app allowlist; `demo.counter` and `games.flunk_out_frenzy` are hidden in production while approved apps such as `classroom.group-seating-studio` still resolve
- `ST-09-07` / `PR-0170` are done and live on Hemma:
  - `src/skriptoteket/config.py`, `src/skriptoteket/web/request_metadata.py`, `src/skriptoteket/web/api/v1/auth.py`, `src/skriptoteket/observability/health.py`, `src/skriptoteket/observability/metrics.py`, `src/skriptoteket/web/routes/observability.py`, and `compose.prod.yaml` now fail closed on the confirmed March 29 public-edge findings
  - production defaults now keep `/docs` and `/openapi.json` off, public `/healthz` minimal, identity/session gauges off in `/metrics`, and trusted client IP parsing limited to explicitly trusted proxies; Docker-based local dev login via `http://127.0.0.1:5174` works again because `skriptoteket_web` is allowed only outside production
  - independent `skriptoteket_reviewer` approved the final code slice with no actionable findings after one `skriptoteket_implementation_specialist` follow-up iteration
- `ST-09-08` / `PR-0171` are done and live on Hemma:
  - `~/apps/skriptoteket/.env` now sets exact proxy trust for the current nginx-proxy (`TRUSTED_PROXY_CIDRS=172.18.0.5/32`), keeps public `/healthz` minimal, keeps identity/session gauges off in `/metrics`, and nginx now returns `403` for public `/metrics`
  - `hule.education`, `api.hule.education`, and `ws.hule.education` are claimed by the explicit placeholder instead of falling through to Skriptoteket, and Hemma fast-forwarded to published `main`, rebuilt `skriptoteket-web` / `skriptoteket-worker`, and upgraded the production DB to Alembic head `5a7c1d9e3b2f`
- EPIC-02 local password reset is now implemented locally against the approved docs slice:
  - backend adds `password_reset_tokens`, hashed token lookup, normalized-email cooldowns, explicit `forgot-password`/`reset-password` contracts, and bulk session revocation through `src/skriptoteket/application/identity/handlers/request_password_reset.py`, `src/skriptoteket/application/identity/handlers/reset_password.py`, `src/skriptoteket/infrastructure/repositories/password_reset_token_repository.py`, `src/skriptoteket/infrastructure/repositories/session_repository.py`, `src/skriptoteket/web/api/v1/auth.py`, and `migrations/versions/8f3d2c1b4a6e_add_password_reset_tokens.py`; frontend adds `/forgot-password` and `/reset-password`, fixes post-register auth drift, and exposes the login-modal recovery entry point through `frontend/apps/skriptoteket/src/views/ForgotPasswordView.vue`, `frontend/apps/skriptoteket/src/views/ResetPasswordView.vue`, `frontend/apps/skriptoteket/src/components/auth/LoginModal.vue`, `frontend/apps/skriptoteket/src/stores/auth.ts`, and regenerated `frontend/apps/skriptoteket/src/api/openapi.d.ts`
  - runtime note: the local Docker `web` service briefly looked broken after migration because `uvicorn --reload` plus bind-mounted polling kept reloading on host-side file mtime churn; the DB itself was current at `8f3d2c1b4a6e`, and the service settled healthy once file changes stopped
- Smart-assignment docs are approved and aligned across `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`, `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` through `story-27-06`, and `docs/backlog/prs/pr-0167-st-27-04-smart-grouping-v1-grouping-history-and-live-seating-influence.md`.
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
- Same-shell transition continuity is now active and partially shipped: `ADR-0077` is accepted, `REV-EPIC-30` is approved, `EPIC-30` is active, `ST-30-01` / `PR-0165` are done, and `ST-30-02` / `PR-0166` now ship the editor/rules-map/tool-file-picker/Vault adoption plus the adjacent route/topbar/profile transition audit
- `PR-0161` / `ST-29-02` shell-compression follow-up is now implemented locally:
  - grouping/seating keep detached sticky toolbars above the live workspace, the rules rail stays sticky, and the shell no longer carries the dead planner-side `download latest` export contract
  - recovered export completion now announces once per browser session via toast with `Mina filer` copy, while export progress/error stays localized to the toolbar row and no success/helper band returns on re-entry
## Verification
- 2026-03-30 docs follow-up: `pdm run docs-validate`
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
  - backend-only close-out; no planner UI/route smoke was required because no UI behavior changed in this session
- 2026-03-30 EPIC-02 local password reset:
  - `pdm run ruff check src/skriptoteket/application/identity/handlers/request_password_reset.py src/skriptoteket/application/identity/handlers/reset_password.py src/skriptoteket/domain/identity/password_reset.py src/skriptoteket/protocols/password_reset.py src/skriptoteket/web/api/v1/auth.py src/skriptoteket/di/identity.py src/skriptoteket/di/infrastructure/repositories.py src/skriptoteket/di/infrastructure/services.py src/skriptoteket/infrastructure/repositories/password_reset_token_repository.py src/skriptoteket/infrastructure/security/password_reset_request_throttle.py src/skriptoteket/infrastructure/db/models/password_reset_token.py src/skriptoteket/infrastructure/repositories/session_repository.py tests/unit/application/identity/test_request_password_reset_handler.py tests/unit/application/identity/test_reset_password_handler.py tests/unit/web/test_password_reset_api_routes.py tests/integration/infrastructure/repositories/test_password_reset_token_repository.py tests/integration/infrastructure/repositories/test_session_repository.py tests/unit/web/test_error_handler_middleware.py`
  - `pdm run fe-gen-api-types`; `pdm run fe-type-check`; `pnpm --filter @skriptoteket/spa exec eslint src/stores/auth.ts src/stores/auth.spec.ts src/router/routes.ts src/components/auth/LoginModal.vue src/components/auth/LoginModal.spec.ts src/views/ForgotPasswordView.vue src/views/ForgotPasswordView.spec.ts src/views/ResetPasswordView.vue src/views/ResetPasswordView.spec.ts`; `pnpm --filter @skriptoteket/spa exec vitest run src/stores/auth.spec.ts src/api/client.spec.ts src/router/index.spec.ts src/components/auth/LoginModal.spec.ts src/views/ForgotPasswordView.spec.ts src/views/ResetPasswordView.spec.ts`
  - `pdm run pytest tests/unit/application/identity/test_request_password_reset_handler.py tests/unit/application/identity/test_reset_password_handler.py tests/unit/web/test_password_reset_api_routes.py tests/integration/infrastructure/repositories/test_password_reset_token_repository.py tests/integration/infrastructure/repositories/test_session_repository.py tests/unit/web/test_error_handler_middleware.py -q`; `pdm run typecheck`
  - live check: `docker exec windsurf-project-db-1 psql -U postgres -d skriptoteket -c "select version_num from alembic_version order by version_num;"` -> `8f3d2c1b4a6e`; `docker compose restart web`; `curl --max-time 5 -sS -D - http://127.0.0.1:8000/healthz` -> `200`; `pdm run python - <<'PY' ... headless Playwright forgot-password/reset-password/login-modal check ... PY` -> `ui-password-reset-check: ok`
- 2026-03-30 security edge hardening:
  - baseline before edits:
    - `pdm run pytest tests/unit/web/test_app_security_hardening.py tests/unit/web/test_observability_routes.py tests/unit/web/test_api_v1_auth_and_csrf_routes.py -q`
    - `pdm run ruff check src/skriptoteket/config.py src/skriptoteket/web/app.py src/skriptoteket/web/middleware/security_headers.py tests/unit/web/test_app_security_hardening.py`
    - live production-edge audit confirmed public `/docs`, `/openapi.json`, `/metrics`, `/healthz`, plus reserved-host fallthrough for `hule.education` / `api.hule.education` / `ws.hule.education`
  - repo-side hardening verification after implementation:
    - `pdm run pytest tests/unit/test_config.py tests/unit/web/test_request_metadata.py tests/unit/web/test_observability_routes.py tests/unit/web/test_api_v1_auth_and_csrf_routes.py tests/unit/web/test_app_security_hardening.py -q`
    - `pdm run ruff check src/skriptoteket/config.py src/skriptoteket/web/request_metadata.py src/skriptoteket/web/api/v1/auth.py src/skriptoteket/observability/health.py src/skriptoteket/observability/metrics.py src/skriptoteket/web/routes/observability.py tests/unit/test_config.py tests/unit/web/test_request_metadata.py tests/unit/web/test_observability_routes.py tests/unit/web/test_app_security_hardening.py`
    - `docker compose -f compose.prod.yaml config >/dev/null`
    - live functional check:
      - `curl -sS -o /tmp/skriptoteket-login-wrong.out -w '%{http_code}\n' -H 'Content-Type: application/json' -d '{"email":"superuser@local.dev","password":"wrong-password"}' http://127.0.0.1:5174/api/v1/auth/login` -> `401`
      - bootstrap-superuser login through `http://127.0.0.1:5174/api/v1/auth/login` -> `200` with `user` + `csrf_token`
      - `docker exec windsurf-project-frontend-1 node -e "fetch('http://skriptoteket_web:8000/healthz',{headers:{Host:'skriptoteket_web:8000'}})..."` -> `200`
  - reviewer loop summary:
    - first `skriptoteket_reviewer` pass found broad proxy trust, production host-allowlist drift, and missing regression coverage
    - one `skriptoteket_implementation_specialist` iteration fixed the approved slice
    - final `skriptoteket_reviewer` pass returned no actionable code findings; remaining risk is operational drift if the nginx-proxy IP/network changes and `TRUSTED_PROXY_CIDRS` is not kept aligned
  - Hemma deploy/revalidation:
    - `ssh hemma 'cd ~/apps/skriptoteket && git pull --ff-only origin main'`; `ssh hemma 'sudo docker exec -e PYTHONPATH=/app/src skriptoteket-worker pdm run db-upgrade'`; `ssh hemma 'cd ~/apps/skriptoteket && sudo docker compose -f compose.prod.yaml up -d --build web worker'`; `ssh hemma /bin/bash -s <<'EOF' ... sudo docker exec skriptoteket-web curl -sS http://127.0.0.1:8000/healthz ... sudo docker exec skriptoteket-web /bin/sh -lc \"curl -sS http://127.0.0.1:8000/metrics | rg 'skriptoteket_(active_sessions|users_by_role)' || true\" ... EOF` -> healthy JSON and no leaked identity/session gauges
    - `curl -sS -D - -o /dev/null https://skriptoteket.hule.education/docs` -> `404`; `curl -sS -D - -o /dev/null https://skriptoteket.hule.education/openapi.json` -> `404`; `curl -sS -D - -o /dev/null https://skriptoteket.hule.education/metrics` -> `403`; `curl -sS https://skriptoteket.hule.education/healthz` -> `{\"status\":\"healthy\",\"message\":\"Service is healthy\"}`; `curl -k https://hule.education` / `api.hule.education` / `ws.hule.education` -> `200` `HuleEdu reserved host placeholder`
- 2026-03-27/2026-03-29 smart-assignment docs scope refinement:
  - `pdm run docs-validate`
  - updated `ADR-0074`, `REV-EPIC-27`, `ST-27-04`, `PR-0167`, and earlier smart-assignment docs so grouping history is separate from live seating continuity, active seating continuity outranks rotational diversity when explicitly enabled, and smart reruns still prefer different good candidates on repeated `Slumpa` runs
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
- 2026-03-27 `PR-0154` smart seating:
  - backend semantics alignment verified with domain/application/web/repository pytest lanes plus `pdm run typecheck` and `pdm run docs-validate`
  - live proof against a fresh host backend: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run uvicorn --app-dir src skriptoteket.web.app:app --reload --host 127.0.0.1 --port 8002` and `pdm run python -m scripts.live_st_27_03_smart_seating_semantics_check --base-url http://127.0.0.1:8002 --runs 120`
  - artifacts under `.artifacts/st-27-03-smart-seating-semantics/summary.json`
- 2026-03-29 `ST-07-07` supported web DI/runtime cutover:
  - `pdm run lint`; `pdm run docs-validate`
  - `pdm run pytest tests/unit/web tests/test_smoke.py tests/test_openapi_contracts.py tests/unit/web/test_startup_checks.py`
  - `pdm run pytest tests/unit/web/test_dishka_dependencies.py tests/unit/web/test_dishka_websocket_routes.py tests/unit/web/test_observability_routes.py tests/test_openapi_contracts.py`
  - `PYTHONPATH=src pdm run python -c "from skriptoteket.web.app import create_app; app=create_app(); print(app.title); print(bool(app.openapi().get('info', {}).get('title')))"`
  - local container proof: `pdm run dev-rebuild`; `docker exec skriptoteket_web pdm run python -c "from importlib.metadata import version; print('fastapi', version('fastapi')); print('starlette', version('starlette')); print('dishka', version('dishka')); print('starlette-dishka', version('starlette-dishka'))"`; `curl -sf http://127.0.0.1:8000/healthz`; `curl -sf http://127.0.0.1:8000/metrics | head -n 20`
  - Hemma proof: `ssh hemma "sudo docker ps --format 'table {{.Names}}\t{{.Status}}' | sed -n '1,10p'"`; `ssh hemma "sudo docker inspect -f '{{json .State.Health}}' skriptoteket-web"`; `ssh hemma "sudo docker exec skriptoteket-web curl -sf http://127.0.0.1:8000/healthz"`; `ssh hemma "sudo docker exec skriptoteket-web curl -sf http://127.0.0.1:8000/metrics | sed -n '1,10p'"`; `ssh hemma "tail -n 120 ~/apps/skriptoteket/.artifacts/st-07-07-hemma-deploy.log"`; host-level `ssh hemma "curl -sf http://127.0.0.1:8000/healthz"` does not work there because `skriptoteket-web` is not host-published
- 2026-03-29 `ST-08-34` planner contextual help:
  - `pdm run fe-test -- --run src/components/help/HelpPanel.spec.ts`
  - `pdm run fe-type-check`; `pdm run docs-validate`
  - live proof: `pdm run python - <<'PY' ... planner help return-cycle check ... PY` confirmed repeated `Översikt -> Grupper -> Översikt` transitions keep `Översikt: klass och klassrum` instead of falling back to the empty help index; artifacts: `.artifacts/help-debug/planner-overview-help-fixed.png`, `.artifacts/help-debug/planner-help-overview-return-fixed-local.png`
- 2026-03-29 `PR-0165` / `PR-0166` same-shell transition continuity:
  - `pdm run fe-test -- --run src/components/editor/EditorWorkspacePanel.spec.ts src/components/tool-run/ToolFileFieldPicker.spec.ts src/components/vault/VaultPanel.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/App.spec.ts`
  - `pdm run fe-type-check`; `pdm run docs-validate`
  - live proof: `pdm run python -m scripts.playwright_pr_0165_seating_editor_sync_check --base-url http://127.0.0.1:5173`, `pdm run python - <<'PY' ... planner transition render check ... PY`, `pdm run python -m scripts.playwright_pr_0166_topbar_brand_hit_target_check --base-url http://127.0.0.1:5173`, and `pdm run python -m scripts.playwright_pr_0166_transition_continuity_audit --base-url http://127.0.0.1:5173`
  - artifacts under `.artifacts/pr-0165-seating-editor-sync-check`, `.artifacts/pr-0166-transition-check`, `.artifacts/pr-0166-topbar-brand-hit-target-check`, and `.artifacts/pr-0166-transition-continuity-audit`; proof confirmed planner shell transitions, rules-map projection switching, route-shell crossfades, topbar focus-label swaps, and Vault refresh continuity all kept their stage count at `>= 1`, while the editor live lane was skipped only because the local DB had no saved admin-tool versions and `ProfileInlineField` is not mounted in the current profile flow
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
- Hemma production now includes the ST-09-07/ST-09-08 hardening deploy; keep `TRUSTED_PROXY_CIDRS` aligned with the current nginx-proxy container/network and replace the temporary reserved-host placeholder when the real HuleEdu edge services ship.
- The warnings-as-errors audit still surfaces a dependency-level Python 3.14 deprecation in `pytest-asyncio` (`asyncio.AbstractEventLoopPolicy`); repo-owned code is clean for the audited patterns, but the plugin likely needs a compatible bump.
- Keep the `7d4c1a2b9e6f` repair migration in mind if a long-lived local DB reports Alembic head but misses the roster smart-rule root contract.
- Smart-assignment sequencing is still strict: `ST-27-04` should build on the shipped `PR-0150` geometry-based checkpoint registry, the `PR-0152` session/lane split, and the new `PR-0154` smart seating run seam, not on older planner-wide save assumptions.
## Next Steps
- Next checkpoints are any follow-up continuity fixes that emerge once local editor fixtures exist for a live editor-shell audit, the continuing planner redesign lane in `ST-29-03` and later `ST-29-06`, and `ST-02-09` before any multi-instance auth rollout.
