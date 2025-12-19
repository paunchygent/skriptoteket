# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).

## Snapshot

- Date: 2025-12-19
- Branch / commit: `main` @ `7315d90`
- Goal of the session: Fix hamburger menu HTMX navigation bug (ST-05-11).

## 2025-12-19 ST-05-11 Hamburger Menu Fix

**Deployed:** commit `7315d90` to production (`hemma.hule.education`)

**Bug fixed:** Hamburger menu stopped working after HTMX `hx-boost` navigation. Worked on first click, failed on subsequent clicks until page reload.

**Root cause:** With `hx-boost="true"`, HTMX swaps only `<main>` content but re-executes `app.js`, attaching duplicate event listeners. Multiple listeners fought for control, breaking the toggle.

**Fix:** Added initialization guard at top of IIFE in `src/skriptoteket/web/static/js/app.js:3-9`:
```javascript
if (window.__huleeduAppInitialized) return;
window.__huleeduAppInitialized = true;
```

**Files changed:**
- `src/skriptoteket/web/static/js/app.js` - Added init guard
- `docs/backlog/stories/story-05-11-hamburger-htmx-bug.md` - Created and marked done

**Verification:** `curl https://skriptoteket.hule.education/static/js/app.js | head -15` shows guard in place.

## What changed

### Current session (EPIC-05 Responsive Frontend: ST-05-07, ST-05-08, ST-05-10)

**ST-05-07 (Frontend stabilization) - VALIDATED:**
- `src/skriptoteket/web/static/css/app/base.css:62-66` - `@supports clamp()` fluid typography confirmed working
- `src/skriptoteket/web/static/css/app/layout.css:14-35` - `@supports dvh` progressive enhancement confirmed working

**ST-05-08 (Responsive header with hamburger menu) - DONE:**
- `src/skriptoteket/web/static/css/app/components.css:409-491` - Added hamburger button styles (44x44px touch target), X animation on expand, mobile nav dropdown
- `src/skriptoteket/web/static/css/app/layout.css:90-103` - Mobile media query hides desktop nav and header separator at <768px
- `src/skriptoteket/web/templates/base.html:36-42` - Hamburger button markup with `aria-expanded`, `aria-controls`
- `src/skriptoteket/web/templates/base.html:51-62` - Mobile nav dropdown with same links as desktop nav
- `src/skriptoteket/web/static/js/app.js:405-421` - Hamburger toggle handler (click toggles `aria-expanded` and `hidden`)

**ST-05-10 (Editor responsive layout) - DONE:**
- `src/skriptoteket/web/static/css/app/editor.css:68-100` - At ≤1024px: flex column layout, sidebar `order: -1` (appears above code), `max-height: 40vh` with scroll, touch targets 44px min-height

**Live verification (Puppeteer screenshots):**
- Mobile (375px): Hamburger visible, menu opens with all nav links, editor sidebar above code
- Tablet (768px): Desktop nav visible, no hamburger
- Desktop (1440px): Full layout, two-column editor

**QC gates:** `pdm run lint` and `pdm run typecheck` both pass.

### Previous session (ST-06-08 Editor UI fixes: sizing, borders, CodeMirror init, file input)

- Layout refactor (less brittle across browsers; avoids `calc(100vh - …)`/JS sizing):
  - `src/skriptoteket/web/static/css/app.css` - make `.huleedu-frame` a flex column + use `100dvh`; editor page uses flex/grid with `min-height: 0` + `minmax(0, 1fr)` to keep CodeMirror scroll inside container; toolbar stays pinned within code card.
  - `src/skriptoteket/web/templates/admin/script_editor.html` - `main_class` now includes `huleedu-editor-page` and editor-only inline styles were moved into CSS classes.
- File input shown twice fix:
  - `src/skriptoteket/web/templates/admin/script_editor.html` - switched to a `<label>` wrapper + visually-hidden native input (no overlay hacks).
  - `src/skriptoteket/web/static/css/app.css` - `.huleedu-file-native` now uses a screen-reader-only pattern; added `:focus-within` outline.
- CodeMirror first-visit init fix under HTMX (`hx-boost`) + modularized JS:
  - `src/skriptoteket/web/templates/base.html` - loads new global `/static/js/app.js`.
  - `src/skriptoteket/web/static/js/app.js` - initializes CodeMirror on `DOMContentLoaded` and `htmx:load`, dynamically loads CodeMirror CSS/JS when a `textarea[data-huleedu-codemirror]` is present, and syncs CodeMirror → `<textarea>` before boosted submits (`submit` capture + `htmx:configRequest`) so “Spara” persists edits.
- Browse flow single-panel width consistency:
  - `src/skriptoteket/web/static/css/app/utilities.css` - `.huleedu-panel` (width + max-width + auto margins) for deterministic panel widths.
  - `src/skriptoteket/web/templates/browse_professions.html` - uses `.huleedu-panel`.
  - `src/skriptoteket/web/templates/browse_categories.html` - uses `.huleedu-panel`.
  - `src/skriptoteket/web/templates/browse_tools.html` - uses `.huleedu-panel`.
- Panel/toast/spinner refinements (cross-browser stability + consistent visuals):
  - `src/skriptoteket/web/static/css/app/utilities.css` - make `.huleedu-panel` a fixed target width (`--huleedu-max-width-2xl`, capped at `100%`) + `display: block`; add `.huleedu-flex-between-start` + `.huleedu-mb-0`.
  - `src/skriptoteket/web/static/css/app/components.css` - tool rows align to top + allow action wrap; toast container aligns to the right and sits below header (avoids overlapping “Logga ut”).
  - `src/skriptoteket/web/static/js/app.js` - toast auto-dismiss is robust via `MutationObserver` on `#toast-container`; CodeMirror refresh scheduled after HTMX swaps.
  - `src/skriptoteket/web/templates/browse_tools.html` - align “Kör” button to top using `.huleedu-flex-between-start`; remove inline `style="margin-bottom:0"`.
  - `src/skriptoteket/web/templates/tools/run.html`, `src/skriptoteket/web/templates/tools/result.html` - wrap in `.huleedu-panel` so tool run pages match other single-panel routes.
  - `src/skriptoteket/web/templates/admin/script_editor.html` - run button uses `.huleedu-btn-icon` for centered spinner.
  - `src/skriptoteket/web/templates/admin/script_editor.html` + `src/skriptoteket/web/static/css/app/editor.css` - run results container scrolls and is height-capped (prevents CodeMirror collapsing after “Testkör”).
  - `src/skriptoteket/web/pages/admin_scripting_runs.py`, `src/skriptoteket/web/pages/tools.py` - run-result toasts use `error` vs `success` based on run status.
  - `src/skriptoteket/web/templates/partials/toast.html` - default `type` now applies even when the value is falsey (prevents unstyled “blank” toasts).
