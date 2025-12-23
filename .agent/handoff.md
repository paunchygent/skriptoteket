# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-23
- Branch / commit: `main` (uncommitted EPIC-11 changes)
- Current sprint: `SPR-2025-12-21` (EPIC-11 full SPA migration)
- Stories done: ST-11-01/02/03/04/05/06/07/08/09/10/11/12/14/15/21
- Production: still SSR + SPA islands (legacy) until EPIC-11 cutover

## Current Session (2025-12-23)

### ST-11-06 (catalog browse views)

- SPA browse views + API in `src/skriptoteket/web/api/v1/catalog.py` (`/browse`, `/browse/:profession`, `/browse/:category`)

### ST-11-07 (tool run + results)

- Tool run API + SPA views (`src/skriptoteket/web/api/v1/tools.py`, `ToolRunFormView.vue`, `ToolRunResultView.vue`); Playwright `scripts/playwright_st_11_07_spa_tool_run_e2e.py`

### ST-11-08 (my-runs)

- My-runs API + SPA views (`src/skriptoteket/web/api/v1/my_runs.py`, `MyRunsListView.vue`, `MyRunsDetailView.vue`); Playwright `scripts/playwright_st_11_08_spa_my_runs_e2e.py`

### ST-11-09 (curated apps)

- Curated apps API + SPA view (`src/skriptoteket/web/api/v1/apps.py`, `AppDetailView.vue`); Playwright `scripts/playwright_st_11_09_curated_app_e2e.py`

### ST-11-10 (suggestions flows SPA)

- Suggestions API + DTOs in `src/skriptoteket/web/api/v1/suggestions.py` + `suggestions_dto.py` (contributor/admin flows).
- SPA views: `SuggestionNewView.vue`, `AdminSuggestionsListView.vue`, `AdminSuggestionDetailView.vue`.
- Types regenerated: `pdm run fe-gen-api-types`.

### ST-11-11 (admin tools management)

- Admin tools API in `src/skriptoteket/web/api/v1/admin_tools.py` (list + publish/depublish) + router registration.
- SPA view: `AdminToolsView.vue` (`/admin/tools`, minRole admin).

### ST-11-12 (editor migration foundation)

- Editor API in `src/skriptoteket/web/api/v1/editor.py`; shared helpers in `src/skriptoteket/web/editor_support.py`.
- SPA: `ScriptEditorView.vue` + `components/editor/CodeMirrorEditor.vue` for `/admin/tools/:toolId` + `/admin/tool-versions/:versionId`.
- Verification pending for editor routes (needs backend + Vite).

### ST-11-14 (admin tools status enrichment)

- ADR-0033; `AdminToolItem` enriched with version status; `AdminToolsView.vue` split into Pågående/Klara with badges.

### ST-11-15 (my-tools contributor dashboard)

- API: `GET /api/v1/my-tools` in `src/skriptoteket/web/api/v1/my_tools.py` (contributor+, id/title/summary/is_published)
- Router: registered `api_v1_my_tools.router` in `src/skriptoteket/web/router.py`
- SPA view: `frontend/apps/skriptoteket/src/views/MyToolsView.vue` (list rows + empty state + edit link)
- Shared row: `frontend/apps/skriptoteket/src/components/tools/ToolListRow.vue` (slots for main/status/actions)
- Admin refactor: `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue` now uses `ToolListRow`

### ST-11-21 (unified landing page + modal-first login)

- Home landing page: `frontend/apps/skriptoteket/src/views/HomeView.vue` (auth-adaptive hero + quick nav).
- Modal-first login: header login opens modal; auth guards already open modal (`frontend/apps/skriptoteket/src/App.vue`, `frontend/apps/skriptoteket/src/router/index.ts`).
- Modal ARIA: `role="dialog"`, `aria-modal`, `aria-labelledby`, `aria-describedby` in `frontend/apps/skriptoteket/src/App.vue`.
- Story docs aligned: `docs/backlog/stories/story-11-21-unified-landing-page.md`; follow-up story added `docs/backlog/stories/story-11-22-remove-login-route.md` + linked from EPIC-11.

