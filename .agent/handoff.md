# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-07
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: ST-14-01/14-02 done; ST-14-09 done; ST-14-10 done; ST-14-13/14 done; ST-14-15 done; ST-14-16 done; ST-14-17 done; ST-14-18 done; ST-14-30 done; ST-14-31 done; ST-08-23 done

## Current Session (2026-01-07)

- Chat drawer UI consolidated into a single scrollable conversation surface (no per-message boxes), cleaned copy, and stronger hierarchy: `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`.
- Focus mode now defaults on editor load (no toast), preserving user manual toggle afterward: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Migration integration test added for tool_session_messages (0024): `tests/integration/test_migration_0024_tool_session_messages_idempotent.py`.
- Playwright chat drawer check added: `scripts/playwright_st_08_20_editor_chat_drawer_check.py`.
- PR-0008: marked done; normalized chat storage docs updated with TTL-on-access semantics (docs: `docs/backlog/prs/pr-0008-editor-chat-message-storage-minimal-c.md`).
- Chat history storage: new `tool_session_messages` table + repo + migration; chat handler no longer reads/writes `tool_sessions.state["messages"]` (infra/app: `src/skriptoteket/infrastructure/db/models/tool_session_message.py`, `src/skriptoteket/infrastructure/repositories/tool_session_message_repository.py`, `migrations/versions/0024_tool_session_messages.py`, `src/skriptoteket/application/editor/chat_handler.py`).
- Chat semantics: tail cap 60 (`LLM_CHAT_TAIL_MAX_MESSAGES`), TTL based on last message timestamp, assistant persistence uses `message_id` correlation + `orphaned` meta when missing user message (app/config: `src/skriptoteket/application/editor/chat_handler.py`, `src/skriptoteket/config.py`).
- Clear chat endpoint now deletes message rows via `EditorChatClearHandler` (app/web: `src/skriptoteket/application/editor/clear_chat_handler.py`, `src/skriptoteket/web/api/v1/editor/chat.py`).
- Tests updated/added: chat handler unit tests, clear handler unit tests, guard/orphaned + duplicate-message concurrency unit tests, integration repo test (tests: `tests/unit/application/test_editor_chat_handler.py`, `tests/unit/application/test_editor_chat_clear_handler.py`, `tests/unit/application/test_editor_chat_handler_concurrency.py`, `tests/integration/infrastructure/repositories/test_tool_session_message_repository.py`).
- ST-08-23: implemented tool-scoped SSE chat endpoints `POST`/`DELETE /api/v1/editor/tools/{tool_id}/chat` (web: `src/skriptoteket/web/api/v1/editor/chat.py`).
- ST-08-23: canonical chat thread stored in `tool_session_messages` (context `editor_chat`), TTL enforced on access via message timestamps (app: `src/skriptoteket/application/editor/chat_handler.py`).
- ST-08-23: budgeting now uses sliding window (drop oldest turns; never truncate system prompt) and returns 422 on too-long newest message (app: `src/skriptoteket/application/editor/prompt_budget.py`).
- ST-08-23: provider compatibility: `cache_prompt: true` only for local llama-server `:8082` (infra: `src/skriptoteket/infrastructure/llm/openai_provider.py`).
- ST-08-23: updated unit tests for handler behavior and persistence semantics (tests: `tests/unit/application/test_editor_chat_handler.py`).
- ST-08-23: added message-id based thread persistence with conflict retry + assistant insertion by `message_id`, plus in-process single-flight guard (app: `src/skriptoteket/application/editor/chat_handler.py`; infra: `src/skriptoteket/infrastructure/llm/chat_inflight_guard.py`; DI: `src/skriptoteket/di/llm.py`; protocol: `src/skriptoteket/protocols/llm.py`).
- Tests: added concurrency coverage (tests: `tests/unit/application/test_editor_chat_handler_concurrency.py`).
- Rule-040: removed `from __future__ import annotations` from API router modules to keep OpenAPI typing stable (files: `src/skriptoteket/web/api/v1/editor/completions.py`, `src/skriptoteket/web/api/v1/editor/edits.py`, `src/skriptoteket/web/api/v1/favorites.py`, `src/skriptoteket/web/api/v1/admin_users.py`).
- Docs: PR-0008 marked done; ST-08-23 TTL/storage wording updated; EPIC-08 summary aligned (docs: `docs/backlog/prs/pr-0008-editor-chat-message-storage-minimal-c.md`, `docs/backlog/stories/story-08-23-ai-chat-streaming-proxy-and-config.md`, `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`).
- Docs: added PR-0009 for message_id persistence, updated PR-0008 coordination notes, aligned ST-08-23 scope, and updated `docs/index.md`.
- Docs: PR plan `docs/backlog/prs/pr-0007-editor-ai-chat-thread-tool-scoped-sse.md` + story `docs/backlog/stories/story-08-23-ai-chat-streaming-proxy-and-config.md` marked done; EPIC-08 implementation summary updated.
- Ops (hemma): allowed `172.18.0.0/16 -> 8082/tcp` in UFW, switched LLM edit model to Devstral, and raised AI edit limits in `~/apps/skriptoteket/.env` + `compose.prod.yaml`; web recreated.

