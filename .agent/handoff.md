# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-14
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-08-24 done; ST-08-28 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-14)

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
- Verification:
  - `pdm run db-upgrade`
  - `pdm run fe-gen-api-types`
  - `pdm run fe-type-check` / `pdm run fe-test` / `pdm run fe-build`
  - `BASE_URL=http://localhost:5173 pdm run ui-smoke` (Playwright; requires escalation on macOS)
  - `BASE_URL=http://localhost:5173 pdm run ui-editor-smoke` (Playwright; requires escalation on macOS)
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

- Working tree contains out-of-scope docs change: `docs/runbooks/runbook-home-server.md` (do not include without explicit approval).
- Streaming cancellation: client disconnect cancels upstream best-effort; `done.reason="cancelled"` may not be observed client-side if the connection is already closed.
- Prompt budgeting is tokenizer-backed (GPT-5 via `tiktoken`; devstral via Tekken if configured; heuristic fallback otherwise).
- If `LLM_CHAT_ENABLED=false` (default) or chat is misconfigured, SSE returns a single `done` event with the Swedish “not available” message.

## Next Steps

- Deploy: set `LLM_DEVSTRAL_TEKKEN_JSON_PATH` (tekken.json asset path) for accurate devstral token counting.
- ST-14-19: implement `SKRIPTOTEKET_ACTION` + runner toolkit (no shims); update script bank + tests that currently rely on `action.json`.
- Decide whether to keep or remove any story-specific Playwright scripts (prefer using `pdm run ui-editor-smoke`).
- Parallel refactors (optional): PR-0019 (backend LLM hotspots) + PR-0020 (frontend AI hotspots).
- PR-0028: ready to open PR once out-of-scope diffs are handled.
