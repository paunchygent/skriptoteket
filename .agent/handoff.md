# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-29
- Branch / commit: `main` (`440ae14`)
- Current sprint: `SPR-2026-01-05 Tool Editor Vertical Slice` (EPIC-14)
- Production: Full Vue SPA (unchanged)
- Completed: EPIC-14 Admin Tool Authoring (ST-14-01/14-02) done

## Current Session (2025-12-28)

- ST-14-07 draft head locks implemented end-to-end (API + enforcement + tests).
  - Config: `src/skriptoteket/config.py` (`DRAFT_LOCK_TTL_SECONDS`).
  - Helpers + handlers: `src/skriptoteket/application/scripting/draft_lock_checks.py`, updates in
    `src/skriptoteket/application/scripting/handlers/run_sandbox.py`,
    `src/skriptoteket/application/scripting/handlers/start_sandbox_action.py`,
    `src/skriptoteket/application/scripting/handlers/save_draft_version.py`,
    `src/skriptoteket/application/scripting/handlers/create_draft_version.py`.
  - API: `src/skriptoteket/web/api/v1/editor.py` (lock request/response, acquire/release endpoints,
    boot response lock metadata).
  - DI: `src/skriptoteket/di/scripting.py`.
  - Tests: `tests/unit/application/scripting/handlers/test_draft_lock_handler.py`,
    `tests/unit/application/scripting/handlers/test_run_sandbox_handler.py`,
    `tests/unit/application/scripting/handlers/test_start_sandbox_action_handler.py`,
    `tests/unit/application/test_scripting_draft_handlers.py`,
    `tests/unit/web/test_editor_draft_lock_api.py`,
    `tests/unit/web/test_api_v1_auth_and_csrf_routes.py`.
- Migration idempotency: fixed `tests/integration/test_migration_0019_draft_locks_idempotent.py` (tz-aware datetime).
- OpenAPI types + SPA build: `frontend/apps/skriptoteket/src/api/openapi.d.ts`, `src/skriptoteket/web/static/spa/` regenerated.
- Docs alignment: split-phase notes + review updates in
  `docs/adr/adr-0038-editor-sandbox-interactive-actions.md`,
  `docs/adr/adr-0044-editor-sandbox-preview-snapshots.md`,
  `docs/backlog/stories/story-14-03-sandbox-next-actions-parity.md`,
  `docs/backlog/stories/story-14-06-editor-sandbox-preview-snapshots.md`,
  `docs/backlog/epics/epic-14-admin-tool-authoring.md`,
  `docs/backlog/reviews/review-epic-14-editor-sandbox-preview.md`.
- ST-14-06 backend snapshots: migration + models/repos + handlers + API contracts + CLI cleanup.
  - Migration: `migrations/versions/0020_sandbox_snapshots.py`.
  - Domain/protocols: `src/skriptoteket/domain/scripting/sandbox_snapshots.py`,
    `src/skriptoteket/protocols/sandbox_snapshots.py`.
  - Infra/DI: `src/skriptoteket/infrastructure/db/models/sandbox_snapshot.py`,
    `src/skriptoteket/infrastructure/repositories/sandbox_snapshot_repository.py`,
    `src/skriptoteket/di/infrastructure.py`, `src/skriptoteket/di/scripting.py`.
  - Handlers/API: `src/skriptoteket/application/scripting/handlers/run_sandbox.py`,
    `src/skriptoteket/application/scripting/handlers/start_sandbox_action.py`,
    `src/skriptoteket/web/api/v1/editor/sandbox.py`,
    `src/skriptoteket/web/api/v1/editor/runs.py`.
  - CLI/config: `src/skriptoteket/cli/main.py`, `src/skriptoteket/config.py`.
- ST-14-07 SPA lock UX: added draft lock acquisition/heartbeat + read-only gating + force takeover banner.
  - New: `frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`,
    `frontend/apps/skriptoteket/src/components/editor/DraftLockBanner.vue`.
  - Read-only gating: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`,
    `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`,
    `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`,
    `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`,
    `frontend/apps/skriptoteket/src/components/editor/InstructionsDrawer.vue`.
  - Tracker: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md` (ST-14-07 checkboxes).
