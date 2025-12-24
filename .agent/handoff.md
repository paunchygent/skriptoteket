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
- Branch / commit: `main` (`813da05`)
- Current sprint: `SPR-2025-12-21` (EPIC-11 full SPA migration)
- Stories done: ST-11-01/02/03/04/05/06/07/08/09/10/11/12/13/14/15/16/17/18/19/20/21/22/23, ST-12-02
- Production: Full Vue SPA; `d0e0bd6` deployed 2025-12-23

## Current Session (2025-12-23)

### ST-08-10 Script Editor Intelligence review (design-ready)

- Reviewed ADR + stories; confirmed Lezer-first analysis (regex only where structure doesn’t matter) and entered decisions into docs.
- Key decisions captured in: `docs/adr/adr-0035-script-editor-intelligence-architecture.md`, `docs/backlog/stories/story-08-10-script-editor-intelligence.md`, `docs/backlog/stories/story-08-11-script-editor-intelligence-phase2.md`.
- Implementation notes: entrypoint-aware linting/completions, reactive `extensions` via CodeMirror `Compartment` + `reconfigure`, gated `startCompletion`, add `lintGutter()` in bundle.

### ST-12-02 Native PDF output helper (implemented)

- Runner helper module: `runner/pdf_helper.py` + safe exception `runner/tool_errors.py` (API: `save_as_pdf(html, output_dir, filename) -> str`).
- Runner error summary: `runner/_runner.py` returns safe message for `ToolUserError` (no traceback in `error_summary`).
- Runner image ships helper: `Dockerfile.runner` now copies `runner/` to `/runner/` so scripts can `import pdf_helper`.
- Script author docs updated: `docs/reference/ref-ai-script-generation-kb.md` uses `pdf_helper.save_as_pdf(...)`.
- SPA verification (Playwright): `pdm run python -m scripts.playwright_st_12_02_native_pdf_output_helper_e2e` (artifacts: `.artifacts/st-12-02-native-pdf-output-helper-e2e/`).

### ST-12-03 Personalized tool settings (implemented)

- Tool version schema: `migrations/versions/0014_tool_versions_settings.py`, `src/skriptoteket/domain/scripting/models.py`, `src/skriptoteket/infrastructure/db/models/tool_version.py`.
- Settings API (per user/tool/schema version): `src/skriptoteket/web/api/v1/tools.py`, `src/skriptoteket/application/scripting/handlers/get_tool_settings.py`, `src/skriptoteket/application/scripting/handlers/update_tool_settings.py`.
- Runner injection: `memory.json` + `SKRIPTOTEKET_MEMORY_PATH` via `src/skriptoteket/infrastructure/runner/docker_runner.py` (+ protocol update).
- SPA: Settings panel on tool run (`frontend/apps/skriptoteket/src/views/ToolRunView.vue`, `frontend/apps/skriptoteket/src/composables/tools/useToolSettings.ts`, `frontend/apps/skriptoteket/src/components/tool-run/ToolRunSettingsPanel.vue`).
- Editor: settings schema JSON textarea (`frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`).
- Script author docs: `docs/reference/ref-ai-script-generation-kb.md` (read `memory.json` settings snippet).
- SPA verification (Playwright): `pdm run python -m scripts.playwright_st_12_03_personalized_tool_settings_e2e --base-url http://127.0.0.1:5173` (artifacts: `.artifacts/st-12-03-personalized-tool-settings-e2e/`).

### EPIC-02 Phase 2: Self-Registration & User Profiles (implemented)

