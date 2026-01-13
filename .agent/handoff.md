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
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-14-11/12 done; ST-08-24 done; ST-08-28 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-13)

- Refactored editor AI frontend into SRP modules + lazy-loaded AI UI (`frontend/apps/skriptoteket/src/composables/editor/chat/`, `frontend/apps/skriptoteket/src/composables/editor/editOps/`, `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/components/editor/diff/AiVirtualFileDiffViewer.vue`).
- Fixed AI panel slot binding to avoid double `.value` unwrapping that crashed the tool editor (`frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`).
- Added ESLint rule to ban `.value` access in Vue templates (`frontend/eslint-rules/no-template-ref-value.js`, `frontend/apps/skriptoteket/eslint.config.js`, `frontend/packages/huleedu-ui/eslint.config.js`).
- Attempted to expand diff/test empty states to fill available panel space (`frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`, `frontend/apps/skriptoteket/src/components/editor/EditorSandboxPanel.vue`); needs visual confirmation (user reports issue persists).
- Added Playwright smoke coverage for chat input editability + diff/test empty-state sizing (`scripts/playwright_ui_editor_smoke.py`).
- Split edit-ops specs into smaller files and removed the monolith spec (`frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.apply.spec.ts`, `.selection.spec.ts`, `.preview.spec.ts`).
- Verification:
  - `BASE_URL=http://localhost:5173 pdm run ui-editor-smoke`

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