- ST-14-04 sandbox input_schema parity + snapshot payload wiring.
  - New composable: `frontend/apps/skriptoteket/src/composables/editor/useEditorSchemaParsing.ts`.
  - New components: `frontend/apps/skriptoteket/src/components/editor/SandboxInputPanel.vue`,
    `frontend/apps/skriptoteket/src/components/editor/SandboxRunnerActions.vue`.
  - Updated: `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`,
    `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`,
    `frontend/apps/skriptoteket/src/composables/tools/useToolInputs.ts`.
- Sandbox settings decisions recorded in docs (endpoint shape, settings service wrapper,
  ExecuteToolVersion settings_context override, new useSandboxSettings composable).
  - ADR addendum: `docs/adr/adr-0045-sandbox-settings-isolation.md`.
  - Story updates: `docs/backlog/stories/story-14-05-editor-sandbox-settings-parity.md`,
    `docs/backlog/stories/story-14-08-editor-sandbox-settings-isolation.md`.
  - Sprint note: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`.
- Suggestions: added a small help toggle “sticky note” on `/suggestions/new` beside the description field.
  - UI: `frontend/apps/skriptoteket/src/views/SuggestionNewView.vue`.
- SPA: cohesive route transitions (fade-only, `mode="out-in"`), opt-out for editor routes, suppress on auth redirects to avoid “shutter” artifacts (esp. on `/my-runs` + `/my-tools`).
  - Layout: `frontend/apps/skriptoteket/src/App.vue`.
  - Styles: `frontend/apps/skriptoteket/src/assets/main.css`.
  - Suppress helper: `frontend/apps/skriptoteket/src/composables/usePageTransition.ts`.
  - Opt-out meta: `frontend/apps/skriptoteket/src/router/routes.ts`.
  - Login redirect fix: `frontend/apps/skriptoteket/src/components/auth/LoginModal.vue` (emit `success` before `close`).
- Smoke + typecheck fixes:
  - UI smoke now anchors on `Indata (JSON)` and allows optional file picker: `scripts/playwright_ui_editor_smoke.py`.
  - Mypy invariance fix in snapshot handler tests: `tests/unit/application/scripting/handlers/test_run_sandbox_handler_snapshots.py`,
    `tests/unit/application/scripting/handlers/test_start_sandbox_action_handler_snapshots.py`.
- Ops: installed sandbox snapshot cleanup units on `hemma` and enabled timer.
  - Systemd: `/etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service`,
    `/etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer`.
  - Runbook reorganized + updated: `docs/runbooks/runbook-home-server.md`.
- Docs: observability runbook split into index + tool-specific guides.
  - New: `docs/runbooks/runbook-observability.md`,
    `docs/runbooks/runbook-observability-logging.md`,
    `docs/runbooks/runbook-observability-metrics.md`,
    `docs/runbooks/runbook-observability-grafana.md`,
    `docs/runbooks/runbook-observability-tracing.md`.
  - Updated references in: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`,
    `docs/backlog/stories/story-07-05-observability-stack-deployment.md`,
    `docs/backlog/stories/story-12-06-session-file-cleanup.md`,
    `docs/backlog/stories/story-17-04-jaeger-public-access.md`,
    `docs/backlog/stories/story-17-05-runbook-verification.md`,
    `docs/runbooks/runbook-home-server.md`.
  - Docs hygiene: fixed missing ADR frontmatter owners in `docs/adr/adr-0048-linter-context-and-data-flow.md`.
- ST-17-06 metrics + dashboard:
  - Metrics: `skriptoteket_active_sessions`, `skriptoteket_logins_total`, `skriptoteket_users_by_role` in
    `src/skriptoteket/observability/metrics.py`.
  - Login instrumentation + metrics scrape updates in
    `src/skriptoteket/application/identity/handlers/login.py`,
    `src/skriptoteket/web/routes/observability.py`,
    `src/skriptoteket/infrastructure/repositories/session_repository.py`,
    `src/skriptoteket/infrastructure/repositories/user_repository.py`,
    `src/skriptoteket/protocols/identity.py`.
  - Grafana: `observability/grafana/provisioning/dashboards/skriptoteket-user-activity.json`.
  - Story status: `docs/backlog/stories/story-17-06-user-session-metrics.md` (done).
