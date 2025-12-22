# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-22
- Branch / commit: `main` (uncommitted EPIC-11 changes)
- Current sprint: `SPR-2025-12-21` (EPIC-11 full SPA migration)
- Stories done: ST-11-01/02/03/04/05/06/07/08/09/10/11/12/14
- Production: still SSR + SPA islands (legacy) until EPIC-11 cutover

## Current Session (2025-12-22)

### ST-11-06 (catalog browse views)

- API: `GET /api/v1/catalog/professions`, `.../categories`, `.../tools` in `src/skriptoteket/web/api/v1/catalog.py`
- Views: `BrowseProfessionsView.vue`, `BrowseCategoriesView.vue`, `BrowseToolsView.vue`
- Routes: `/browse`, `/browse/:profession`, `/browse/:profession/:category`

### ST-11-07 (tool run + results)

- API: `GET /api/v1/tools/{slug}`, `POST /api/v1/tools/{slug}/run` in `src/skriptoteket/web/api/v1/tools.py`
- Views: `ToolRunFormView.vue`, `ToolRunResultView.vue`
- Components: `ui-outputs/*`, `ui-actions/*`
- Playwright: `scripts/playwright_st_11_07_spa_tool_run_e2e.py`

### ST-11-08 (my-runs)

- API: `GET /api/v1/my-runs`, `GET /api/v1/runs/{run_id}` in `src/skriptoteket/web/api/v1/my_runs.py`
- Views: `MyRunsListView.vue`, `MyRunsDetailView.vue`
- Shared: `RunResultPanel.vue` (reused across tool results, my-runs, apps)
- Playwright: `scripts/playwright_st_11_08_spa_my_runs_e2e.py`

### ST-11-09 (curated apps)

- API: `GET /api/v1/apps/{app_id}` in `src/skriptoteket/web/api/v1/apps.py`
- View: `AppDetailView.vue` with `performAction()` helper (refactored)
- Route: `/apps/:appId` (SPA fallback serves deep links)
- Playwright: `scripts/playwright_st_11_09_curated_app_e2e.py`
- Cleanups done: Swedish typos fixed (`foer`→`för`, `Koer`→`Kör`), i18n consistency, deleted `templates/apps/detail.html`

### ST-11-10 (suggestions flows SPA)

- API v1 (new): `src/skriptoteket/web/api/v1/suggestions.py` with routes
  - `POST /api/v1/suggestions` (contributor+, CSRF)
  - `GET /api/v1/admin/suggestions` (admin+)
  - `GET /api/v1/admin/suggestions/{id}` (admin+)
  - `POST /api/v1/admin/suggestions/{id}/decide` (admin+, CSRF)
- DTO helpers: `src/skriptoteket/web/api/v1/suggestions_dto.py`
- Catalog helper endpoint added: `GET /api/v1/catalog/categories` for SPA taxonomy
- Router: registered suggestions API; legacy SSR suggestions pages unregistered from web router
- SPA views/routes:
  - `SuggestionNewView.vue` (`/suggestions/new`, minRole contributor)
  - `AdminSuggestionsListView.vue` (`/admin/suggestions`, admin)
  - `AdminSuggestionDetailView.vue` (`/admin/suggestions/:id`, admin)
- Generated types: `pdm run fe-gen-api-types`
- Quality run: `pnpm -C frontend --filter @skriptoteket/spa lint`, `typecheck`, `build`; `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`

### ST-11-11 (admin tools management)

- API v1 (new): `src/skriptoteket/web/api/v1/admin_tools.py`
  - `GET /api/v1/admin/tools` (admin+)
  - `POST /api/v1/admin/tools/{tool_id}/publish` (admin+, CSRF)
  - `POST /api/v1/admin/tools/{tool_id}/depublish` (admin+, CSRF)
- Router: registered in `src/skriptoteket/web/router.py`
- SPA view: `AdminToolsView.vue` (`/admin/tools`, minRole admin)
- Reuses existing handlers: `ListToolsForAdminHandler`, `PublishToolHandler`, `DepublishToolHandler`
- Quality run: all gates passed

### ST-11-12 (editor migration foundation)

- API: moved editor endpoints to `src/skriptoteket/web/api/v1/editor.py`; added
  `GET /api/v1/editor/tools/{tool_id}` + `GET /api/v1/editor/tool-versions/{version_id}` boot payloads.
- Shared helpers: `src/skriptoteket/web/editor_support.py` (defaults + access/visibility helpers),
  reused by SSR editor support and API.
- SPA: `ScriptEditorView.vue` + `components/editor/CodeMirrorEditor.vue`; routes
  `/admin/tools/:toolId` + `/admin/tool-versions/:versionId` (contributor+); editor link added in
  `AdminToolsView.vue`.
