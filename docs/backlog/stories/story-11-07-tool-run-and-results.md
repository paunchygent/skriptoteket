---
type: story
id: ST-11-07
title: "Tool run + results (uploads, artifacts, typed outputs)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user visits /tools/:slug/run, when uploading one or more files and submitting, then the tool executes and the SPA navigates to a run result view"
  - "Given a run has artifacts and typed ui_payload outputs, when viewing results, then the SPA renders outputs and allows artifact downloads"
ui_impact: "Moves the main tool execution flow into the SPA and reuses the typed UI contract components."
dependencies: ["ADR-0022", "ADR-0024", "ADR-0031", "ST-11-04", "ST-11-05", "ST-12-01"]
---

## Context

Tool execution and results are the highest-value user flow and must work reliably with multipart uploads and artifact
downloads.

## Implementation (SPA)

### Backend API (v1)

- Tool metadata: `GET /api/v1/tools/{slug}`
  - Response: `ToolMetadataResponse` (id, slug, title, summary) + `upload_constraints` from `Settings`
  - File: `src/skriptoteket/web/api/v1/tools.py`
- Tool execution (multipart): `POST /api/v1/tools/{slug}/run`
  - Accepts `files[]` (multipart, multiple)
  - Executes via `RunActiveToolCommand` and returns `StartToolRunResponse { run_id }`
  - File: `src/skriptoteket/web/api/v1/tools.py`
- Run details extended for UI: `GET /api/v1/runs/{run_id}` now includes `error_summary` in `RunDetails`
  - Files: `src/skriptoteket/application/scripting/interactive_tools.py`,
    `src/skriptoteket/application/scripting/handlers/get_tool_run.py`

After API changes, regenerate TypeScript OpenAPI types:

- `pdm run fe-gen-api-types` (writes `frontend/apps/skriptoteket/src/api/openapi.d.ts`)

### Frontend (Vue/Vite SPA)

- Output renderers (typed outputs, reusable): `frontend/apps/skriptoteket/src/components/ui-outputs/`
  - `UiOutputRenderer.vue` dispatches by `output.kind` (no template switch)
  - Per-kind components: `notice`, `markdown`, `table`, `json`, `html_sandboxed` (+ placeholder `vega_lite`)
- Action rendering (typed next_actions, reusable): `frontend/apps/skriptoteket/src/components/ui-actions/`
  - `UiActionForm.vue` (no API calls; emits `{ actionId, input }`)
  - `UiActionFieldRenderer.vue` dispatches by `field.kind` (no template switch)
  - Per-kind field components: `string`, `text`, `integer`, `number`, `boolean`, `enum`, `multi_enum`
- New views:
  - `frontend/apps/skriptoteket/src/views/ToolRunFormView.vue` (`/tools/:slug/run`)
  - `frontend/apps/skriptoteket/src/views/ToolRunResultView.vue` (`/tools/:slug/runs/:runId`)
- Routes:
  - `frontend/apps/skriptoteket/src/router/routes.ts`
  - `frontend/apps/skriptoteket/src/views/BrowseToolsView.vue` links to tool-run via `RouterLink`

### Route cutover (SSR → SPA)

- `/login`, `/browse`, and `/tools/:slug/run` are now served by the SPA (SSR handlers removed / unregistered).
- Legacy SSR `POST /tools/interactive/start_action` remains for now (used by SSR my-runs/apps views).

### Verification

- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pnpm -C frontend --filter @skriptoteket/spa typecheck`
- `pnpm -C frontend --filter @skriptoteket/spa lint`
- `pnpm -C frontend --filter @skriptoteket/spa build`
- Live check: `curl -s http://127.0.0.1:8000/login | head`, `curl -s http://127.0.0.1:8000/browse | head`, `curl -s http://127.0.0.1:8000/tools/does-not-matter/run | head`
- Live flow (2025-12-22): seeded + ran tool `demo-next-actions` end-to-end (upload → results → artifact download → `next_actions` loop via `Nollställ` then `Nästa steg` until no actions).