- Migration + schema: `migrations/versions/0013_user_profiles_and_security.py`, `src/skriptoteket/infrastructure/db/models/user.py`, new `user_profiles` table/model (`src/skriptoteket/infrastructure/db/models/user_profile.py`).
- Domain/app: `UserProfile` + lockout helpers (`src/skriptoteket/domain/identity/models.py`, `src/skriptoteket/domain/identity/lockout.py`); new handlers for register/profile/password/email; login lockout updates (`src/skriptoteket/application/identity/handlers/*`).
- Infra/DI: profile repo + user repo updates + DI wiring (`src/skriptoteket/infrastructure/repositories/profile_repository.py`, `src/skriptoteket/di/infrastructure.py`, `src/skriptoteket/di/identity.py`); CLI provisioning creates profiles (`src/skriptoteket/cli/main.py`).
- API: `/api/v1/auth/register` + `/api/v1/profile` (GET/PATCH) + `/api/v1/profile/password` + `/api/v1/profile/email` (`src/skriptoteket/web/api/v1/auth.py`, `src/skriptoteket/web/api/v1/profile.py`, `src/skriptoteket/web/router.py`).
- SPA: register/profile views + composable + auth store action + routes/links (`frontend/apps/skriptoteket/src/views/RegisterView.vue`, `frontend/apps/skriptoteket/src/views/ProfileView.vue`, `frontend/apps/skriptoteket/src/composables/useProfile.ts`, `frontend/apps/skriptoteket/src/stores/auth.ts`, `frontend/apps/skriptoteket/src/router/routes.ts`, layout/login modal links).

### EPIC-02 Phase 2 review fixes (2025-12-24)

- Email validation helper + same-email rejection; applied to local user creation + change email (`src/skriptoteket/application/identity/email_validation.py`, `src/skriptoteket/application/identity/local_user_creation.py`, `src/skriptoteket/application/identity/handlers/change_email.py`).
- Lockout now returns ACCOUNT_LOCKED on 5th failed attempt; validation errors mapped to 422 (`src/skriptoteket/application/identity/handlers/login.py`, `src/skriptoteket/web/error_mapping.py`).
- Added unit coverage for register/change-email/lockout (`tests/unit/application/identity/test_register_user_handler.py`, `tests/unit/application/identity/test_change_email_handler.py`, `tests/unit/application/identity/test_login_handler.py`).
- Added migration to widen `alembic_version.version_num` + adjust ordering (`migrations/versions/0014_extend_alembic_version_length.py`, `migrations/versions/0014_tool_versions_settings.py`) + idempotency test (`tests/integration/test_migration_0014_extend_alembic_version_length_idempotent.py`).
- Fixed SPA lint warning in settings schema placeholder quoting (`frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`).

### Mobile Sidebar Right-Side Positioning

- Moved mobile sidebar drawer to slide from right (matches hamburger button position)
- File: `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`
- Changes: `right: 0` + `translateX(100%)` for mobile; desktop unchanged (left sidebar)
- Verified: typecheck + lint pass

### HuleEdu Design Alignment (layout + dashboard)

- SPA layout + dashboard aligned with HuleEdu tokens (grid bg, transparent frame, landing/auth layouts, role-guarded dashboard); key files: `frontend/apps/skriptoteket/src/assets/main.css`, `src/skriptoteket/web/static/css/app/layout.css`, `frontend/apps/skriptoteket/src/App.vue`, `frontend/apps/skriptoteket/src/views/HomeView.vue`.

### App.vue Refactor (694 → 119 LoC)

- Extracted layout components (login modal + landing/auth layouts + sidebar/topbar) to keep `App.vue` small; verified via frontend typecheck + lint.

### ST-11-16 (editor workflow actions)

