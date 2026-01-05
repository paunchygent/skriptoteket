# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-05
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: ST-14-01/14-02 done; ST-14-09 done; ST-14-10 done; ST-14-13/14 done; ST-14-15 done; ST-14-16 done

## Current Session (2026-01-05)

- ST-14-17 (Phase 5): added Vitest coverage for virtual file canon, unified patch invariants, and minimal compare-state query handling.
  - Tests: `frontend/apps/skriptoteket/src/composables/editor/virtualFiles.spec.ts`, `frontend/apps/skriptoteket/src/composables/editor/diff/unifiedPatch.spec.ts`
  - Tests: `frontend/apps/skriptoteket/src/composables/editor/editorRouteKey.spec.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorCompareState.spec.ts`
  - Test harness fixes: add `params: {}` to mocked routes in `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.spec.ts` and `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.spec.ts`.
  - Adjusted `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.spec.ts` to assert close-on-version navigation (align with `editorBaseRouteKey`).
  - Lint cleanup (no behavior change): removed unused eslint-disable directives in `frontend/apps/skriptoteket/src/composables/editor/useEditorCompareState.ts`, `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`, `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.ts`.
- DevOps: investigated recurrent host hard hangs on `hemma` (RDNA4 R9700 + kernel/ROCm/amdgpu) and applied mitigations for the “silent wedge” pattern.
  - Disabled Tabby for Vulkan-only isolation (Tabby `Wants=llama-server.service` can start ROCm/KFD llama on boot).
  - Added boot-persistent runtime-PM clamp: `/etc/systemd/system/amdgpu-force-active.service` (forces `/sys/class/drm/card1/device/power/control=on`).
  - Captured `llama-bench` baseline (Vulkan): `pp512 366.65 t/s`, `tg128 19.97 t/s` (build `0f89d2ecf`); report updated.
  - Canonical output-quality A/B (HTTP chat review+diff): Devstral produced a usable patch; Qwen3-Coder (Q4_K_M) produced a non-usable patch even at `temperature=0.1`; reverted `llama-server-vulkan.service` back to Devstral. Artifacts: `docs/reference/reports/artifacts/llama-canonical-chat-v3/`.
  - Updated report: `docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md`
- ST-14-16 (done): Backend schema validation UX (render issues + block Save/Run when parseable-but-invalid).
  - Composable: `frontend/apps/skriptoteket/src/composables/editor/useEditorSchemaValidation.ts`
  - Wire-up: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`, `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`
  - Rendering: `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- Editor SRP refactor: split oversized editor UI modules to keep files <500 LOC (no behavior changes).
  - `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue` -> extracted panels/toolbars/drawers
  - `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` -> header extracted + reduced prop wiring via `v-model:*`
  - `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue` -> session-files composable + settings card component
- Editor SRP refactor (continued): extracted drawers/guards + sandbox runner logic into composables (reduce view/component to wiring).
  - New: `frontend/apps/skriptoteket/src/composables/editor/useUnsavedChangesGuards.ts`, `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.ts`
  - New: `frontend/apps/skriptoteket/src/composables/editor/useEditorSandboxRunExecution.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorSandboxActions.ts`
  - Wire-up: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, `frontend/apps/skriptoteket/src/components/editor/SandboxRunner.vue`
- ST-14-13/14 (done): CodeMirror JSON editors for `settings_schema` + `input_schema` with JSON lint markers + summary, preset guidance, prettify, and snippet insertion.
  - UI: `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
  - Editor config: `frontend/apps/skriptoteket/src/composables/editor/schemaJsonEditor.ts`
  - Parse details: `frontend/apps/skriptoteket/src/composables/editor/schemaJsonHelpers.ts`
  - CodeMirror overrides: `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`
- Editor AI planning: tightened story acceptance criteria and added a backend slice for separate chat vs ops endpoints/profiles.
  - Updated: `docs/backlog/stories/story-08-20-editor-ai-chat-drawer-mvp.md`, `docs/backlog/stories/story-08-21-ai-structured-crud-edit-ops-protocol-v1.md`, `docs/backlog/stories/story-08-22-editor-ai-diff-preview-apply-undo.md`
  - Added: `docs/backlog/stories/story-08-23-ai-chat-streaming-proxy-and-config.md`
  - Updated index: `docs/index.md`, `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- Epic 14 planning: updated diff/compare specs and added a working-copy persistence story (IndexedDB) to support diff + AI workflows.
  - Updated: `docs/backlog/stories/story-14-17-editor-version-diff-view.md`, `docs/backlog/stories/story-14-18-editor-review-navigation-and-compare.md`
  - Added: `docs/backlog/stories/story-14-30-editor-working-copy-persistence-indexeddb.md`
  - Added: `docs/backlog/stories/story-14-31-editor-focus-mode-collapse-sidebar.md`
  - Updated: `docs/backlog/epics/epic-14-admin-tool-authoring.md`, `docs/index.md`
