# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-11
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: ST-14-01/14-02 done; ST-14-09 done; ST-14-10 done; ST-14-13/14 done; ST-14-15 done; ST-14-16 done; ST-14-17 done; ST-14-18 done; ST-14-30 done; ST-14-31 done; ST-08-23 done

## Current Session (2026-01-11)

- EPIC-08 edit-ops v2: review set to `changes_requested` + clarified v2 semantics (triggering, patch/anchor shapes, AI diff preview UI): `docs/backlog/reviews/review-epic-08-ai-edit-ops-v2.md`, `docs/adr/adr-0051-chat-first-ai-editing.md`, `docs/backlog/stories/story-08-24-ai-edit-ops-anchor-patch-v2.md`.
- Docs validate (after the review/doc edits): `pdm run docs-validate` (pass).
- ST-08-24 implementation: v2 patch/anchor support + backend-first preview/apply + controlled fuzz ladder + cursor TTL request semantics (plus updated tests + regenerated OpenAPI TS types):
  - Backend: `src/skriptoteket/protocols/llm.py`, `src/skriptoteket/web/api/v1/editor/models.py`, `src/skriptoteket/application/editor/edit_ops_handler.py`, `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`, `tests/unit/application/test_editor_edit_ops_handler.py`.
  - Frontend: `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.spec.ts`, `frontend/apps/skriptoteket/src/components/editor/EditorEditOpsPanel.vue`, `frontend/apps/skriptoteket/src/components/editor/diff/AiVirtualFileDiffViewer.vue`, `frontend/apps/skriptoteket/src/api/openapi.d.ts`.
