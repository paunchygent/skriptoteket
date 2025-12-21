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

- Date: 2025-12-21
- Branch / commit: `main` @ `66905ee`
- Current sprint: `docs/backlog/sprints/sprint-2025-12-22-ui-contract-and-curated-apps.md`
- Backend now: ST-10-06 done
- Frontend now: ST-10-10 done

## 2025-12-21

- ST-10-08 (SPA islands toolchain): pnpm workspace + Vite/Vue/Tailwind build to `/static` + Jinja manifest integration: `frontend/package.json`, `frontend/pnpm-workspace.yaml`, `frontend/islands/`, `src/skriptoteket/web/vite.py`, `src/skriptoteket/web/templating.py`.
- PDM↔pnpm integration: `pdm run fe-install|fe-dev|fe-build|fe-build-watch|fe-preview|fe-type-check|fe-lint|fe-lint-fix` delegates to pnpm in the `frontend/` workspace: `pyproject.toml`. (ESLint 9 flat config: `frontend/islands/eslint.config.js`.)
- Demo SPA page (`hx-boost="false"` around mount): `/spa/demo` → `src/skriptoteket/web/pages/spa_islands.py`, `src/skriptoteket/web/templates/spa/demo.html`.
- ST-10-09 (editor SPA island MVP): CodeMirror 6 Vue island + JSON save endpoints + HTMX-safe embed on `/admin/tools/{tool_id}` + `/admin/tool-versions/{version_id}`: `frontend/islands/src/entrypoints/editor.ts`, `frontend/islands/src/editor/*`, `src/skriptoteket/web/routes/editor.py`, `src/skriptoteket/web/templates/admin/script_editor.html`, `src/skriptoteket/web/pages/admin_scripting_support.py`, `src/skriptoteket/web/static/css/app/editor.css`, `tests/unit/web/test_editor_api_routes.py`.
- ST-10-10 (runtime SPA island MVP): Vue runtime island renders stored `ui_payload` + `next_actions` on interactive pages and calls `POST /api/start_action` with optimistic concurrency: `frontend/islands/src/entrypoints/runtime.ts`, `frontend/islands/src/runtime/*`, `src/skriptoteket/web/templates/tools/partials/run_result.html`, `src/skriptoteket/web/templates/apps/detail.html`, `src/skriptoteket/web/templates/my_runs/detail.html`.
- Tests: `tests/unit/web/test_vite_assets.py`.

## What changed

- This handoff is intentionally compressed to current sprint-critical work only (see `.agent/readme-first.md` for history).
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

- Contract v2 allowlists (ADR-0022): outputs `notice|markdown|table|json|html_sandboxed` (+ `vega_lite` curated-only); action fields `string|text|integer|number|boolean|enum|multi_enum`.
- Normalizer returns combined result `{ui_payload, state}` via `UiNormalizationResult` (ADR-0024).
- Policy budgets/caps approved (default vs curated) in `src/skriptoteket/domain/scripting/ui/policy.py`.
- `vega_lite` enabled in curated policy now; restrictions MUST be implemented before the platform accepts/renders it (ADR-0024 risk).

## How to run / verify

- Canonical local recipe: see `.agent/readme-first.md` (includes `ARTIFACTS_ROOT` note).
- Frontend build (prod-style): `pdm run fe-install` then `pdm run fe-build` (writes `src/skriptoteket/web/static/spa/manifest.json` + hashed assets).
- Frontend dev (HMR): set `VITE_DEV_SERVER_URL=http://localhost:5173` in `.env` and run `pdm run fe-dev`.
- UI smoke (Playwright): `pdm run ui-smoke` (requires local dev server + `.env` bootstrap credentials; does not create users).
- Editor island smoke (Playwright): `pdm run ui-editor-smoke` (requires Playwright browsers installed + `.env` bootstrap credentials; writes screenshots to `.artifacts/ui-editor-smoke`).
- Runtime island smoke (Playwright): `pdm run ui-runtime-smoke` (requires Playwright browsers installed + `.env` bootstrap credentials; writes screenshots to `.artifacts/ui-runtime-smoke`).
- Quality gates: `pdm run lint`.
- Typecheck: `pdm run typecheck`.
- Unit tests: `pdm run pytest tests/unit/domain/scripting/ui` + `pdm run pytest tests/unit/infrastructure/runner/test_result_contract.py tests/unit/infrastructure/runner/test_docker_runner.py tests/unit/application/test_scripting_execute_tool_version_handler.py tests/unit/domain/scripting/test_models.py`.
- Migration idempotency: `pdm run pytest -m docker --override-ini addopts='' tests/integration/test_migration_0008_tool_runs_ui_payload_idempotent.py tests/integration/test_migration_0009_tool_sessions_idempotent.py`.
- Live check (2025-12-20): `pdm run db-upgrade`; login via curl cookie jar; `/browse/gemensamt/ovrigt` shows curated app → open `/apps/demo.counter` → Starta → Öka (step=2) → Spara som fil (action_id=`export`) → file stored at `ARTIFACTS_ROOT/<run_id>/output/counter.txt` and downloadable via `/my-runs/<run_id>/artifacts/output_counter_txt` (200).
- Live check (2025-12-21): `docker compose up -d db`, `pdm run db-upgrade`, `npm_config_cache=.tmp/npm-cache pdm run fe-build`, then `pdm run ui-editor-smoke` (verifies CodeMirror 6 mounts on `/admin/tools/<tool_id>` and Save creates/saves a version and redirects).
- Live check (2025-12-21): `pdm run ui-runtime-smoke` (verifies runtime island mounts on `/apps/demo.counter` + `/my-runs/<run_id>` + `/tools/<slug>/run`, action updates UI, and concurrency “Uppdatera” refresh path works).
- Verified (2025-12-20): `pdm run lint`, `pdm run typecheck`, `pdm run pytest tests/unit/application/scripting/handlers/test_interactive_tool_api.py tests/unit/infrastructure/runner/test_artifact_manager.py`, `pdm run docs-validate`.

## Known issues / risks

- `vega_lite` restrictions are not implemented yet; do not accept/render vega-lite outputs until restrictions exist (ADR-0024).
- Dev DB can get bloated with test accounts: avoid creating new superusers for UI checks (reuse `.env` bootstrap account).
- SSR action forms are minimal: no required/default/placeholder/help text yet; supported types match contract allowlist.

## Next steps (recommended order)

- Backend: if multi-context sessions are needed, decide how to correlate `tool_sessions.context` ↔ tool runs (currently latest_run_id is computed from `tool_runs` per tool+user).
- Backend: confirm vega-lite approach (implement restrictions vs keep blocked); current implementation blocks `vega_lite` outputs with a system notice.
