# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-02
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: ST-14-01/14-02 done; ST-14-09 done; ST-14-10 done

## Current Session (2026-01-02)

- ST-14-10: schema JSON guardrails only (shared parsing helper + save blocking); schema editor UI actions deferred to ST-14-14.
  - Shared helper: `frontend/apps/skriptoteket/src/composables/editor/schemaJsonHelpers.ts` (JSON array parsing with more actionable errors)
  - Refactors: `useEditorSchemaParsing.ts`, `useScriptEditor.ts` (save uses helper, no drift)
  - Save blocked when schema JSON invalid: `EditorWorkspacePanel.vue` (disabled Save button) + save handler shows parse error
- ST-14-09: schema-only inputs (no `input_schema=null` legacy upload-first); DB `input_schema` columns now NOT NULL DEFAULT `[]` + backfill (SQL NULL + JSON `null`) in `migrations/versions/0023_input_schema_not_null.py`; script bank + SPA updated so file picker appears only when schema includes `{"kind":"file"}`.
- Docs/backlog alignment: updated statuses (ST-14-01/02, ST-06-10, ST-11-01/02/07/08/09/15/16), EPIC-08 active, EPIC-16 active with ST-16-08 pending, added ST-15-02 stub, aligned sprint dates, moved ST-08-17 to `SPR-2026-05-12`, added EPIC-11 implementation summary, refreshed `.agent/readme-first.md`.
- EPIC-14 story alignment (AI-ready foundations): updated ST-14-11/12/17/18/19/20 to support upcoming chat-first AI editing (explicit debug truncation flags + copy bundle, reusable diff viewer, field-aware compare deep links, AI-friendly toolkit conventions).
- Drafted AI continuation stories for chat-first CRUD editing: ST-08-20 (chat drawer), ST-08-21 (structured CRUD edit ops protocol), ST-08-22 (diff preview + apply/undo); added to EPIC-08 and validated docs.
- EPIC-08 + sprint plans: updated EPIC-08 scope to include chat-first AI edits and updated sprint plans (SPR-2026-03-03/03-17/04-28/05-12) with explicit Before/After sections + pacing checklists; `pdm run docs-validate` passes.
- ADRs (AI): added `ADR-0051` (chat-first AI editing) and renumbered the duplicate LLM budgeting ADR to `ADR-0052` (accepted); updated EPIC-08 references, ST-08-18 dependencies, and `docs/backlog/reviews/review-epic-08-ai-completion.md`; `pdm run docs-validate` passes.
- **AI infrastructure deployed**: llama-server (ROCm) + Tabby on hemma for self-hosted code completion.
  - Model: Qwen3-Coder-30B-A3B (MoE, ~18.5GB VRAM); ADR-0050; runbooks in `docs/runbooks/`.
- ST-08-14: AI inline completions MVP (ghost text) wired end-to-end.
  - Backend proxy: `POST /api/v1/editor/completions` in `src/skriptoteket/web/api/v1/editor/completions.py` (auth + CSRF), with protocol-first DI in `src/skriptoteket/di/llm.py`.
  - OpenAI-compatible provider: `src/skriptoteket/infrastructure/llm/openai_provider.py` (chat/completions + Qwen FIM tokens; truncation discard).
  - CodeMirror extension: `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts` (auto-trigger 1500ms, Alt+\\, Tab accept, Escape dismiss, clear-on-change).
- ST-08-16: AI edit suggestions MVP (llama-server only, raw replacement text).
  - Backend endpoint: `POST /api/v1/editor/edits` in `src/skriptoteket/web/api/v1/editor/edits.py` (auth + CSRF).
  - Handler + protocol: `src/skriptoteket/application/editor/edit_suggestion_handler.py`, `src/skriptoteket/protocols/llm.py` (separate edit provider config).
  - UI preview/apply: `frontend/apps/skriptoteket/src/components/editor/EditorEditSuggestionPanel.vue` + `useEditorEditSuggestions.ts`.
  - CodeMirror view exposure: `CodeMirrorEditor.vue` emits `viewReady` for edit-apply transactions.
