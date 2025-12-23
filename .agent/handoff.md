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
- Branch / commit: `main` (EPIC-11 complete)
- Current sprint: `SPR-2025-12-21` (EPIC-11 full SPA migration)
- Stories done: ST-11-01/02/03/04/05/06/07/08/09/10/11/12/13/14/15/16/17/18/19/20/21/22
- Production: Full Vue SPA (SSR/HTMX removed in ST-11-13)

## Current Session (2025-12-23)

### Mobile Sidebar Right-Side Positioning

- Moved mobile sidebar drawer to slide from right (matches hamburger button position)
- File: `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`
- Changes: `right: 0` + `translateX(100%)` for mobile; desktop unchanged (left sidebar)
- Verified: typecheck + lint pass

### HuleEdu Design Alignment (layout + dashboard)

**Completed**:
- Grid background pattern added to SPA (`frontend/apps/skriptoteket/src/assets/main.css`)
- SSR frame made transparent for grid visibility (`src/skriptoteket/web/static/css/app/layout.css`)
- Conditional layout in `App.vue`: Landing (logo only) vs Authenticated (sidebar + top bar)
- Role-guarded dashboard in `HomeView.vue` with live API data (runs, tools, admin stats)
- CSS refactored to use HuleEdu design tokens (`--huleedu-*` variables)
- Layout structure aligned with HuleEdu: landing logo-only, desktop sidebar + top bar, mobile header + drawer; top bar uses canvas background + navy text.

### App.vue Refactor (694 → 119 LoC)

- Extracted layout components to enforce <500 LoC rule:
  - `components/auth/LoginModal.vue` - Login form + modal
  - `components/layout/AuthLayout.vue` - Mobile header + sidebar + topbar + slot
  - `components/layout/AuthSidebar.vue` - Brand + nav + mobile footer
  - `components/layout/AuthTopBar.vue` - Desktop user info + logout
  - `components/layout/LandingLayout.vue` - Landing header + slot
- `App.vue` now 119 lines: layout orchestration, auth state, route guards only
- Verified: `pnpm -C frontend --filter @skriptoteket/spa typecheck && lint` pass

### ST-11-16 (editor workflow actions)

