# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-22
- Branch / commit: `main` (uncommitted ST-11-06 changes)
- Current sprint: `SPR-2025-12-21` (EPIC-11 full SPA migration foundations)
- Backend now: ST-11-03/04/05/06 done (catalog API + SPA browse views complete)
- Frontend now: ST-11-01/02/03/06 done; browse views implemented; next vertical slice is tool run views
- Production today: still SSR + SPA islands (legacy) until EPIC-11 cutover

## 2025-12-22

- ST-11-06 Phase 1 (catalog API): Created three catalog endpoints for SPA browse views. Files: `src/skriptoteket/web/api/v1/catalog.py` (new: `GET /api/v1/catalog/professions`, `GET .../professions/{slug}/categories`, `GET .../categories/{slug}/tools`), `src/skriptoteket/web/router.py` (registered catalog routes). Response models: `ProfessionItem`, `CategoryItem`, `ToolItem`, `CuratedAppItem`, `ListProfessionsResponse`, `ListCategoriesResponse`, `ListToolsResponse`. Reuses existing handlers. TypeScript types regenerated: `pdm run fe-gen-api-types`. Verified: `pdm run lint`, `pdm run typecheck`, `pnpm -C frontend --filter @skriptoteket/spa typecheck`.
- ST-11-06 Phase 2 (frontend views): Created three Vue browse views consuming the catalog API. Routes: `/browse` (BrowseProfessionsView), `/browse/:profession` (BrowseCategoriesView), `/browse/:profession/:category` (BrowseToolsView). All routes `requiresAuth: true`. Files: `frontend/apps/skriptoteket/src/router/routes.ts`, `frontend/apps/skriptoteket/src/views/BrowseProfessionsView.vue`, `BrowseCategoriesView.vue`, `BrowseToolsView.vue`. Removed old `BrowseView.vue` placeholder. Styling: pure CSS with HuleEdu design tokens (ADR-0029), scoped styles, responsive mobile layout. Also fixed: router now uses `createWebHistory(import.meta.env.BASE_URL)` for correct base path handling; Vite proxy excludes `/static/spa` so SPA is served by Vite dev server. Verified: `pdm run lint`, `pdm run typecheck`, `pnpm -C frontend --filter @skriptoteket/spa typecheck`. Live Playwright test: auth redirect, login, profession list (5), category list (4), tools/curated apps view all working.
- ST-11-06 decisions: (1) API structure = three RESTful endpoints (Option A); (2) Vue routes = child routes under `/browse` (Option A); (3) State management = local component state, no Pinia store initially (Option A, YAGNI).
- ST-11-03 (SPA hosting + history fallback): FastAPI now serves SPA with history mode routing; deep links (e.g., `/browse/foo`) serve SPA index.html; API routes (`/api/*`) not intercepted; Dockerfile builds `@skriptoteket/spa` (replaces `@skriptoteket/islands`). Files: `frontend/apps/skriptoteket/vite.config.ts` (added `base: "/static/spa/"` + `outDir`), `src/skriptoteket/web/routes/spa_fallback.py` (new catch-all route), `src/skriptoteket/web/router.py` (registered fallback LAST), `Dockerfile` (SPA build stage), `tests/unit/web/test_spa_fallback.py`. Verified: `pdm run fe-build` + `curl http://127.0.0.1:8000/browse` returns SPA HTML + `curl http://127.0.0.1:8000/api/v1/auth/me` returns JSON; `pdm run lint`, `pdm run typecheck`, `pdm run pytest tests/unit/web/test_spa_fallback.py -v` (10 passed).

## 2025-12-21