- Workflow actions (submit review/publish/request changes/rollback): API in `src/skriptoteket/web/api/v1/editor.py`, SPA in `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, tests + Playwright.

### ST-11-18 (maintainers + editor UX)

- Editor API: maintainer list/add/remove endpoints in `src/skriptoteket/web/api/v1/editor.py`; tests in `tests/unit/web/test_editor_api_routes.py`.
- SPA: drawer-based maintainer management (`MaintainersDrawer.vue`, `useToolMaintainers.ts`) with button “Redigeringsbehörigheter” and title “Ändra redigeringsbehörigheter”.
- History drawer: rollback button for archived versions (superuser) + soft-load version switch via `?version=` (no refresh).
- Script bank seeding now dedupes on normalized title+summary and reuses existing tool (`src/skriptoteket/cli/main.py`).
- Follow-up ST-11-23: persisted `owner_user_id` on tools + stricter permissions (admins can’t remove owner; only superuser can add/remove superuser maintainers); maintainer API exposes `owner_user_id` and UI disables invalid removals.
- Policy documented in ADRs: `docs/adr/adr-0005-user-roles-and-script-governance.md`, `docs/adr/adr-0006-identity-and-authorization-mvp.md`.

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

- Editor foundation: `src/skriptoteket/web/api/v1/editor.py`, `src/skriptoteket/web/editor_support.py`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.

### ST-11-14 (admin tools status enrichment)

- ADR-0033; `AdminToolItem` enriched with version status; `AdminToolsView.vue` split into Pågående/Klara with badges.

### ST-11-15 (my-tools contributor dashboard)

- My tools view: `src/skriptoteket/web/api/v1/my_tools.py`, `frontend/apps/skriptoteket/src/views/MyToolsView.vue`, shared `frontend/apps/skriptoteket/src/components/tools/ToolListRow.vue`.

### ST-11-21 (unified landing page + modal-first login)

- Unified landing + modal login: `frontend/apps/skriptoteket/src/views/HomeView.vue`, `frontend/apps/skriptoteket/src/App.vue`, `frontend/apps/skriptoteket/src/router/index.ts` (ST-11-22 removes `/login` route).

### Phase 4 story review (ST-11-15..19)

- ST-11-17/19 done + help panel wired in SPA (help button moved into mobile hamburger; `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`, `frontend/apps/skriptoteket/src/components/help/HelpButton.vue`, `frontend/apps/skriptoteket/src/components/help/useHelp.ts`, `frontend/apps/skriptoteket/src/App.vue`, `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue`, `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`, `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`, `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue`); story docs updated (`docs/backlog/stories/story-11-17-tool-metadata-editor.md`, `docs/backlog/stories/story-11-19-help-framework.md`).
- Docs contract check: `pdm run docs-validate` (pass).

### ST-11-20 (taxonomy editor wiring)

- Taxonomy editor: API in `src/skriptoteket/web/api/v1/editor.py`, SPA in `frontend/apps/skriptoteket/src/components/editor/MetadataDrawer.vue` + `frontend/apps/skriptoteket/src/composables/editor/useToolTaxonomy.ts`.

### Verification

- EPIC-02: `pdm run pytest -m docker --override-ini addopts=''`, `pdm run test tests/unit/application/identity/`, `pdm run db-upgrade`, `pdm run docs-validate`.
- EPIC-02 (2025-12-24): `pdm run pytest -m docker --override-ini addopts=''` (pass).
- EPIC-02 (2025-12-24): `pdm run test tests/unit/application/identity/` (pass).
- EPIC-02 (2025-12-24): `docker compose up -d db && pdm run db-upgrade` (pass).
- Frontend (2025-12-24): `pnpm -C frontend --filter @skriptoteket/spa typecheck` (pass).
- Frontend (2025-12-24): `pnpm -C frontend --filter @skriptoteket/spa lint` (pass).
- Live check (2025-12-23): `pdm run dev` + `pdm run fe-dev` (left running); `curl http://127.0.0.1:5173/register`, `curl http://127.0.0.1:5173/profile`, `curl http://127.0.0.1:8000/healthz`.
- Quality: `pdm run precommit-run` (pass), `pdm run fe-gen-api-types`, `pdm run db-upgrade` (0012).
- Live check (2025-12-23): `pdm run python -m scripts.playwright_st_11_18_editor_maintainers_e2e --base-url http://127.0.0.1:5173` (artifacts: `.artifacts/st-11-18-editor-maintainers/`).
- Live check (2025-12-23): `docker build -f Dockerfile.runner -t skriptoteket-runner:latest .`, `pdm run db-upgrade` (0013), `pdm run python -m scripts.playwright_st_12_02_native_pdf_output_helper_e2e`.
- Prod deploy (2025-12-23): `ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"` + `ssh hemma "docker exec -e PYTHONPATH=/app/src skriptoteket-web pdm run db-upgrade"`.

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
pdm run precommit-run

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

- SPA migration stories and older work: see `.agent/readme-first.md` + story docs under `docs/backlog/stories/`.
