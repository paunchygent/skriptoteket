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

- Date: 2025-12-20
- Branch / commit: `main` @ `9308cd6` (dirty working tree)
- Current sprint: `docs/backlog/sprints/sprint-2025-12-22-ui-contract-and-curated-apps.md`
- Backend now: ST-10-02 (tool sessions + optimistic concurrency) is next
- Frontend now: N/A (completed work moved to `.agent/readme-first.md`)

## 2025-12-19 ST-07-02 Health & Metrics (DONE)

**Story:** `docs/backlog/stories/story-07-02-healthz-and-metrics-endpoints.md`

Implementation (HuleEdu singleton pattern):
- `src/skriptoteket/observability/metrics.py` - Prometheus metrics singleton
- `src/skriptoteket/observability/health.py` - Health check logic with 2s DB timeout
- `src/skriptoteket/web/middleware/metrics.py` - HTTP metrics middleware (uses singleton)
- `src/skriptoteket/web/routes/observability.py` - `/healthz` and `/metrics` endpoints
- `compose.yaml` + `compose.prod.yaml` - Updated healthcheck URL to `/healthz`
- `pyproject.toml` - Added `prometheus-client>=0.20.0`
- `docs/runbooks/runbook-observability-logging.md` - Added Health/Metrics sections

## 2025-12-19 ST-07-04 Logging Redaction (DONE)

- Redaction processor: `src/skriptoteket/observability/logging.py`
- Tests: `tests/unit/observability/test_logging_redaction.py`
- Policy: `docs/runbooks/runbook-observability-logging.md`

## 2025-12-19 ST-05-12 Mobile Editor Scroll Follow-up (DONE)

- DONE: verified on real iOS device in deployed app (Testyta + Mina verktyg); story marked `done` in `docs/backlog/stories/story-05-12-mobile-editor-ux.md`.

## 2025-12-19 UI minor consistency fixes (IN PROGRESS)

- Home/login confirmation: controlled line breaks + safe email wrapping in `src/skriptoteket/web/templates/home.html`.
- Browse lists: add spacing between long labels and arrow in `src/skriptoteket/web/static/css/app/components.css`.
- Buttons: remove hover color-swap (no burgundy→navy swap), add amber hover outline/border in `src/skriptoteket/web/static/css/app/buttons.css`.
- Mobile nav: style hamburger “Logga ut” as a proper secondary button (navy outline) + amber hover in `src/skriptoteket/web/templates/base.html` + `src/skriptoteket/web/static/css/app/components.css`.
- Verification: `pdm run ui-smoke` (Playwright: iPhone + desktop hover) → screenshots in `.artifacts/ui-smoke/`.

## 2025-12-19 ST-05-12 Mobile Editor UX Issues (DONE)

- Completed; details live in `docs/backlog/stories/story-05-12-mobile-editor-ux.md`.

## 2025-12-19 ST-05-11 Hamburger Menu Fix (DONE)

- Completed; details live in `docs/backlog/stories/story-05-11-hamburger-htmx-bug.md`.

## What changed

- This handoff is intentionally compressed to current sprint-critical work only (see `.agent/readme-first.md` for history).
- Runner: contract v2 result.json only (no v1): `runner/_runner.py`.
- App: strict v2 parsing + contract violations raise `DomainError(INTERNAL_ERROR)`: `src/skriptoteket/infrastructure/runner/result_contract.py`, `src/skriptoteket/infrastructure/runner/docker_runner.py`.
- App: normalize + persist `tool_runs.ui_payload` (only via `DeterministicUiPayloadNormalizer`): `src/skriptoteket/application/scripting/handlers/execute_tool_version.py`, `src/skriptoteket/domain/scripting/models.py`, `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`.
- DB: migration `0008_tool_runs_ui_payload` + idempotency test `tests/integration/test_migration_0008_tool_runs_ui_payload_idempotent.py`.
- UI: run results render from `run.ui_payload.outputs` via `src/skriptoteket/web/templates/partials/ui_outputs.html` (iframe sandbox for `html_sandboxed`).
- Typing: OpenTelemetry stubs + no-`Any` tracing facade fixes: `stubs/opentelemetry/`, `src/skriptoteket/observability/tracing.py`.

### Current session (EPIC-05 Responsive Frontend: ST-05-07, ST-05-08, ST-05-10)

- Archived; completed story details live in `.agent/readme-first.md` + story docs under `docs/backlog/stories/`.

### Previous session (ST-06-08 Editor UI fixes: sizing, borders, CodeMirror init, file input)

- Archived; see `.agent/readme-first.md` (links only) and the story docs.