- EPIC-11 planning + docs alignment (full SPA): new PRD/ADRs + epic/stories + sprint plan; superseded SSR/HTMX + islands ADRs: `docs/prd/prd-spa-frontend-v0.1.md`, `docs/adr/adr-0027-full-vue-vite-spa.md`, `docs/adr/adr-0028-spa-hosting-and-routing-integration.md`, `docs/adr/adr-0029-frontend-styling-pure-css-design-tokens.md`, `docs/adr/adr-0030-openapi-as-source-and-openapi-typescript.md`, `docs/backlog/epics/epic-11-full-vue-spa-migration.md`, `docs/backlog/sprints/sprint-2025-12-21-spa-migration-foundations.md`, `docs/reference/reports/ref-vue-spa-migration-roadmap.md` (validated: `pdm run docs-validate`).
- Frontend foundations (ST-11-01/02): pnpm workspace now supports `apps/*` + `packages/*`; added `frontend/apps/skriptoteket` SPA scaffold and `frontend/packages/huleedu-ui` stub; removed Tailwind from legacy `frontend/islands` per ADR-0029 (validated: `pnpm -C frontend install`, `pnpm -C frontend lint`, `pnpm -C frontend typecheck`, `pnpm -C frontend build`, plus `pnpm -C frontend --filter @huleedu/ui lint|typecheck|build` and `pnpm -C frontend --filter @skriptoteket/islands lint|typecheck`).
- ST-11-04 (API v1 + OpenAPI TS): migrated legacy `/api/*` JSON routes → `/api/v1/*` (no shim) + enforced `X-CSRF-Token` on `POST`s; added `/api/v1/auth/*`; added deterministic OpenAPI export + TS generation: `src/skriptoteket/web/routes/interactive_tools.py`, `src/skriptoteket/web/routes/editor.py`, `src/skriptoteket/web/api/v1/auth.py`, `src/skriptoteket/web/auth/api_dependencies.py`, `scripts/export_openapi_v1.py`, `frontend/apps/skriptoteket/src/api/openapi.d.ts`, `pyproject.toml`, tests `tests/unit/web/test_api_v1_auth_and_csrf_routes.py` (verify: `pdm run fe-gen-api-types`, `pnpm -C frontend --filter @skriptoteket/spa typecheck`, `pdm run pytest tests/unit/web/test_api_v1_auth_and_csrf_routes.py`).
- ST-11-05 (SPA auth + route guards): added auth store + API client wrapper + router guards; `/` is public and `/browse` is protected; role-gated placeholders at `/my-tools` (contributor+) and `/admin/tools` (admin+); role-too-low routes go to `/forbidden`; API 401 clears auth and redirects to `/login?next=...` when on a protected route: `frontend/apps/skriptoteket/src/stores/auth.ts`, `frontend/apps/skriptoteket/src/api/client.ts`, `frontend/apps/skriptoteket/src/router/index.ts`, `frontend/apps/skriptoteket/src/router/routes.ts`, `frontend/apps/skriptoteket/src/views/LoginView.vue`, `frontend/apps/skriptoteket/src/views/ForbiddenView.vue`, `frontend/apps/skriptoteket/src/App.vue` (verify: `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`, `pnpm -C frontend --filter @skriptoteket/spa typecheck`, `pdm run fe-type-check-islands`, `pdm run pytest tests/unit/web/test_api_v1_auth_and_csrf_routes.py`, `pdm run db-upgrade`; live check: started SPA Vite on `http://127.0.0.1:5174` (port 5173 in use by islands), backend already running on `http://127.0.0.1:8000`, ran headless Playwright smoke covering redirect/login/logout + 401-clear-to-login).
- ST-08-01 (Hjälp-ramverk): global “Hjälp” i base-shell. Mobile UX (post-ST-08-01): Hjälp ligger i hamburger-menyn (även utloggad), och hjälp-panelen är en inset overlay med safe-area insets (inte flush edge-to-edge). Close-beteende: Escape + click/focus utanför + HTMX `beforeRequest` stänger (click utanför är close-and-continue). Files: `src/skriptoteket/web/templates/base.html`, `src/skriptoteket/web/templates/partials/help/`, `src/skriptoteket/web/static/js/app.js`, `src/skriptoteket/web/static/css/app/layout.css`, `src/skriptoteket/web/static/css/app/components.css`, `scripts/playwright_ui_smoke.py`. Verifierat lokalt (2025-12-21): `pdm run ui-smoke` (inkl. `help-logged-*-mobile.png` i `.artifacts/ui-smoke/`) + manual mobile pass (Playwright artifacts i `.artifacts/manual-ux/`).
- ST-08-01 mobile UX re-audit (2025-12-21): confirmed iPhone-sized viewport behavior + that `.artifacts/ui-smoke/mobile-nav.png`, `.artifacts/ui-smoke/help-logged-out-mobile.png`, `.artifacts/ui-smoke/help-logged-in-mobile.png` match reality.
- ST-08-02 (Login help + micro-help): added login topic copy (incl. “glömt lösenord → kontakta admin”) + field-level micro-help (ghost placeholders + inline `?` tooltip buttons). Files: `src/skriptoteket/web/templates/login.html`, `src/skriptoteket/web/templates/partials/help/topics/login.html`, `src/skriptoteket/web/static/js/app.js`, `src/skriptoteket/web/static/css/app/components.css`, `scripts/playwright_ui_smoke.py`, story `docs/backlog/stories/story-08-02-login-help.md`. Verified (2025-12-21): `pdm run ui-smoke` + iPhone-sized Playwright screenshots `.artifacts/manual-ux-st-08-02/01-login-mobile.png` + `03-login-email-tooltip.png`.
- ST-08-03 (Home help index / sitemap): expanded logged-in help index with 1-line descriptions (role-aware) and expanded `home` topic with role-aware sitemap copy. Files: `src/skriptoteket/web/templates/partials/help/index_logged_in.html`, `src/skriptoteket/web/templates/partials/help/topics/home.html`, `src/skriptoteket/web/static/css/app/components.css`, story `docs/backlog/stories/story-08-03-home-help-index.md`. Verified (2025-12-21): `pdm run ui-smoke` + iPhone-sized screenshots `.artifacts/manual-ux-st-08-03/01-help-index-mobile.png` + `02-home-topic-sitemap-mobile.png`.
- ST-09-02 (CSP): CSP is enforced at nginx reverse proxy (`~/infrastructure/nginx/conf.d/skriptoteket.conf` on hemma) with `script-src 'self'` + `script-src-attr 'none'` + `style-src 'unsafe-inline'` (CodeMirror) + Google Fonts + `frame-src 'self' about:` (for `srcdoc` iframes). Removed inline `onclick=` from admin versions list (Option A) by making link + rollback form siblings and using `hx-confirm`: `src/skriptoteket/web/templates/admin/partials/version_list.html`, `src/skriptoteket/web/static/css/app/editor.css`. Verified on prod (2025-12-21): no CSP console violations (Playwright probe).
- ST-06-07 (toasts): admin actions now show success/error toasts without full reloads by using HTMX `HX-Location` redirects + toast cookies; added error toasts and rollback success toast; suggestions decision now uses toast + removes the inline “saved” banner: `src/skriptoteket/web/pages/admin_scripting_support.py`, `src/skriptoteket/web/pages/admin_scripting.py`, `src/skriptoteket/web/pages/suggestions.py`, `src/skriptoteket/web/templates/suggestions_review_detail.html`, `src/skriptoteket/web/htmx.py`.
- ST-10-08 (SPA islands toolchain): pnpm workspace + Vite/Vue/Tailwind build to `/static` + Jinja manifest integration: `frontend/package.json`, `frontend/pnpm-workspace.yaml`, `frontend/islands/`, `src/skriptoteket/web/vite.py`, `src/skriptoteket/web/templating.py`.
- PDM↔pnpm integration: `pdm run fe-install|fe-dev|fe-build|fe-build-watch|fe-preview|fe-type-check|fe-lint|fe-lint-fix` delegates to pnpm in the `frontend/` workspace: `pyproject.toml`. (ESLint 9 flat config: `frontend/islands/eslint.config.js`.)
- Demo SPA page (`hx-boost="false"` around mount): `/spa/demo` → `src/skriptoteket/web/pages/spa_islands.py`, `src/skriptoteket/web/templates/spa/demo.html`.
- ST-10-09 (editor SPA island MVP): CodeMirror 6 Vue island + JSON save endpoints + HTMX-safe embed on `/admin/tools/{tool_id}` + `/admin/tool-versions/{version_id}`: `frontend/islands/src/entrypoints/editor.ts`, `frontend/islands/src/editor/*`, `src/skriptoteket/web/routes/editor.py` (`/api/v1/editor/*`), `src/skriptoteket/web/templates/admin/script_editor.html`, `src/skriptoteket/web/pages/admin_scripting_support.py`, `src/skriptoteket/web/static/css/app/editor.css`, `tests/unit/web/test_editor_api_routes.py`.
- ST-10-10 (runtime SPA island MVP): Vue runtime island renders stored `ui_payload` + `next_actions` on interactive pages and calls `POST /api/v1/start_action` with optimistic concurrency: `frontend/islands/src/entrypoints/runtime.ts`, `frontend/islands/src/runtime/*`, `src/skriptoteket/web/templates/tools/partials/run_result.html`, `src/skriptoteket/web/templates/apps/detail.html`, `src/skriptoteket/web/templates/my_runs/detail.html`.
- Tests: `tests/unit/web/test_vite_assets.py`.

