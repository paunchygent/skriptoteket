# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-25
- Branch / commit: `main` (`a71759d`)
- Current sprint: `SPR-2025-12-21` (EPIC-12 SPA UX)
- Production: Full Vue SPA; `d0e0bd6` deployed 2025-12-23
- Completed: EPIC-11 (SPA migration), EPIC-02 (identity) - see `.agent/readme-first.md`

## Current Session (2025-12-25)

### ST-08-13 Tool usage instructions (done)

Display + editor for `usage_instructions` markdown field on tool versions.

- **Display**: `UsageInstructions.vue` drawer in ToolRunView, `UiMarkdown.vue` renderer
- **Seen-state**: per-user via tool_sessions (`src/skriptoteket/web/api/v1/tools.py`)
- **Editor**: `InstructionsDrawer.vue` with edit/preview toggle, integrated in ScriptEditorView
- **API**: `usage_instructions` in `EditorBootResponse`, `CreateDraftVersionRequest`, `SaveDraftVersionRequest`
- Story: `docs/backlog/stories/story-08-13-tool-usage-instructions.md`

### ST-08-10 Script Editor Intelligence (design-ready)

Lezer-first analysis for linting/completions. No implementation yet.

- ADR: `docs/adr/adr-0035-script-editor-intelligence-architecture.md`
- Stories: `story-08-10-script-editor-intelligence.md`, `story-08-11-script-editor-intelligence-phase2.md`
- Notes: entrypoint-aware, `Compartment` + `reconfigure`, gated `startCompletion`, `lintGutter()`

### ST-12-02 Native PDF output helper (done)

Runner helper for script authors to generate PDFs.

- Helper: `runner/pdf_helper.py` (`save_as_pdf(html, output_dir, filename)`)
- Safe errors: `runner/tool_errors.py` (`ToolUserError` shows message, no traceback)
- Dockerfile: copies `runner/` to `/runner/` so scripts can import
- Docs: `docs/reference/ref-ai-script-generation-kb.md`

### ST-12-03 Personalized tool settings (done)

Per-user settings stored in tool_sessions, injected to runner as `memory.json`.

- Schema: `settings_schema` on tool_versions (JSON array of UiActionField)
- API: `GET/PATCH /api/v1/tools/{id}/settings`
- Runner: `SKRIPTOTEKET_MEMORY_PATH` env var points to `memory.json`
- SPA: `ToolRunSettingsPanel.vue`, `useToolSettings.ts`
- Editor: settings schema textarea in ScriptEditorView

### ST-13-01 Toast system primitives (done)

Consolidated toast feedback system (SPA) + docs-as-code artifacts.

- ADR/Backlog/Ref: `docs/adr/adr-0037-toast-and-system-messages-spa.md`, `docs/backlog/epics/epic-13-toast-and-system-messages.md`,
  `docs/backlog/stories/story-13-01-toast-system-primitives-spa.md`, `docs/reference/ref-toast-system-messages.md`
- ADR: flipped ADR-0037 to `status: accepted`
- Store + API: `frontend/apps/skriptoteket/src/stores/toast.ts`, `frontend/apps/skriptoteket/src/composables/useToast.ts`
- Host: `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue` mounted in `frontend/apps/skriptoteket/src/App.vue`
- CSS primitives + transitions: `frontend/apps/skriptoteket/src/assets/main.css`
- UI smoke script updated for login modal: `scripts/playwright_ui_smoke.py`

### ST-13-02 Replace inline action feedback with toasts (done)

Migrated key flows to `useToast()` for transient action feedback (keep blocking/validation errors inline).

- Admin tools publish/depublish: `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue`
- Admin create draft tool: `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue` (toast “Verktyg skapat.”)
- Suggestions submit/decide: `frontend/apps/skriptoteket/src/views/SuggestionNewView.vue`,
  `frontend/apps/skriptoteket/src/views/admin/AdminSuggestionDetailView.vue`
- Tool settings save: `frontend/apps/skriptoteket/src/composables/tools/useToolSettings.ts`,
  `frontend/apps/skriptoteket/src/components/tool-run/ToolRunSettingsPanel.vue`