- Header nav:
  - `src/skriptoteket/web/templates/base.html` - added “Mina verktyg” link for contributor+ users (`/my-tools`).
- CSS modularization (replaces brittle monolith):
  - `src/skriptoteket/web/static/css/app.css` is now an entrypoint that `@import`s modules under `src/skriptoteket/web/static/css/app/`.
- Toasts now actually render:
  - `src/skriptoteket/web/toasts.py` - cookie-based “flash toast” helpers (`skriptoteket_toast`).
  - `src/skriptoteket/web/middleware/toasts.py` + `src/skriptoteket/web/app.py` - middleware reads toast cookie into `request.state.toast_*` and clears it after render.
  - `src/skriptoteket/web/templates/base.html` - renders toast on page load; removed inline toast JS.
  - `src/skriptoteket/web/static/js/app.js` - toast auto-dismiss now runs on page load and after HTMX swaps.
  - `src/skriptoteket/web/templates/partials/toast.html` - fixed OOB swap to append a toast element (no duplicate `id="toast-container"`).
  - `src/skriptoteket/web/pages/admin_scripting.py` - sets toast cookie on successful save/create draft/submit review/publish/request changes/metadata save.
- Toasts on run (HTMX partial):
  - `src/skriptoteket/web/templates/admin/partials/run_result_with_toast.html` - returns run result + OOB toast.
  - `src/skriptoteket/web/templates/tools/partials/run_result_with_toast.html` - returns run result + OOB toast.
  - `src/skriptoteket/web/pages/admin_scripting_runs.py` - uses `run_result_with_toast.html` for HTMX sandbox runs.
  - `src/skriptoteket/web/pages/tools.py` - uses `run_result_with_toast.html` for HTMX production runs.
- Run spinners + file input de-brittle:
  - `src/skriptoteket/web/templates/admin/script_editor.html` - “Testkör” now shows spinner during HTMX request.
  - `src/skriptoteket/web/templates/tools/run.html` - “Kör” now shows spinner; removed inline `onchange` and switched to shared file input markup.
  - `src/skriptoteket/web/static/css/app/components.css` - `.htmx-indicator` now wins over spinner display (prevents always-visible spinners).
  - `src/skriptoteket/web/static/css/app/forms.css` - shared file input styling (`.huleedu-file-*`) + truncation (`.huleedu-file-name`).
  - `src/skriptoteket/web/static/css/app/editor.css` - removed file input styles (moved to forms) and made sidebar card independently scrollable (`overflow-y: auto`).
- Scroll robustness:
  - `src/skriptoteket/web/static/css/app/layout.css` - `.huleedu-frame` is now fixed-height + `overflow: hidden`; `.huleedu-main*` scrolls (`overflow-y: auto`) so the editor columns can scroll independently across browsers.