- Deps/types: CodeMirror deps added in `frontend/apps/skriptoteket/package.json`;
  regenerated `frontend/apps/skriptoteket/openapi.json` + `src/api/openapi.d.ts`.
- Commands run: `pnpm -C frontend install`, `pdm run fe-gen-api-types`.
- Verification: NOT run yet (needs `pdm run dev` + `pdm run fe-dev`, then visit
  `http://127.0.0.1:5173/admin/tools/<tool_id>` and `.../admin/tool-versions/<version_id>`).

### ST-11-14 (admin tools status enrichment)

- ADR: `docs/adr/adr-0033-admin-tool-status-enrichment.md`
- Backend: `AdminToolItem` DTO extended with `version_count`, `latest_version_state`, `has_pending_review`
- Repository: `get_version_stats_for_tools()` batch aggregation in `ToolVersionRepository`
- Frontend: `AdminToolsView.vue` two-section layout ("Pågående" / "Klara")
- Status badges: "Ingen kod" (no versions), "Utkast" (draft), "Granskas" (in_review)
- Toggle + labels only in "Klara" section

### Phase 4 story review (ST-11-15..19)

- Updated stories for My Tools, editor workflow actions, metadata, maintainers, and help to align with SSR behavior + correct handlers/routes (`docs/backlog/stories/story-11-15-my-tools-view.md`, `docs/backlog/stories/story-11-16-editor-workflow-actions.md`, `docs/backlog/stories/story-11-17-tool-metadata-editor.md`, `docs/backlog/stories/story-11-18-maintainer-management.md`, `docs/backlog/stories/story-11-19-help-framework.md`).
- Follow-up story added for taxonomy editing (`docs/backlog/stories/story-11-20-tool-taxonomy-editor.md`) and linked from EPIC-11.
- Refined ST-11-20 to use ID-based API payloads and a dedicated taxonomy GET endpoint (kept out of editor boot).
- Docs contract check: `pdm run docs-validate` (pass).

### ST-11-20 (taxonomy editor wiring)

- Added taxonomy query/handler and repo support for listing tool tag IDs.
- API: `GET /api/v1/editor/tools/{tool_id}/taxonomy` (admin+) in `src/skriptoteket/web/api/v1/editor.py`.
- Protocol/repo: `ToolRepositoryProtocol.list_tag_ids()` + PostgreSQL implementation.
- Added taxonomy update command/handler + repo changes:
  - `UpdateToolTaxonomyCommand` + handler in `src/skriptoteket/application/catalog/handlers/update_tool_taxonomy.py`
  - `ToolRepositoryProtocol.replace_tags(...)` + SQLAlchemy implementation
- Category/Profession repos now support `list_by_ids(...)`
- API: `PATCH /api/v1/editor/tools/{tool_id}/taxonomy` (admin+, CSRF)
- SPA wiring started in `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (taxonomi panel + GET/patch wiring); OpenAPI types regenerated via `pdm run fe-gen-api-types`.
- Refactor: moved editor boot/save + taxonomy logic into composables
  `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts` and
  `frontend/apps/skriptoteket/src/composables/editor/useToolTaxonomy.ts`; view now focuses on UI.

### Verification

- Tests: `pdm run pytest tests/unit/application/catalog/handlers/test_list_tool_taxonomy.py tests/unit/application/catalog/handlers/test_update_tool_taxonomy.py tests/unit/web/test_editor_api_routes.py tests/integration/infrastructure/repositories/test_catalog_repository.py`
- UI check: Vite dev server already running on 5173; verified SPA responded (`curl http://127.0.0.1:5173/admin/tools/00000000-0000-0000-0000-000000000000` returned HTML + Vite client). Backend/Vite start attempts failed due to ports in use.
- Frontend: `pnpm -C frontend --filter @skriptoteket/spa typecheck`, `pnpm -C frontend --filter @skriptoteket/spa lint`
- UI check: logged in via `/api/v1/auth/login`, loaded `/api/v1/admin/tools` to pick a tool,
  GET/PATCH taxonomy at `/api/v1/editor/tools/{tool_id}/taxonomy`, and confirmed
  `/admin/tools/{tool_id}` returned 200 from Vite.

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
1. **ST-11-15** (my-tools): Contributor dashboard - placeholder needs implementation
2. **ST-11-16** (editor workflows): Submit review, publish, request changes, rollback
3. **ST-11-17** (metadata): Tool title, summary, tags editing
4. **ST-11-18** (maintainers): Add/remove contributor access
5. **ST-11-19** (help): Contextual help panel for all views

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
