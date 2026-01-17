# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-16
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-14-19 done; ST-14-20 done; ST-14-23 done; ST-08-24 done; ST-08-28 done; ST-08-29 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-16)

- ST-14-23 implemented (action defaults/prefill): ADR-0060 + review doc approved; updated story + sprint plan + `docs/index.md` (`docs/adr/adr-0060-ui-contract-v2x-action-prefill.md`, `docs/backlog/reviews/review-epic-14-ui-contract-v2x-action-prefill.md`, `docs/backlog/stories/story-14-23-ui-contract-action-defaults-prefill.md`, `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md`).
- ST-08-29 implemented: edit-ops patch ops now use `patch_lines` encoding (PR-0034) and llama.cpp chat-ops requests are constrained with a patch-only strict GBNF grammar to prevent malformed JSON `parse_failed` (PR-0035). (`docs/adr/adr-0051-chat-first-ai-editing.md`, `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py`)
- Implemented PR-0031 “Editor AI: patch-only edit-ops alignment (prompt + diff hygiene + correlation)”:
  - Correlation header propagated across edit-ops → preview → apply; selection/cursor omitted in edit-ops requests (`frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`).
  - Patch-only system prompt + backend enforcement (safe-fail non-patch ops) (`src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`, `src/skriptoteket/application/editor/edit_ops_handler.py`).
  - Unified diff hunk header count repair + malformed patch message mapping (`src/skriptoteket/infrastructure/editor/unified_diff_applier.py`).
  - Tests: FE correlation plumbing + request semantics; BE hunk repair + malformed hunk (`frontend/apps/skriptoteket/src/composables/editor/editOps/editorEditOpsApi.spec.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.apply.spec.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.request.spec.ts`, `tests/unit/infrastructure/test_unified_diff_applier.py`, `tests/unit/application/test_editor_edit_ops_handler.py`).