- Follow-up hardening fixes (trust/UX):
  - Diff scroll: ensure CodeMirror MergeView scrolls via `.cm-mergeView` and that AI + working-copy diffs are height-constrained: `frontend/apps/skriptoteket/src/components/editor/diff/CodeMirrorMergeDiff.vue`, `frontend/apps/skriptoteket/src/components/editor/diff/{AiVirtualFileDiffViewer,VirtualFileDiffViewer}.vue`, `frontend/apps/skriptoteket/src/components/editor/WorkingCopyRestorePrompt.vue`.
  - Post-apply UX: remove the “AI-ÄNDRING … tillämpat” banner; replace with compact toolbar “AI” pill + undo/redo mini-buttons (no extra vertical space): `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`, `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`.
  - Surface AI undo/redo errors inline in the AI pill popover (no toast needed): `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`.
  - Save UX: show “blockers” inline in the save dropdown when disabled (schema errors, read-only, etc): `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`.
  - Local llama.cpp: bump chat-ops timeout from 60s → 120s to avoid false failures: `src/skriptoteket/config.py`.
  - New Playwright check: working-copy diff modal remains scrollable/closable: `scripts/playwright_st_08_24_working_copy_diff_scroll_check.py`.
  - Chat UX: show a “still generating” hint after 45s (slow ≠ failure): `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`.
  - Remove undo/redo success toasts (state is visible in toolbar controls): `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Editor modes now fixed toggles (Källkod/Diff/Metadata) with compare text relabeled to Diff; metadata/instructions/behörigheter render as in-page panels (no drawer overlay): `frontend/apps/skriptoteket/src/components/editor/{EditorWorkspaceToolbar,EditorWorkspacePanel,MetadataDrawer,InstructionsDrawer,MaintainersDrawer}.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorComparePanel.vue`, `frontend/apps/skriptoteket/src/components/editor/diff/VirtualFileDiffViewer.vue`, `frontend/apps/skriptoteket/src/composables/editor/{editorCompareDefaults,useEditorCompareData}.ts`.
- Editor workspace layout refit: toolbar sits under header; mode content uses fixed-height row; chat now aligns to editor row with a spacer row for schemas; diff toggle always enabled (shows empty state if no compare target): `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`.
- ST-08-21 backend scaffold: edit-ops handler + OpenAI provider + prompt template + settings + router/model wiring (POST `/api/v1/editor/edit-ops`): `src/skriptoteket/application/editor/edit_ops_handler.py`, `src/skriptoteket/infrastructure/llm/openai_provider.py`, `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`, `src/skriptoteket/config.py`, `src/skriptoteket/web/api/v1/editor/{edit_ops.py,models.py,__init__.py}`, `src/skriptoteket/protocols/llm.py`, `src/skriptoteket/di/llm.py`, `src/skriptoteket/application/editor/prompt_{templates,budget,composer}.py`.
- ST-08-22 frontend: edit-ops proposal preview/apply/undo panel + stale fingerprint guard + chat CTA + tests: `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.spec.ts`, `frontend/apps/skriptoteket/src/components/editor/EditorEditOpsPanel.vue`, `frontend/apps/skriptoteket/src/components/editor/{ChatDrawer,EditorWorkspacePanel,EditorWorkspaceDrawers}.vue`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Docs: PR-0011 marked done (Kodassistenten naming), created PR-0012 + ST-14-32 for the next cohesion pass (selectors + Testkör/Metadata/Diff density): `docs/backlog/prs/pr-0011-editor-mode-toggles-and-metadata-mode.md`, `docs/backlog/prs/pr-0012-editor-cohesion-pass-input-selectors.md`, `docs/backlog/stories/story-14-32-editor-cohesion-pass-input-selectors.md`.
- PR-0012 started (ST-14-32 in_progress): compact selectors + tooltip `aria-describedby` pattern (Preset→Förval, entrypoint dropdown), diff file selector now dropdown + per-side copy/download (clear Före/Efter) with file-specific names, and Testkör actions downgraded to compact ghost utilities: `frontend/apps/skriptoteket/src/components/editor/{EntrypointDropdown,EditorInputSchemaPanel,EditorComparePanel,SandboxInputPanel}.vue`, `frontend/apps/skriptoteket/src/components/editor/diff/VirtualFileDiffViewer.vue`, `frontend/apps/skriptoteket/src/composables/editor/{virtualFiles,useEditorWorkingCopy}.ts`.
- Metadata-läget paneler (Verktygsinfo/Instruktioner/Behörigheter) är nu kompakta och följer editor-utilities (ingen drawer-header inne i editorn; actions i header): `frontend/apps/skriptoteket/src/components/editor/{MetadataDrawer,InstructionsDrawer,MaintainersDrawer}.vue`.
- Testkör-subpaneler (inputs/sessionfiler/inställningar/debug/actions/artifacts/outputs) är nu kompakta och använder samma panel-header + utility-styling som resten av editorn: `frontend/apps/skriptoteket/src/components/editor/{SandboxInputPanel,SandboxRunner,SandboxRunnerActions,SandboxSettingsCard}.vue`, `frontend/apps/skriptoteket/src/components/tool-run/{SessionFilesPanel,ToolInputForm,ToolRunSettingsPanel,ToolRunActions,ToolRunArtifacts}.vue`, `frontend/apps/skriptoteket/src/components/ui-actions/UiActionField*.vue`.
- UiOutput-komponenter stödjer `density` så editorn kan rendera outputs compact utan att ändra ToolRunView: `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutput*.vue`, `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutputRenderer.vue`.
- Schema editors unified into a shared "Indata & inställningar (JSON)" section with divider layout and synced headers/actions; removed duplicate "Schema (JSON)" headers; settings panel has aligned header row placeholder: `frontend/apps/skriptoteket/src/components/editor/{EditorInputSchemaPanel,EditorSettingsSchemaPanel}.vue`.
- Editor layout tightened again: header/toolbar live inside the left column grid (mode selector aligns to editor edge), schema section has shared collapse toggle, chat column gets a top border, and chat rail no longer steals width when expanded: `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`.
- Editor route height is now constrained so CodeMirror scrolls inside the viewport (route-stage + auth-main-content editor classes): `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`, `frontend/apps/skriptoteket/src/App.vue`, `frontend/apps/skriptoteket/src/assets/main.css`.
- Auth top bar now shows the back-to-tools link only in focus mode (no user email label): `frontend/apps/skriptoteket/src/components/layout/AuthTopBar.vue`. PR-0010 updated to note focus-mode back link is deferred: `docs/backlog/prs/pr-0010-editor-save-restore-ux-clarity.md`.
- Focus toggle moved to top bar (always visible, label toggles) and editor focus still auto-enabled on load: `frontend/apps/skriptoteket/src/components/layout/{AuthTopBar,AuthLayout}.vue`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Chat drawer renamed to “Kodassistenten”, copy updated, default open on load; collapse via robot icon (no toolbar toggle). History load triggers on open + tool change: `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`, `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.ts`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Taxonomy UI copy renamed to “Sökord” (metadata panel + help + toasts): `frontend/apps/skriptoteket/src/components/editor/MetadataDrawer.vue`, `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`, `frontend/apps/skriptoteket/src/composables/editor/useToolTaxonomy.ts`.
- Playwright chat drawer check updated for new label/default open: `scripts/playwright_st_08_20_editor_chat_drawer_check.py`.
- Playwright chat drawer check now asserts the “Föreslå ändringar” button and waits for Send enable: `scripts/playwright_st_08_20_editor_chat_drawer_check.py`.
- Chat drawer now fills the full right column (no empty lower panel), shows an assistant intro message when empty, aligns buttons with schema actions, and auto-resizes the prompt textarea: `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`.
- Chat drawer responsive fix: on narrow viewports the drawer auto-collapses (rail width) and does not render a modal backdrop in column mode, keeping the code editor usable while still allowing expand via the rail button: `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.ts`, `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`.
- Working copy restore prompt restyled to match editor surface (compact, no big CTAs): `frontend/apps/skriptoteket/src/components/editor/WorkingCopyRestorePrompt.vue`.
- Editor workspace now full-height split with independent scroll per column; code editor flexes to fill available height: `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorSourceCodePanel.vue`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Version history popover + Spara/Öppna menu further aligned: restore point naming (“Spara ny återställningspunkt”), no nested shadows in Öppna sparade, compact “ledger/menu” rows with timestamp, subtle active-row fill, and actions are lightweight text links (status is secondary): `frontend/apps/skriptoteket/src/components/editor/{EditorWorkspaceToolbar,VersionHistoryDrawer,EditorWorkspacePanel}.vue`.
- Diff viewer controls now sit directly above their respective panes; patch actions labeled as global: `frontend/apps/skriptoteket/src/components/editor/diff/VirtualFileDiffViewer.vue`.
- AI-REDIGERING panel removed from the editor flow (chat replaces it): `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`.
- Toolbar regrouped: single Spara/Öppna menu (save + local checkpoint + open popover), lock badge, mode toggles; workflow actions live in header strip; no chat toggle: `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`, `frontend/apps/skriptoteket/src/components/editor/WorkflowContextButtons.vue`, `frontend/apps/skriptoteket/src/components/editor/ScriptEditorHeaderPanel.vue`.
- Title/summary/slug header panel moved into editor main column as a compact inline strip (no separate panel); workflow actions no longer live there: `frontend/apps/skriptoteket/src/components/editor/ScriptEditorHeaderPanel.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- Lock indicator is now a small badge in the toolbar for owner/acquiring; full banner only shows when locked by another user: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, `frontend/apps/skriptoteket/src/components/editor/DraftLockBanner.vue`.
- Version history list is compact (latest 12) with “Visa fler”; action buttons are small text buttons; history opens as a left-side popover modal: `frontend/apps/skriptoteket/src/components/editor/VersionHistoryDrawer.vue`.
- Drawers now full-height on desktop with tighter padding and subdued action buttons (ghost instead of primary/CTA): `frontend/apps/skriptoteket/src/components/editor/{Chat,Metadata,Instructions,Maintainers,VersionHistory}Drawer.vue`.
- Focus mode now defaults on editor load and auto-enables when any drawer opens (no toast spam): `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`.
- PR-0010 + PR-0011 created for upcoming editor UX work: `docs/backlog/prs/pr-0010-editor-save-restore-ux-clarity.md`, `docs/backlog/prs/pr-0011-editor-mode-toggles-and-metadata-mode.md`.
- Migration integration test added for tool_session_messages (0024): `tests/integration/test_migration_0024_tool_session_messages_idempotent.py`.
- Playwright chat drawer check added: `scripts/playwright_st_08_20_editor_chat_drawer_check.py`.
- Planning: ADR-0051 set to proposed for anchor/patch edit-ops v2; new ST-08-24 + PR-0015 + review doc pending: `docs/adr/adr-0051-chat-first-ai-editing.md`, `docs/backlog/stories/story-08-24-ai-edit-ops-anchor-patch-v2.md`, `docs/backlog/prs/pr-0015-editor-ai-edit-ops-anchor-patch-v2.md`, `docs/backlog/reviews/review-epic-08-ai-edit-ops-v2.md`.
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