**Live functional check (required for UI changes):**
- `docker compose up -d db`
- `pdm run db-upgrade`
- Create local superuser: `pdm run bootstrap-superuser --email <email> --password <password>`
- Seed at least one tool for editor: `SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL=<email> SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD=<password> pdm run seed-script-bank`
- Seed tools (local dev admin creds): `pdm run seed-script-bank` (requires `SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL` + `SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD`)
- Ensure tool execution works locally:
  - `mkdir -p /tmp/skriptoteket/artifacts`
  - Run server with `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts ...` (default `/var/lib/...` doesn't exist locally)
- Run server on a free port (8000/8001 may be in use locally): `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts uvicorn --app-dir src skriptoteket.web.app:app --reload --host 127.0.0.1 --port 8002`
- Login + fetch editor HTML (placeholders; do not paste real passwords):
  - `curl -c /tmp/cookies.txt -X POST -d "email=<email>&password=<password>" http://127.0.0.1:8002/login`
  - `curl -b /tmp/cookies.txt http://127.0.0.1:8002/admin/tools/<tool_id>` returned `200` and HTML contained `huleedu-editor-page`, `data-huleedu-codemirror="python"`, and `hx-indicator="#sandbox-run-indicator"`.
- Verify browse panel class + modular CSS served:
  - `curl -b /tmp/cookies.txt http://127.0.0.1:8002/browse/` returned `200` and HTML contained `huleedu-card huleedu-panel`.
  - `curl -o /dev/null -w "%{http_code}" http://127.0.0.1:8002/static/css/app/utilities.css` returned `200`.
- Verify CodeMirror save sync hook is served:
  - `curl http://127.0.0.1:8002/static/js/app.js | rg \"htmx:configRequest\"` matches.
- Verify “Mina verktyg” nav + page heading:
  - `curl -b /tmp/cookies.txt http://127.0.0.1:8002/ | rg \"/my-tools\"` matches.
  - `curl -b /tmp/cookies.txt http://127.0.0.1:8002/my-tools | rg \"<h2>Mina verktyg</h2>\"` matches.
- Verify toasts appear after a redirecting action:
  - POST metadata save then GET editor and confirm HTML contains `huleedu-toast` and `data-auto-dismiss` (cookie is cleared by middleware).
- Verify spinners:
  - `tools/run.html` submit shows spinner while request is running (`hx-indicator="#run-indicator"`).
  - `admin/script_editor.html` “Testkör” shows spinner while request is running (`hx-indicator="#sandbox-run-indicator"`).

### Current session (ST-04-04 continuation - Maintainer Admin + My Tools + Rollback)

**Observability / logging (HuleEdu-compatible):**
- Dependencies: `pyproject.toml`, `pdm.lock` - added `structlog`
- Config: `src/skriptoteket/observability/logging.py` - JSON logs with required fields (`timestamp`, `level`, `event`, `service.name`, `deployment.environment`) + callsite; optional OTEL `trace_id`/`span_id`
- Correlation: `src/skriptoteket/web/middleware/correlation.py` - binds `correlation_id` via `structlog.contextvars` and echoes `X-Correlation-ID`
- Web wiring: `src/skriptoteket/web/app.py` - configures logging + adds correlation middleware
- Error logging: `src/skriptoteket/web/middleware/error_handler.py` - logs `DomainError` + unhandled exceptions; includes `correlation_id` in JSON errors
- Structured events: `src/skriptoteket/web/pages/my_runs.py`, `src/skriptoteket/application/scripting/handlers/execute_tool_version.py`, `src/skriptoteket/infrastructure/runner/docker_runner.py`
- Env examples: `.env.example`, `.env.example.prod` - `SERVICE_NAME`, `LOG_LEVEL`, `LOG_FORMAT`
- Docs: `docs/backlog/epics/epic-07-observability-and-operations.md`, `docs/backlog/stories/story-07-01-structured-logging-and-correlation.md`, `docs/adr/adr-0018-observability-structured-logging-and-correlation.md`
- Runbook: `docs/runbooks/runbook-observability-logging.md`
- Reference guide (docs-contract aligned): `docs/reference/reports/ref-external-observability-integration.md`

**User decisions captured:**
- Audit trail: Separate `tool_maintainer_audit_log` table (not columns on main table)
- Navigation: "Mina verktyg" in main header nav (contributors+ only)
- Rollback: Copy-on-rollback (creates new version with next version number, preserves history)

**Migration + Infrastructure:**
- `migrations/versions/0007_tool_maintainer_audit_log.py` - Creates audit log table with indexes
- `tests/integration/test_migration_0007_tool_maintainer_audit_log_idempotent.py` - Idempotency test
- `src/skriptoteket/infrastructure/db/models/tool_maintainer_audit_log.py` - SQLAlchemy model with `MaintainerAuditAction` enum
- `src/skriptoteket/infrastructure/repositories/tool_maintainer_audit_repository.py` - Audit logging methods (`log_assignment`, `log_removal`)

**Repository extensions (already existed, verified):**
- `src/skriptoteket/infrastructure/repositories/tool_maintainer_repository.py`:
  - `list_maintainers(tool_id)` - Returns list of user UUIDs
  - `remove_maintainer(tool_id, user_id)` - Removes maintainer assignment
  - `list_tools_for_user(user_id)` - Returns list of tool UUIDs user maintains

**Commands/Queries added:**
- `src/skriptoteket/application/catalog/commands.py`:
  - `AssignMaintainerCommand(tool_id, user_id, reason?)` / `AssignMaintainerResult`
  - `RemoveMaintainerCommand(tool_id, user_id, reason?)` / `RemoveMaintainerResult`
- `src/skriptoteket/application/catalog/queries.py`:
  - `ListMaintainersQuery(tool_id)` / `ListMaintainersResult`
  - `ListToolsForContributorQuery()` / `ListToolsForContributorResult`
- `src/skriptoteket/application/scripting/commands.py`:
  - `RollbackVersionCommand(version_id)` / `RollbackVersionResult` (moved to domain models.py)

**Domain logic:**
- `src/skriptoteket/domain/scripting/models.py`:
  - Added `RollbackVersionResult` model class
  - Added `rollback_to_version()` function (mirrors `publish_version` pattern)
  - Creates new ACTIVE version with `derived_from_version_id = archived.id`
  - Archives current active if exists

**Handlers created:**
- `src/skriptoteket/application/catalog/handlers/list_maintainers.py` - Admin+ only
- `src/skriptoteket/application/catalog/handlers/assign_maintainer.py` - Admin+ only, validates target is contributor+
- `src/skriptoteket/application/catalog/handlers/remove_maintainer.py` - Admin+ only
- `src/skriptoteket/application/catalog/handlers/list_tools_for_contributor.py` - Contributor+ only, uses actor.id
- `src/skriptoteket/application/scripting/handlers/rollback_version.py` - **Superuser ONLY**

**DI refactored into domain-specific providers (user decision):**
- `src/skriptoteket/di/__init__.py` - Container assembly, exports `create_container()` and all providers
- `src/skriptoteket/di/infrastructure.py` - Database, repositories, core services (Settings, engine, sessionmaker, UoW, all repos)
- `src/skriptoteket/di/identity.py` - Auth handlers (CurrentUserProvider, LoginHandler, LogoutHandler, CreateLocalUserHandler, ProvisionLocalUserHandler)
- `src/skriptoteket/di/catalog.py` - Catalog + maintainer handlers (ListProfessions, ListCategories, ListTools, UpdateToolMetadata, ListMaintainers, AssignMaintainer, RemoveMaintainer, ListToolsForContributor)
- `src/skriptoteket/di/scripting.py` - Scripting handlers (Execute, CreateDraft, SaveDraft, SubmitForReview, Publish, RequestChanges, RunSandbox, RunActiveTool, RollbackVersion)
- `src/skriptoteket/di/suggestions.py` - Suggestion handlers

**Web routes (completed):**
- `src/skriptoteket/web/pages/admin_scripting.py`:
  - `GET /admin/tools/{tool_id}/maintainers` - HTMX partial listing maintainers
  - `POST /admin/tools/{tool_id}/maintainers` - Assign maintainer (form: user_email)
  - `DELETE /admin/tools/{tool_id}/maintainers/{user_id}` - Remove maintainer
  - `POST /admin/tool-versions/{version_id}/rollback` - Superuser only rollback
- `src/skriptoteket/web/pages/my_tools.py` - `GET /my-tools` (Contributor+ only)
- `src/skriptoteket/web/router.py` - Registered my_tools router

**Templates (completed):**
- `src/skriptoteket/web/templates/my_tools.html` - Contributor tool list page
- `src/skriptoteket/web/templates/admin/partials/maintainer_list.html` - HTMX partial for maintainer management
- `src/skriptoteket/web/templates/base.html` - Added "Mina verktyg" nav link for contributors+
- `src/skriptoteket/web/templates/admin/partials/version_list.html` - Added rollback button for superuser on archived versions

**Tests:**
- `tests/integration/web/conftest.py` - Updated for domain-split DI providers
- All 29 web integration tests pass
- `pdm run lint` passes

**Plan file:** `.claude/plans/serialized-spinning-wadler.md` contains full implementation plan (completed)

### Previous session (ST-04-05 User execution of active tools)

- **Templates** (user-facing tool execution):
  - `src/skriptoteket/web/templates/tools/run.html` - Upload form with HTMX execution
  - `src/skriptoteket/web/templates/tools/result.html` - Full-page result wrapper
  - `src/skriptoteket/web/templates/tools/partials/run_result.html` - User-facing result partial (NO stdout/stderr per security requirement)
  - `src/skriptoteket/web/templates/my_runs/detail.html` - Past run view page
  - `src/skriptoteket/web/templates/browse_tools.html` - Added "Kör" button for published tools with active version

- **Design decisions**:
  - Failed runs: Burgundy border (`border-color: var(--huleedu-burgundy)`)
  - Empty artifacts: Hidden completely
  - Loading state: HTMX `htmx-indicator` class
  - User templates hide stdout/stderr; show only `html_output` and `error_summary`

- **Tests**:
  - `tests/unit/application/scripting/handlers/test_run_active_tool.py` (6 unit tests)
  - `tests/integration/web/test_tools_routes.py` (6 integration tests)
  - `tests/integration/web/test_my_runs_routes.py` (6 integration tests)

- **Bug fixes** (during live testing):
  - `.env` requires `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts` for local dev (default `/var/lib/skriptoteket/artifacts` doesn't exist locally)
  - Artifact download links need `hx-boost="false" download` to prevent HTMX interception and trigger native browser download:
    - `src/skriptoteket/web/templates/tools/partials/run_result.html`
    - `src/skriptoteket/web/templates/admin/partials/run_result.html`
  - `src/skriptoteket/web/middleware/error_handler.py` - Replaced debug print statements with proper `logger.exception()` for unhandled exceptions
  - Transaction ownership is now consistent across web + CLI:
    - `src/skriptoteket/infrastructure/db/uow.py` commits/rolls back the active transaction (nested/root) and uses SAVEPOINTs only for nested `async with uow:` blocks
    - `src/skriptoteket/di.py` rolls back any leftover transaction at request end (UoW owns commit)
    - `tests/integration/web/conftest.py` wraps each request in a SAVEPOINT to protect flushed fixture data from app rollbacks

- Story status: `docs/backlog/stories/story-04-05-user-execution.md` set to `done`

### Previous session (ST-04-04 Contributor iteration after publication)

- Implemented explicit tool maintainer assignment (no lineage-based access): `tool_maintainers` + domain/web/app enforcement.
  - Migration + backfill: `migrations/versions/0006_tool_maintainers.py` (+ docker idempotency: `tests/integration/test_migration_0006_tool_maintainers_idempotent.py`)
  - Infra + DI: `src/skriptoteket/infrastructure/db/models/tool_maintainer.py`, `src/skriptoteket/infrastructure/repositories/tool_maintainer_repository.py`, `src/skriptoteket/protocols/catalog.py`, `src/skriptoteket/di.py`
  - Policies: `src/skriptoteket/domain/scripting/policies.py` (contributors: maintainers can view ACTIVE/ARCHIVED + own drafts/in_review)
  - Handlers: maintainer checks in `create_draft_version.py`, `save_draft_version.py`, `submit_for_review.py`, `run_sandbox.py`
  - Web gating: `src/skriptoteket/web/pages/admin_scripting.py`, `src/skriptoteket/web/pages/admin_scripting_support.py`, `src/skriptoteket/web/pages/admin_scripting_runs.py`
  - Test isolation fix: `src/skriptoteket/infrastructure/db/uow.py` uses nested transactions when already in a transaction
  - Docs updated: `docs/backlog/stories/story-04-03-admin-script-editor-ui.md`, `docs/reference/ref-scripting-api-contracts.md`
  - Tests updated: `tests/integration/web/test_admin_scripting_editor_routes.py`, `tests/unit/web/test_admin_scripting_routes.py`

### Current session (ST-06-06 Test warnings hygiene)

- Baseline: `pdm run test -- -q` emitted 18 Starlette `TemplateResponse` DeprecationWarnings.
- Migrated all `templates.TemplateResponse(...)` call sites to the new keyword signature:
  - `src/skriptoteket/web/pages/admin_scripting.py`
  - `src/skriptoteket/web/pages/admin_scripting_runs.py`
  - `src/skriptoteket/web/pages/admin_scripting_support.py`
  - `src/skriptoteket/web/pages/admin_tools.py`
  - `src/skriptoteket/web/pages/browse.py`
  - `src/skriptoteket/web/pages/suggestions.py`
  - `src/skriptoteket/web/middleware/error_handler.py`
- Updated the usage example in `src/skriptoteket/web/templates/partials/toast.html`.
- No new `filterwarnings` needed (kept existing narrow ignores for dependency internals).
- Results: `pdm run test -- -q` now emits zero warnings; `pdm run docs-validate` passes.
- Story status: `docs/backlog/stories/story-06-06-test-warnings-hygiene.md` set to `done`.

### Current session (ST-06-05 Web pages router test coverage)

- Story status: `docs/backlog/stories/story-06-05-web-pages-test-coverage.md` set to `done`.
- Added behavior-focused unit tests (mock protocols/DI; assert on status/headers/template context):
  - Admin tools pages: `tests/unit/web/test_admin_tools_pages.py`
  - Admin scripting runs pages: `tests/unit/web/test_admin_scripting_runs_pages.py`
  - Suggestions pages: `tests/unit/web/test_suggestions_pages.py`
- Coverage targets met (>70% each):
  - `src/skriptoteket/web/pages/admin_tools.py` (100%)
  - `src/skriptoteket/web/pages/admin_scripting_runs.py` (96%)
  - `src/skriptoteket/web/pages/suggestions.py` (98%)
- Kept unit suite green: updated `tests/unit/application/scripting/handlers/test_run_active_tool.py` to use `RunStatus.SUCCEEDED`
  and current `ToolRun` fields.

### Previous session (ST-04-04 QC)

- Katalog-metadata (titel/sammanfattning) separerat från skript-källkod + enkel admin-UI för uppdatering:
  - `src/skriptoteket/application/catalog/commands.py` (`UpdateToolMetadataCommand/Result`)
  - `src/skriptoteket/application/catalog/handlers/update_tool_metadata.py`
  - `src/skriptoteket/protocols/catalog.py` (`UpdateToolMetadataHandlerProtocol`, `ToolRepositoryProtocol.update_metadata`)
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py` (`update_metadata`)
  - `src/skriptoteket/web/pages/admin_scripting.py` (`POST /admin/tools/{tool_id}/metadata`)
  - `src/skriptoteket/web/templates/admin/script_editor.html` (kort: “Verktygsmetadata”)
- Svensk UI-copy i admin-skripteditor + state/status-labels:
  - `src/skriptoteket/web/ui_text.py` (labels + `ui_error_message`)
  - `src/skriptoteket/web/templating.py` (Jinja-filter: `version_state_label`, `run_status_label`)
  - `src/skriptoteket/web/templates/admin/script_editor.html`
  - `src/skriptoteket/web/templates/admin/partials/version_list.html`
  - `src/skriptoteket/web/templates/admin/partials/run_result.html`
  - `src/skriptoteket/web/pages/admin_scripting.py`, `src/skriptoteket/web/pages/admin_scripting_runs.py` (UI-feltexter)
  - `src/skriptoteket/web/middleware/error_handler.py` (svensk feltext för HTML-svar)
- Docs:
  - `docs/backlog/stories/story-04-04-governance-audit-rollback.md` (noterar metadata-separation + regressiontest)
- Tests:
  - `tests/integration/web/test_admin_tool_metadata_routes.py` (regression: Katalog visar tool-metadata, inte kod)

### EPIC-05: HuleEdu Design System Harmonization (IN PROGRESS)

- **Completed ST-05-01 (CSS/base template)**:
  - `src/skriptoteket/web/templates/base.html` updated with:
    - `hx-boost="true"` for global SPA-like navigation
    - Linked `/static/css/app.css` (HuleEdu tokens + app extensions)
    - Google Fonts preconnects (IBM Plex family)
    - HuleEdu layout structure (`.huleedu-frame`, `.huleedu-header`, `.huleedu-main`)
    - Toast container (`#toast-container`)
  - `src/skriptoteket/web/static/css/huleedu-design-tokens.css` - full design tokens
  - `src/skriptoteket/web/static/css/app.css` - application CSS

- **Completed ST-05-02 (Simple template migration)**:
  - `src/skriptoteket/web/templates/login.html` converted to HuleEdu card, input, and button classes.
  - `src/skriptoteket/web/templates/home.html` converted to HuleEdu card and link classes.
  - `src/skriptoteket/web/templates/error.html` converted to HuleEdu styling with burgundy accent.

- **Completed ST-05-03 (Browse template migration)**:
  - `src/skriptoteket/web/templates/browse_professions.html` converted to `huleedu-card`, `huleedu-list`, `huleedu-list-item`.
  - `src/skriptoteket/web/templates/browse_categories.html` converted with `huleedu-link` for back navigation.
  - `src/skriptoteket/web/templates/browse_tools.html` converted with `huleedu-muted` for summaries and empty state.

- **Completed ST-05-04 (Suggestion template migration)**:
  - `src/skriptoteket/web/templates/suggestions_new.html` converted with `huleedu-checkbox-group`, `huleedu-form-group`, proper label/input classes.
  - `src/skriptoteket/web/templates/suggestions_review_queue.html` converted with status dots (`huleedu-dot-active`/`huleedu-dot-success`), `huleedu-list-item`.
  - `src/skriptoteket/web/templates/suggestions_review_detail.html` converted with `huleedu-radio-group`, `huleedu-checkbox-group`, form styling.

- **Completed ST-05-05 (Admin template migration)**:
  - `src/skriptoteket/web/templates/admin_tools.html` converted with `huleedu-list-item`, button hierarchy (Publicera=burgundy CTA, Avpublicera=secondary), "Öppna skripteditor" changed from link to navy button.
  - `src/skriptoteket/web/templates/admin/script_editor.html` removed inline `<style>` block, uses `huleedu-editor-layout`, `huleedu-pill`, `huleedu-card-flat` for nested sections.
  - `src/skriptoteket/web/templates/admin/partials/version_list.html` converted with `huleedu-list`, `huleedu-badge` for state labels.
  - `src/skriptoteket/web/templates/admin/partials/run_result.html` converted with `huleedu-card` (brutal shadow), `huleedu-pill` for status.
  - `src/skriptoteket/web/static/css/app.css` added `huleedu-min-w-32` utility for consistent button widths.

### Previous session (ST-04-04 QC)

- ST-04-04 docs status updates:
  - `docs/adr/adr-0014-versioning-and-single-active.md` (implementation status)
  - `docs/backlog/stories/story-04-04-governance-audit-rollback.md` (status/progress notes)
- Deferred governance options for future epics:
  - `docs/reference/ref-scripting-governance-deferred-options.md` (hard reject, review queue, decision log, email notifications)
- Story + contracts:
  - `docs/backlog/stories/story-04-03-admin-script-editor-ui.md` (status: done; records UI/asset decisions)
  - `docs/reference/ref-scripting-api-contracts.md` (clarifies v0.1 `/admin/...` is HTML/HTMX UI; JSON DTOs are conceptual)
- Application handlers + commands (draft lifecycle + sandbox):
  - `src/skriptoteket/application/scripting/commands.py`
  - `src/skriptoteket/application/scripting/handlers/publish_version.py`
  - `src/skriptoteket/application/scripting/handlers/request_changes.py`
  - `src/skriptoteket/application/scripting/handlers/create_draft_version.py`
  - `src/skriptoteket/application/scripting/handlers/save_draft_version.py` (expected-parent draft head check)
  - `src/skriptoteket/application/scripting/handlers/submit_for_review.py`
  - `src/skriptoteket/application/scripting/handlers/run_sandbox.py` (reuses `ExecuteToolVersionHandler` with SANDBOX context)
  - `src/skriptoteket/application/scripting/handlers/execute_tool_version.py` (preflight `compile(...)`; `SyntaxError` -> FAILED run without Docker)
- Protocols + DI:
  - `src/skriptoteket/protocols/scripting.py`
  - `src/skriptoteket/protocols/catalog.py` (`ToolRepositoryProtocol.set_active_version_id`)
  - `src/skriptoteket/di.py`
  - `src/skriptoteket/infrastructure/repositories/tool_repository.py` (`PostgreSQLToolRepository.set_active_version_id`)
- Web UI (server-rendered + HTMX):
  - `src/skriptoteket/web/pages/admin_scripting.py` (editor + draft routes; includes publish + request-changes; includes run router)
  - `src/skriptoteket/web/pages/admin_scripting_runs.py` (sandbox run + run refresh + artifact download)
  - `src/skriptoteket/web/pages/admin_scripting_support.py` (shared helpers)
  - `src/skriptoteket/web/router.py` (includes admin scripting pages)
  - `src/skriptoteket/web/app.py` (mounts `/static`)
  - `src/skriptoteket/web/templates/admin/script_editor.html` (adds Review version card for IN_REVIEW + admin/superuser)
  - `src/skriptoteket/web/templates/admin/partials/version_list.html`
  - `src/skriptoteket/web/templates/admin/partials/run_result.html`
  - `src/skriptoteket/web/templates/admin_tools.html` (adds “Öppna skripteditor” link)
  - `src/skriptoteket/web/templates/base.html` (adds HTMX include + extension blocks; fixes checkbox/radio input styling)
  - `src/skriptoteket/web/static/vendor/` (vendored CodeMirror + HTMX; pinned versions in `README.md`)
- Quality fixes uncovered by QC:
  - `src/skriptoteket/infrastructure/runner/docker_runner.py` (mypy-friendly typing for docker client interactions)
  - `tests/unit/infrastructure/runner/test_retention.py`, `tests/unit/infrastructure/runner/test_docker_runner_utils.py`
- Tests:
  - `tests/unit/application/test_scripting_execute_tool_version_handler.py` (runner not called on `SyntaxError`)
  - `tests/unit/application/test_scripting_draft_handlers.py` (draft save concurrency guard)
  - `tests/unit/application/test_scripting_review_handlers.py` (publish + request-changes)
  - `tests/integration/web/test_admin_scripting_review_routes.py` (POST routes)

## Decisions (and links)

- **HuleEdu Design System** (ADR-0017): Adopt full HuleEdu design tokens for future integration compatibility. Uses Google Fonts CDN for IBM Plex family. Grid background pattern at 4% opacity included.
- Editor UX: integrate CodeMirror now (no plain textarea-only MVP); keep `<textarea>` as fallback and for form submission.
- Assets: vendor pinned JS/CSS under `src/skriptoteket/web/static/vendor/` (no CDN at runtime).
- Execution UX: HTMX used for sandbox run result updates (partial HTML under `templates/admin/partials/`).
- Safety: preflight `compile(...)` prevents Docker runs for syntax errors and returns a FAILED run with actionable `error_summary`.
- ST-04-04 publish/reject workflow decisions are pending (reject semantics + review queue + notifications); see `docs/backlog/stories/story-04-04-governance-audit-rollback.md`.

## How to run / verify

- Ensure `.env` has `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts` (required for local tool execution)
- Create artifacts directory: `mkdir -p /tmp/skriptoteket/artifacts`
- Start DB (ran): `docker compose up -d db`
- Run migrations (ran): `pdm run db-upgrade`
- Seed tool (ran): `SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL=... SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD=... PYTHONPATH=src pdm run python -m skriptoteket.cli seed-script-bank --slug ist-vh-mejl-bcc`
- Start app (ran): `PYTHONPATH=src pdm run uvicorn --app-dir src skriptoteket.web.app:app --host 127.0.0.1 --port 8000`
- Live functional check (ran, no secrets/tokens recorded):
  - Unauthenticated `GET /login` returns 200.
  - After login, verified:
    - `GET /admin/tools` returns 200.
    - `GET /admin/tools/<tool_id>` returns 200 (script editor route renders).
  - Run migrations (ran): `pdm run db-upgrade`.
  - Created a temporary admin + session row via one-off `PYTHONPATH=src pdm run python` script.
  - With the session cookie, verified:
    - `GET /admin/tools` returns 200 and includes `<h2>Verktyg</h2>`.
    - `GET /suggestions/new` returns 200 and includes `<h2>Föreslå ett skript</h2>`.
    - `GET /admin/suggestions` returns 200 and includes `<h2>Förslag</h2>`.
    - `GET /` returns 200 (started local server on port 8001).
    - `GET /admin/tool-runs/{random_uuid}` returns 404.
  - UI refinements sanity check (ran, no secrets/tokens recorded):
    - Start app: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts PYTHONPATH=src pdm run uvicorn --app-dir src skriptoteket.web.app:app --host 127.0.0.1 --port 8016`
    - Created a temporary superuser + session row via one-off `PYTHONPATH=src pdm run python` script.
    - With the session cookie, verified these render and include `.huleedu-panel`:
      - `GET /browse/` returns 200 and includes `<h2>Välj yrke</h2>`.
      - `GET /my-tools` returns 200 and includes `<h2>Mina verktyg</h2>`.
      - `GET /suggestions/new` returns 200 and includes `<h2>Föreslå ett skript</h2>`.
      - `GET /admin/suggestions` returns 200 and includes `<h2>Förslag</h2>`.
      - `GET /admin/tools` returns 200 and includes `<h2>Verktyg</h2>`.
      - `GET /tools/<published-slug>/run` returns 200 and wraps content in `.huleedu-panel`.
    - Verified toast HTML renders when `skriptoteket_toast` cookie is present (ensures toast container + markup exists in `base.html`).
- Observability smoke check (ran, no secrets/tokens recorded):
  - Start app: `PYTHONPATH=src pdm run uvicorn --app-dir src skriptoteket.web.app:app --host 127.0.0.1 --port 8010`
  - `GET /login` returns 200 and echoes `X-Correlation-ID` when provided.
  - Logs are JSON and include `timestamp`, `level`, `event`, `service.name`, `deployment.environment`.
- QC (ran): `pdm run lint` and `pdm run typecheck` both pass.
- Docs validation (ran): `pdm run docs-validate` passes.
- Unit tests (ran): `pdm run test tests/unit -q` passes (232 tests).

## Known issues / risks

- `/work` per-run volume does not have a portable per-run size cap (unlike tmpfs); a buggy/malicious script can fill disk.
- docker.sock mount expands blast radius if the app container is compromised (keep production opt-in and hardened).
- Maintainer list partial requires HTMX; script_editor.html sidebar integration still needs implementation (manual HTMX include).

## Next steps (recommended order)

### ST-04-04 COMPLETED

All ST-04-04 work is done:

- [X] DI container refactored into domain-specific providers
- [X] Web routes for maintainer management (list/assign/remove)
- [X] My Tools page (`/my-tools`) for contributors
- [X] Rollback route for superuser
- [X] Templates created (my_tools.html, maintainer_list.html)
- [X] Navigation updated ("Mina verktyg" link)
- [X] Rollback button on archived versions (superuser only)
- [X] `pdm run lint` passes
- [X] `pdm run test tests/integration/web/` passes (29 tests)

**Remaining UI integration:** Add maintainer list HTMX include to `script_editor.html` sidebar for live admin experience.

### EPIC-05: Button/UI Consistency Audit (IN PROGRESS)

**Status**: Stories ST-05-01 through ST-05-06 complete. Refinement pass needed for button consistency.

**Remaining work**:

1. Audit ALL 15 templates for button class consistency (COMPLETED)
2. Ensure uniform `min-width` on action buttons in rows (COMPLETED)
3. Verify header "Logga ut" stays fixed on resize (VERIFIED - flex-shrink: 0 is correct)
4. Verify `suggestions_review_queue.html` matches `admin_tools.html` pattern (VERIFIED - uses huleedu-tool-list)

**Templates to audit** (in priority order):

- [X] `base.html` - header logout button
- [X] `admin_tools.html` - action buttons (partially fixed)
- [X] `suggestions_review_queue.html` - "Öppna" buttons
- [X] `suggestions_review_detail.html` - action buttons
- [X] `admin/script_editor.html` - multiple action buttons
- [X] `admin/partials/version_list.html` - version actions (No buttons found, implicitly consistent)
- [X] `login.html` - "Logga in" CTA
- [X] `suggestions_new.html` - "Skicka förslag" CTA
- [X] Browse templates (3 files) - navigation links (No buttons found, implicitly consistent)

**Button CSS reference** (`app.css` lines 171-229):

- `.huleedu-btn` = burgundy CTA
- `.huleedu-btn-navy` = navy functional
- `.huleedu-btn-secondary` = outline
- `.huleedu-btn-sm` = small variant
- `.huleedu-tool-actions .huleedu-btn { min-width: 130px; }` = row consistency

### Other

1. Implement rollback (Superuser-only) if scope expands (handler + route + UI).
2. Consider artifact size caps (max bytes per file/total) and/or operational disk quotas.

## Notes

- Do not include secrets/tokens in this file.

---

## 2025-12-19 Security Hardening (EPIC-09)

**Completed stories:**
- ST-09-01: HTTP security headers via nginx (done)
- ST-09-03: Firewall audit and cleanup (done)

**Pending:**
- ST-09-02: Content-Security-Policy (Phase 2, requires HTMX/CodeMirror testing)

**Changes deployed to production:**

1. **nginx security headers** added to `~/infrastructure/nginx/conf.d/skriptoteket.conf`:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

2. **Stale UFW rules removed:** Port 5000 (IPv4 + IPv6)

**Verification:**
```bash
curl -sI https://skriptoteket.hule.education/login | grep -iE 'strict|x-frame|x-content|referrer|permissions'
```

**Security grade:** B- → B+ (home server baseline)

**Docs created:**
- `docs/adr/adr-0021-http-security-headers.md`
- `docs/backlog/epics/epic-09-security-hardening.md`
- `docs/backlog/stories/story-09-01-http-security-headers.md`
- `docs/backlog/stories/story-09-02-content-security-policy.md`
- `docs/backlog/stories/story-09-03-firewall-audit.md`

---

## 2025-12-17 Production Deployment (COMPLETE)

**Deployed:** commit `85b7a33` (main) to hemma.hule.education

**Actions performed:**
1. `git pull` + `docker compose -f compose.prod.yaml up -d --build` (159 files changed)
2. Applied migrations: `0006_tool_maintainers`, `0007_tool_maintainer_audit_log`
3. Verified HTTPS: `curl -sI https://skriptoteket.hule.education/login` → 200 OK

**Users provisioned (17 admin accounts):**

| Email | Role |
|-------|------|
| camilla_ahlin@hule.education | admin |
| anders_uvebrant@hule.education | admin |
| katrin_forsgren@hule.education | admin |
| lars_bohman@hule.education | admin |
| karin_lagerstrom@hule.education | admin |
| christina_alstrom@hule.education | admin |
| maria_holmgren@hule.education | admin |
| olof_larsson@hule.education | admin |
| karin_ek_thorbjornsson@hule.education | admin |
| liselotte_akerfelt@hule.education | admin |
| hampus_kvarnliden@hule.education | admin |
| carl_larsson@hule.education | admin |
| jenny_olofsson_reijer@hule.education | admin |
| par_lydmark@hule.education | admin |
| viktor_moller@hule.education | admin |
| fredrik_jacobsson@hule.education | admin |
| johan_stahl@hule.education | admin |

**Total users in production:** 20 (1 superuser, 17 admins, 1 contributor, 1 user)

**Credentials:** Distributed separately to users

---

## 2025-12-17 ST-05-07 Frontend Stabilisering (ny story)

**Story:** `docs/backlog/stories/story-05-07-frontend-stabilization.md` (uppdaterad med validering + patch-förslag)

**Källa:** Frontend-expert analys via repomix-paket (`.claude/repomix_packages/TASK-frontend-review.md`)

**Gjort denna session (implementation + live-check):**

- CSS-integritet verifierad: `components.css` och `utilities.css` är syntaktiskt balanserade; toast “saknad `}`” var **FALSE POSITIVE**.
- Panelbredd implementerad: `.huleedu-panel` använder `--huleedu-content-width` (responsiv `clamp()` min 42rem, max 56rem) och templates migrerade till `.huleedu-panel` (`login.html`, `home.html`, `error.html`, `my_runs/detail.html`, `suggestions_review_detail.html`).
- `dvh`-fallback implementerad: `src/skriptoteket/web/static/css/app/layout.css` stackar `100vh` före `100dvh` (inkl. `calc()` i desktop breakpoint).
- Editor-bräcklighet kartlagd: code-card/editor tenderar att inte krympa och run-result expanderar utan scrollcap; CodeMirror refresh är HTMX events + debounce `setTimeout`.
- Admin-nav UX-fix: `/admin/tools` heter nu “Testyta” (för att skilja från “Mina verktyg”) i `src/skriptoteket/web/templates/base.html` + rubrik i `src/skriptoteket/web/templates/admin_tools.html`.

### Nästa sessions uppdrag

- **Källa till sanning:** följ `docs/backlog/stories/story-05-07-frontend-stabilization.md` (innehåller patch-snuttar + fil:rad).
- **Rekommenderad implementeringsordning (återstår):** editor-stabilisering (CSS, ev ResizeObserver).
- **Beslut (2025-12-17, implementerat):** alla single-column sidor använder responsiv panelbredd via `.huleedu-panel` (min 42rem, max 56rem).
- **Beslut (2025-12-17, implementerat):** byt label i headern för `/admin/tools` från “Verktyg” → “Testyta” (`src/skriptoteket/web/templates/base.html:31`).
- **Metod (för att undvika drift):** repomix kan vara trunkerat; verifiera alltid mot faktiska filer och håll detaljer/patchediff i storyn (inte i handoff).

### Relevanta filer

- Story: `docs/backlog/stories/story-05-07-frontend-stabilization.md`
- Epic: `docs/backlog/epics/epic-05-huleedu-design-harmonization.md`
- Expert-rapport: `docs/reference/reports/ref-frontend-expert-review-epic-05.md`
- Plan: `.claude/plans/vast-sprouting-locket.md`
- Task-beskrivning: `.claude/repomix_packages/TASK-frontend-review.md`
- Repomix-paket: `.claude/repomix_packages/repomix-frontend-architecture-review.xml`

---

## 2025-12-17 Editor/UI fixes (live check)

**Live functional check performed** (per UI/route session rule):

- DB: `pdm run db-upgrade` (no pending migrations).
- Started web server: `pdm run uvicorn --app-dir src skriptoteket.web.app:app --host 127.0.0.1 --port 8018`
- Created a temporary superuser (email only; password not recorded here) via `pdm run bootstrap-superuser`.
- Verified rendered pages (via `curl` with the session cookie):
  - `GET /` renders and includes cache-busted assets `app.css?v=...`, `app.js?v=...`, `htmx.min.js?v=...`.
  - `GET /browse/`, `GET /my-tools`, `GET /admin/tools` render and include `.huleedu-panel` on the primary card.
  - `POST /tools/nonexistent/run` with `HX-Request: true` returns an error alert + OOB toast (`huleedu-toast-error`, `hx-swap-oob="beforeend:#toast-container"`).

- Re-verified after final toast/layout tweaks on port `8019` (same checks as above).

- Re-verified panelbredd + “Testyta” på port `8020`:
  - `GET /login` innehåller `.huleedu-panel` på kortet.
  - Inloggning via `POST /login` (utan CSRF) + cookie.
  - `GET /` och `GET /browse/` renderar utan template-fel.
  - `GET /admin/tools` visar nav-label “Testyta” + rubrik `<h2>Testyta</h2>`.

- Re-verified `vh` fallback för `dvh` på port `8021`:
  - `GET /login` renderar (200).
  - `GET /static/css/app/layout.css` innehåller både `100vh` och `100dvh` samt `calc(100vh - …)` + `calc(100dvh - …)`.

- Re-verified editor-stabilisering på port `8022`:
  - Inloggning via `POST /login` (utan CSRF) + cookie.
  - `GET /admin/tools` renderar och listar verktyg.
  - `GET /admin/tools/{tool_id}` renderar editorn (200) och innehåller `hx-indicator="#sandbox-run-button"` samt tom `#run-result` (för `:empty`-regeln).
  - `GET /static/css/app/editor.css` innehåller `max-height` + `overflow: auto` för `.huleedu-editor-run-result` samt `:empty { display: none; }`.
