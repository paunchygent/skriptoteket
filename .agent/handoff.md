# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-28
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

## Verification

- Docs: `pdm run docs-validate` (pass)
- Format: `pdm run format` (pass)
- Lint: `pdm run lint` (pass)
- Typecheck: `pdm run typecheck` (pass)
- Tests: `pdm run test` (pass)
- Migration idempotency: `pdm run pytest -m docker tests/integration/test_migration_0019_draft_locks_idempotent.py` (pass)
- OpenAPI types: `pdm run fe-gen-api-types` (pass)
- SPA build: `pdm run fe-build` (pass)
- SPA typecheck: `pdm run fe-type-check` (pass)
- SPA lint: `pdm run fe-lint` (pass)
- UI (editor): `pdm run ui-editor-smoke` (pass; artifacts in `.artifacts/ui-editor-smoke/`; Playwright required escalation on macOS)

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