- ST-14-05/08 manual checks automation:
  - Editor sandbox settings E2E updated for lock acquire + settings toggle targeting + isolation check:
    `scripts/playwright_st_14_05_editor_sandbox_settings_e2e.py`.
- ST-14-03 manual verification:
  - New Playwright E2E for html-to-pdf preview next_actions in editor sandbox:
    `scripts/playwright_st_14_03_editor_sandbox_html_to_pdf_preview_e2e.py`.

## Verification

- Docs: `pdm run docs-validate` (pass)
- Re-run (2025-12-29): `pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run docs-validate` (pass)
- Format: `pdm run format` (pass)
- Lint: `pdm run lint` (pass)
- Typecheck: `pdm run typecheck` (pass)
- Tests: `pdm run test` (pass)
- Migration idempotency: `pdm run pytest -m docker tests/integration/test_migration_0019_draft_locks_idempotent.py` (pass)
- Tests: `pdm run pytest tests/unit/web/test_editor_sandbox_api.py` (pass)
- Tests: `pdm run pytest tests/integration/infrastructure/repositories/test_sandbox_snapshot_repository.py tests/integration/cli/test_cleanup_sandbox_snapshots.py` (pass)
- OpenAPI types: `pdm run fe-gen-api-types` (pass)
- SPA build: `pdm run fe-build` (pass)
- SPA typecheck: `pdm run fe-type-check` (pass)
- SPA lint: `pdm run fe-lint` (pass)
- UI (editor): `pdm run ui-editor-smoke` (pass; artifacts in `.artifacts/ui-editor-smoke/`; Playwright required escalation on macOS)
- UI (suggestion-new): `pdm run python -m scripts.playwright_suggestion_new_smoke` (pass; artifacts in `.artifacts/ui-smoke/`; Playwright required escalation on macOS)
- UI (nav transitions): `pdm run python -m scripts.playwright_nav_transitions_smoke --base-url http://127.0.0.1:5173` (pass; artifacts in `.artifacts/ui-smoke/`; Playwright required escalation on macOS)
- Docs: `pdm run docs-validate` (pass; sprint tracker update)
- Live check: `pdm run dev` (port 8000 already in use), `pdm run fe-dev` (port 5173 already in use)
- Live check: `curl -I http://127.0.0.1:5173/` (200), `curl -I http://127.0.0.1:5173/admin/tools` (200)
- Re-run (2025-12-29): `pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run fe-gen-api-types`,
  `pdm run fe-type-check`, `pdm run fe-lint` (all pass).
- UI (editor): `pdm run ui-editor-smoke` (pass; artifacts in `.artifacts/ui-editor-smoke/`; Playwright required escalation on macOS)
- Live check: `curl -I http://127.0.0.1:8000/health` (405 on HEAD; backend responding)
- Docs: `pdm run docs-validate` (pass)
- Seed: `pdm run seed-script-bank --slug demo-settings-test --sync-code` (pass)
- UI (editor settings): `pdm run python -m scripts.playwright_st_14_05_editor_sandbox_settings_e2e` (pass; artifacts in `.artifacts/st-14-05-editor-sandbox-settings-e2e`; Playwright required escalation on macOS)
- Seed: `pdm run seed-script-bank --slug html-to-pdf-preview` (pass)
- UI (html-to-pdf preview): `pdm run python -m scripts.playwright_st_14_03_editor_sandbox_html_to_pdf_preview_e2e` (pass; artifacts in `.artifacts/st-14-03-editor-sandbox-html-to-pdf-preview-e2e`; Playwright required escalation on macOS)

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000
pdm run fe-dev              # SPA 127.0.0.1:5173

# Quality gates
pdm run format
pdm run lint
pdm run typecheck
pdm run test

# Playwright
pdm run ui-editor-smoke
```

## Known Issues / Risks

- Playwright Chromium may require escalated permissions on macOS (MachPort permission errors).

## Next Steps

- If editor UX changes are needed (read-only state or lock acquisition), verify manually in SPA dev and record steps here.