### Phase 4 story review (ST-11-15..19)

- Story docs aligned for ST-11-15..19 + ST-11-20; follow-up ST-11-22 added and linked from EPIC-11.
- Docs contract check: `pdm run docs-validate` (pass).

### ST-11-20 (taxonomy editor wiring)

- Taxonomy API + repo wiring in `src/skriptoteket/web/api/v1/editor.py` + catalog handlers/repos.
- SPA taxonomy panel started in `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`; types regenerated via `pdm run fe-gen-api-types`.

### Verification

- Tests: `pdm run pytest tests/unit/application/catalog/handlers/test_list_tool_taxonomy.py tests/unit/application/catalog/handlers/test_update_tool_taxonomy.py tests/unit/web/test_editor_api_routes.py tests/integration/infrastructure/repositories/test_catalog_repository.py`
- UI check: Vite dev server already running on 5173; verified SPA responded (`curl http://127.0.0.1:5173/admin/tools/00000000-0000-0000-0000-000000000000` returned HTML + Vite client). Backend/Vite start attempts failed due to ports in use.
- Frontend: `pnpm -C frontend --filter @skriptoteket/spa typecheck`, `pnpm -C frontend --filter @skriptoteket/spa lint`
- UI check: logged in via `/api/v1/auth/login`, loaded `/api/v1/admin/tools` to pick a tool,
  GET/PATCH taxonomy at `/api/v1/editor/tools/{tool_id}/taxonomy`, and confirmed
  `/admin/tools/{tool_id}` returned 200 from Vite.
- Live check (2025-12-22): `pdm run python -m scripts.playwright_st_11_15_spa_my_tools_e2e --base-url http://127.0.0.1:5173`
- Live check (2025-12-23): `pdm run python -m scripts.playwright_st_11_21_login_modal_e2e --base-url http://127.0.0.1:5173`

## Key Architecture

- Full SPA migration: ADR-0027..0030 + EPIC-11
- Contract v2 (ADR-0022): outputs `notice|markdown|table|json|html_sandboxed` (+ `vega_lite` curated-only)
- Sessions + optimistic concurrency (ADR-0024): `expected_state_rev` on actions
- UI paradigm: Vue 3 + Vite + Tailwind 4 with `@theme` design tokens (ADR-0032)

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000
pdm run fe-dev              # SPA 127.0.0.1:5173

# Quality gates
pdm run lint && pdm run typecheck && pdm run docs-validate
pnpm -C frontend --filter @skriptoteket/spa typecheck
pnpm -C frontend --filter @skriptoteket/spa lint
pnpm -C frontend --filter @skriptoteket/spa build

# Playwright e2e
pdm run python -m scripts.playwright_st_11_09_curated_app_e2e --base-url http://127.0.0.1:5173
```

## Known Issues / Risks

- `vega_lite` restrictions not implemented; do not render until restrictions exist (ADR-0024)
- Frontend scripts split: `pdm run fe-*` = SPA, `pdm run fe-*-islands` = legacy islands
- SSR action forms minimal: no required/default/placeholder yet

## Next Steps

### Phase 4: Remaining features (ready)
1. **ST-11-16** (editor workflows): Submit review, publish, request changes, rollback
2. **ST-11-17** (metadata): Tool title, summary, tags editing
3. **ST-11-18** (maintainers): Add/remove contributor access
4. **ST-11-19** (help): Contextual help panel for all views

### Phase 5: Cutover
6. **ST-11-13** (cutover): Delete SSR/HTMX, Playwright E2E suite

### Later
- Governance: ST-02-02 (admin nomination + superuser approval)

## Historical (2025-12-21)

Completed in prior sessions (see `.agent/readme-first.md` for details):

- ST-08-01/02/03: Help framework + login help + home index
- ST-09-02: CSP enforcement at nginx
- ST-06-07: Admin toast notifications
- ST-10-08/09/10: SPA islands toolchain, editor island, runtime island
- ST-11-01/02: Frontend workspace + UI library scaffold
- ST-11-04: API v1 + OpenAPI→TypeScript
- ST-11-05: SPA auth + route guards