- UI live check (dev local): `pdm run dev-local` (Vite + Uvicorn running); `pdm run ui-smoke --base-url http://127.0.0.1:5173` failed (Playwright strict mode: help panel has two headings matching "Hjälp").
- UI live check (dev local): `pdm run python -m scripts.playwright_nav_transitions_smoke --base-url http://127.0.0.1:5173` (pass; screenshots in `.artifacts/ui-smoke`).
- Backend unit tests (edit-ops v2 hardening): `pdm run pytest tests/unit/application/test_editor_edit_ops_preview_handler.py tests/unit/infrastructure/test_unified_diff_applier.py tests/unit/web/test_editor_edit_ops_preview_apply_api.py -q` (pass).
- Frontend unit tests: `pdm run fe-test` (pass).
- Playwright chat drawer check (Vite): `pdm run python -m scripts.playwright_st_08_20_editor_chat_drawer_check --base-url http://127.0.0.1:5173` (pass; artifacts in `.artifacts/ui-editor-chat/`).
- Not run (this session): `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q`, `pdm run pytest tests/unit/application/test_editor_chat_clear_handler.py -q`, `pdm run pytest tests/integration/infrastructure/repositories/test_tool_session_message_repository.py -q`, live `/api/v1/editor/tools/{tool_id}/chat` SSE + clear checks.
- FE lint: `pdm run fe-lint` (pass)
- Quality gates (frontend): `pdm run lint`, `pdm run fe-test`, `pdm run typecheck`, `pdm run fe-build` (pass; Vite chunk-size warning).
- Playwright editor smoke (Vite, macOS escalation; re-run after `panel-inset*` nested-border sweep): `pdm run ui-editor-smoke --base-url http://127.0.0.1:5173` (pass; artifacts in `.artifacts/ui-editor-smoke/`).
- Edit-ops handler unit tests: `pdm run pytest tests/unit/application/test_editor_edit_ops_handler.py -q` (pass).
- OpenAPI route check (local dev): `curl -sS http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[] | select(.==\"/api/v1/editor/edit-ops\")'`.
- Frontend OpenAPI types: `pdm run fe-gen-api-types` (pass).
- Full test run (incl. integration): `pdm run test` (pass).
- Edit-ops smoke (auth + CSRF + tool access; returns disabled when ops off): `set -a && source .env && set +a && BASE_URL=http://127.0.0.1:8000 && COOKIE_JAR=/tmp/skriptoteket-cookies.txt && CSRF_FILE=/tmp/skriptoteket-csrf.txt && curl -sS -c "$COOKIE_JAR" -H 'Content-Type: application/json' -d "{\"email\":\"$BOOTSTRAP_SUPERUSER_EMAIL\",\"password\":\"$BOOTSTRAP_SUPERUSER_PASSWORD\"}" "$BASE_URL/api/v1/auth/login" | jq -r .csrf_token > "$CSRF_FILE" && TOOL_ID=$(curl -sS -b "$COOKIE_JAR" "$BASE_URL/api/v1/catalog/tools" | jq -r '.items[0].id') && PAYLOAD=$(curl -sS -b "$COOKIE_JAR" "$BASE_URL/api/v1/editor/tools/$TOOL_ID" | jq -c --arg message "Föreslå en enkel förbättring." '{tool_id: .tool.id, message: $message, active_file: "tool.py", virtual_files: {"tool.py": .source_code, "entrypoint.txt": .entrypoint, "settings_schema.json": (if .settings_schema == null then "" else (.settings_schema|tojson) end), "input_schema.json": (if .input_schema == null then "" else (.input_schema|tojson) end), "usage_instructions.md": (.usage_instructions // "")}}') && CSRF=$(cat "$CSRF_FILE") && curl -sS -w '\n%{http_code}\n' -b "$COOKIE_JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' -d "$PAYLOAD" "$BASE_URL/api/v1/editor/edit-ops"` (200; enabled=false when ops disabled).
- Frontend unit (drawers): covered by full `pdm run fe-test` (pass).
- Migration test (docker): `pdm run pytest -m docker tests/integration/test_migration_0024_tool_session_messages_idempotent.py -q` (pass)
- Dev DB migration: `pdm run db-upgrade`
- Unit tests (chat): `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q` (pass)
- Unit tests (chat concurrency): `pdm run pytest tests/unit/application/test_editor_chat_handler_concurrency.py -q` (pass)
- Unit tests (application): `pdm run pytest tests/unit/application -q` (pass)
- Docs validate: `pdm run docs-validate` (pass)
- Docker web logs check (why first request failed): `docker logs --tail 400 skriptoteket_web` (observed chat-ops request ~60s → generic failure; timeout bumped to 120s).
- Docs validate (post-PR-0011 update): `pdm run docs-validate` (pass)
- OpenAPI/docs (local): `curl -sS http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[] | select(.=="/api/v1/editor/tools/{tool_id}/chat")'` and `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/docs` (200)
- Rule-040 check (local): `rg -n "from __future__ import annotations" src/skriptoteket/web/api -S` (no output)
- Live SSE smoke (docker dev; no secrets):
  - Login: `set -a && source .env && set +a && COOKIE_JAR=/tmp/skriptoteket-cookies.txt && CSRF_FILE=/tmp/skriptoteket-csrf.txt && curl -sS -c "$COOKIE_JAR" -H 'Content-Type: application/json' -d "{\"email\":\"$BOOTSTRAP_SUPERUSER_EMAIL\",\"password\":\"$BOOTSTRAP_SUPERUSER_PASSWORD\"}" http://127.0.0.1:8000/api/v1/auth/login | jq -r .csrf_token > "$CSRF_FILE"`
  - SSE: `TOOL_ID=$(curl -sS -b "$COOKIE_JAR" http://127.0.0.1:8000/api/v1/catalog/tools | jq -r '.items[0].id') && CSRF=$(cat "$CSRF_FILE") && curl -N --max-time 10 -b "$COOKIE_JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' -d '{"message":"Hej"}' http://127.0.0.1:8000/api/v1/editor/tools/$TOOL_ID/chat`
  - Clear: `curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE -b "$COOKIE_JAR" -H "X-CSRF-Token: $CSRF" http://127.0.0.1:8000/api/v1/editor/tools/$TOOL_ID/chat` (expect 204)