- Committed runbook note about kdump watchdog hardening (`docs/runbooks/runbook-home-server.md`).
- Refactored editor AI frontend into SRP modules + lazy-loaded AI UI (`frontend/apps/skriptoteket/src/composables/editor/chat/`, `frontend/apps/skriptoteket/src/composables/editor/editOps/`, `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/components/editor/diff/AiVirtualFileDiffViewer.vue`).
- Fixed AI panel slot binding to avoid double `.value` unwrapping that crashed the tool editor (`frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`).
- Added ESLint rule to ban `.value` access in Vue templates (`frontend/eslint-rules/no-template-ref-value.js`, `frontend/apps/skriptoteket/eslint.config.js`, `frontend/packages/huleedu-ui/eslint.config.js`).
- Fixed `v-else` adjacency bug that caused a Vite overlay crash in testkör mode (`frontend/apps/skriptoteket/src/components/editor/EditorSandboxPanel.vue`).
- Fixed editor height-chain so left panels (källkod/diff/metadata/testkör) stretch vertically instead of being content-sized (`frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`).
- Moved remote-fallback consent to Profile (server-persisted `allow_remote_fallback` on `user_profiles`) + added `/api/v1/profile/ai-settings` update endpoint (`migrations/versions/0026_profile_ai_settings.py`, `src/skriptoteket/web/api/v1/profile.py`, `src/skriptoteket/application/identity/handlers/update_ai_settings.py`).
- Frontend now hydrates remote-fallback preference from server profile (localStorage used only as migration) and persists changes via API (`frontend/apps/skriptoteket/src/stores/ai.ts`, `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`).
- Editor chat drawer no longer renders an in-context checkbox; instead shows a contextual “Aktivera/Stäng av” prompt on first remote-required attempt when preference is `unset` (`frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`, `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`).
- Refactored chat drawer density + composer UX: extracted `ChatMessageList.vue` + `ChatComposer.vue`, moved “Ny chatt” into composer tool row, added Chat/Redigera toggle + icon-only send button (`frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatComposer.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatMessageList.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.spec.ts`).
- Added Playwright smoke coverage for chat input editability + diff/test empty-state sizing (`scripts/playwright_ui_editor_smoke.py`).
- Added Profile AI settings panel (canonical panel/button primitives) with tri-state remote-fallback preference (server persisted; localStorage migration only): `frontend/apps/skriptoteket/src/components/profile/ProfileAiSettingsPanel.vue`, `frontend/apps/skriptoteket/src/components/profile/ProfileEditAiSettings.vue`, `frontend/apps/skriptoteket/src/views/ProfileView.vue`, `frontend/apps/skriptoteket/src/components/profile/ProfileDisplay.vue`, `frontend/apps/skriptoteket/src/stores/ai.ts`.
- Split edit-ops specs into smaller files and removed the monolith spec (`frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.apply.spec.ts`, `.selection.spec.ts`, `.preview.spec.ts`).
- Completed PR-0028 checklist + verification notes: `docs/backlog/prs/pr-0028-editor-focus-mode-and-ai-drawer-density.md`.
- PR-0029: updated chat empty-state intro + chat placeholder (`frontend/apps/skriptoteket/src/components/editor/ChatMessageList.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatComposer.vue`).
- PR-0029: smooth “typing” via frontend progressive reveal + fade-in for assistant messages (`frontend/apps/skriptoteket/src/components/editor/ChatMessageContent.vue`, `frontend/apps/skriptoteket/src/composables/editor/chat/editorChatReducer.ts`, `frontend/apps/skriptoteket/src/composables/editor/chat/editorChatTypes.ts`, `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`).
- PR-0029: scrubbed system prompt terminology to avoid internal version labels while keeping constraints/examples (`src/skriptoteket/application/editor/system_prompts/editor_chat_v1.txt`, `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`, `src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt`, `src/skriptoteket/application/editor/prompt_fragments.py`).
- ST-14-19: made `skriptoteket_toolkit` the canonical way to read inputs/settings/actions/state (docs + starter template + AI KB) (`runner/skriptoteket_toolkit.py`, `runner/README.md`, `src/skriptoteket/web/editor_support.py`, `src/skriptoteket/application/editor/prompt_fragments.py`, `docs/reference/ref-ai-script-generation-kb*.md`).
- ST-14-20: editor intelligence supports `skriptoteket_toolkit` (completions/hover + lint nudges), fixes `outputs` false-positive for list variables, and adds toolkit import quick-fix (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketMetadata.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketCompletions.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketHover.ts`, `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/contractRule.ts`, `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/bestPracticesRule.ts`).
- Fixed linter false-positive “ogiltig Python-syntax” for bare `yield` inside generator functions (Lezer parse quirk) + regression test (`frontend/apps/skriptoteket/src/composables/editor/pythonLezer/syntaxErrors.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.spec.ts`).
- PR-0029 docs: `docs/backlog/prs/pr-0029-editor-ai-ux-copy-and-smooth-typing.md` + indexed in `docs/index.md`.
- PR-0030: fixed streaming UX by making chat message objects reactive and moving typing reveal pacing into the composable (raw `content` vs rendered `visibleContent`), plus “Tänker...” → “Skriver...” inline status based on first visible batch (`frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts`, `frontend/apps/skriptoteket/src/composables/editor/chat/editorChatReducer.ts`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatMessageList.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatComposer.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatMessageContent.vue`).
- PR-0030 docs: `docs/backlog/prs/pr-0030-editor-chat-streaming-reactivity-and-typing-status.md` + indexed in `docs/index.md` (cross-link added to PR-0029 frontmatter).
- Logging: replaced substring-based redaction with key/segment/value-aware redaction (keeps `*_tokens` diagnostics visible) and moved logic to `src/skriptoteket/observability/redaction.py` (tests: `tests/unit/observability/test_logging_redaction.py`).
- Health: increased SMTP health check timeout to 10s so `/healthz` reports healthy in dev when SMTP greeting is slow (`src/skriptoteket/observability/health.py`).
- ST-07-06 implemented (PR-0032): pure ASGI correlation middleware + middleware ordering so `uvicorn.access` logs include `correlation_id` for successful + streaming/SSE (`src/skriptoteket/web/middleware/correlation.py`, `src/skriptoteket/web/app.py`, `tests/unit/web/test_correlation_middleware_asgi.py`, docs: `docs/backlog/reviews/review-epic-07-correlation-middleware-asgi.md`, `docs/adr/adr-0061-asgi-correlation-middleware.md`, `docs/backlog/stories/story-07-06-asgi-correlation-middleware.md`, `docs/backlog/prs/pr-0032-asgi-correlation-middleware.md`, `docs/backlog/epics/epic-07-observability-and-operations.md`).
- Verification:
  - `pdm run db-upgrade`
  - `pdm run fe-gen-api-types`
  - `pdm run fe-type-check` / `pdm run fe-test` / `pdm run fe-build` (rerun for ST-14-20: `fe-type-check`, `fe-test`)
  - `pdm run docs-validate`
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run test`
  - `pdm run fe-test`
  - `BASE_URL=http://localhost:5173 pdm run ui-smoke` (Playwright; requires escalation on macOS)
  - `pdm run dev-local` (backend + Vite)
  - `BASE_URL=http://127.0.0.1:5173 pdm run ui-editor-smoke` (Playwright; requires escalation on macOS)
  - `pdm run seed-script-bank --slug demo-next-actions --sync-code`
  - `docker build --progress=plain -f Dockerfile.runner -t skriptoteket-runner:latest .` (log: `.artifacts/runner-build-20260115T122634Z.log`)
  - `pdm run ui-runtime-smoke --base-url http://127.0.0.1:5173` (Playwright; asserts prefill; screenshot: `.artifacts/ui-runtime-smoke/tool-run-next-actions-prefill.png`)
  - `curl -i http://127.0.0.1:8000/healthz` (expects 200 + `"smtp":{"status":"healthy"}`)
  - `pdm run pytest tests/unit/web/test_correlation_middleware_asgi.py`
  - Live (ST-07-06): `pdm run dev-logs` then `curl -s -D - -o /dev/null -H 'X-Correlation-ID: 11111111-1111-1111-1111-111111111111' http://127.0.0.1:8000/healthz` + `rg '11111111-1111-1111-1111-111111111111' .artifacts/dev-backend.log` (expects `uvicorn.access` JSON line includes `correlation_id`)
  - Manual (PR-0031 correlation): called `/api/v1/editor/edit-ops` → `/preview` → `/apply` with `X-Correlation-ID=72d70ad9-0265-4e7e-94b8-cd0753c87b79`; confirmed response headers + `docker compose logs web --since 10m | rg '72d70ad9-0265-4e7e-94b8-cd0753c87b79|ai_chat_ops_result|edit_ops_preview'`.
  - Manual (ST-08-29): confirmed `/openapi.json` exposes `EditorEditOpsPatchOp.patch_lines` and `POST /api/v1/editor/edit-ops` returns `ops[0].patch_lines` (no `parse_failed`).
  - Manual (PR-0035 grammar): called `POST /api/v1/editor/edit-ops` with `X-Correlation-ID=edf309e7-525f-4728-b79f-41ffa6f825ff`; confirmed llama-server request + `ai_chat_ops_result` logs show `parse_ok=true` and `ops_count=1` (no `parse_failed`).
  - Manual (edit-ops preview/apply blank-skip): `POST /api/v1/editor/edit-ops/preview` + `/apply` with patch op that omits an internal blank line; confirmed ok, `requires_confirmation=true`, `fuzz_level_used=1`, `applied_cleanly=false` (`X-Correlation-ID=ad0a7e3d-60ac-450d-9efe-56b2f2a2948d`).
  - Artifacts: `.artifacts/ui-smoke/profile-ai-settings-desktop.png`, `.artifacts/ui-editor-smoke/editor-loaded.png`, `.artifacts/ui-editor-smoke/diff-mode.png`, `.artifacts/ui-editor-smoke/diff-empty-state.png`, `.artifacts/ui-editor-smoke/test-mode.png`

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

- Working tree contains out-of-scope change: `README.md` (confirm intent before including in any PR).
- Streaming cancellation: client disconnect cancels upstream best-effort; `done.reason="cancelled"` may not be observed client-side if the connection is already closed.
- Prompt budgeting is tokenizer-backed (GPT-5 via `tiktoken`; devstral via Tekken if configured; heuristic fallback otherwise).
- If `LLM_CHAT_ENABLED=false` (default) or chat is misconfigured, SSE returns a single `done` event with the Swedish “not available” message.

## Next Steps

- Deploy: set `LLM_DEVSTRAL_TEKKEN_JSON_PATH` (tekken.json asset path) for accurate devstral token counting.
- Plan/implement ST-14-23/24: ADR-0060 accepted (action defaults/prefill); write separate ADR for ST-14-24 file references before implementation.
- Decide whether to keep or remove any story-specific Playwright scripts (prefer using `pdm run ui-editor-smoke`).
- Parallel refactors (optional): PR-0019 (backend LLM hotspots) + PR-0020 (frontend AI hotspots).
- PR-0028/PR-0029: ready to open PRs once `README.md` (unrelated diff) is resolved.