## What changed

- This handoff is intentionally compressed to current sprint-critical work only (see `.agent/readme-first.md` for history).
- UI paradigm decision changed: full SPA is now the target (ADR-0027); SSR/HTMX and SPA islands are superseded and will be deleted at cutover.
- Docker: multi-stage Dockerfile builds full SPA (`@skriptoteket/spa`) instead of legacy islands (Node.js stage → pnpm workspace → Vite build → copy to production image): `Dockerfile`.
- Docker: compose project names added to avoid orphan warnings: `compose.prod.yaml` (`skriptoteket`), `compose.observability.yaml` (`skriptoteket-observability`).
- Runner: contract v2 result.json only (no v1): `runner/_runner.py`.
- App: strict v2 parsing + contract violations raise `DomainError(INTERNAL_ERROR)`: `src/skriptoteket/infrastructure/runner/result_contract.py`, `src/skriptoteket/infrastructure/runner/docker_runner.py`.
- App: normalize + persist `tool_runs.ui_payload` (only via `DeterministicUiPayloadNormalizer`): `src/skriptoteket/application/scripting/handlers/execute_tool_version.py`, `src/skriptoteket/domain/scripting/models.py`, `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`.
- App: tool sessions persistence (state + optimistic concurrency): `src/skriptoteket/domain/scripting/tool_sessions.py`, `src/skriptoteket/protocols/tool_sessions.py`, `src/skriptoteket/infrastructure/repositories/tool_session_repository.py`, `src/skriptoteket/application/scripting/handlers/*tool_session_state.py`.
- App: ST-10-04 interactive tool API endpoints: `src/skriptoteket/application/scripting/handlers/start_action.py`, `src/skriptoteket/web/routes/interactive_tools.py`.
- Repo: compute `get_session_state.latest_run_id` at read time (no schema change): `src/skriptoteket/protocols/scripting.py`, `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`.
- DB: migrations `0008_tool_runs_ui_payload` + `0009_tool_sessions` + `0010_curated_apps_runs` (tool_runs source_kind + allow curated tool_id in runs/sessions).
- Curated apps: registry+executor (+ artifacts under `ARTIFACTS_ROOT/<run_id>/...`) + `/apps/<app_id>` page + catalog integration: `src/skriptoteket/infrastructure/curated_apps/executor.py`, `src/skriptoteket/application/scripting/handlers/start_action.py`, `src/skriptoteket/infrastructure/artifacts/filesystem.py`, `src/skriptoteket/web/pages/curated_apps.py`, `src/skriptoteket/web/templates/apps/detail.html`, `src/skriptoteket/web/templates/browse_tools.html`, `src/skriptoteket/application/scripting/handlers/get_interactive_session_state.py`.
- UI: SSR renders `run.ui_payload.outputs` + `run.ui_payload.next_actions` via `src/skriptoteket/web/templates/partials/ui_outputs.html` + `src/skriptoteket/web/templates/partials/ui_actions.html` (POST `/tools/interactive/start_action`; parser `src/skriptoteket/web/interactive_action_forms.py`; tests `tests/unit/web/test_interactive_actions_pages.py`).
- Typing: OpenTelemetry stubs + no-`Any` tracing facade fixes: `stubs/opentelemetry/`, `src/skriptoteket/observability/tracing.py`.
- Docs: removed credentials from `docs/runbooks/runbook-home-server.md` (no secrets in repo).