- HTTPS healthz: `curl -sk https://skriptoteket.hule.education/healthz`
- Local HTTPS (host header): `ssh hemma "curl -sk -H 'Host: skriptoteket.hule.education' https://127.0.0.1/healthz"`
- Postgres data restored: `ssh hemma "sudo docker exec shared-postgres psql -U skriptoteket -d skriptoteket -c '\\dt'"`
- Bootstrap login (server): `/api/v1/auth/login` using `BOOTSTRAP_SUPERUSER_*` from `~/apps/skriptoteket/.env` (no secrets stored here).
- LLM edit connectivity (container → host): `ssh hemma "sudo docker exec skriptoteket-web python -c \"import urllib.request; print(urllib.request.urlopen('http://172.18.0.1:8082/health').read().decode())\""`
- UI check (Playwright; macOS escalation may be needed):
  - Focus mode toggle + topbar logo: open `http://127.0.0.1:5173`, login, toggle focus mode; verify sidebar fades, topbar logo stays fixed, and toggle width does not jump.
  - Working-copy diff modal scroll/close: `pdm run python -m scripts.playwright_st_08_24_working_copy_diff_scroll_check --base-url http://localhost:5173` (pass; artifacts in `.artifacts/ui-working-copy-diff/`).
- Frontend unit: `pdm run fe-test` (pass; added CodeMirror MergeView scroll contract tests + Range polyfills in `frontend/apps/skriptoteket/src/test/setup.ts`).

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
- Docs contract: review ids must match `^REV-EPIC-\\d{2}$`; `docs/backlog/reviews/review-epic-08-ai-edit-ops-v2.md` uses `id: REV-EPIC-08` (duplicate of the older EPIC-08 review doc) to satisfy `pdm run docs-validate`.

## Next Steps

- If v2 plan is approved: flip review + ADR status to approved/accepted and re-run `pdm run docs-validate`.
- Decide whether to keep or remove any story-specific Playwright scripts (prefer using the standard `pdm run ui-editor-smoke`).
- If you want to validate real streaming locally, enable `LLM_CHAT_ENABLED=true` and point `LLM_CHAT_BASE_URL` to a working OpenAI-compatible provider (default `http://localhost:8082`).
