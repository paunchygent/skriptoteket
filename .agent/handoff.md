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
- Backend now: ST-10-06 done; fonts added to Dockerfiles for PDF generation
- Frontend now: N/A (completed work moved to `.agent/readme-first.md`)

## 2025-12-21

- Test fixes: removed future annotations from route modules; updated ist_vh_mejl_bcc to Contract v2; added `json.dumps()` to migration test JSONB
- Docker fonts: `fontconfig`, `fonts-liberation2`, `fonts-dejavu-core`, `fonts-freefont-ttf`, `fonts-noto-core` in both Dockerfiles

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
- UI smoke (Playwright): `pdm run ui-smoke` (requires local dev server + `.env` bootstrap credentials; does not create users).
- Quality gates: `pdm run lint`.
- Typecheck: `pdm run typecheck`.
- Unit tests: `pdm run pytest tests/unit/domain/scripting/ui` + `pdm run pytest tests/unit/infrastructure/runner/test_result_contract.py tests/unit/infrastructure/runner/test_docker_runner.py tests/unit/application/test_scripting_execute_tool_version_handler.py tests/unit/domain/scripting/test_models.py`.
- Migration idempotency: `pdm run pytest -m docker --override-ini addopts='' tests/integration/test_migration_0008_tool_runs_ui_payload_idempotent.py tests/integration/test_migration_0009_tool_sessions_idempotent.py`.
- Live check (2025-12-20): `pdm run db-upgrade`; login via curl cookie jar; `/browse/gemensamt/ovrigt` shows curated app → open `/apps/demo.counter` → Starta → Öka (step=2) → Spara som fil (action_id=`export`) → file stored at `ARTIFACTS_ROOT/<run_id>/output/counter.txt` and downloadable via `/my-runs/<run_id>/artifacts/output_counter_txt` (200).
- Verified (2025-12-20): `pdm run lint`, `pdm run typecheck`, `pdm run pytest tests/unit/application/scripting/handlers/test_interactive_tool_api.py tests/unit/infrastructure/runner/test_artifact_manager.py`, `pdm run docs-validate`.

## Known issues / risks

- `vega_lite` restrictions are not implemented yet; do not accept/render vega-lite outputs until restrictions exist (ADR-0024).
- Dev DB can get bloated with test accounts: avoid creating new superusers for UI checks (reuse `.env` bootstrap account).
- SSR action forms are minimal: no required/default/placeholder/help text yet; supported types match contract allowlist.

## Next steps (recommended order)

- Frontend: improve SSR action form UX (required/defaults/help text, tighter layout) while keeping the allowlists intact.
- Backend: if multi-context sessions are needed, decide how to correlate `tool_sessions.context` ↔ tool runs (currently latest_run_id is computed from `tool_runs` per tool+user).
- Backend: confirm vega-lite approach (implement restrictions vs keep blocked); current implementation blocks `vega_lite` outputs with a system notice.