- ST-08-16 fix (empty suggestions): Qwen edit responses were empty due to stop sequence + fenced outputs.
  - Remove fenced examples from Contract fragment: `src/skriptoteket/application/editor/prompt_fragments.py`.
  - Edit provider uses stop `"\n```"` (avoid immediate stop): `src/skriptoteket/infrastructure/llm/openai_provider.py`.
  - Edit handler unwraps fenced output + accepts raw text: `src/skriptoteket/application/editor/edit_suggestion_handler.py`.
- ST-08-16 context budget fix (llama.cpp `n_ctx=4096`): switch to LLM KB + strict prompt budgeting + graceful 400 handling.
  - System prompt templates: `LLM_COMPLETION_TEMPLATE_ID` / `LLM_EDIT_TEMPLATE_ID` defaults in `src/skriptoteket/config.py` (registry in `src/skriptoteket/application/editor/prompt_templates.py`).
  - Budgeting helper: `src/skriptoteket/application/editor/prompt_budget.py` (selection preserved; trim prefix/suffix first).
  - Handlers: `src/skriptoteket/application/editor/completion_handler.py`, `src/skriptoteket/application/editor/edit_suggestion_handler.py`.
  - Docs: updated env var + budgeting spec in `docs/reference/ref-ai-completion-architecture.md`.
- ST-08-17 drafted: Tabby edit suggestions + prompt A/B evaluation follow-up story.
  - `docs/backlog/stories/story-08-17-tabby-edit-suggestions-ab-testing.md` + epic list update.
- ST-08-18: AI prompt system v1 (templates + contract fragments + validation + template-id logging).
  - Registry: `src/skriptoteket/application/editor/prompt_templates.py` (IDs + required placeholders).
  - Composition/validation: `src/skriptoteket/application/editor/prompt_composer.py` (placeholder resolution + system prompt budget).
  - Code-owned fragments: `src/skriptoteket/application/editor/prompt_fragments.py` (Contract v2 + runner constraints + helpers).
  - Templates: `src/skriptoteket/application/editor/system_prompts/*.txt` (placeholders like `{{CONTRACT_V2_FRAGMENT}}`).
  - Env vars: `LLM_COMPLETION_TEMPLATE_ID`, `LLM_EDIT_TEMPLATE_ID`.
  - Tests: `tests/unit/application/test_ai_prompt_system_v1.py`.
- ST-08-19: live prompt eval harness + admin-only eval headers.
  - Harness: `scripts/ai_prompt_eval/run_live_backend.py` + fixture bank in `scripts/ai_prompt_eval/fixture_bank.py`.
  - Eval headers: `X-Skriptoteket-Eval` on `/api/v1/editor/completions` and `/api/v1/editor/edits`.