## Verification

- Not run (this session): `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q`, `pdm run pytest tests/unit/application/test_editor_chat_clear_handler.py -q`, `pdm run pytest tests/integration/infrastructure/repositories/test_tool_session_message_repository.py -q`, live `/api/v1/editor/tools/{tool_id}/chat` SSE + clear checks.
- Migration test (docker): `pdm run pytest -m docker tests/integration/test_migration_0024_tool_session_messages_idempotent.py -q` (pass)
- Dev DB migration: `pdm run db-upgrade`
- Unit tests (chat): `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q` (pass)
- Unit tests (chat concurrency): `pdm run pytest tests/unit/application/test_editor_chat_handler_concurrency.py -q` (pass)
- Unit tests (application): `pdm run pytest tests/unit/application -q` (pass)
- Docs validate: `pdm run docs-validate` (pass)
- OpenAPI/docs (local): `curl -sS http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[] | select(.=="/api/v1/editor/tools/{tool_id}/chat")'` and `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/docs` (200)
- Rule-040 check (local): `rg -n "from __future__ import annotations" src/skriptoteket/web/api -S` (no output)
- Live SSE smoke (docker dev; no secrets):
  - Login: `set -a && source .env && set +a && COOKIE_JAR=/tmp/skriptoteket-cookies.txt && CSRF_FILE=/tmp/skriptoteket-csrf.txt && curl -sS -c "$COOKIE_JAR" -H 'Content-Type: application/json' -d "{\"email\":\"$BOOTSTRAP_SUPERUSER_EMAIL\",\"password\":\"$BOOTSTRAP_SUPERUSER_PASSWORD\"}" http://127.0.0.1:8000/api/v1/auth/login | jq -r .csrf_token > "$CSRF_FILE"`
  - SSE: `TOOL_ID=$(curl -sS -b "$COOKIE_JAR" http://127.0.0.1:8000/api/v1/catalog/tools | jq -r '.items[0].id') && CSRF=$(cat "$CSRF_FILE") && curl -N --max-time 10 -b "$COOKIE_JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' -d '{"message":"Hej"}' http://127.0.0.1:8000/api/v1/editor/tools/$TOOL_ID/chat`
  - Clear: `curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE -b "$COOKIE_JAR" -H "X-CSRF-Token: $CSRF" http://127.0.0.1:8000/api/v1/editor/tools/$TOOL_ID/chat` (expect 204)
- Playwright chat drawer check (Vite): `pdm run seed-script-bank --slug demo-next-actions`, then `pdm run python -m scripts.playwright_st_08_20_editor_chat_drawer_check --base-url http://127.0.0.1:5173` (screenshot: `.artifacts/ui-editor-chat/chat-drawer.png`)
- HTTPS healthz: `curl -sk https://skriptoteket.hule.education/healthz`
- Local HTTPS (host header): `ssh hemma "curl -sk -H 'Host: skriptoteket.hule.education' https://127.0.0.1/healthz"`
- Postgres data restored: `ssh hemma "sudo docker exec shared-postgres psql -U skriptoteket -d skriptoteket -c '\\dt'"`
- Bootstrap login (server): `/api/v1/auth/login` using `BOOTSTRAP_SUPERUSER_*` from `~/apps/skriptoteket/.env` (no secrets stored here).
- LLM edit connectivity (container → host): `ssh hemma "sudo docker exec skriptoteket-web python -c \"import urllib.request; print(urllib.request.urlopen('http://172.18.0.1:8082/health').read().decode())\""`

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
- Prompt budgeting is a conservative char→token approximation; rare over-budget cases can still happen.
- If `LLM_CHAT_ENABLED=false` (default) or chat is misconfigured, SSE returns a single `done` event with the Swedish “not available” message.

## Next Steps

- ST-08-20 (UI): wire the chat drawer to `POST`/`DELETE /api/v1/editor/tools/{tool_id}/chat` (no client-managed history).
- ST-08-21/22 (future): reuse the same canonical server-side thread (`context="editor_chat"`) for edit-ops/diff/apply/undo chat-first endpoints.
- If you want to validate real streaming locally, enable `LLM_CHAT_ENABLED=true` and point `LLM_CHAT_BASE_URL` to a working OpenAI-compatible provider (default `http://localhost:8082`).