## Decisions (and links)

- Full SPA migration: ADR-0027..0030 + PRD `PRD-spa-frontend-v0.1` + EPIC-11.
- Contract v2 allowlists (ADR-0022): outputs `notice|markdown|table|json|html_sandboxed` (+ `vega_lite` curated-only); action fields `string|text|integer|number|boolean|enum|multi_enum`.
- Normalizer returns combined result `{ui_payload, state}` via `UiNormalizationResult` (ADR-0024).
- Policy budgets/caps approved (default vs curated) in `src/skriptoteket/domain/scripting/ui/policy.py`.
- `vega_lite` enabled in curated policy now; restrictions MUST be implemented before the platform accepts/renders it (ADR-0024 risk).

## How to run / verify

- Canonical local recipe: see `.agent/readme-first.md` (includes `ARTIFACTS_ROOT` note).
- Frontend install: `pdm run fe-install` (or `pnpm -C frontend install`)
- SPA dev: `pdm run fe-dev` (or `pnpm -C frontend --filter @skriptoteket/spa dev`)
- SPA build: `pdm run fe-build` (or `pnpm -C frontend --filter @skriptoteket/spa build`)
- UI package checks: `pnpm -C frontend --filter @huleedu/ui lint|typecheck|build`
- Islands (legacy) checks: `pdm run fe-dev-islands` / `pdm run fe-build-islands` (or `pnpm -C frontend --filter @skriptoteket/islands ...`)
- UI smoke (Playwright): `pdm run ui-smoke` (dev: `.env` `BOOTSTRAP_SUPERUSER_*`; prod: `--dotenv .env.prod-smoke` with `PLAYWRIGHT_*`; does not create users).
- Editor island smoke (Playwright): `pdm run ui-editor-smoke` (dev: `.env` `BOOTSTRAP_SUPERUSER_*`; prod: `--dotenv .env.prod-smoke`; screenshots in `.artifacts/ui-editor-smoke`).
- Runtime island smoke (Playwright): `pdm run ui-runtime-smoke` (dev: `.env` `BOOTSTRAP_SUPERUSER_*`; prod: `--dotenv .env.prod-smoke`; screenshots in `.artifacts/ui-runtime-smoke`).
- CSP header (prod, 2025-12-21): `curl -sI https://skriptoteket.hule.education/login | rg -i content-security-policy` (enforced; no Report-Only).
- Quality gates: `pdm run lint`.
- Typecheck: `pdm run typecheck`.
- Unit tests: `pdm run pytest tests/unit/domain/scripting/ui` + `pdm run pytest tests/unit/infrastructure/runner/test_result_contract.py tests/unit/infrastructure/runner/test_docker_runner.py tests/unit/application/test_scripting_execute_tool_version_handler.py tests/unit/domain/scripting/test_models.py`.
- Migration idempotency: `pdm run pytest -m docker --override-ini addopts='' tests/integration/test_migration_0008_tool_runs_ui_payload_idempotent.py tests/integration/test_migration_0009_tool_sessions_idempotent.py tests/integration/test_migration_0010_curated_apps_runs_idempotent.py tests/integration/test_migration_0011_tool_runs_input_manifest_idempotent.py`.
- Live check (2025-12-20): `pdm run db-upgrade`; login via curl cookie jar; `/browse/gemensamt/ovrigt` shows curated app → open `/apps/demo.counter` → Starta → Öka (step=2) → Spara som fil (action_id=`export`) → file stored at `ARTIFACTS_ROOT/<run_id>/output/counter.txt` and downloadable via `/my-runs/<run_id>/artifacts/output_counter_txt` (200).
- Live check (2025-12-21): `pdm run ui-smoke`, `pdm run ui-editor-smoke`, `pdm run ui-runtime-smoke` (artifacts under `.artifacts/`).
- Live check (2025-12-21): `docker compose up -d db`, `pdm run db-upgrade`, `npm_config_cache=.tmp/npm-cache pdm run fe-build-islands`, then `pdm run ui-editor-smoke` (verifies CodeMirror 6 mounts on `/admin/tools/<tool_id>` and Save creates/saves a version and redirects).
- Live check (2025-12-21): `pdm run ui-runtime-smoke` (verifies runtime island mounts on `/apps/demo.counter` + `/my-runs/<run_id>` + `/tools/<slug>/run`, action updates UI, and concurrency "Uppdatera" refresh path works).
- Live check (2025-12-21): with local dev server running on `http://127.0.0.1:8000`, used Playwright (via `pdm run python`) to exercise editor submit-review → publish → metadata save and suggestions submit → deny; verified toasts appear ("Skickat för granskning.", "Version publicerad.", "Metadata sparad.", "Förslag avslaget.").
- Live check (2025-12-21): verified multi-file inputs render via curl login cookie: `/tools/st-10-07-interactive-counter/run` has `name="files"` + `multiple`; `/admin/tools/c36645c2-950b-483e-b544-7a73466e473b` sandbox input has `name="files"` + `multiple`.
- Production deploy (2025-12-21): `ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"` + `docker compose -f compose.observability.yaml up -d` (verified runner executes, SPA islands render).
- Verified (2025-12-20): `pdm run lint`, `pdm run typecheck`, `pdm run pytest tests/unit/application/scripting/handlers/test_interactive_tool_api.py tests/unit/infrastructure/runner/test_artifact_manager.py`, `pdm run docs-validate`.
- Verified (2025-12-21): `pdm run test`, `pdm run docs-validate`, `pdm run pytest -m docker --override-ini addopts='' tests/integration/test_migration_0011_tool_runs_input_manifest_idempotent.py`.
- Verified (2025-12-22, ST-11-04/05 review): `pdm run lint` (All checks passed), `pdm run typecheck` (no issues in 296 files), `pdm run docs-validate`, `pnpm -C frontend --filter @skriptoteket/spa typecheck`, `pdm run fe-type-check-islands`, `pdm run pytest tests/unit/web/test_api_v1_auth_and_csrf_routes.py -v` (9 passed); backend auth API verified via curl (login/me/csrf/logout+CSRF all work correctly); SPA manual tests passed (unauthenticated→/login?next=, post-login lands on next target, role-gating→/forbidden?required=&from=, logout→/, 401-clear-to-login); role-gating verified with `user` role account (`test-user@local.dev`): nav links hidden for role-gated routes, direct URL to /admin/tools→/forbidden?required=admin&from=/admin/tools, /my-tools→/forbidden?required=contributor&from=/my-tools.

## Known issues / risks

- Frontend scripts are split: `pdm run fe-*` targets the SPA (`@skriptoteket/spa`), and `pdm run fe-*-islands` targets legacy islands (`@skriptoteket/islands`).
- `vega_lite` restrictions are not implemented yet; do not accept/render vega-lite outputs until restrictions exist (ADR-0024).
- Dev DB can get bloated with test accounts: avoid creating new superusers for UI checks (reuse `.env` bootstrap account).
- SSR action forms are minimal: no required/default/placeholder/help text yet; supported types match contract allowlist.

## Next steps (recommended order)

- **ST-11-06 complete**: Browse views implemented and live-tested via Playwright. Screenshots in `.artifacts/st-11-06-*.png`.
- EPIC-11: continue vertical slices for route parity: ST-11-07 (tool run views), ST-11-08 (my-runs views), ST-11-09 (apps views), ST-11-10+ (admin/editor).
- EPIC-12: keep ST-12-02/03/04 blocked until EPIC-11 cutover (ST-11-13); implement UX only in the SPA.
- Admin UX: ST-06-08 (editor UI fixes) should be re-audited against the SPA island editor; close or rescope.
- Governance: ST-02-02 (admin nomination + superuser approval) to complete the auditable promotion gate.