- Editor save + workflow success toasts (workflow failures remain inline): `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`,
  `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.ts`,
  `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
- Editor taxonomy/maintainers updates: `frontend/apps/skriptoteket/src/composables/editor/useToolTaxonomy.ts`,
  `frontend/apps/skriptoteket/src/composables/editor/useToolMaintainers.ts`

### ST-13-03 Standardize inline system messages (done)

Added shared inline “system message” component + CSS primitives and migrated blocking/long-lived messages (Scope A).

- Component: `frontend/apps/skriptoteket/src/components/ui/SystemMessage.vue` (variants + close “×”)
- Styling primitives: `frontend/apps/skriptoteket/src/assets/main.css` (`.system-message*`)
- Migrations (examples): `frontend/apps/skriptoteket/src/components/auth/LoginModal.vue`,
  `frontend/apps/skriptoteket/src/components/editor/WorkflowActionModal.vue`,
  `frontend/apps/skriptoteket/src/views/ToolRunView.vue`
- Docs status: set EPIC-13 + ST-13-02 + ST-13-03 to `done` in `docs/backlog/`

### ST-13-04 Toastify profile actions (done)

Replace ProfileView inline success banners with toasts; standardize inline errors to `SystemMessage`.

- View: `frontend/apps/skriptoteket/src/views/ProfileView.vue`
- Docs status: set ST-13-04 + EPIC-13 to `done` in `docs/backlog/`

### EPIC-14 Admin tool authoring (ST-14-01 + ST-14-02) (done)

Admin quick-create of draft tools + URL-namn lifecycle (ADR-0037).

- **Backend**
  - Create draft tool: `POST /api/v1/admin/tools` (admin+CSRF) in `src/skriptoteket/web/api/v1/admin_tools.py`
    → creates `Tool(id, slug=draft-<tool_id>, title, summary, owner=admin, maintainer=admin)` via
    `src/skriptoteket/application/catalog/handlers/create_draft_tool.py`
  - URL-namn edit (unpublished only): `PATCH /api/v1/editor/tools/{tool_id}/slug` (admin+CSRF) in
    `src/skriptoteket/web/api/v1/editor.py` + handler `src/skriptoteket/application/catalog/handlers/update_tool_slug.py`
  - Publish guards: `src/skriptoteket/application/catalog/handlers/publish_tool.py`
    (requires active version + URL-namn not `draft-*` + valid + taxonomy present via `tools.list_tag_ids`)
  - IMPORTANT: `PublishVersionHandler` no longer auto-publishes the tool; tool publish is gated via admin publish
    (`src/skriptoteket/application/scripting/handlers/publish_version.py`)
  - Suggestion accept placeholder unified: `draft-<tool_id>` in `src/skriptoteket/application/suggestions/handlers/decide_suggestion.py`
- **SPA**
  - Admin tools list create flow: `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue` +
    modal `frontend/apps/skriptoteket/src/components/admin/CreateDraftToolModal.vue`
  - Editor metadata drawer: “URL-namn” field + “Använd nuvarande titel” helper in
    `frontend/apps/skriptoteket/src/components/editor/MetadataDrawer.vue` + logic in
    `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`
  - Refactor: keep Vue files <500 LOC by extracting panel 2 into
    `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- **Copy**
  - UI says “URL-namn” (not “slug”) everywhere in admin/editor flows.

## Verification

- Docs: `pdm run docs-validate` (pass)
- Types: `pnpm -C frontend --filter @skriptoteket/spa typecheck` (pass)
- Lint: `pnpm -C frontend --filter @skriptoteket/spa lint` (pass)
- UI: `docker compose up -d db && pdm run db-upgrade`, then `pdm run dev` + `pdm run fe-dev`, then `pdm run ui-smoke --base-url http://127.0.0.1:5173` (pass; screenshots in `.artifacts/ui-smoke/`)
- UI (editor): `pdm run ui-editor-smoke --base-url http://127.0.0.1:5173` (pass; screenshots in `.artifacts/ui-editor-smoke/`)
 - EPIC-14 FE: `pdm run fe-type-check` (pass), `pdm run fe-lint` (pass)
 - EPIC-14 BE: `pdm run pytest -q tests/unit/application/test_scripting_review_handlers.py` (pass)
 - EPIC-14 live: `docker compose up -d db && pdm run db-upgrade`, then `pdm run dev` + `pdm run fe-dev`
  - EPIC-14 functional (API): verified create draft tool, URL-namn edit validation, publish guards (placeholder/taxonomy),
   and URL-namn immutability post-publish via authenticated `httpx` calls against `http://127.0.0.1:8000`
- Playwright (ST-14): `pdm run python -m scripts.playwright_st_14_admin_tool_authoring_e2e --base-url http://127.0.0.1:5173` (pass; screenshots in `.artifacts/st-14-admin-tool-authoring/`)
- Playwright note (Codex): if you run Playwright escalated, run `pdm run dev` + `pdm run fe-dev` escalated too (same “world”); otherwise Playwright may get `ERR_CONNECTION_REFUSED` to `http://127.0.0.1:5173`.

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000
pdm run fe-dev              # SPA 127.0.0.1:5173

# Quality gates
pdm run precommit-run

# Playwright e2e
pdm run python -m scripts.playwright_st_08_13_tool_usage_instructions_e2e --base-url http://127.0.0.1:5173
```

## Known Issues / Risks

- `vega_lite` restrictions not implemented; do not render until restrictions exist (ADR-0024)
- **Rule**: All Vue files must be <500 LoC. Use composables for logic, components for UI.

## Next Steps

- ST-08-10: Implement script editor intelligence (Lezer integration)
- EPIC-12: Continue SPA UX stories
- EPIC-14 (done): Admin tool authoring (quick-create drafts + URL-namn lifecycle) — PRD `docs/prd/prd-tool-authoring-v0.1.md`, ADR `docs/adr/adr-0037-tool-slug-lifecycle.md`, stories `docs/backlog/stories/story-14-01-admin-quick-create-draft-tools.md` + `docs/backlog/stories/story-14-02-draft-slug-edit-and-publish-guards.md`