### Current session (ST-04-04 continuation - Maintainer Admin + My Tools + Rollback)

- Archived; see story docs under `docs/backlog/stories/`.

### Previous session (ST-04-05 User execution of active tools)

- Archived; see story docs under `docs/backlog/stories/`.

### Previous session (ST-04-04 Contributor iteration after publication)

- Archived; see story docs under `docs/backlog/stories/`.

### Current session (ST-06-06 Test warnings hygiene)

- Archived; see `.agent/readme-first.md`.

### Current session (ST-06-05 Web pages router test coverage)

- Archived; see `.agent/readme-first.md`.

### Previous session (ST-04-04 QC)

- Archived; see `.agent/readme-first.md`.

### EPIC-05: HuleEdu Design System Harmonization (IN PROGRESS)

- Not in current sprint scope; see `docs/backlog/epics/epic-05-huleedu-design-harmonization.md`.

### Previous session (ST-04-04 QC)

- Archived; see `.agent/readme-first.md`.

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
- Migration idempotency: `pdm run pytest -m docker --override-ini addopts='' tests/integration/test_migration_0008_tool_runs_ui_payload_idempotent.py`.
- Live check (UI change): `pdm run dev > .artifacts/dev.log 2>&1 &` then `curl -s -o /dev/null -w "%{http_code}\\n" http://127.0.0.1:8000/login` → `200`.
- Verified (2025-12-20): `pdm run typecheck`, `pdm run lint`, `pdm run pytest tests/unit/domain/scripting/ui/test_ui_payload_normalizer.py tests/unit/infrastructure/runner/test_result_contract.py tests/unit/application/test_scripting_execute_tool_version_handler.py`.

## Known issues / risks

- `vega_lite` restrictions are not implemented yet; do not accept/render vega-lite outputs until restrictions exist (ADR-0024).
- Dev DB can get bloated with test accounts: avoid creating new superusers for UI checks (reuse `.env` bootstrap account).
- Next actions (`ui_payload.next_actions`) are persisted but not rendered yet (ST-10-02/ST-10-04 follow-ups).

## Next steps (recommended order)

- Backend: implement ST-10-02 tool sessions (persist normalized `state` + optimistic concurrency).
- Backend: confirm vega-lite approach (implement restrictions vs keep blocked); current implementation blocks `vega_lite` outputs with a system notice.
- Follow-up: render `next_actions` in UI and wire `start_action` (per ADR-0024).

### ST-04-04 COMPLETED

- Archived; see story docs under `docs/backlog/stories/`.

### EPIC-05: Button/UI Consistency Audit (IN PROGRESS)

- Archived/not sprint-critical; see `.agent/readme-first.md`.

### Other

- Keep `.agent/handoff.md` under 200 lines; keep `.agent/readme-first.md` under 300 lines (enforced by pre-commit).

## Notes

- Old/completed story detail belongs in `.agent/readme-first.md` (links only) + `docs/backlog/stories/`.

## 2025-12-19 Security Hardening (EPIC-09)

- Not sprint-critical; see `docs/backlog/epics/epic-09-security-hardening.md` + `docs/runbooks/`.

## 2025-12-17 Production Deployment (COMPLETE)

- Not sprint-critical; keep deployment procedures in `docs/runbooks/` (do not store personal data here).

## 2025-12-17 ST-05-07 Frontend Stabilisering (ny story)

- Completed/archived; see `docs/backlog/stories/story-05-07-frontend-stabilization.md`.

### Nästa sessions uppdrag

- Archived; see story doc.

### Relevanta filer

- Archived; see story doc.

## 2025-12-17 Editor/UI fixes (live check)

- Not sprint-critical; keep canonical live-check recipe in `.agent/readme-first.md` and story docs.

## 2025-12-19 SPR-2025-12-22 Session A (DONE)

- Scope: contract/policy seams only (no DB/API/runner/UI changes).
- Protocol seams: `src/skriptoteket/protocols/scripting_ui.py`
- Contract v2 models: `src/skriptoteket/domain/scripting/ui/contract_v2.py`
- Policy profiles + caps: `src/skriptoteket/domain/scripting/ui/policy.py`
- Normalization result type: `src/skriptoteket/domain/scripting/ui/normalization.py`
- Tests: `tests/unit/domain/scripting/ui/test_policy_profiles.py`, `tests/unit/domain/scripting/ui/test_contract_v2_models.py`
- Docs: `docs/adr/adr-0022-tool-ui-contract-v2.md`, `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`, `docs/backlog/stories/story-10-03-ui-payload-normalizer.md`