- ST-14-15: reviewed implementation (endpoint + handler + tests) and marked story done.

## Verification

- Frontend OpenAPI types: `pdm run fe-gen-api-types` (pass)
- Frontend tests: `pdm run fe-test` (pass)
- Frontend lint: `pdm run fe-lint` (pass)
- Frontend typecheck: `pdm run fe-type-check` (pass)
- Frontend build: `pdm run fe-build` (pass)
- Docs validate: `pdm run docs-validate` (pass)
- Backend unit tests (ST-14-15): `pdm run pytest tests/unit/application/scripting/handlers/test_validate_tool_schemas_handler.py -q` (pass)
- Live check (dev containers): `curl -sSf http://127.0.0.1:5173/ | head -n 5` (SPA HTML served)
- Live check (dev backend): `curl -sSf http://127.0.0.1:8000/healthz`
- Script run (yrkesgenerator PDF): `pdm run python -c "import json,os,sys,tempfile; from importlib.util import module_from_spec,spec_from_file_location; from pathlib import Path; sys.path.insert(0,'runner'); spec=spec_from_file_location('yrkesgenerator','src/skriptoteket/script_bank/scripts/yrkesgenerator.py'); module=module_from_spec(spec); spec.loader.exec_module(module); tmp=tempfile.TemporaryDirectory(); input_dir=Path(tmp.name)/'input'; output_dir=Path(tmp.name)/'output'; input_dir.mkdir(parents=True, exist_ok=True); (input_dir/'action.json').write_text(json.dumps({'action_id':'pdf','input':{},'state':{}})); os.environ['SKRIPTOTEKET_INPUTS']=json.dumps({'full_name':'Test Person'}); module.run_tool(str(input_dir), str(output_dir)); print([p.name for p in output_dir.glob('*.pdf')]); tmp.cleanup()"` (generated `yrkesdiplom_Test_Person.pdf`; fontconfig cache warnings)
- Live check (Playwright, escalated): `BASE_URL=http://127.0.0.1:5173 pdm run python -m scripts.playwright_st_14_16_editor_schema_validation_errors_ux_e2e` (pass; artifacts: `.artifacts/st-14-16-editor-schema-validation-errors-ux-e2e/`)
- Hemma: `ssh hemma "sudo systemctl status --no-pager amdgpu-force-active.service"` (active/exited; SUCCESS)
- Hemma: `ssh hemma "sudo sh -c 'cat /sys/class/drm/card1/device/power/control; cat /sys/class/drm/card1/device/power/runtime_status'"` (`on` / `active`)
- Hemma: `ssh hemma "curl -s http://127.0.0.1:8082/v1/models | jq -r '.data[0].id'"` (confirm served model)
- Hemma: `ssh hemma "/home/paunchygent/llama.cpp/build-vulkan/bin/llama-bench -m /home/paunchygent/models/Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf -p 512 -n 128 -r 1 --no-warmup -t 8 -ngl 99 -dev Vulkan0 -o md"` (baseline)

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
- AI inference (hemma): Vulkan-only trial is currently enforced by disabling `tabby.service` + clamping GPU runtime-PM to `control=on` via `amdgpu-force-active.service`.
- Prompt budgeting is a conservative char→token approximation; rare over-budget cases can still happen and return empty completion/suggestion (see `docs/reference/reports/ref-ai-edit-suggestions-kb-context-budget-blocker.md`).
- Dev UI uses Vite proxy to `127.0.0.1:8000` (host backend); check the `pdm run dev` terminal for errors, not `docker logs`, unless the UI is pointed at the container port directly.

## Next Steps

- ST-14-17/18: implement full-width compare + diff viewer primitive (incl before/after + unified patch downloads, and correct default compare targets).
- ST-14-31: implement Focus mode (collapse left sidebar) to maximize editor/diff width on desktop.
- ST-14-30: implement IndexedDB working copy persistence + rolling checkpoints + restore UX.
- Follow-up (EPIC-08): key chat history by tool id (not version id) so saves don’t silently reset conversations.
