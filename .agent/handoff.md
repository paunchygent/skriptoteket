# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-13
- Branch: `main`
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-08-24 done; ST-08-28 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-13)

- Added ADR + story for settings suggestions from tool runs: `docs/adr/adr-0057-settings-suggestions-from-tool-runs.md`, `docs/backlog/stories/story-14-34-settings-suggestions-from-tool-runs.md`, linked in `docs/index.md` + `docs/backlog/epics/epic-14-admin-tool-authoring.md` (docs-only).
- Reconciled tool editor backlog docs: ST-14-11/12 marked done; sprints `SPR-2026-03-17`, `SPR-2026-03-31`, `SPR-2026-04-14`, `SPR-2026-04-28` marked done; EPIC-14 summary refreshed (`docs/backlog/epics/epic-14-admin-tool-authoring.md`).
- Expanded PRD v0.2 with tool datasets, file vault, automation/connectors, analytics, and collaboration primitives (`docs/prd/prd-script-hub-v0.2.md`).
- Planned EPIC-14 data libraries sprint: ADR-0058/0059 + stories ST-14-35/36 + sprint plan `docs/backlog/sprints/sprint-2026-02-24-tool-data-libraries-v1.md` (docs-only).
- Updated ADR-0059 + ST-14-36 to require soft delete + restore + retention purge for vault files (docs-only).
- Added review doc for EPIC-14 data libraries and packaged repomix bundle: `docs/backlog/reviews/review-epic-14-tool-data-libraries.md`, `.claude/repomix_packages/repomix-epic-14-tool-data-libraries-review.xml`.
- Drafted docs for script bank curation + group generator tool: `docs/adr/adr-0056-script-bank-seed-profiles.md`, `docs/backlog/stories/story-14-33-script-bank-curation-and-group-generator.md`, `docs/backlog/prs/pr-0025-script-bank-curation-and-group-generator.md`; linked in `docs/index.md` + `docs/backlog/epics/epic-14-admin-tool-authoring.md`. Verification: not run (docs-only).
- Handoff compression: moved detailed “shipped AI editor work + verification recipes” to `.agent/readme-first.md`.
- Contract decision prep (EPIC-14 / ST-14-19): recorded decision to move action payload transport to `SKRIPTOTEKET_ACTION` (ADRs updated) + added PR doc `docs/backlog/prs/pr-0024-action-payload-skriptoteket-action-docs-prompt-alignment.md`; `pdm run docs-validate` OK.
- Baseline: `docs/adr/adr-0051-chat-first-ai-editing.md` is `accepted`; EPIC-08 summary refreshed in `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`.
- Platform-only AI debug capture (Option A): `LLM_CAPTURE_ON_ERROR_ENABLED` + captures under `ARTIFACTS_ROOT/llm-captures/` (access: `docs/runbooks/runbook-observability-logging.md`).
- ST-08-27 implemented (PR-0022 + PR-0023): virtual file context retention + tokenizer-backed prompt budgets.
  - Backend: `src/skriptoteket/application/editor/chat_handler.py`, `src/skriptoteket/application/editor/prompt_budget.py`, `src/skriptoteket/application/editor/chat_history_handler.py`, `src/skriptoteket/infrastructure/llm/token_counter_resolver.py`.
  - Frontend: `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, regenerated `frontend/apps/skriptoteket/src/api/openapi.d.ts`.
  - Prompt injection guard: `src/skriptoteket/application/editor/system_prompts/editor_chat_v1.txt`.
- Fixed AI chat deadlock (llama-server “roles must alternate”) by introducing turn-based persistence (Option A): `migrations/versions/0025_tool_session_turns.py`, `src/skriptoteket/application/editor/chat_handler.py`, `src/skriptoteket/application/editor/edit_ops_handler.py`, `src/skriptoteket/application/editor/chat_history_handler.py`, `src/skriptoteket/web/api/v1/editor/chat.py`, `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`.
- Fixed dev-container 500 on chat start caused by `SettingsBasedTokenCounterResolver.for_model` caching requiring a hashable instance (`Settings` is unhashable): `src/skriptoteket/infrastructure/llm/token_counter_resolver.py`, test `tests/unit/infrastructure/llm/test_token_counter_resolver.py`.
- Fixed dev-container 500 on chat start when SSE meta included UUIDs (`TypeError: Object of type UUID is not JSON serializable`): `src/skriptoteket/web/api/v1/editor/chat.py`, test `tests/unit/web/test_editor_chat_sse_encoding.py`.
- Fixed chat streaming on upstream HTTP errors: eagerly read streaming error bodies before `raise_for_status()` to avoid `httpx.ResponseNotRead` and allow clean `ai_chat_failed` handling (`src/skriptoteket/infrastructure/llm/openai_provider.py`).
- Tweaked heuristic token counting for Devstral when Tekken assets are missing (more conservative) + raised chat system prompt budget to avoid false “system prompt unavailable” in dev (`src/skriptoteket/infrastructure/llm/token_counter_resolver.py`, `src/skriptoteket/config.py`).
- Verification:
  - `pdm run typecheck`
  - `pdm run test`
  - `pdm run fe-test`
  - `pdm run docs-validate`
  - Live (local):
    - `docker compose up -d db`
    - `pdm run db-upgrade`
    - `ARTIFACTS_ROOT=$(pwd)/.artifacts pdm run dev` (left running)
    - `pdm run fe-dev` (left running)
    - `curl -s -o /dev/null -w "%{http_code}\\n" http://127.0.0.1:8000/healthz` (200)
    - `curl -s -o /dev/null -w "%{http_code}\\n" http://127.0.0.1:5173/` (200)

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000

# Quality gates
pdm run format
pdm run lint
pdm run typecheck
pdm run test
```

## Known Issues / Risks

- Streaming cancellation: client disconnect cancels upstream best-effort; `done.reason="cancelled"` may not be observed client-side if the connection is already closed.
- Prompt budgeting is tokenizer-backed (GPT-5 via `tiktoken`; devstral via Tekken if configured; heuristic fallback otherwise).
- If `LLM_CHAT_ENABLED=false` (default) or chat is misconfigured, SSE returns a single `done` event with the Swedish “not available” message.

## Next Steps

- Deploy: set `LLM_DEVSTRAL_TEKKEN_JSON_PATH` (tekken.json asset path) for accurate devstral token counting.
- ST-14-19: implement `SKRIPTOTEKET_ACTION` + runner toolkit (no shims); update script bank + tests that currently rely on `action.json`.
- Decide whether to keep or remove any story-specific Playwright scripts (prefer using `pdm run ui-editor-smoke`).
- Parallel refactors (optional): PR-0019 (backend LLM hotspots) + PR-0020 (frontend AI hotspots).