- EPIC-06 linter (ST-06-10/11/12): lint panel + navigation keymaps live in intelligence (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketLintPanel.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`); base editor stays generic (`frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`).
- ST-06-13: lint gutter filtering now shows only error/warning markers via `lintGutter({ markerFilter, tooltipFilter })` in `frontend/apps/skriptoteket/src/composables/editor/linter/adapters/codemirror/skriptoteketLinterAdapter.ts` (info/hint still discoverable via lint panel/tooltip).
- ST-06-14: headless linter rule harness + unit tests (EditorState-only) in `frontend/apps/skriptoteket/src/test/headlessLinterHarness.ts` and `frontend/apps/skriptoteket/src/composables/editor/linter/headlessLinterHarness.spec.ts` (syntax error mapping + scope chain variable resolution + entrypoint rule example).
- ST-08-15: Contract diagnostics now emit stable `source` IDs (e.g. `ST_CONTRACT_OUTPUT_KIND_INVALID`) in `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/contractRule.ts`; lint tooltip hides source row for error/warning only via CodeMirror theme in `frontend/apps/skriptoteket/src/composables/editor/linter/adapters/codemirror/skriptoteketLinterAdapter.ts` (lint panel still shows sources).
- Contract copy tweak: invalid output kind message now says "Ogiltig typ" (not "Ogiltigt kind") in `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/contractRule.ts`.
- ST-06-12 E2E: `scripts/playwright_st_06_12_lint_panel_navigation_e2e.py` (opens lint panel, verifies F8/Shift-F8 + Mod-Alt-n/p, checks quick-fix buttons appear in the panel).
- Frontend auth: align register response typing by not reading `csrf_token` from `RegisterResponse` (`frontend/apps/skriptoteket/src/stores/auth.ts`).
- EPIC-14 ongoing: see `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`.
- ST-08-02: robust email verification — registration email send is transactional with retry/backoff + new `EMAIL_SEND_FAILED` error code; SMTP health check runs on startup and is optionally included in `/healthz` via `HEALTHZ_SMTP_CHECK_ENABLED`.
- ST-08-03: email verification frontend route confirmed implemented; story marked `done`.
- Healthz SMTP strict mode: default `HEALTHZ_SMTP_CHECK_ENABLED=true` (and set in `compose.prod.yaml` + `.env.example*`) so `/healthz` includes SMTP when `EMAIL_PROVIDER=smtp`.
- Ops note: documented SMTP-down => `/healthz` 503 troubleshooting in `docs/runbooks/runbook-observability-metrics.md`.
- Promtail (hemma): fixed crash-looping config; nginx-proxy access logs are now labeled in Loki (`vhost`, `client_ip`, `method`, `status`) via `observability/promtail/promtail-config.yaml` (promtail recreated).
- Security (hemma): added Fail2ban `nginx-proxy-probe` jail (polling, `usedns=no`) + provisioned Grafana dashboard `skriptoteket-nginx-proxy-security`.
- Env examples: aligned `.env.example` + `.env.example.prod` with current local `.env` and `hemma:~/apps/skriptoteket/.env` keys (email/LLM/observability); local `ARTIFACTS_ROOT` now points to `/tmp/skriptoteket/artifacts`; deduped `hemma:~/apps/skriptoteket/.env` (keep last values) and added `HEALTHZ_SMTP_CHECK_ENABLED=true` once; on `hemma` docker requires `sudo` and `compose.prod.yaml` was patched+backed up to pass `HEALTHZ_SMTP_CHECK_ENABLED` into the container (web recreated).
- Devops docs/skills: updated `docs/runbooks/runbook-home-server.md` + `AGENTS.md` to reflect `sudo docker` on `hemma`; updated and synced `skriptoteket-devops` skill (repo + `~/.codex/skills`).
- Ops tooling: installed `ripgrep`/`yq`/`fd-find`/`bat`/`fzf` on `hemma` and `yq`/`fd`/`bat`/`tree`/`fzf` locally (Homebrew); documented recommended packages in `docs/runbooks/runbook-home-server.md`.
- DX: added Playwright HMR probe `scripts/playwright_hmr_probe.py` + `pdm run ui-hmr-probe` (artifacts in `.artifacts/hmr-probe/`); documented in `AGENTS.md` and frontend specialist skill.
- ST-12-07: added explicit session file reuse/clear + session file listing APIs; new SPA SessionFilesPanel wired in tool run + sandbox; new tests in `tests/unit/application/scripting/handlers/test_run_*_session_files.py`; OpenAPI regenerated.
- Ops (hemma): network outage investigation (no crash/pstore/lockup logs; last log 2026-01-02 08:34:55 UTC); Wi-Fi disabled persistently via cloud-init (moved `/etc/netplan/50-cloud-init.yaml` → `.disabled` + `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg`); kernel auto-reboot on lockups enabled (`/etc/sysctl.d/99-watchdog.conf`); `ssh-watchdog` now restarts network/tailscaled + reboots after 3 consecutive failures (`/usr/local/bin/ssh-watchdog.sh`); smartmontools installed + `smartmontools.service` enabled with `/etc/smartd.conf`; SMART snapshots saved in `/root/logs/smart/` with cleanup timer (`/usr/local/bin/cleanup-smart-logs.sh`, `cleanup-smart-logs.timer`); heartbeat timer logs every minute (`heartbeat-log.timer`); non-root SSH key added for `paunchygent` (local key `~/.ssh/hemma-paunchygent_ed25519` + server `~/.ssh/authorized_keys`); raw 1-minute pre-hang log saved on server at `/root/logs/incident-20260102-083355-083455.log`.
- Ops (hemma) follow-up: deeper watchdog probe (`dmesg`/`lspci`) found no watchdog/IPMI/BMC entries; `~/.ssh/config` now defaults `hemma`/`hemma-local` to `paunchygent` with `hemma-root`/`hemma-local-root` aliases; updated `AGENTS.md`, `docs/runbooks/runbook-home-server.md`, and `~/.codex/skills/skriptoteket-devops/SKILL.md` for non-root defaults + new host log paths/heartbeat/watchdog notes.
- Docs (ops): trimmed `docs/runbooks/runbook-home-server.md` verbosity (moved CLI tools, architecture diagram, cleanup unit blocks to reference docs); added `docs/reference/ref-home-server-cli-tools.md`, `docs/reference/ref-home-server-architecture.md`, `docs/reference/ref-home-server-cleanup-timers.md`; moved observability stack lifecycle to `docs/runbooks/runbook-observability.md`; `pdm run docs-validate` passes.
- Docs (ops) follow-up: moved SSH hardening + Fail2ban details into `docs/reference/ref-home-server-security-hardening.md`; moved nginx-proxy add-service + edge hardening into `docs/reference/ref-home-server-nginx-proxy.md`; updated `docs/runbooks/runbook-home-server.md` to link; added new docs to `docs/index.md`; `AGENTS.md` now requires adding new docs to the index; `pdm run docs-validate` passes.

## Verification

- Docs: `pdm run docs-validate` (pass; fixed `REF-*` id mismatch in `docs/reference/reports/ref-security-perimeter-vpn-gating-ssh-and-observability.md`)
- ST-08-02 tests: `pdm run test tests/unit/application/identity/test_register_user_handler.py` (pass)
- ST-08-02 health/api tests: `pdm run test tests/unit/observability/test_health_smtp.py tests/unit/web/test_register_api_routes.py` (pass)
- Typecheck: `pdm run typecheck` (pass)
- Lint: `pdm run lint` (pass)
- Live check (dev): `pdm run dev`; `curl -sS http://127.0.0.1:8000/healthz | python -m json.tool` => `healthy` with `smtp` dependency
- Live check (forced SMTP failure): start temp server `EMAIL_SMTP_HOST=127.0.0.1 EMAIL_SMTP_PORT=1 ... pdm run uvicorn ... --port 8001`; `/healthz` => 503 degraded; `POST /api/v1/auth/register` => 503 `EMAIL_SEND_FAILED` after ~1.6s (backoff 0.5s + 1.0s), repeat with same email still 503 (rollback); temp server stopped
- SPA typecheck: `pnpm -C frontend --filter @skriptoteket/spa typecheck` (pass)
- SPA lint: `pnpm -C frontend --filter @skriptoteket/spa lint` (pass)
- Frontend tests: `pdm run fe-test` (pass)
- OpenAPI types: `pdm run fe-gen-api-types` (pass)
- Backend tests (ST-12-07): `pdm run pytest tests/unit/application/scripting/handlers/test_run_active_tool_session_files.py tests/unit/application/scripting/handlers/test_run_sandbox_session_files.py` (pass)
- Live check (dev): `pdm run dev-local` (left running) + `curl -sSf http://127.0.0.1:5173/ | head -n 5` (SPA HTML served)
- SPA build: not rerun after ST-08-16 changes
- UI (editor smoke): `pdm run ui-editor-smoke` (pass; artifacts in `.artifacts/ui-editor-smoke/`; Playwright required escalation on macOS)
- UI (ST-08-14): `pdm run python -m scripts.playwright_st_08_14_ai_inline_completions_e2e` (pass; artifacts in `.artifacts/st-08-14-ai-inline-completions-e2e/`; Playwright required escalation on macOS)
- UI (ST-08-16): `BASE_URL=http://127.0.0.1:5173 pdm run python -m scripts.playwright_st_08_16_ai_edit_suggestions_e2e` (pass; artifacts in `.artifacts/st-08-16-ai-edit-suggestions-e2e/`; Playwright required escalation on macOS)
- Manual (ST-08-16): `PYTHONPATH=src pdm run python - <<'PY'` login + `POST /api/v1/editor/edits` (eval headers) confirms non-empty suggestion after restart.
- Backend tests (ST-08-14): `pdm run test tests/unit/application/test_editor_inline_completion_handler.py tests/unit/web/test_editor_inline_completion_api.py` (pass)
- Backend tests (ST-08-16): `pdm run test tests/unit/application/test_editor_edit_suggestion_handler.py tests/unit/web/test_editor_edit_suggestion_api.py` (pass)
- Backend tests (context budgeting): `pdm run test tests/unit/application/test_editor_inline_completion_handler.py tests/unit/application/test_editor_edit_suggestion_handler.py` (pass)
- Backend tests (ST-08-18): `pdm run test tests/unit/application/test_ai_prompt_system_v1.py tests/unit/application/test_editor_inline_completion_handler.py tests/unit/application/test_editor_edit_suggestion_handler.py` (pass)
- UI (ST-06-11): `pdm run python -m scripts.playwright_st_06_11_quick_fix_actions_e2e` (pass; artifacts in `.artifacts/st-06-11-quick-fix-actions-e2e/`; Playwright required escalation on macOS)
- UI (ST-06-12): `pdm run python -m scripts.playwright_st_06_12_lint_panel_navigation_e2e` (pass; artifacts in `.artifacts/st-06-12-lint-panel-navigation-e2e/`; Playwright required escalation on macOS)
- UI (HMR probe): `pdm run ui-hmr-probe` (pass; artifacts in `.artifacts/hmr-probe/`; Playwright required escalation on macOS)
- Backend tests (ST-14-09): `pdm run test` (pass; 543 passed)
- Migrations (ST-14-09): `pdm run pytest -m docker --override-ini addopts=''` (pass; 20 passed)
- UI (ST-14-09): `pdm run python -m scripts.playwright_st_14_09_input_schema_no_legacy_e2e --base-url http://127.0.0.1:5173` (pass; artifacts in `.artifacts/st-14-09-input-schema-no-legacy-e2e/`; Playwright required escalation on macOS)
- UI (ST-14-10): `pdm run dev-local` (running) + `pdm run python -m scripts.playwright_st_14_09_input_schema_no_legacy_e2e --base-url http://127.0.0.1:5173` (updated to assert invalid JSON blocks Save; screenshot `editor-invalid-json-blocks-save.png`)
- Gate: `pdm run precommit-run` (pass)

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

- Playwright Chromium may require escalated permissions on macOS (MachPort permission errors); CodeMirror lint tooltip action buttons can be flaky to click in Playwright—use a DOM-evaluate click helper.
- AI inference: llama-server (:8082) + Tabby (:8083) running on hemma; see GPU/Tabby runbooks if services need restart.
- Prompt budgeting is a conservative char→token approximation; rare over-budget cases can still happen and return empty completion/suggestion (see `docs/reference/reports/ref-ai-edit-suggestions-kb-context-budget-blocker.md`).
- Dev UI uses Vite proxy to `127.0.0.1:8000` (host backend); check the `pdm run dev` terminal for errors, not `docker logs`, unless the UI is pointed at the container port directly.

## Next Steps

- ST-08-17: Evaluate Tabby chat + prompt A/B testing once ST-08-16 is validated.
- Re-run `pdm run fe-build` after recent editor UI changes.