- API workflow endpoints added in `src/skriptoteket/web/api/v1/editor.py` (submit review, publish, request changes, rollback) + new DTOs.
- SPA header action strip + modal workflow actions in `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Composable logic in `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.ts`.
- Tests added in `tests/unit/web/test_editor_api_routes.py` (workflow responses + toast cookies).
- Playwright E2E script: `scripts/playwright_st_11_16_editor_workflow_actions_e2e.py`.
- Playwright config reads `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE` from dotenv in `scripts/_playwright_config.py`.
- Mini-IDE refactor in `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`: action bar (Spara + ändringssammanfattning + Åtgärder), editor toolbar (Startfunktion dropdown + Öppna sparade/Redigera metadata), status line cleanup.
- New components: `frontend/apps/skriptoteket/src/components/editor/EntrypointDropdown.vue`, `WorkflowActionsDropdown.vue`, `VersionHistoryDrawer.vue`, `MetadataDrawer.vue`.
- Copy updates: “Begär publicering” confirm text; save button label now “Spara”.
- Playwright ST-11-16: added debug screenshot on open-editor failure (`open-editor-failure.png`).

### ST-11-18 (maintainers + editor UX)

- Editor API: maintainer list/add/remove endpoints in `src/skriptoteket/web/api/v1/editor.py`; tests in `tests/unit/web/test_editor_api_routes.py`.
- SPA: drawer-based maintainer management (`MaintainersDrawer.vue`, `useToolMaintainers.ts`) with button “Redigeringsbehörigheter” and title “Ändra redigeringsbehörigheter”.
- History drawer: rollback button for archived versions (superuser) + soft-load version switch via `?version=` (no refresh).
- Script bank seeding now dedupes on normalized title+summary and reuses existing tool (`src/skriptoteket/cli/main.py`).

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
- Story docs aligned: `docs/backlog/stories/story-11-21-unified-landing-page.md`; ST-11-22 implemented (remove `/login` route; modal-only login).

### Phase 4 story review (ST-11-15..19)

- ST-11-17/19 done + help panel wired in SPA (help button moved into mobile hamburger; `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`, `frontend/apps/skriptoteket/src/components/help/HelpButton.vue`, `frontend/apps/skriptoteket/src/components/help/useHelp.ts`, `frontend/apps/skriptoteket/src/App.vue`, `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue`, `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`, `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`, `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue`); story docs updated (`docs/backlog/stories/story-11-17-tool-metadata-editor.md`, `docs/backlog/stories/story-11-19-help-framework.md`).
- Docs contract check: `pdm run docs-validate` (pass).

### ST-11-20 (taxonomy editor wiring)

- Taxonomy API + repo wiring in `src/skriptoteket/web/api/v1/editor.py` + catalog handlers/repos.
- SPA taxonomy editor in `MetadataDrawer.vue` / `useToolTaxonomy.ts`; types regenerated via `pdm run fe-gen-api-types`.

### Verification

- Tests: `pdm run pytest tests/unit/application/catalog/handlers/test_list_tool_taxonomy.py tests/unit/application/catalog/handlers/test_update_tool_taxonomy.py tests/unit/web/test_editor_api_routes.py tests/integration/infrastructure/repositories/test_catalog_repository.py`
- Live check (2025-12-23): `pdm run python -m scripts.playwright_spa_editor_metadata_check --base-url http://127.0.0.1:5173` (edit title/summary, title required, reload persists, restore original)
- Live check (2025-12-23): `pdm run dev` + `pdm run fe-dev`; `BASE_URL=http://127.0.0.1:5173 pdm run python -m scripts.playwright_st_11_19_help_mobile_menu_check` (mobile hamburger help; screenshot `.artifacts/st-11-19-help-mobile-menu/help-in-mobile-menu.png`).
- Live check (2025-12-23): `pdm run python -m scripts.playwright_st_11_21_login_modal_e2e --base-url http://127.0.0.1:5173` (verifies `/login` redirects to `/` and opens modal; artifacts in `.artifacts/st-11-21-login-modal-e2e/`)
- Frontend: `pnpm -C frontend --filter @skriptoteket/spa typecheck`, `pnpm -C frontend --filter @skriptoteket/spa lint`
- UI check: `/admin/tools` + taxonomy GET/PATCH on `/api/v1/editor/tools/{tool_id}/taxonomy` confirmed via Vite.
- Live check (2025-12-22): `pdm run python -m scripts.playwright_st_11_15_spa_my_tools_e2e --base-url http://127.0.0.1:5173`
- Live check (2025-12-23): `pdm run python -m scripts.playwright_st_11_16_editor_workflow_actions_e2e --base-url http://127.0.0.1:5173` (escalated) succeeded; artifacts in `.artifacts/st-11-16-editor-workflow-actions/`.
- Live check (2025-12-23): `pdm run python -m scripts.playwright_st_11_18_editor_maintainers_e2e --base-url http://127.0.0.1:5173` (soft version switch via `?version=` + add/remove maintainer; screenshots in `.artifacts/st-11-18-editor-maintainers/`).

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
- **Rule**: All Vue files must be <500 LoC. Use composables for logic, components for UI.

## Next Steps

### EPIC-11 Complete
- ST-11-13 cutover deployed (2025-12-23)
- All SSR/HTMX code deleted, SPA serving all routes

### Later
- EPIC-12: Start SPA-only UX stories (ST-12-02/03/04) now that ST-11-13 is deployed

## Historical (2025-12-21)

Completed in prior sessions (see `.agent/readme-first.md` for details):

- ST-08-01/02/03: Help framework + login help + home index
- ST-09-02: CSP enforcement at nginx
- ST-06-07: Admin toast notifications
- ST-10-08/09/10: SPA islands toolchain, editor island, runtime island
- ST-11-01/02: Frontend workspace + UI library scaffold
- ST-11-04: API v1 + OpenAPI→TypeScript
- ST-11-05: SPA auth + route guards
